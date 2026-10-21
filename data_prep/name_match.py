"""질문 글 속에서 1세대 포켓몬 이름을 찾는다 (자유 질문용).

예: "리자몽은 드래곤 타입이야?" → [6]
긴 이름부터 찾고(뮤츠를 뮤보다 먼저), 이름 앞뒤가 다른 한글 낱말로 이어지면 이름으로 보지 않는다
("뮤지컬"의 "뮤", "공지사항"의 "고지"는 무시).
"""
import re
from functools import lru_cache

from data_prep.build_item_text import load_pokemon

# 이름 바로 뒤에 붙어도 되는 조사의 첫 글자
PARTICLES = set("은는이가을를의도와과랑만에께한")
HANGUL = re.compile(r"[가-힣]")


@lru_cache(maxsize=1)
def _names() -> list[tuple[str, int]]:
    """(한국어 이름, 도감 번호)를 긴 이름 순서로."""
    pairs = [(p["name_ko"], p["id"]) for p in load_pokemon()]
    return sorted(pairs, key=lambda x: -len(x[0]))


def find_pokemon_in_text(text: str) -> list[int]:
    """질문에 나온 포켓몬 번호를 나온 순서대로, 중복 없이."""
    taken = [False] * len(text)
    found: list[tuple[int, int]] = []  # (위치, 번호)
    for name, pid in _names():
        start = text.find(name)
        while start != -1:
            end = start + len(name)
            before = text[start - 1] if start > 0 else ""
            after = text[end] if end < len(text) else ""
            free = not any(taken[start:end])
            bounded = not HANGUL.match(before) and (not HANGUL.match(after) or after in PARTICLES)
            if free and bounded:
                for i in range(start, end):
                    taken[i] = True
                found.append((start, pid))
            start = text.find(name, start + 1)
    ids: list[int] = []
    for _, pid in sorted(found):
        if pid not in ids:
            ids.append(pid)
    return ids
