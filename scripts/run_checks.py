"""검증 항목을 실제로 실행해 결과를 docs/evidence/checks.md에 남긴다 (V03~V05, V09~V11, V13, V14, V18).

실행: python -m scripts.run_checks
"""
import json
from datetime import datetime

from features import battle_coach, evolution_guide, finder
from rag.collector import load_registry
from rag.graph import run
from rag.retriever import retrieve
from services.config import settings

QUESTIONS = [
    ("Q1", 133, "이브이는 1세대에서 무엇으로 진화하고, 조건은 무엇인가?"),
    ("Q2", 6, "리자몽은 드래곤 타입인가?"),
    ("Q3", 94, "고스트 타입 기술은 에스퍼 타입에게 효과가 어떤가?"),
    ("Q4", 94, "팬텀은 어떻게 진화하나?"),
    ("Q5", 150, "뮤츠의 분류는 무엇인가?"),
    ("Q6", 143, "잠만보의 몸무게는?"),
]

out: list[str] = []


def w(line: str = "") -> None:
    print(line, flush=True)
    out.append(line)


def show(result: dict) -> None:
    w("```")
    w(result["answer"])
    w("```")
    w("- 인용된 근거: " + (", ".join(f"[{c['no']}] {c['source_label']} · {c['title']}" for c in result["citations"])
                         or "없음 (no_citation=true → 화면 안내)"))
    col = result["collected"]
    w(f"- 검색어: {col['queries']}")
    w(f"- 색인한 문서: {col['indexed']}")
    w(f"- 버린 문서: {[s['title'] + ' (' + s['reason'] + ')' for s in col['skipped']]}")
    w(f"- 캐시로 건너뛴 검색어: {col['cached']}")
    w(f"- 처리 시간: {result['elapsed_ms']}ms")


def main() -> None:
    w(f"# 검증 실행 기록 — {datetime.now():%Y-%m-%d %H:%M}")
    w(f"모델 {settings['llm']['chat_model']} · 청크 {settings['chunk']['size']}/{settings['chunk']['overlap']} · "
      f"Top-k {settings['retrieval']['top_k']} · {settings['retrieval']['search_type']}")
    times = {}
    for qid, pid, q in QUESTIONS:
        w(f"\n## {qid}. {q} (V03·V05·V09)")
        r = run(pid, q)
        times[qid] = [r["elapsed_ms"]]
        show(r)
        r2 = run(pid, q)  # V04 — 같은 질문 다시
        times[qid].append(r2["elapsed_ms"])
        w(f"- 재질문(V04): 캐시로 건너뛴 검색어 {r2['collected']['cached']}, 새로 색인 {r2['collected']['indexed']}, "
          f"{r2['elapsed_ms']}ms")

    # 가이드 예시 "피카츄의 성우는?"은 위키 피카츄 문서에 답이 있어 '문서에 없는 질문'이 되지 않으므로 바꿈
    w("\n## V10·V11 문서에 없는 질문 — 피카츄의 꼬리 길이는?")
    show(run(25, "피카츄의 꼬리 길이는 몇 cm야?"))

    w("\n## V13 조건 탐색 — 물 타입인데 몸무게 100kg 넘는 포켓몬")
    f = finder.find("물 타입인데 몸무게 100kg 넘는 포켓몬")
    w(f"- 먼저 건 필터: {f['filters']}")
    for c in f["cards"]:
        w(f"- {c['dex_no']} {c['name_ko']} {c['types']} — {c['reason']}")
    w("- 데이터 기준 정답: 쥬레곤, 파르셀, 갸라도스, 라프라스")

    w("\n## V14 특화 기능 ① 배틀 — 피카츄 vs 꼬부기")
    b = battle_coach.coach(25, opponent_id=7)
    w(f"- 판정 도장: {b['verdict']}")
    show(b)
    w("\n## V14 특화 기능 ② 진화 안내 — 이브이")
    e = evolution_guide.guide(133)
    show(e)

    w("\n## V19 자유 질문 — 포켓몬을 고르지 않고 묻기")
    for q, truth in [("1세대에서 가장 무거운 포켓몬은?", "잠만보 460kg"),
                     ("고스트 타입 기술은 에스퍼 타입에게 효과가 어때?", "현재 2배, 1세대 0배"),
                     ("피카츄와 꼬부기 중 누가 더 빨라?", "피카츄(스피드 90) > 꼬부기(43)")]:
        w(f"\n### {q}  (데이터 기준 정답: {truth})")
        r = run(None, q)
        w(f"- 질문에서 찾은 포켓몬: {[m['name_ko'] for m in r['matched']] if r['matched'] else '없음 → 범위 제한 없이 검색'}")
        show(r)

    w("\n## V20 자유 질문 문서가 포켓몬별 검색에 섞이지 않음")
    reg_free = load_registry()["docs"].get("free", {})
    leaks = 0
    for pid in (1, 6, 25, 94, 133, 143, 150):
        for st in ("similarity", "mmr"):
            for q in [d["title"] for d in reg_free.values()][:3] or ["포켓몬"]:
                ids = [e["id"] for e in retrieve(pid, q, top_k=8, search_type=st)]
                leaks += sum(1 for i in ids if i.split(":")[0] not in (str(pid), "shared", "pkm"))
    w(f"- 자유 질문 문서 {len(reg_free)}개의 제목으로 포켓몬 7마리 × 유사도·MMR 검색 → 다른 칸 문서가 섞인 수: {leaks}")

    w("\n## V18 처리 시간 (NF2001) — 첫 질문 / 재질문 (ms)")
    w("| 질문 | 첫 질문 | 재질문 |")
    w("|---|---|---|")
    for qid, (a, b2) in times.items():
        w(f"| {qid} | {a} | {b2} |")

    path = settings.path("docs", "evidence", "checks.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\n저장: docs/evidence/{path.name}")


if __name__ == "__main__":
    main()
