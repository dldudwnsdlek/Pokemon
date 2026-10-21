"""검색 설정 비교 (검증 V07 Top-k, V16 유사도 vs MMR / F2014).

같은 질문에 Top-k와 검색 방식을 바꿔 가며 근거 목록이 어떻게 달라지는지 출력하고 docs/search_comparison.md에 저장한다.
실행 예: python -m scripts.compare_search --pokemon 133 --question "이브이는 무엇으로 진화해?" --top-k 3 8
(먼저 그 질문을 화면에서 한 번 물어 위키 문서를 모아 두면 차이가 잘 보인다)
"""
import argparse

from data_prep.build_item_text import pokemon_by_id
from rag.collector import collect
from rag.retriever import retrieve
from services.config import settings


def table(evidence: list[dict]) -> list[str]:
    return [f"| {e['no']} | {e['source_label']} | {e['title']} | `{e['id']}` |" for e in evidence]


def main() -> None:
    parser = argparse.ArgumentParser(description="Top-k·검색 방식 비교")
    parser.add_argument("--pokemon", type=int, required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--top-k", type=int, nargs="+", default=[3, 8])
    parser.add_argument("--no-collect", action="store_true", help="위키 수집을 건너뛴다")
    args = parser.parse_args()

    name = pokemon_by_id(args.pokemon)["name_ko"]
    if not args.no_collect:
        collect(args.pokemon, args.question)

    out = [f"# 검색 설정 비교 — {name}: {args.question}", "",
           f"MMR 설정: fetch_k={settings['retrieval']['mmr_fetch_k']}, lambda={settings['retrieval']['mmr_lambda']}", ""]
    for k in args.top_k:
        results = {st: retrieve(args.pokemon, args.question, top_k=k, search_type=st) for st in ("similarity", "mmr")}
        sim_ids = {e["id"] for e in results["similarity"]}
        mmr_ids = {e["id"] for e in results["mmr"]}
        for st, ev in results.items():
            print(f"\n[Top-k={k} · {st}] 근거 {len(ev)}개 (서로 다른 문서 {len({e['title'] for e in ev})}개)")
            for e in ev:
                print(f"  [근거 {e['no']}] {e['source_label']:8} {e['title']}  ({e['id']})")
            out += [f"## Top-k={k} · {st} — 근거 {len(ev)}개, 서로 다른 문서 {len({e['title'] for e in ev})}개", "",
                    "| 번호 | 출처 | 제목 | 청크 ID |", "|---|---|---|---|", *table(ev), ""]
        out += [f"> Top-k={k}: 유사도·MMR 공통 근거 {len(sim_ids & mmr_ids)}개, "
                f"MMR에만 있는 근거 {len(mmr_ids - sim_ids)}개", ""]
    path = settings.path("docs", "search_comparison.md")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\n저장: docs/{path.name}")


if __name__ == "__main__":
    main()
