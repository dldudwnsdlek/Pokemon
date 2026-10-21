"""한국어 위키백과 검색·요약·본문 가져오기 (F2004).

모든 호출은 services/http.py를 거쳐 User-Agent(연락처)·호출 간격·재시도 규칙을 지킨다 (NF2006).
본문 원본은 cache/wiki/<pageid>.json에 저장해 다시 쓴다 (NF2002).
"""
import json
import re
from datetime import date

from services.config import settings
from services.http import get_json

API = "https://ko.wikipedia.org/w/api.php"
CACHE = settings.path("cache", "wiki")

# 이 제목의 단락부터 뒤쪽은 버린다 (본문이 아닌 목록·각주)
CUT_SECTIONS = ["같이 보기", "각주", "외부 링크", "참고 자료", "참고 문헌", "각주 및 참고 문헌"]


def _api(params: dict, sub: str) -> dict:
    """위키백과 API 호출 (응답은 cache/wiki/<sub>/ 에 저장)."""
    full = {"format": "json", "formatversion": 2, **params}
    return get_json(API, params=full, cache_dir=CACHE / sub,
                    offline=bool(settings["collect"].get("offline")))


def page_url(pageid: int) -> str:
    """원문 주소."""
    return f"https://ko.wikipedia.org/?curid={pageid}"


def search(query: str, limit: int) -> list[dict]:
    """검색어로 후보 문서의 pageid·제목을 모은다."""
    data = _api({"action": "query", "list": "search", "srsearch": query, "srlimit": limit}, "search")
    return [{"pageid": r["pageid"], "title": r["title"]} for r in data.get("query", {}).get("search", [])]


def summaries(pageids: list[int]) -> dict[int, str]:
    """선별용 짧은 요약(첫 단락)을 summary_chars 글자로 잘라 돌려준다."""
    if not pageids:
        return {}
    limit = int(settings["collect"]["summary_chars"])
    data = _api({"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
                 "exlimit": "max", "pageids": "|".join(map(str, pageids))}, "summary")
    out = {}
    for p in data.get("query", {}).get("pages", []):
        text = re.sub(r"\s+", " ", p.get("extract", "")).strip()
        out[p["pageid"]] = text[:limit]
    return out


def find_item_page(name_ko: str) -> tuple[dict | None, str]:
    """선택한 포켓몬 자체를 다룬 문서를 찾는다. 결과: ({pageid, title} 또는 None, 이유).

    '팬텀'처럼 이름이 동음이의어 문서면 '팬텀 (포켓몬)'을 쓰고,
    '꼬렛'처럼 표로만 된 목록 문서로 넘어가면 단독 문서가 없는 것으로 본다.
    """
    titles = [f"{name_ko} (포켓몬)", name_ko]
    data = _api({"action": "query", "titles": "|".join(titles), "redirects": 1,
                 "prop": "pageprops", "ppprop": "disambiguation"}, "titles")
    q = data.get("query", {})
    redirects = {r["from"]: r for r in q.get("redirects", [])}
    pages = {p["title"]: p for p in q.get("pages", []) if not p.get("missing")}

    for t in titles:
        target = redirects.get(t, {}).get("to", t)
        page = pages.get(target)
        if not page or "disambiguation" in page.get("pageprops", {}):
            continue
        if redirects.get(t, {}).get("tofragment") or "포켓몬 목록" in target:
            continue  # 표로만 된 목록 문서로 넘어감
        if name_ko not in target:
            continue  # 다른 포켓몬 문서로 넘어감 (예: 신뇽 → 망나뇽)
        if "포켓몬" not in summaries([page["pageid"]]).get(page["pageid"], "") + page["title"]:
            continue  # 같은 이름의 다른 주제 문서
        return {"pageid": page["pageid"], "title": page["title"]}, "found"
    return None, "위키백과에 이 포켓몬만 다룬 문서가 없어요"


def clean_text(text: str) -> str:
    """'같이 보기', '각주', '외부 링크' 이후를 버리고 빈 줄을 하나로 줄인다."""
    for name in CUT_SECTIONS:
        m = re.search(rf"^=+ ?{re.escape(name)} ?=+\s*$", text, re.M)
        if m:
            text = text[:m.start()]
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def fetch_page(pageid: int) -> dict:
    """문서 본문을 가져온다. 이미 저장해 둔 본문이 있으면 그것을 쓴다."""
    path = CACHE / f"{pageid}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    data = _api({"action": "query", "prop": "extracts", "explaintext": 1,
                 "exsectionformat": "wiki", "pageids": pageid}, "body")
    p = data["query"]["pages"][0]
    page = {
        "pageid": pageid,
        "title": p["title"],
        "text": clean_text(p.get("extract", "")),
        "url": page_url(pageid),
        "collected_at": date.today().isoformat(),
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(page, ensure_ascii=False), encoding="utf-8")
    return page
