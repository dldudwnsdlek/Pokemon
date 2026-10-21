"""API 서버 (F2013). 화면(web/)과 서버를 나누고, 같은 주소에서 web/ 파일도 함께 내려준다.

실행: uvicorn api.server:app --reload → http://localhost:8000
"""
import json
import mimetypes
import queue
import threading
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from data_prep.build_item_text import load_pokemon, pokemon_by_id
from data_prep.finder_terms import type_names
from data_prep.sprites import sprite_urls
from features import battle_coach, evolution_guide, finder
from rag.collector import collected_titles, load_registry
from rag.graph import check_ready, run
from rag.retriever import retrieve
from services.config import settings
from services.errors import ServiceError
from services.http import UpstreamError
from services.llm import ApiKeyMissing
from services.log import get_logger
from store.vector_store import DOCS, META, count

log = get_logger("api")
app = FastAPI(title="오박사의 연구노트 API", version="1.0")


# ---------- 요청 형식 (pydantic으로 검사) ----------
class AskRequest(BaseModel):
    pokemon_id: int = Field(ge=1)
    question: str = Field(min_length=1, max_length=500)


class BattleRequest(BaseModel):
    pokemon_id: int = Field(ge=1)
    opponent_id: int | None = Field(default=None, ge=1)
    opponent_type: str | None = None


class EvolutionRequest(BaseModel):
    pokemon_id: int = Field(ge=1)


class FindRequest(BaseModel):
    condition: str = Field(min_length=1, max_length=500)


class CompareRequest(BaseModel):
    pokemon_id: int = Field(ge=1)
    question: str = Field(min_length=1, max_length=500)
    top_k: int | None = Field(default=None, ge=1, le=20)


# ---------- 오류 응답 (모든 주소 공통, NF2004: 키·프롬프트·traceback·경로 비노출) ----------
@app.exception_handler(ServiceError)
async def service_error(_: Request, e: ServiceError):
    return JSONResponse(e.to_dict(), status_code=e.status)


@app.exception_handler(RequestValidationError)
async def bad_request(_: Request, e: RequestValidationError):
    log.info("요청 형식 오류: %s", e.errors())
    err = ServiceError("BAD_REQUEST")
    return JSONResponse(err.to_dict(), status_code=err.status)


@app.exception_handler(Exception)
async def internal_error(_: Request, e: Exception):
    log.exception("처리 중 오류")
    err = ServiceError("INTERNAL")
    return JSONResponse(err.to_dict(), status_code=err.status)


def _as_service_error(e: Exception) -> ServiceError:
    if isinstance(e, ServiceError):
        return e
    if isinstance(e, ApiKeyMissing):
        return ServiceError("API_KEY_MISSING")
    if isinstance(e, UpstreamError):
        return ServiceError("UPSTREAM_ERROR")
    log.exception("처리 중 오류", exc_info=e)
    return ServiceError("INTERNAL")


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream(job: Callable[[Callable], dict]) -> StreamingResponse:
    """job을 따로 실행하면서 진행 상태(progress)를 한 줄씩 보내고, 끝나면 결과(result)를 보낸다."""
    q: queue.Queue = queue.Queue()

    def progress(step: str, message: str, detail=None) -> None:
        q.put(("progress", {"step": step, "message": message, "detail": detail}))

    def worker() -> None:
        try:
            q.put(("result", job(progress)))
        except Exception as e:  # noqa: BLE001
            q.put(("error", _as_service_error(e).to_dict()))
        q.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def events():
        while (item := q.get()) is not None:
            yield _sse(*item)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _summary(p: dict) -> dict:
    return {"id": p["id"], "dex_no": p["dex_no"], "name_ko": p["name_ko"], "types": p["types"],
            "is_legendary": p["is_legendary"], "is_mythical": p["is_mythical"], "sprite": sprite_urls(p["id"])}


def _get_pokemon(pid: int) -> dict:
    lo, hi = settings["scope"]["dex_from"], settings["scope"]["dex_to"]
    p = pokemon_by_id(pid) if lo <= pid <= hi else None
    if p is None:
        raise ServiceError("OUT_OF_SCOPE")
    return p


# ---------- 엔드포인트 ----------
@app.get("/api/status")  # F2002, F2012
def status():
    reg = load_registry()
    return {
        "meta_count": count(META),
        "doc_count": count(DOCS),
        "collected_docs": sum(len(d) for d in reg["docs"].values()),
        "api_key": settings.has_api_key(),
        "search_type": settings["retrieval"]["search_type"],
    }


@app.get("/api/pokemon")  # F2009
def pokemon_list():
    return {"pokemon": [_summary(p) for p in load_pokemon()], "types": type_names()}


@app.get("/api/pokemon/{pid}")  # F2009
def pokemon_detail(pid: int):
    p = _get_pokemon(pid)
    return {**_summary(p), "genus_ko": p["genus_ko"], "abilities": p["abilities"],
            "height_m": p["height_m"], "weight_kg": p["weight_kg"], "stats": p["stats"],
            "evolution": p["evolution"], "flavor_ko": p["flavor_ko"],
            "chain": evolution_guide.chain_for(pid), "collected_titles": collected_titles(pid)}


@app.post("/api/ask")  # F2003~F2008, F2012
def ask(req: AskRequest):
    check_ready(req.pokemon_id)
    return stream(lambda prog: run(req.pokemon_id, req.question.strip(), "chat", on_progress=prog))


@app.post("/api/battle")  # F2010
def battle(req: BattleRequest):
    check_ready(req.pokemon_id)
    if req.opponent_id:
        _get_pokemon(req.opponent_id)
    elif req.opponent_type not in type_names():
        raise ServiceError("BAD_REQUEST")
    return stream(lambda prog: battle_coach.coach(req.pokemon_id, req.opponent_id,
                                                  None if req.opponent_id else req.opponent_type, prog))


@app.post("/api/evolution")  # F2010
def evolution(req: EvolutionRequest):
    check_ready(req.pokemon_id)
    return stream(lambda prog: evolution_guide.guide(req.pokemon_id, prog))


@app.post("/api/find")  # F2011
def find(req: FindRequest):
    return finder.find(req.condition.strip())


@app.post("/api/compare-search")  # F2014 — 같은 질문의 유사도/MMR 근거 목록 나란히
def compare_search(req: CompareRequest):
    check_ready(req.pokemon_id)

    def brief(evidence: list[dict]) -> list[dict]:
        return [{"no": e["no"], "id": e["id"], "title": e["title"], "source_type": e["source_type"],
                 "source_label": e["source_label"], "url": e["url"],
                 "snippet": e["text"].split("\n", 1)[-1][:120]} for e in evidence]

    try:
        sim = retrieve(req.pokemon_id, req.question, top_k=req.top_k, search_type="similarity")
        mmr = retrieve(req.pokemon_id, req.question, top_k=req.top_k, search_type="mmr")
    except Exception as e:  # noqa: BLE001
        raise _as_service_error(e) from e
    sim_ids, mmr_ids = {e["id"] for e in sim}, {e["id"] for e in mmr}
    return {
        "similarity": brief(sim),
        "mmr": brief(mmr),
        "shared": len(sim_ids & mmr_ids),
        "distinct_docs": {"similarity": len({e["title"] for e in sim}), "mmr": len({e["title"] for e in mmr})},
    }


# web/ 파일 내려주기 (API 주소들 뒤에 둔다).
# 윈도우는 레지스트리 설정에 따라 .js를 text/plain으로 알려 줄 수 있어 직접 지정한다.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
app.mount("/", StaticFiles(directory=str(settings.path("web")), html=True), name="web")
