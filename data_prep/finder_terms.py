"""조건 탐색용 단어 사전: 조건 글 속 단어를 Chroma 메타데이터 필터로 바꾼다 (F2011).

예: "물 타입인데 몸무게 100kg 넘는 포켓몬" → 타입=물 AND weight_kg > 100
"""
import json
import re
from functools import lru_cache

from services.config import settings

# 숫자 뒤에 오는 비교 말 → Chroma 연산자
COMPARE = [
    (r"(넘는|넘게|초과|보다\s*무거운|보다\s*큰|보다\s*높은)", "$gt"),
    (r"(이상)", "$gte"),
    (r"(미만|보다\s*가벼운|보다\s*작은|보다\s*낮은|안\s*되는)", "$lt"),
    (r"(이하|아래)", "$lte"),
]
NUMBER = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|킬로그램|킬로|cm|센티미터|센티|m|미터)\s*(?:가|이|를|을|는|은)?\s*"
                    r"(넘는|넘게|초과|보다\s*무거운|보다\s*큰|보다\s*높은|이상|미만|보다\s*가벼운|보다\s*작은|"
                    r"보다\s*낮은|안\s*되는|이하|아래)?")


@lru_cache(maxsize=1)
def type_names() -> list[str]:
    """18개 타입의 한국어 이름 (데이터에서 읽음)."""
    docs = json.loads(settings.path("data", "type_docs.json").read_text(encoding="utf-8"))
    return [d["type_ko"] for d in docs]


def find_types(text: str) -> list[str]:
    """조건 글에서 타입 이름을 찾는다. '물', '풀'처럼 한 글자 이름은 '타입'이 붙을 때만 인정."""
    found = []
    for t in type_names():
        if re.search(rf"{t}\s*타입", text) or (len(t) >= 2 and t in text):
            found.append(t)
    return found


def _op(word: str) -> str:
    """비교 말('넘는', '이하' …)을 연산자로. 비교 말이 없으면 '이상'으로 본다."""
    for pattern, op in COMPARE:
        if word and re.search(pattern, word):
            return op
    return "$gte"


def parse_condition(text: str) -> tuple[dict | None, list[str]]:
    """(Chroma where 필터 또는 None, 사람이 읽는 필터 설명 목록)."""
    clauses, notes = [], []
    for t in find_types(text):
        clauses.append({"$or": [{"type_1": t}, {"type_2": t}]})
        notes.append(f"{t} 타입")
    if "전설" in text:
        clauses.append({"is_legendary": True})
        notes.append("전설의 포켓몬")
    if "환상" in text:
        clauses.append({"is_mythical": True})
        notes.append("환상의 포켓몬")
    for value, unit, word in NUMBER.findall(text):
        num = float(value)
        if unit in ("kg", "킬로그램", "킬로"):
            field, shown = "weight_kg", f"{num:g}kg"
        else:
            field = "height_m"
            if unit in ("cm", "센티미터", "센티"):
                num /= 100
            shown = f"{num:g}m"
        op = _op(word)
        clauses.append({field: {op: num}})
        sign = {"$gt": "초과", "$gte": "이상", "$lt": "미만", "$lte": "이하"}[op]
        notes.append(f"{'몸무게' if field == 'weight_kg' else '키'} {shown} {sign}")
    if not clauses:
        return None, notes
    return (clauses[0] if len(clauses) == 1 else {"$and": clauses}), notes
