"""외부 문서 수집: 검색어 추출 → 후보 선별 → 본문 수집 → 색인 (F2003, F2004, F2005).

LangGraph 바깥에서 질문마다 먼저 실행한다. 이미 수집한 '포켓몬ID|검색어'는 다시 수집하지 않는다 (NF2002).
"""
import json
import threading
from datetime import date
from typing import Callable

from data_prep import wiki_source
from data_prep.build_item_text import item_text, pokemon_by_id
from rag import prompts
from services.config import settings
from services.http import UpstreamError
from services.llm import ask_llm
from services.log import get_logger
from store.indexer import FREE_ID, index_wiki_page, owner_key

log = get_logger("collector")
REGISTRY = settings.path("cache", "collected_queries.json")
_lock = threading.Lock()

Progress = Callable[[str, str, object], None]


def _noop(step: str, message: str, detail: object = None) -> None:
    pass


def load_registry() -> dict:
    """수집 기록. {"queries": {"6|리자몽": {...}}, "docs": {"6": {"122681": {...}}}}"""
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {"queries": {}, "docs": {}}


def save_registry(reg: dict) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")


def collected_titles(pokemon_id: int | None) -> list[str]:
    """지금까지 이 포켓몬(None이면 자유 질문)을 위해 모은 위키 문서 제목 목록."""
    owner = owner_key(FREE_ID if pokemon_id is None else pokemon_id)
    docs = load_registry()["docs"].get(owner, {})
    return [d["title"] for d in docs.values()]


# F2003 — 프롬프트 1로 검색어를 뽑는다. 포켓몬 이름은 결과와 상관없이 맨 앞에.
# p가 None(자유 질문)이면 자유 질문용 프롬프트를 쓰고, 읽지 못하면 질문 자체를 검색어로 쓴다.
def extract_queries(p: dict | None, question: str) -> list[str]:
    limit = int(settings["collect"]["max_queries"])
    if p is None:
        prompt = prompts.KEYWORDS_FREE.format(max_queries=limit, question=question)
        raw = prompts.ask_json_array(prompt, ask_llm) or [question[:40]]
        queries: list[str] = []
    else:
        prompt = prompts.KEYWORDS.format(max_queries=limit, name_ko=p["name_ko"],
                                         item_text=item_text(p), question=question)
        raw = prompts.ask_json_array(prompt, ask_llm) or []
        queries = [p["name_ko"]]
    for q in raw:
        q = str(q).strip()
        if q and q not in queries:
            queries.append(q)
    return queries[:limit]


# F2004 — 프롬프트 2로 후보 중 색인할 문서를 고른다
def select_candidates(name_ko: str | None, question: str, candidates: list[dict]) -> list[int] | None:
    """고른 후보 번호 목록. LLM 응답을 읽지 못하면 None. name_ko가 None이면 자유 질문."""
    if not candidates:
        return []
    lines = [f"{i}. {c['title']} — {c.get('summary', '')}" for i, c in enumerate(candidates)]
    focus = prompts.SELECT_FOCUS_FREE if name_ko is None else prompts.SELECT_FOCUS.format(name_ko=name_ko)
    prompt = prompts.SELECT.format(focus_rules=focus, max_docs=int(settings["collect"]["max_docs_per_question"]),
                                   question=question, numbered_candidates="\n".join(lines))
    picked = prompts.ask_json_array(prompt, ask_llm)
    if picked is None:
        return None
    return [int(i) for i in picked if str(i).lstrip("-").isdigit() and 0 <= int(i) < len(candidates)]


