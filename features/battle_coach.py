"""특화 기능 ① 배틀 상성 코치 (F2010).

타입 상성은 포켓몬에서 가장 많이 묻고 가장 자주 틀리는 지식이라 근거가 꼭 필요하다.
근거: 내 것 + 상대 것 메타데이터, 두 쪽 타입의 상성 문서(항상), 위키 청크(검색).
"""
import re

from data_prep.build_item_text import pokemon_by_id
from rag.collector import Progress, _noop
from rag.graph import run

VERDICTS = ("유리", "불리", "비슷함")


def read_verdict(answer: str) -> str | None:
    """답변의 '판정:' 줄에서 유리/불리/비슷함을 읽는다."""
    m = re.search(r"판정\s*[:：]\s*\**\s*(유리|불리|비슷함)", answer)
    return m.group(1) if m else None


def coach(pokemon_id: int, opponent_id: int | None = None, opponent_type: str | None = None,
          on_progress: Progress = _noop) -> dict:
    """선택한 포켓몬이 상대를 만났을 때의 상성을 분석한다."""
    me = pokemon_by_id(pokemon_id)["name_ko"]
    opp = pokemon_by_id(opponent_id)["name_ko"] if opponent_id else f"{opponent_type} 타입"
    question = f"{me}이(가) {opp}을(를) 상대할 때 타입 상성은 어떤가?"
    result = run(pokemon_id, question, mode="battle", on_progress=on_progress,
                 opponent_id=opponent_id, opponent_type=opponent_type)
    result["verdict"] = read_verdict(result["answer"])
    result["opponent"] = opp
    return result
