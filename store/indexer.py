"""청킹(글 자르기) + 색인(Vector DB에 넣기) (F2002, F2005).

청크 ID를 고정하고 upsert(있으면 덮어쓰기, 없으면 추가)로 넣으므로 두 번 돌려도 건수가 늘지 않는다.
"""
from datetime import date

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from data_prep.build_item_text import item_text
from services.config import settings
from services.http import with_retry
from store.vector_store import DOCS, META, get_store, raw_collection


def meta_chunk_id(pokemon_id: int) -> str:
    """메타데이터 청크 ID: pkm:{도감번호}"""
    return f"pkm:{pokemon_id}"


def doc_chunk_id(owner: int | str, doc_id: str | int, index: int) -> str:
    """외부 문서 청크 ID: {포켓몬ID 또는 shared}:{문서ID}:{순번}. 여러 포켓몬이 같은 문서를 모아도 안 겹친다."""
    return f"{owner}:{doc_id}:{index}"


def _upsert(name: str, docs: list[Document], ids: list[str]) -> None:
    """임베딩해서 넣는다. 한 번에 너무 많이 보내지 않도록 64개씩 나눈다."""
    store = get_store(name)
    for start in range(0, len(docs), 64):
        part, part_ids = docs[start:start + 64], ids[start:start + 64]
        with_retry(lambda: store.add_documents(part, ids=part_ids), "임베딩 색인")


# F2002 — 포켓몬 1마리 = 1청크 (자르지 않음)
def index_meta(pokemon: list[dict]) -> None:
    docs, ids = [], []
    for p in pokemon:
        types = p["types"]
        docs.append(Document(
            page_content=item_text(p),
            metadata={
                "pokemon_id": p["id"],
                "dex_no": p["dex_no"],
                "name_ko": p["name_ko"],
                "types": ",".join(types),  # Chroma 메타데이터는 목록 대신 글자로
                "type_1": types[0],
                "type_2": types[1] if len(types) > 1 else "",
                "is_legendary": p["is_legendary"],
                "is_mythical": p["is_mythical"],
                "weight_kg": float(p["weight_kg"]),
                "height_m": float(p["height_m"]),
                "doc_id": meta_chunk_id(p["id"]),
                "source_type": "meta",
                "source_title": f"{p['name_ko']} · PokéAPI 도감",
                "source_url": p["source_url"],
            },
        ))
        ids.append(meta_chunk_id(p["id"]))
    _upsert(META, docs, ids)


# F2016 — 구조화 문서(타입·진화)는 짧아서 자르지 않고 1청크로, 공용(shared)으로 넣는다
def index_structured(type_docs: list[dict], evo_docs: list[dict]) -> int:
    today = date.today().isoformat()
    docs, ids = [], []
    for d in type_docs + evo_docs:
        docs.append(Document(
            page_content=d["text"],
            metadata={
                "pokemon_id": 0,  # 공용 문서: 어느 포켓몬에서나 검색됨
                "related_names": ",".join(d.get("related_names", [])) or d.get("type_ko", ""),
                "doc_id": d["doc_id"],
                "source_type": "pokeapi",
                "source_title": d["title"],
                "source_url": d["source_url"],
                "query": "",
                "collected_at": today,
                "chunk_index": 0,
            },
        ))
        ids.append(doc_chunk_id("shared", d["doc_id"], 0))
    _upsert(DOCS, docs, ids)
    return len(ids)


def splitter() -> RecursiveCharacterTextSplitter:
    """설정의 청크 크기·중복 길이를 그대로 쓰는 글 자르개."""
    return RecursiveCharacterTextSplitter(
        chunk_size=int(settings["chunk"]["size"]),
        chunk_overlap=int(settings["chunk"]["overlap"]),
        separators=["\n\n", "\n", ". ", " "],
    )


# F2005 — 위키 본문을 설정값으로 잘라 pokemon_docs에 넣는다
def index_wiki_page(pokemon_id: int, related_name: str, page: dict, query: str) -> int:
    """page: {pageid, title, text, url, collected_at}. 넣은 청크 수를 돌려준다."""
    pieces = splitter().split_text(page["text"])
    # 같은 문서를 다시 넣을 때 예전 청크가 남지 않도록 먼저 지운다
    raw_collection(DOCS).delete(where={"$and": [{"pokemon_id": pokemon_id},
                                                {"doc_id": str(page["pageid"])}]})
    docs, ids = [], []
    for i, piece in enumerate(pieces):
        docs.append(Document(
            page_content=f"[문서: {page['title']}]\n{piece}",  # 잘린 청크만 봐도 어느 문서인지 알게
            metadata={
                "pokemon_id": pokemon_id,
                "related_names": related_name,
                "doc_id": str(page["pageid"]),
                "source_type": "wikipedia",
                "source_title": page["title"],
                "source_url": page["url"],
                "query": query,
                "collected_at": page.get("collected_at", date.today().isoformat()),
                "chunk_index": i,
            },
        ))
        ids.append(doc_chunk_id(pokemon_id, page["pageid"], i))
    if docs:
        _upsert(DOCS, docs, ids)
    return len(ids)
