"""포켓몬 1마리 → 검색용 글 1개 (F2001).

사용자는 이름뿐 아니라 "불꽃 타입", "날개 달린", "무거운", "전설의" 같은 말로 찾으므로
모든 속성을 한 글로 묶는다. 확인: python -m data_prep.build_item_text --id 6
"""
import argparse
import json
from functools import lru_cache

from services.config import settings

STAT_LABELS = [("hp", "HP"), ("attack", "공격"), ("defense", "방어"),
               ("sp_attack", "특수공격"), ("sp_defense", "특수방어"), ("speed", "스피드")]


@lru_cache(maxsize=1)
def load_pokemon() -> list[dict]:
    """data/pokemon.json 정리본을 읽는다."""
    path = settings.path("data", "pokemon.json")
    return json.loads(path.read_text(encoding="utf-8"))


def pokemon_by_id(pid: int) -> dict | None:
    """도감 번호로 포켓몬 1마리를 찾는다."""
    return next((p for p in load_pokemon() if p["id"] == pid), None)


def category(p: dict) -> str:
    """전설/환상/일반 구분 글자."""
    if p["is_legendary"]:
        return "전설의 포켓몬"
    if p["is_mythical"]:
        return "환상의 포켓몬"
    return "일반 포켓몬"


def item_text(p: dict) -> str:
    """포켓몬 1마리의 모든 속성을 검색용 글 하나로 만든다."""
    stats = p["stats"]
    total = sum(stats.values())
    stat_line = " / ".join(f"{label} {stats[key]}" for key, label in STAT_LABELS)
    lines = [
        f"[포켓몬] {p['name_ko']} (전국도감 {p['dex_no']}번, 영문 {p['name_en']})",
        f"분류: {p['genus_ko']}",
        f"타입: {', '.join(p['types'])}",
    ]
    for past in p.get("past_types", []):
        when = "1세대" if past["until_generation"] == 1 else f"{past['until_generation']}세대까지"
        lines.append(f"예전 타입: {when}는 {', '.join(past['types'])} 타입이었다")
    lines += [
        f"특성: {', '.join(p['abilities'])}",
        f"키 {p['height_m']:g}m, 몸무게 {p['weight_kg']:g}kg",
        f"능력치: {stat_line} (합계 {total})",
        f"진화: {p['evolution']}",
        f"구분: {category(p)}",
        f"도감 설명: {p['flavor_ko']}" + (f" ({p['flavor_version']})" if p["flavor_version"] else ""),
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="포켓몬 1마리의 색인 텍스트를 출력한다")
    parser.add_argument("--id", type=int, required=True, help="도감 번호 (예: 6)")
    args = parser.parse_args()
    p = pokemon_by_id(args.id)
    if p is None:
        print("그 번호의 포켓몬이 data/pokemon.json에 없어요.")
        return
    print(item_text(p))


if __name__ == "__main__":
    main()
