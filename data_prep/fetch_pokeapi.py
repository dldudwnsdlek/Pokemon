"""PokéAPI에서 1세대 포켓몬을 모아 data/*.json 정리본을 만든다 (F2001).

실행: python -m data_prep.fetch_pokeapi
처음 한 번만 실제로 호출하고, 두 번째부터는 cache/pokeapi/ 저장본을 쓴다.
"""
import json
import re

from data_prep.evolution_terms import condition_text
from data_prep.pokeapi import fetch, gen_number, id_from_url, ko_name, name_in
from data_prep.structured_docs import build_evolution_docs, build_rank_docs, build_type_docs
from services import http
from services.config import settings

DATA = settings.path("data")

STAT_KO = {
    "hp": "HP",
    "attack": "공격",
    "defense": "방어",
    "special-attack": "특수공격",
    "special-defense": "특수방어",
    "speed": "스피드",
}
STAT_KEY = {
    "hp": "hp",
    "attack": "attack",
    "defense": "defense",
    "special-attack": "sp_attack",
    "special-defense": "sp_defense",
    "speed": "speed",
}


def clean_flavor(text: str) -> str:
    """도감 설명 속 줄바꿈·특수 공백을 보통 공백으로 바꾼다."""
    return re.sub(r"\s+", " ", text.replace("\f", " ")).strip()


def latest_ko_flavor(species: dict) -> tuple[str, str]:
    """한국어 도감 설명 중 가장 최근 버전 1개와 그 버전의 한국어 이름. 없으면 빈칸."""
    ko = [f for f in species["flavor_text_entries"] if f["language"]["name"] == "ko"]
    if not ko:
        return "", ""
    last = ko[-1]
    version_ko, _ = ko_name("version", last["version"]["name"])
    return clean_flavor(last["flavor_text"]), version_ko


def species_label(species_id: int) -> tuple[str, int]:
    """종 번호로 (한국어 이름, 처음 나온 세대)를 돌려준다."""
    sp = fetch(f"/pokemon-species/{species_id}")
    return name_in(sp["names"]) or sp["name"], gen_number(sp["generation"]["name"])


def chain_stages(chain: dict) -> list[dict]:
    """진화 계통을 단계 목록으로 펼친다. 각 단계: id, 이름, 이전 단계 id, 조건, 세대, 깊이."""
    stages: list[dict] = []

    def walk(node: dict, parent_id: int | None, depth: int) -> None:
        sid = id_from_url(node["species"]["url"])
        name, gen = species_label(sid)
        details = node.get("evolution_details") or []
        cond = condition_text(details[0]) if details else ""
        stages.append({"id": sid, "name_ko": name, "from_id": parent_id,
                       "condition": cond, "generation": gen, "depth": depth})
        for child in node["evolves_to"]:
            walk(child, sid, depth + 1)

    walk(chain["chain"], None, 0)
    return stages


def evolution_line(stages: list[dict]) -> str:
    """단계 목록을 '파이리 → (레벨 16) 리자드 → (레벨 36) 리자몽' 같은 한 줄로 만든다."""
    by_parent: dict[int | None, list[dict]] = {}
    for s in stages:
        by_parent.setdefault(s["from_id"], []).append(s)

    def label(s: dict) -> str:
        return s["name_ko"] + (f"({s['generation']}세대에 추가)" if s["generation"] > 1 else "")

    def render(s: dict) -> str:
        kids = by_parent.get(s["id"], [])
        if not kids:
            return label(s)
        branches = " / ".join(f"({k['condition']}) {render(k)}" for k in kids)
        return f"{label(s)} → {branches}"

    root = by_parent[None][0]
    if not by_parent.get(root["id"]):
        return f"{root['name_ko']} (진화하지 않음)"
    return render(root)


def build_pokemon(pid: int, chains: dict[int, list[dict]]) -> dict:
    """포켓몬 1마리의 정리본을 만든다."""
    p = fetch(f"/pokemon/{pid}")
    sp = fetch(f"/pokemon-species/{pid}")

    types, type_missing = [], False
    for t in sorted(p["types"], key=lambda t: t["slot"]):
        name, missing = ko_name("type", t["type"]["name"])
        types.append(name)
        type_missing |= missing

    abilities, ability_missing = [], False
    for a in sorted(p["abilities"], key=lambda a: a["slot"]):
        name, missing = ko_name("ability", a["ability"]["name"])
        abilities.append(name + ("(숨겨진 특성)" if a["is_hidden"] else ""))
        ability_missing |= missing

    # 세대가 바뀌며 타입이 달라진 기록 (예: 삐삐는 5세대까지 노말)
    past_types = []
    for pt in p.get("past_types", []):
        names = [ko_name("type", t["type"]["name"])[0] for t in sorted(pt["types"], key=lambda t: t["slot"])]
        past_types.append({"until_generation": gen_number(pt["generation"]["name"]), "types": names})

    chain_id = id_from_url(sp["evolution_chain"]["url"])
    if chain_id not in chains:
        chains[chain_id] = chain_stages(fetch(sp["evolution_chain"]["url"]))

    flavor, flavor_version = latest_ko_flavor(sp)
    item = {
        "id": pid,
        "dex_no": f"{pid:03d}",
        "name_ko": name_in(sp["names"]) or p["name"],
        "name_en": p["name"],
        "genus_ko": name_in(sp["genera"], key="genus") or "",
        "types": types,
        "past_types": past_types,
        "abilities": abilities,
        "height_m": p["height"] / 10,   # 데시미터 → m
        "weight_kg": p["weight"] / 10,  # 헥토그램 → kg
        "stats": {STAT_KEY[s["stat"]["name"]]: s["base_stat"] for s in p["stats"]},
        "evolution": evolution_line(chains[chain_id]),
        "evolution_chain_id": chain_id,
        "is_legendary": sp["is_legendary"],
        "is_mythical": sp["is_mythical"],
        "capture_rate": sp["capture_rate"],
        "flavor_ko": flavor,
        "flavor_version": flavor_version,
        "source_url": f"https://pokeapi.co/api/v2/pokemon-species/{pid}/",
    }
    if type_missing or ability_missing:
        item["name_ko_missing"] = True
    return item


def main() -> None:
    DATA.mkdir(exist_ok=True)
    lo, hi = settings["scope"]["dex_from"], settings["scope"]["dex_to"]
    chains: dict[int, list[dict]] = {}
    pokemon = []
    for pid in range(lo, hi + 1):
        pokemon.append(build_pokemon(pid, chains))
        if pid % 10 == 0:
            print(f"  {pid}/{hi} 완료 (지금까지 외부 호출 {http.call_count}회)", flush=True)

    type_docs = build_type_docs()
    evo_docs = build_evolution_docs(chains, lo, hi)
    rank_docs = build_rank_docs(pokemon)

    for name, obj in [("pokemon.json", pokemon), ("type_docs.json", type_docs),
                      ("evolution_docs.json", evo_docs), ("rank_docs.json", rank_docs)]:
        (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"포켓몬 {len(pokemon)}마리, 타입 문서 {len(type_docs)}개, 진화 계통 문서 {len(evo_docs)}개, "
          f"순위 문서 {len(rank_docs)}개 저장")
    print(f"이번 실행의 외부 호출: {http.call_count}회 (0회면 모두 캐시에서 읽음)")


if __name__ == "__main__":
    main()
