"""진화 조건 영어 값을 한국어로 바꾸는 표와 함수."""
from data_prep.pokeapi import ko_name

TRIGGER_KO = {
    "level-up": "레벨업",
    "trade": "통신교환",
    "use-item": "도구 사용",
    "shed": "빈자리 진화",
    "spin": "회전",
    "tower-of-darkness": "악의 탑",
    "tower-of-waters": "물의 탑",
    "three-critical-hits": "급소 3회",
    "take-damage": "피해 받기",
    "other": "특수 조건",
    "agile-style-move": "속공 스타일 기술",
    "strong-style-move": "강공 스타일 기술",
    "recoil-damage": "반동 피해",
}

TIME_KO = {"day": "낮", "night": "밤", "dusk": "황혼"}


def condition_text(detail: dict) -> str:
    """evolution_details 하나를 '레벨 16', '불꽃의돌', '통신교환' 같은 짧은 한국어로 바꾼다."""
    trigger = detail["trigger"]["name"]
    parts: list[str] = []

    if trigger == "use-item" and detail.get("item"):
        parts.append(ko_name("item", detail["item"]["name"])[0])
    elif trigger == "trade":
        parts.append("통신교환")
        if detail.get("held_item"):
            parts.append(ko_name("item", detail["held_item"]["name"])[0] + "을(를) 지닌 채")
        if detail.get("trade_species"):
            parts.append("특정 포켓몬과 교환")
    elif trigger == "level-up":
        if detail.get("min_level"):
            parts.append(f"레벨 {detail['min_level']}")
        if detail.get("min_happiness"):
            parts.append(f"친밀도 {detail['min_happiness']} 이상")
        if detail.get("min_affection"):
            parts.append("친밀도(우정) 높음")
        if detail.get("known_move"):
            parts.append(ko_name("move", detail["known_move"]["name"])[0] + " 기술을 배운 상태")
        if detail.get("known_move_type"):
            parts.append(ko_name("type", detail["known_move_type"]["name"])[0] + " 타입 기술을 배운 상태")
        if detail.get("held_item"):
            parts.append(ko_name("item", detail["held_item"]["name"])[0] + "을(를) 지닌 채")
        if detail.get("location") or detail.get("near_special_rock"):
            parts.append("특정 장소")
        if not parts:
            parts.append("레벨업")
    else:
        parts.append(TRIGGER_KO.get(trigger, trigger))

    time = TIME_KO.get(detail.get("time_of_day") or "")
    if time:
        parts.append(time)
    return ", ".join(parts)
