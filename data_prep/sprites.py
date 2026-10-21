"""포켓몬 그림 주소. 그림은 저장소에 복사하지 않고 PokéAPI sprites 저장소 주소로 불러온다."""

BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"


def sprite_urls(pokemon_id: int) -> dict:
    """움직이는 5세대 GIF와, 실패할 때 쓸 정지 그림 주소."""
    return {
        "animated": f"{BASE}/versions/generation-v/black-white/animated/{pokemon_id}.gif",
        "static": f"{BASE}/{pokemon_id}.png",
    }
