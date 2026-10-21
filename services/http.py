"""외부 호출 공용 함수. 재시도·호출 간격·User-Agent 규칙을 이곳 한 군데에서 지킨다 (NF2006)."""
import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

import requests

from services.config import settings
from services.log import get_logger

log = get_logger("http")

_lock = threading.Lock()
_last_call = 0.0

# 실제로 바깥에 나간 호출 수 (캐시 덕분에 0회인지 확인할 때 씀)
call_count = 0


class UpstreamError(Exception):
    """외부 호출이 끝까지 실패했을 때 쓰는 오류."""


def _wait_interval() -> None:
    """직전 호출과 request_interval_sec 이상 간격을 둔다."""
    global _last_call
    gap = float(settings["http"]["request_interval_sec"])
    with _lock:
        wait = _last_call + gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def with_retry(func: Callable[[], Any], what: str) -> Any:
    """func를 실행하고, 실패하면 1초·2초·4초…로 늘려 가며 max_retries번까지 다시 시도한다."""
    retries = int(settings["http"]["max_retries"])
    for attempt in range(retries + 1):
        try:
            return func()
        except Exception as e:  # noqa: BLE001 — 어떤 실패든 재시도 대상
            if attempt == retries:
                log.error("%s 실패 (재시도 %d회 후): %r", what, retries, e)
                raise UpstreamError(what) from e
            delay = 2 ** attempt
            log.warning("%s 실패, %d초 뒤 다시 시도: %r", what, delay, e)
            time.sleep(delay)


def cache_name(url: str, params: dict | None = None) -> str:
    """주소와 조건을 파일 이름으로 쓸 수 있는 짧은 글자로 바꾼다."""
    key = url + "?" + json.dumps(params or {}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json"


def get_json(url: str, params: dict | None = None, cache_dir: Path | None = None,
             offline: bool = False) -> Any:
    """JSON을 받아 온다. cache_dir이 있으면 먼저 저장본을 찾고, 없을 때만 호출해서 저장한다.
    offline=True면 저장본만 쓰고 바깥으로는 호출하지 않는다."""
    global call_count
    cache_file = cache_dir / cache_name(url, params) if cache_dir else None
    if cache_file and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    if offline:
        raise UpstreamError(f"오프라인 모드인데 저장본이 없음: {url}")

    def _call():
        _wait_interval()
        resp = requests.get(
            url,
            params=params,
            headers={"User-Agent": settings["http"]["user_agent"]},
            timeout=float(settings["http"]["timeout_sec"]),
        )
        resp.raise_for_status()
        return resp.json()

    data = with_retry(_call, f"GET {url}")
    call_count += 1
    if cache_file:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data
