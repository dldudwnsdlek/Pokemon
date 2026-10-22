"""연구소 놀이터 — 포켓몬과 대화하기, 나는 어떤 포켓몬일까 (성격 테스트).

둘 다 위키 검색 없이 도감 데이터만 쓴다. 근거 번호를 붙이는 RAG 답변이 아니라 놀이용이라
"자료에 없는 사실은 지어내지 않는다"는 규칙만 프롬프트에 둔다.
"""
from data_prep.build_item_text import category, item_text, load_pokemon, pokemon_by_id
from data_prep.sprites import sprite_urls
from rag import prompts
from services.config import settings
from services.errors import ServiceError
from services.llm import ask_llm


def talk(pokemon_id: int, message: str, history: list[dict]) -> dict:
    """고른 포켓몬이 1인칭으로 대답한다. history: [{"role": "user"|"pokemon", "text": ...}]"""
    p = pokemon_by_id(pokemon_id)
    keep = int(settings["play"]["talk_history_turns"])
    lines = [f"{'트레이너' if h['role'] == 'user' else p['name_ko']}: {h['text']}" for h in history[-keep:]]
    prompt = prompts.TALK.format(name_ko=p["name_ko"], item_text=item_text(p),
                                 history="\n".join(lines) or "(처음 만남)", message=message)
    reply = ask_llm(prompt, float(settings["play"]["talk_temperature"])).strip()
    return {"reply": reply}


def persona(answers: list[dict]) -> dict:
    """성격 테스트 답 → 닮은 포켓몬 1마리와 이유."""
    answer_lines = "\n".join(f"- {a['q']} → {a['a']}" for a in answers)
    candidates = "\n".join(f"{p['id']}. {p['name_ko']} ({'/'.join(p['types'])}, {p['genus_ko']}, {category(p)})"
                           for p in load_pokemon())
    prompt = prompts.PERSONA.format(answers=answer_lines, candidates=candidates)
    temp = float(settings["play"]["persona_temperature"])
    picked = prompts.ask_json_array(prompt, lambda text: ask_llm(text, temp))
    for item in picked or []:
        try:
            pid = int(item["id"])
        except (TypeError, KeyError, ValueError):
            continue
        p = pokemon_by_id(pid)
        if p:  # 목록 밖 번호는 버린다
            return {"id": pid, "dex_no": p["dex_no"], "name_ko": p["name_ko"], "types": p["types"],
                    "genus_ko": p["genus_ko"], "sprite": sprite_urls(pid), "reason": str(item.get("reason", ""))}
    raise ServiceError("UPSTREAM_ERROR")  # 형식이 두 번 다 틀리면 다시 시도하도록 안내
