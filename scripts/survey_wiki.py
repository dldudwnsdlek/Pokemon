"""151마리 각각 위키백과에 '그 포켓몬만 다룬 문서'가 있는지 조사한다 (설계문서·검증용).

실행: python -m scripts.survey_wiki  → docs/wiki_coverage.md
"""
from data_prep import wiki_source
from data_prep.build_item_text import load_pokemon
from services.config import settings
from services.http import UpstreamError


def main() -> None:
    found, missing = [], []
    for p in load_pokemon():
        try:
            page, _ = wiki_source.find_item_page(p["name_ko"])
        except UpstreamError:
            page = None
        (found if page else missing).append((p, page))

    lines = [
        "# 위키백과 단독 문서 조사",
        "",
        f"- 단독 문서 있음: **{len(found)}마리** / 151",
        f"- 단독 문서 없음: **{len(missing)}마리** (대부분 '1세대 포켓몬 목록' 표로만 연결됨 → 도감 데이터·구조화 문서로 답함)",
        "",
        "## 단독 문서 없음",
        "",
        ", ".join(f"{p['dex_no']} {p['name_ko']}" for p, _ in missing) or "없음",
        "",
        "## 이름과 문서 제목이 다른 경우 (동음이의어 → '(포켓몬)' 문서 사용)",
        "",
    ]
    lines += [f"- {p['name_ko']} → {page['title']}" for p, page in found if page["title"] != p["name_ko"]] or ["- 없음"]
    out = settings.path("docs", "wiki_coverage.md")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"단독 문서 있음 {len(found)} / 없음 {len(missing)} → {out.name}")


if __name__ == "__main__":
    main()
