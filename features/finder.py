"""조건 기반 탐색 — "이런 포켓몬 찾아줘" (F2011).

① 규칙 필터(타입·전설·숫자) → ② 필터를 건 채 의미 검색으로 후보 → ③ 프롬프트 C로 조건을 모두 만족하는 것만 선별
"""
from data_prep.build_item_text import pokemon_by_id
from data_prep.finder_terms import parse_condition
from data_prep.sprites import sprite_urls
from rag import prompts
from services.config import settings
from services.errors import ServiceError
from services.http import UpstreamError, with_retry
from services.llm import ApiKeyMissing, ask_llm
from store.vector_store import META, count, get_store

EMPTY_MESSAGE = "조건에 맞는 포켓몬을 찾지 못했어요. 조건을 하나 줄여보세요."


def _card(pid: int, reason: str, unsure: bool = False) -> dict:
    """탐색 결과 카드 1장. 근거는 그 포켓몬의 도감 데이터."""
    p = pokemon_by_id(pid)
    return {
        "id": pid,
        "dex_no": p["dex_no"],
        "name_ko": p["name_ko"],
        "types": p["types"],
        "reason": reason,
        "unsure": unsure,
        "sprite": sprite_urls(pid),
        "citation": {"title": f"{p['name_ko']} · PokéAPI 도감", "source_type": "meta",
                     "source_label": "도감 데이터", "url": p["source_url"]},
    }


def find(condition: str) -> dict:
    """자연어 조건으로 포켓몬을 찾는다. 결과: {cards, filters, message}."""
    if not settings.has_api_key():
        raise ServiceError("API_KEY_MISSING")
    if count(META) == 0:
        raise ServiceError("INDEX_EMPTY")

    where, notes = parse_condition(condition)
    k = int(settings["finder"]["candidates"])
    try:
        store = get_store(META)
        docs = with_retry(lambda: store.similarity_search(condition, k=k, filter=where), "조건 검색")
        if not docs:
            return {"cards": [], "filters": notes, "message": EMPTY_MESSAGE}
        lines = [f"{i}. (도감번호 {d.metadata['pokemon_id']})\n{d.page_content}" for i, d in enumerate(docs)]
        prompt = prompts.FINDER.format(condition=condition, numbered_candidates="\n\n".join(lines))
        picked = prompts.ask_json_array(prompt, ask_llm)
    except ApiKeyMissing as e:
        raise ServiceError("API_KEY_MISSING") from e
    except UpstreamError as e:
        raise ServiceError("UPSTREAM_ERROR") from e

    allowed = {int(d.metadata["pokemon_id"]) for d in docs}
    if picked is None:  # 선별 응답을 읽지 못하면: 검색 상위 5마리를 '확인 필요'로
        cards = [_card(int(d.metadata["pokemon_id"]), "조건 일치 여부를 직접 확인해 주세요", True)
                 for d in docs[:5]]
        return {"cards": cards, "filters": notes, "message": ""}

    cards, seen = [], set()
    for item in picked:
        try:
            pid = int(item["id"])
        except (TypeError, KeyError, ValueError):
            continue
        if pid in allowed and pid not in seen:  # 후보 밖 번호는 버린다
            seen.add(pid)
            cards.append(_card(pid, str(item.get("reason", ""))))
    return {"cards": cards, "filters": notes, "message": "" if cards else EMPTY_MESSAGE}