def collect(pokemon_id: int | None, question: str, on_progress: Progress = _noop) -> dict:
    """질문 하나에 필요한 위키 문서를 모아 색인한다. 화면에 보여줄 수집 결과를 돌려준다.
    pokemon_id가 None이면 자유 질문: 문서는 'free' 주인으로 따로 저장되어 포켓몬별 검색에 섞이지 않는다."""
    p = pokemon_by_id(pokemon_id) if pokemon_id is not None else None
    owner_id = pokemon_id if pokemon_id is not None else FREE_ID
    owner = owner_key(owner_id)
    result = {"queries": [], "indexed": [], "skipped": [], "cached": [], "failed": []}

    on_progress("keywords", "찾아볼 단어를 고르고 있어요", None)
    queries = extract_queries(p, question)
    result["queries"] = queries
    on_progress("keywords", "찾아볼 단어: " + ", ".join(queries), queries)

    with _lock:
        reg = load_registry()
    have_docs = reg["docs"].setdefault(owner, {})
    new_queries = []
    for q in queries:
        if f"{owner}|{q}" in reg["queries"]:
            result["cached"].append(q)
        else:
            new_queries.append(q)
    if not new_queries:
        on_progress("collect", "예전에 모아 둔 자료를 다시 펼쳤어요", result)
        return result

    on_progress("collect", "위키백과를 뒤적이는 중…", None)
    per_query = int(settings["collect"]["candidates_per_query"])
    candidates: list[dict] = []
    seen: set[int] = set(int(k) for k in have_docs)
    item_page_id = None
    try:
        # F2004 — 선택한 포켓몬 자체를 다룬 문서는 어떤 제외 규칙보다 먼저, 항상 포함
        if p and p["name_ko"] in new_queries:
            item_page, reason = wiki_source.find_item_page(p["name_ko"])
            if item_page:
                item_page_id = item_page["pageid"]
                if item_page_id not in seen:
                    candidates.append({**item_page, "query": p["name_ko"], "forced": True})
                    seen.add(item_page_id)
            else:
                result["skipped"].append({"title": p["name_ko"], "reason": reason})
        for q in new_queries:
            for c in wiki_source.search(q, per_query):
                if c["pageid"] in seen:
                    continue
                seen.add(c["pageid"])
                if wiki_source.is_list_page(c["title"]):  # 표뿐인 목록 문서는 선별 전에 뺀다
                    result["skipped"].append({"title": c["title"], "reason": "표로 된 목록 문서"})
                    continue
                candidates.append({**c, "query": q})
        sums = wiki_source.summaries([c["pageid"] for c in candidates][:20])
    except UpstreamError:
        log.exception("위키백과 검색 실패")
        result["failed"].append("위키백과 검색")
        on_progress("collect", "자료실 연결이 잠시 불안정해요", result)
        return result

    for c in candidates:
        c["summary"] = sums.get(c["pageid"], {}).get("text", "")
    optional = []
    for c in candidates:
        if c.get("forced"):
            continue
        if sums.get(c["pageid"], {}).get("disambiguation"):  # 동음이의어 문서는 선별 전에 뺀다
            result["skipped"].append({"title": c["title"], "reason": "동음이의어 문서"})
            continue
        optional.append(c)
    picked = select_candidates(p["name_ko"] if p else None, question, optional)
    if picked is None:  # 선별 응답을 못 읽으면: 포켓몬 이름과 같은 제목 문서만 (자유 질문이면 없음)
        picked = [i for i, c in enumerate(optional) if p and c["title"] == p["name_ko"]]
    chosen = [c for c in candidates if c.get("forced")] + [optional[i] for i in picked]
    chosen_ids = {c["pageid"] for c in chosen}
    for c in optional:
        if c["pageid"] not in chosen_ids:
            result["skipped"].append({"title": c["title"], "reason": "질문과 관련이 적어 고르지 않음"})

    min_chars = int(settings["collect"]["min_doc_chars"])
    for c in chosen:
        try:
            page = wiki_source.fetch_page(c["pageid"])
        except UpstreamError:
            result["failed"].append(c["title"])
            continue
        if len(page["text"]) < min_chars and c["pageid"] != item_page_id:
            result["skipped"].append({"title": c["title"], "reason": "본문이 너무 짧음"})
            continue
        n = index_wiki_page(owner_id, p["name_ko"] if p else "", page, c["query"])
        have_docs[str(c["pageid"])] = {"title": page["title"], "query": c["query"], "chunks": n}
        result["indexed"].append(page["title"])

    today = date.today().isoformat()
    with _lock:
        latest = load_registry()
        latest["docs"].setdefault(owner, {}).update(have_docs)
        for q in new_queries:
            latest["queries"][f"{owner}|{q}"] = {"at": today}
        save_registry(latest)

    if result["indexed"]:
        names = ", ".join(f"「{t}」" for t in result["indexed"])
        on_progress("collect", f"{names}을 노트에 붙였어요", result)
    else:
        on_progress("collect", "새로 붙일 문서는 없었어요", result)
    return result
