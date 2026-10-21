"""색인 한 번에: 포켓몬 메타데이터 + 구조화 문서(타입·진화) (F2002, F2005, F2016).

실행: python -m scripts.build_index
청크 크기를 바꾼 뒤: python -m scripts.build_index --reset-docs
  → pokemon_docs를 비우고, 지금까지 모은 위키 문서를 새 청크 설정으로 다시 잘라 넣는다
    (본문은 cache/wiki/ 저장본을 쓰므로 다시 내려받지 않는다). 바꾸기 전·후 청크 수를 보여준다.
  --forget-collected 를 함께 주면 수집 기록도 지워서, 다음 질문 때 처음부터 다시 수집한다.
"""
import argparse
import json
import sys

from data_prep import wiki_source
from data_prep.build_item_text import load_pokemon
from rag.collector import REGISTRY, load_registry
from services.config import settings
from services.http import UpstreamError
from services.llm import ApiKeyMissing
from store.indexer import FREE_ID, index_meta, index_structured, index_wiki_page
from store.vector_store import DOCS, META, count, delete_collection


def load(name: str) -> list[dict]:
    return json.loads(settings.path("data", name).read_text(encoding="utf-8"))


def reindex_wiki() -> int:
    """수집 기록에 있는 위키 문서를 지금 청크 설정으로 다시 색인한다."""
    reg = load_registry()
    names = {p["id"]: p["name_ko"] for p in load_pokemon()}
    total = 0
    for owner, docs in reg["docs"].items():
        pid = FREE_ID if owner == "free" else int(owner)  # 'free' = 자유 질문으로 모은 문서
        for pageid, info in docs.items():
            try:
                page = wiki_source.fetch_page(int(pageid))
            except UpstreamError:
                print(f"  ! {info['title']} 본문을 가져오지 못해 건너뜀")
                continue
            info["chunks"] = index_wiki_page(pid, names.get(pid, ""), page, info["query"])
            total += info["chunks"]
    REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    return total


def build_base(say=print) -> None:
    """도감 메타데이터 + 구조화 문서 색인. 서버가 빈 도감으로 켜졌을 때도 이 함수를 부른다 (api/server.py)."""
    pokemon = load_pokemon()
    say(f"포켓몬 데이터 {len(pokemon)}마리 불러옴")
    before = count(META)
    index_meta(pokemon)
    say(f"{META} 색인 완료: {count(META)}청크 (이전 {before} → 지금 {count(META)})")
    type_docs, evo_docs = load("type_docs.json"), load("evolution_docs.json")
    rank_docs = load("rank_docs.json")
    n = index_structured(type_docs, evo_docs + rank_docs)
    say(f"구조화 문서 색인 완료: 타입 {len(type_docs)}개, 진화 계통 {len(evo_docs)}개, "
        f"순위 {len(rank_docs)}개 → {DOCS} 청크 {n}개")


def main() -> None:
    parser = argparse.ArgumentParser(description="포켓몬 RAG 색인")
    parser.add_argument("--reset-docs", action="store_true", help="pokemon_docs를 비우고 새 청크 설정으로 다시 색인")
    parser.add_argument("--forget-collected", action="store_true", help="수집 기록도 지운다")
    args = parser.parse_args()

    if not settings.has_api_key():
        print("연구소 열쇠(API 키)가 없어요. .env 파일에 GMS_API_KEY 를 넣고 다시 실행해 주세요.")
        sys.exit(1)

    try:
        docs_before = count(DOCS)
        if args.reset_docs:
            delete_collection(DOCS)
            print(f"{DOCS} 비움 (이전 {docs_before}청크)")

        build_base()

        if args.reset_docs:
            if args.forget_collected:
                REGISTRY.unlink(missing_ok=True)
                print("수집 기록을 지웠어요. 다음 질문부터 위키백과를 처음부터 다시 모아요.")
            else:
                w = reindex_wiki()
                print(f"위키 문서 다시 색인: 청크 {w}개 "
                      f"(청크 크기 {settings['chunk']['size']}, 중복 {settings['chunk']['overlap']})")
            print(f"{DOCS} 청크 수: 바꾸기 전 {docs_before} → 지금 {count(DOCS)}")
        else:
            print(f"{DOCS} 전체 청크: {count(DOCS)}개")
    except ApiKeyMissing:
        print("연구소 열쇠(API 키)가 없어요. .env 파일을 확인해 주세요.")
        sys.exit(1)
    except UpstreamError:
        print("임베딩 서버 연결이 불안정해요. 잠시 후 다시 실행해 주세요. (자세한 내용: logs/app.log)")
        sys.exit(1)


if __name__ == "__main__":
    main()
