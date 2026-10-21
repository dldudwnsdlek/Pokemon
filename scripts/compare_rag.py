"""F2015 — 대표 질문 Q1~Q6를 RAG 없이 한 번, 근거를 붙여 한 번 답하게 하고 나란히 기록한다.

실행: python -m scripts.compare_rag → docs/rag_comparison.md
'사실 정확성' 판정은 사람이 PokéAPI 데이터와 대조해 채운다. 스크립트는 두 답변과 근거 목록, 데이터 기준 정답까지만 채운다.
"""
from datetime import date

from rag.graph import run
from services.config import settings

# (번호, 포켓몬 ID, 질문, 데이터 기준 정답 — data/*.json에서 확인한 값)
QUESTIONS = [
    ("Q1", 133, "이브이는 1세대에서 무엇으로 진화하고, 조건은 무엇인가?",
     "샤미드(물의돌), 쥬피썬더(천둥의돌), 부스터(불꽃의돌). 에브이·블래키 등은 2세대 이후 추가"),
    ("Q2", 6, "리자몽은 드래곤 타입인가?", "아니다. 불꽃/비행 타입"),
    ("Q3", 94, "고스트 타입 기술은 에스퍼 타입에게 효과가 어떤가?",
     "현재는 효과가 굉장함(2배). 1세대에서는 효과가 없음(0배)"),
    ("Q4", 94, "팬텀은 어떻게 진화하나?", "고오스 → (레벨 25) 고우스트 → (통신교환) 팬텀"),
    ("Q5", 150, "뮤츠의 분류는 무엇인가?", "유전포켓몬 (전설의 포켓몬)"),
    ("Q6", 143, "잠만보의 몸무게는?", "460kg"),
]

UNKNOWN_MARKERS = ["확인되지 않", "알 수 없", "모르", "자료에 없", "정보가 없"]


def says_unknown(text: str) -> str:
    return "예" if any(m in text for m in UNKNOWN_MARKERS) else "아니오"


def cell(text: str) -> str:
    """표 칸 안에 들어가게 줄바꿈과 | 를 바꾼다."""
    return text.replace("|", "\\|").replace("\n", "<br>")


def main() -> None:
    rows, details = [], []
    for qid, pid, question, truth in QUESTIONS:
        print(f"{qid} 처리 중…", flush=True)
        plain = run(pid, question, mode="no_rag")
        rag = run(pid, question, mode="chat")
        cites = "<br>".join(f"[{c['no']}] {c['source_label']} · {c['title']}" for c in rag["citations"]) or "없음"
        rows.append(f"| {qid} | {cell(question)} | {cell(truth)} | {cell(plain['answer'])} | {cell(rag['answer'])} "
                    f"| 없이: ☐맞음 ☐틀림 / RAG: ☐맞음 ☐틀림 "
                    f"| 없이: 없음 / RAG: {len(rag['citations'])}건 "
                    f"| 없이: {says_unknown(plain['answer'])} / RAG: {says_unknown(rag['answer'])} |")
        details.append(f"### {qid}. {question}\n\n- 데이터 기준 정답: {truth}\n- RAG 근거 목록:<br>{cites}\n"
                       f"- 처리 시간: RAG 없이 {plain['elapsed_ms']}ms / RAG {rag['elapsed_ms']}ms\n")

    doc = [
        "# RAG 사용 전후 답변 비교 (F2015)",
        "",
        f"- 생성일: {date.today().isoformat()} · 채팅 모델: {settings['llm']['chat_model']} · "
        f"청크 {settings['chunk']['size']}/{settings['chunk']['overlap']} · Top-k {settings['retrieval']['top_k']} · "
        f"검색 방식 {settings['retrieval']['search_type']}",
        "- 비교 기준: ① 사실 정확성(사람이 데이터와 대조해 체크) ② 근거 제시 여부 ③ 모르는 것을 모른다고 답하는지",
        "",
        "| # | 질문 | 데이터 기준 정답 | RAG 없이 답변 | RAG 답변 | 사실 정확성 | 근거 제시 | 모르면 모른다고 하나 |",
        "|---|---|---|---|---|---|---|---|",
        *rows,
        "",
        "## 질문별 근거",
        "",
        *details,
        "## 정리 (사람이 작성)",
        "",
        "- RAG 없이 틀린 질문:",
        "- RAG로 바로잡힌 질문:",
        "- RAG로도 부족했던 점과 원인:",
    ]
    out = settings.path("docs", "rag_comparison.md")
    out.write_text("\n".join(doc) + "\n", encoding="utf-8")
    print(f"저장: docs/{out.name}")


if __name__ == "__main__":
    main()
