"""LangGraph retrieve → generate (F2007). 노드는 정확히 두 개.

특화 기능도 같은 그래프를 쓰고, mode 값에 따라 generate 노드가 고르는 프롬프트만 바뀐다.
확인: python -m rag.graph --draw
"""
import argparse
import time
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from data_prep.build_item_text import pokemon_by_id
from rag import citations, prompts
from rag.collector import Progress, _noop, collect
from rag.retriever import evidence_block, retrieve
from services.config import settings
from services.errors import ServiceError
from services.http import UpstreamError
from services.llm import ApiKeyMissing, ask_llm
from services.log import get_logger
from store.vector_store import META, count

log = get_logger("graph")


class RagState(TypedDict, total=False):
    pokemon_id: int
    question: str
    mode: str                  # "chat" | "battle" | "evolution" | "no_rag"
    opponent_id: int | None    # 배틀 상대 포켓몬
    opponent_type: str | None  # 배틀 상대 타입(포켓몬 대신)
    top_k: int | None          # 비교 실험용으로 설정값 대신 쓸 값
    search_type: str | None
    evidence: list[dict]       # retrieve가 채움
    answer: str                # generate가 채움
    citations: list[dict]
    no_citation: bool


def retrieve_node(state: RagState) -> dict:
    """검색 노드: 메타데이터 청크(항상) + 외부 문서 의미 검색 → 번호 붙은 근거."""
    if state.get("mode") == "no_rag":
        return {"evidence": []}
    evidence = retrieve(state["pokemon_id"], state["question"], state.get("mode", "chat"),
                        state.get("opponent_id"), state.get("opponent_type"),
                        state.get("top_k"), state.get("search_type"))
    return {"evidence": evidence}


def _opponent_name(state: RagState) -> str:
    if state.get("opponent_id"):
        return pokemon_by_id(state["opponent_id"])["name_ko"]
    return f"{state.get('opponent_type')} 타입 포켓몬"


def generate_node(state: RagState) -> dict:
    """생성 노드: mode에 맞는 프롬프트로 근거만 써서 답하고, 실제 인용된 근거만 남긴다."""
    mode = state.get("mode", "chat")
    temp = float(settings["llm"]["answer_temperature"])
    if mode == "no_rag":
        answer = ask_llm(prompts.NO_RAG.format(question=state["question"]), temp)
        return {"answer": answer, "citations": [], "no_citation": True}

    block = evidence_block(state["evidence"])
    name = pokemon_by_id(state["pokemon_id"])["name_ko"]
    if mode == "battle":
        prompt = prompts.BATTLE.format(name_ko=name, opponent=_opponent_name(state), evidence_block=block)
    elif mode == "evolution":
        prompt = prompts.EVOLUTION.format(name_ko=name, evidence_block=block)
    else:
        prompt = prompts.ANSWER.format(evidence_block=block, question=state["question"])
    answer = ask_llm(prompt, temp)
    cited, none = citations.extract(answer, state["evidence"])
    return {"answer": answer, "citations": cited, "no_citation": none}


def build_graph():
    graph = StateGraph(RagState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


app = build_graph()


def check_ready(pokemon_id: int) -> None:
    """키·색인·범위를 먼저 확인한다. 문제가 있으면 ServiceError."""
    if not settings.has_api_key():
        raise ServiceError("API_KEY_MISSING")
    if count(META) == 0:
        raise ServiceError("INDEX_EMPTY")
    lo, hi = settings["scope"]["dex_from"], settings["scope"]["dex_to"]
    if not (lo <= int(pokemon_id) <= hi) or pokemon_by_id(int(pokemon_id)) is None:
        raise ServiceError("OUT_OF_SCOPE")


def needs_version_note(evidence: list[dict], cited: list[dict], answer: str) -> bool:
    """세대별 차이가 있는 답이면 '게임 버전에 따라 다를 수 있어요' 안내를 붙인다."""
    used = {c["no"] for c in cited}
    texts = [e["text"] for e in evidence if e["no"] in used]
    return any("세대별 변경" in t or "세대에 추가" in t for t in texts) or "세대" in answer


def run(pokemon_id: int, question: str, mode: str = "chat", on_progress: Progress = _noop,
        do_collect: bool = True, **options) -> dict:
    """질문 하나를 끝까지 처리한다: 수집(그래프 밖) → retrieve → generate."""
    started = time.perf_counter()
    check_ready(pokemon_id)
    collected = {"queries": [], "indexed": [], "skipped": [], "cached": [], "failed": []}
    try:
        if do_collect and mode != "no_rag":
            collected = collect(pokemon_id, question, on_progress)
        on_progress("retrieve", "근거를 찾는 중이에요", None)
        state = {"pokemon_id": int(pokemon_id), "question": question, "mode": mode, **options}
        out: dict = {}
        # 노드가 하나 끝날 때마다 결과를 받아 진행 상태를 알린다
        for update in app.stream(state, stream_mode="updates"):
            if "retrieve" in update:
                out.update(update["retrieve"])
                if mode != "no_rag" and not out["evidence"]:
                    raise ServiceError("NO_RESULTS")
                if mode != "no_rag":
                    on_progress("retrieve", f"근거 {len(out['evidence'])}개를 찾았어요", None)
                on_progress("generate", "기록을 정리하고 있어요", None)
            if "generate" in update:
                out.update(update["generate"])
    except ApiKeyMissing as e:
        raise ServiceError("API_KEY_MISSING") from e
    except UpstreamError as e:
        raise ServiceError("UPSTREAM_ERROR") from e

    elapsed = int((time.perf_counter() - started) * 1000)
    log.info("질문 처리 pokemon=%s mode=%s 근거=%d 인용=%d %dms", pokemon_id, mode,
             len(out.get("evidence", [])), len(out.get("citations", [])), elapsed)
    return {
        "answer": out["answer"],
        "citations": out.get("citations", []),
        "no_citation": out.get("no_citation", True),
        "evidence_count": len(out.get("evidence", [])),
        "version_note": needs_version_note(out.get("evidence", []), out.get("citations", []), out["answer"]),
        "collected": {k: collected[k] for k in ("queries", "indexed", "skipped", "cached", "failed")},
        "elapsed_ms": elapsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG 그래프 확인")
    parser.add_argument("--draw", action="store_true", help="그래프 구조(Mermaid)를 출력")
    args = parser.parse_args()
    if args.draw:
        print(app.get_graph().draw_mermaid())


if __name__ == "__main__":
    main()
