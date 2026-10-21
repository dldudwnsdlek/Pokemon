"""PokéAPI의 표 형태 데이터(타입 상성, 진화 계통)를 사람이 읽는 문장으로 바꾼다 (F2016 두 번째 출처).

LLM은 표보다 문장을 더 정확히 읽기 때문에 문장으로 바꿔 외부 문서 컬렉션에 넣는다.
"""
from data_prep.pokeapi import fetch, gen_number, ko_name

TYPE_NAMES = [
    "normal", "fighting", "flying", "poison", "ground", "rock", "bug", "ghost", "steel",
    "fire", "water", "grass", "electric", "psychic", "ice", "dragon", "dark", "fairy",
]


def _names(entries: list[dict]) -> str:
    """타입 목록을 '고스트, 에스퍼'처럼 한국어로 잇는다. 비어 있으면 '없음'."""
    if not entries:
        return "없음"
    return ", ".join(ko_name("type", e["name"])[0] for e in entries)


def _relations_text(rel: dict) -> str:
    """damage_relations 하나를 공격/방어 두 줄로 쓴다."""
    attack = (f"공격할 때 — 효과가 굉장한(2배) 상대: {_names(rel['double_damage_to'])} / "
              f"효과가 별로인(0.5배) 상대: {_names(rel['half_damage_to'])} / "
              f"효과가 없는(0배) 상대: {_names(rel['no_damage_to'])}")
    defend = (f"방어할 때 — 2배로 받는 공격: {_names(rel['double_damage_from'])} / "
              f"0.5배로 받는 공격: {_names(rel['half_damage_from'])} / "
              f"받지 않는(0배) 공격: {_names(rel['no_damage_from'])}")
    return attack + "\n" + defend


def build_type_docs() -> list[dict]:
    """타입마다 상성 문서 1개를 만든다 (18개)."""
    docs = []
    for name in TYPE_NAMES:
        t = fetch(f"/type/{name}")
        ko, _ = ko_name("type", name)
        lines = [f"[타입 상성] {ko} 타입 (영문 {name})"]
        added = gen_number(t["generation"]["name"])
        if added > 1:
            lines.append(f"{ko} 타입은 {added}세대에 추가된 타입이라 1세대 게임(레드·그린·블루·피카츄)에는 없다.")
        lines.append("현재 세대 기준 상성:")
        lines.append(_relations_text(t["damage_relations"]))
        for past in t.get("past_damage_relations", []):
            g = gen_number(past["generation"]["name"])
            when = "1세대에서는" if g == 1 else f"{g}세대까지는"
            lines.append(f"세대별 변경 — {when} 상성이 지금과 달랐다:")
            lines.append(_relations_text(past["damage_relations"]))
        docs.append({
            "doc_id": f"type-{name}",
            "title": f"{ko} 타입 상성",
            "type_en": name,
            "type_ko": ko,
            "text": "\n".join(lines),
            "source_url": f"https://pokeapi.co/api/v2/type/{name}/",
        })
    return docs


# (데이터 키, 한국어 이름, 단위) — 순위 문서를 만들 항목
RANK_FIELDS = [
    ("weight_kg", "몸무게", "kg"), ("height_m", "키", "m"), ("total", "능력치 합계", ""),
    ("hp", "HP", ""), ("attack", "공격", ""), ("defense", "방어", ""),
    ("sp_attack", "특수공격", ""), ("sp_defense", "특수방어", ""), ("speed", "스피드", ""),
]


def build_rank_docs(pokemon: list[dict], top: int = 10, bottom: int = 5) -> list[dict]:
    """1세대 151마리 전체를 항목별로 줄 세운 순위 문서.
    '가장 무거운 포켓몬은?'처럼 전체를 비교해야 하는 질문은 의미 검색만으로는 답할 수 없어서 만든다."""
    def value(p: dict, key: str):
        if key == "total":
            return sum(p["stats"].values())
        return p[key] if key in p else p["stats"][key]

    docs = []
    for key, label, unit in RANK_FIELDS:
        ranked = sorted(pokemon, key=lambda p: (-value(p, key), p["id"]))
        fmt = lambda p: f"{p['name_ko']}(No.{p['dex_no']}) {value(p, key):g}{unit}"  # noqa: E731
        lines = [f"[도감 순위] 1세대(1~151번) 포켓몬 {label} 순위. 151마리 전체를 비교한 결과다."]
        if key not in ("weight_kg", "height_m"):
            lines.append("능력치는 현재 게임 기준 값이다. 1세대 게임에는 특수공격·특수방어 대신 '특수' 하나만 있었다.")
        lines.append(f"{label} 상위 {top} (가장 높거나 큰 순서):")
        lines += [f"{i}위. {fmt(p)}" for i, p in enumerate(ranked[:top], start=1)]
        lines.append(f"{label} 하위 {bottom} (가장 낮거나 작은 순서):")
        lines += [f"{len(ranked) - i}위. {fmt(p)}" for i, p in enumerate(reversed(ranked[-bottom:]))]
        docs.append({
            "doc_id": f"rank-{key}",
            "title": f"1세대 {label} 순위",
            "text": "\n".join(lines),
            "source_url": "https://pokeapi.co/api/v2/pokemon/",
        })
    return docs


def build_evolution_docs(chains: dict[int, list[dict]], lo: int, hi: int) -> list[dict]:
    """1세대 포켓몬이 들어 있는 진화 계통마다 문서 1개를 만든다."""
    from data_prep.fetch_pokeapi import evolution_line  # 순환 import 방지

    docs = []
    for chain_id, stages in sorted(chains.items()):
        members = [s for s in stages if lo <= s["id"] <= hi]
        if not members:
            continue
        root = stages[0]
        names = {s["id"]: s["name_ko"] for s in stages}
        lines = [f"[진화] {root['name_ko']} 계통.", evolution_line(stages), "단계별 설명:"]
        if len(stages) == 1:
            lines.append(f"- {root['name_ko']}: 진화하지 않는 포켓몬이다.")
        for s in stages:
            if s["from_id"] is None:
                if len(stages) > 1:
                    lines.append(f"- {s['name_ko']}: 계통의 첫 단계.")
                continue
            era = ("1세대부터 있는 진화" if s["generation"] == 1
                   else f"{s['generation']}세대에 추가된 포켓몬이라 1세대 게임에는 없다")
            lines.append(f"- {s['name_ko']}: {names[s['from_id']]}에서 [{s['condition']}] 조건으로 진화 ({era}).")
        trade = [s["name_ko"] for s in stages if "통신교환" in s["condition"]]
        if trade:
            lines.append("통신교환으로 진화하는 단계: " + ", ".join(trade) + ".")
        branch_parents = {s["from_id"] for s in stages if s["from_id"] is not None
                          and sum(1 for x in stages if x["from_id"] == s["from_id"]) > 1}
        for bp in branch_parents:
            lines.append(f"{names[bp]}은(는) 조건에 따라 여러 갈래로 진화하는 분기 진화를 한다.")
        docs.append({
            "doc_id": f"evo-{chain_id}",
            "chain_id": chain_id,
            "title": f"{root['name_ko']} 계통 진화",
            "member_ids": [s["id"] for s in members],
            "related_names": [s["name_ko"] for s in members],
            "stages": stages,
            "text": "\n".join(lines),
            "source_url": f"https://pokeapi.co/api/v2/evolution-chain/{chain_id}/",
        })
    return docs
