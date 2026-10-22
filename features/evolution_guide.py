"""특화 기능 ② 진화 안내 (F2010).

진화 조건(레벨, 돌, 통신교환, 분기)은 이름만으로 알 수 없고, 이브이처럼 갈래가 많으면
다른 세대의 진화형을 섞기 쉽다. 근거: 메타데이터 + 해당 진화 계통 문서(항상) + 위키 청크.
"""
import json
from functools import lru_cache

from data_prep.build_item_text import pokemon_by_id
from data_prep.sprites import sprite_urls
from rag.collector import Progress, _noop
from rag.graph import run
from services.config import settings


@lru_cache(maxsize=1)
def _evo_docs() -> dict[int, dict]:
    docs = json.loads(settings.path("data", "evolution_docs.json").read_text(encoding="utf-8"))
    return {d["chain_id"]: d for d in docs}


def chain_for(pokemon_id: int) -> list[dict]:
    """화면에 계통 그림을 그릴 단계 목록 (데이터에서 읽음, 그림 주소 포함)."""
    doc = _evo_docs()[pokemon_by_id(pokemon_id)["evolution_chain_id"]]
    return [{**s, "sprite": sprite_urls(s["id"]), "current": s["id"] == pokemon_id} for s in doc["stages"]]


def next_stages(pokemon_id: int) -> list[dict]:
    """이 포켓몬이 바로 다음에 진화할 수 있는 모습들 (놀이터 진화 극장). 없으면 빈 목록."""
    return [s for s in chain_for(pokemon_id) if s["from_id"] == pokemon_id]


def guide(pokemon_id: int, on_progress: Progress = _noop) -> dict:
    """선택한 포켓몬의 진화 계통을 설명한다."""
    name = pokemon_by_id(pokemon_id)["name_ko"]
    result = run(pokemon_id, f"{name}의 진화 계통과 진화 조건은?", mode="evolution", on_progress=on_progress)
    result["chain"] = chain_for(pokemon_id)
    return result
