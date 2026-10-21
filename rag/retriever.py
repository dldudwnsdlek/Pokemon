"""두 컬렉션 검색·병합·중복 제거 → 번호 붙은 근거 목록 (F2006, F2014)."""
import json
import re
from functools import lru_cache

from data_prep.build_item_text import pokemon_by_id
from services.config import settings
from services.http import with_retry
from store.indexer import SHARED_ID, doc_chunk_id, meta_chunk_id, owner_key
from store.vector_store import DOCS, META, get_by_ids, get_store

SOURCE_LABEL = {"meta": "도감 데이터", "wikipedia": "위키백과", "pokeapi": "PokéAPI 자료"}
PROMPT_LABEL = {"meta": "포켓몬 도감 데이터", "wikipedia": "위키백과", "pokeapi": "PokéAPI 자료"}


@lru_cache(maxsize=1)
def type_en_by_ko() -> dict[str, str]:
    """'불꽃' → 'fire' (구조화 타입 문서 ID를 만들 때)."""
    docs = json.loads(settings.path("data", "type_docs.json").read_text(encoding="utf-8"))
    return {d["type_ko"]: d["type_en"] for d in docs}


def _chunk(item_id: str, text: str, meta: dict) -> dict:
    return {"id": item_id, "text": text, "metadata": meta}


def _id_from_meta(meta: dict) -> str:
    """검색 결과의 메타데이터로 청크 ID를 다시 만든다."""
    if meta.get("source_type") == "meta":
        return meta_chunk_id(meta["pokemon_id"])
    return doc_chunk_id(owner_key(meta["pokemon_id"]), meta["doc_id"], meta.get("chunk_index", 0))


def forced_ids(pokemon_id: int | None, mode: str, opponent_id: int | None = None,
               opponent_type: str | None = None, extra_ids: list[int] | None = None) -> list[tuple[str, str]]:
    """검색 없이 항상 넣을 청크 (컬렉션, ID). 1번은 항상 선택한 포켓몬의 메타데이터.
    자유 질문(pokemon_id=None)이면 항상 넣을 것이 없다. extra_ids: 질문에 함께 나온 다른 포켓몬."""
    if pokemon_id is None:
        return []
    ids = [(META, meta_chunk_id(pokemon_id))]
    ids += [(META, meta_chunk_id(e)) for e in extra_ids or [] if e != pokemon_id]
    if mode == "battle":
        # 배틀: 내 것 + 상대 것 메타데이터, 두 쪽 타입의 상성 문서
        types = list(pokemon_by_id(pokemon_id)["types"])
        if opponent_id:
            ids.append((META, meta_chunk_id(opponent_id)))
            types += pokemon_by_id(opponent_id)["types"]
        if opponent_type:
            types.append(opponent_type)
        en = type_en_by_ko()
        for t in dict.fromkeys(types):
            if t in en:
                ids.append((DOCS, doc_chunk_id("shared", f"type-{en[t]}", 0)))
    if mode == "evolution":
        chain = pokemon_by_id(pokemon_id)["evolution_chain_id"]
        ids.append((DOCS, doc_chunk_id("shared", f"evo-{chain}", 0)))
    return ids


def search_docs(pokemon_id: int | None, question: str, top_k: int, search_type: str,
                extra_ids: list[int] | None = None, collection: str = DOCS) -> list[dict]:
    """질문과 가까운 청크를 찾는다.
    범위: 그 포켓몬(+질문에 함께 나온 포켓몬) 문서 + 공용(0) 문서. 자유 질문이면 범위 제한 없음."""
    store = get_store(collection)
    if pokemon_id is None:
        where = None
    else:
        owners = [pokemon_id, *(extra_ids or []), SHARED_ID]
        where = {"$or": [{"pokemon_id": o} for o in dict.fromkeys(owners)]}
    if search_type == "mmr":
        # F2014 — 넉넉히 가져온 뒤(fetch_k) 다양성을 고려해 top_k개를 고른다
        docs = with_retry(lambda: store.max_marginal_relevance_search(
            question, k=top_k, fetch_k=int(settings["retrieval"]["mmr_fetch_k"]),
            lambda_mult=float(settings["retrieval"]["mmr_lambda"]), filter=where), "MMR 검색")
    else:
        docs = with_retry(lambda: store.similarity_search(question, k=top_k, filter=where), "유사도 검색")
    return [_chunk(_id_from_meta(d.metadata), d.page_content, d.metadata) for d in docs]


def _body(text: str) -> str:
    """청크 앞의 '[문서: 제목]' 줄을 뺀 본문."""
    return re.sub(r"^\[문서: [^\]]*\]\n", "", text)


def merge(chunks: list[dict]) -> list[dict]:
    """중복 제거: ① 같은 청크 ID는 하나만 ② 본문 앞 N자가 같은 청크는 하나만."""
    n = int(settings["retrieval"]["dedup_prefix_chars"])
    seen_ids, seen_prefix, out = set(), set(), []
    for c in chunks:
        prefix = _body(c["text"])[:n]
        if c["id"] in seen_ids or prefix in seen_prefix:
            continue
        seen_ids.add(c["id"])
        seen_prefix.add(prefix)
        out.append(c)
    return out


def number(chunks: list[dict]) -> list[dict]:
    """순서대로 [근거 1], [근거 2] … 번호를 붙이고 화면용 정보를 채운다."""
    out = []
    for i, c in enumerate(chunks, start=1):
        m = c["metadata"]
        st = m.get("source_type", "wikipedia")
        out.append({
            "no": i,
            "id": c["id"],
            "text": c["text"],
            "source_type": st,
            "source_label": SOURCE_LABEL.get(st, st),
            "title": m.get("source_title", ""),
            "url": m.get("source_url", ""),
            "related": m.get("related_names", m.get("name_ko", "")),
        })
    return out


# F2006 — 메타데이터 청크는 항상 + 외부 문서는 의미 검색 → 병합·중복 제거 → 번호
def retrieve(pokemon_id: int | None, question: str, mode: str = "chat", opponent_id: int | None = None,
             opponent_type: str | None = None, top_k: int | None = None,
             search_type: str | None = None, extra_ids: list[int] | None = None) -> list[dict]:
    top_k = int(top_k or settings["retrieval"]["top_k"])
    search_type = search_type or settings["retrieval"]["search_type"]
    forced: list[dict] = []
    for coll, cid in forced_ids(pokemon_id, mode, opponent_id, opponent_type, extra_ids):
        forced += get_by_ids(coll, [cid])
    if pokemon_id is None:
        # 자유 질문: 항상 넣을 메타데이터가 없으므로 질문과 가까운 포켓몬 도감 데이터를 검색으로 가져온다
        forced = search_docs(None, question, int(settings["retrieval"]["free_meta_k"]), "similarity",
                             collection=META)
    searched = search_docs(pokemon_id, question, top_k, search_type, extra_ids)
    return number(merge(forced + searched))


def evidence_block(evidence: list[dict]) -> str:
    """프롬프트에 넣을 근거 글: '[근거 1] (포켓몬 도감 데이터) 리자몽\\n<본문>'을 빈 줄로 구분."""
    parts = []
    for e in evidence:
        parts.append(f"[근거 {e['no']}] ({PROMPT_LABEL.get(e['source_type'], '')}) {e['title']}\n{e['text']}")
    return "\n\n".join(parts)
