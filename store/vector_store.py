"""Vector DB(Chroma) 컬렉션 만들기·조회·건수 (F2002, F2005).

컬렉션은 두 개: pokemon_meta(포켓몬 기본 정보), pokemon_docs(위키백과 + 구조화 문서).
"""
from functools import lru_cache

import chromadb
from langchain_chroma import Chroma

from services.config import settings
from services.llm import get_embeddings

META = settings["store"]["meta_collection"]
DOCS = settings["store"]["doc_collection"]


@lru_cache(maxsize=1)
def client() -> chromadb.ClientAPI:
    """디스크에 저장되는 Chroma 클라이언트."""
    path = settings.path(settings["store"]["path"])
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def get_store(name: str) -> Chroma:
    """LangChain Chroma 객체 (검색·추가용). 임베딩 모델이 필요하므로 API 키가 있어야 한다."""
    return Chroma(
        client=client(),
        collection_name=name,
        embedding_function=get_embeddings(),
        collection_metadata={"hnsw:space": "cosine"},
    )


def count(name: str) -> int:
    """컬렉션의 청크 수. 컬렉션이 없으면 0 (API 키 없이도 동작)."""
    try:
        return client().get_collection(name).count()
    except Exception:  # noqa: BLE001 — 컬렉션이 아직 없음
        return 0


def raw_collection(name: str):
    """임베딩 없이 ID·메타데이터로만 꺼낼 때 쓰는 원래 컬렉션."""
    return client().get_or_create_collection(name, metadata={"hnsw:space": "cosine"})


def get_by_ids(name: str, ids: list[str]) -> list[dict]:
    """청크 ID로 바로 꺼낸다(검색 없이). 결과: [{id, text, metadata}]."""
    if not ids:
        return []
    got = raw_collection(name).get(ids=ids, include=["documents", "metadatas"])
    found = {i: (d, m) for i, d, m in zip(got["ids"], got["documents"], got["metadatas"])}
    return [{"id": i, "text": found[i][0], "metadata": found[i][1]} for i in ids if i in found]


def delete_collection(name: str) -> None:
    """컬렉션을 통째로 지운다 (청크 크기 바꿔 다시 색인할 때)."""
    try:
        client().delete_collection(name)
    except Exception:  # noqa: BLE001 — 없으면 그냥 넘어감
        pass
