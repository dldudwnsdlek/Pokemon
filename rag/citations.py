"""답변 속 [근거 n] 찾기·정리 (F2008). 실제로 인용된 근거만 돌려준다."""
import re

from rag.retriever import _body

CITE = re.compile(r"\[근거\s*(\d+)\]")


def cited_numbers(answer: str) -> list[int]:
    """답변에 나온 근거 번호를 처음 나온 순서대로, 중복 없이."""
    seen: list[int] = []
    for m in CITE.finditer(answer):
        n = int(m.group(1))
        if n not in seen:
            seen.append(n)
    return seen


def extract(answer: str, evidence: list[dict]) -> tuple[list[dict], bool]:
    """(인용된 근거 목록, 인용이 하나도 없는지). 없는 번호는 무시한다."""
    by_no = {e["no"]: e for e in evidence}
    citations = []
    for n in sorted(cited_numbers(answer)):
        e = by_no.get(n)
        if not e:
            continue
        citations.append({
            "no": n,
            "title": e["title"],
            "source_type": e["source_type"],
            "source_label": e["source_label"],
            "url": e["url"],
            "snippet": _body(e["text"])[:120],
        })
    return citations, not citations
