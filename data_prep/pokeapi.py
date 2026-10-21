"""PokéAPI 호출 도우미. 받은 응답은 모두 cache/pokeapi/ 에 저장해서 다시 쓴다 (PokéAPI 공정 이용 규칙)."""
from services.config import settings
from services.http import get_json

BASE = "https://pokeapi.co/api/v2"
CACHE = settings.path("cache", "pokeapi")


def fetch(path_or_url: str) -> dict:
    """'/pokemon/6' 같은 경로나 전체 주소를 받아 JSON을 돌려준다(캐시 우선)."""
    url = path_or_url if path_or_url.startswith("http") else BASE + path_or_url
    if not url.endswith("/"):
        url += "/"
    return get_json(url, cache_dir=CACHE)


def id_from_url(url: str) -> int:
    """'.../pokemon-species/133/' 에서 133을 꺼낸다."""
    return int(url.rstrip("/").split("/")[-1])


def name_in(entries: list[dict], lang: str = "ko", key: str = "name") -> str | None:
    """names 목록에서 원하는 언어의 값을 찾는다. 없으면 None."""
    for e in entries:
        if e["language"]["name"] == lang:
            return e[key]
    return None


def ko_name(resource: str, name: str) -> tuple[str, bool]:
    """타입·특성·도구 같은 자원의 한국어 이름. 없으면 (영어 이름, True=한국어 없음)."""
    data = fetch(f"/{resource}/{name}")
    ko = name_in(data.get("names", []))
    if ko:
        return ko, False
    return name_in(data.get("names", []), "en") or name, True


GEN_NO = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9}


def gen_number(generation_name: str) -> int:
    """'generation-ii' → 2"""
    return GEN_NO[generation_name.split("-")[1]]
