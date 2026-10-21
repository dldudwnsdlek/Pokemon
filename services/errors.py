"""화면에 보여줄 수 있는 오류 종류와 안내 문구 (F2012, NF2004).

문구에는 키, 프롬프트, traceback, 파일 경로를 절대 넣지 않는다.
"""

MESSAGES = {
    "INDEX_EMPTY": "아직 도감이 비어 있어요. 터미널에서 python -m scripts.build_index 를 실행한 뒤 새로고침해 주세요.",
    "API_KEY_MISSING": "연구소 열쇠(API 키)가 설정되지 않았어요. .env 파일에 GMS_API_KEY 를 넣고 서버를 다시 켜 주세요.",
    "NO_RESULTS": "관련 자료를 찾지 못했어요. 질문을 조금 바꿔 보시겠어요?",
    "OUT_OF_SCOPE": "이 노트는 관동지방 1세대(1~151번) 포켓몬만 다뤄요.",
    "UPSTREAM_ERROR": "자료실 연결이 잠시 불안정해요. 잠시 후 다시 시도해 주세요.",
    "INTERNAL": "노트를 넘기다 문제가 생겼어요. 잠시 후 다시 시도해 주세요.",
    "BAD_REQUEST": "요청 형식이 맞지 않아요. 입력한 내용을 확인해 주세요. (질문은 1~500자)",
}

HTTP_STATUS = {
    "INDEX_EMPTY": 503,
    "API_KEY_MISSING": 503,
    "NO_RESULTS": 200,
    "OUT_OF_SCOPE": 400,
    "UPSTREAM_ERROR": 502,
    "INTERNAL": 500,
    "BAD_REQUEST": 400,
}


class ServiceError(Exception):
    """화면에 안내할 수 있는 오류. code로 문구와 HTTP 상태를 정한다."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
        self.message = MESSAGES[code]
        self.status = HTTP_STATUS[code]

    def to_dict(self) -> dict:
        return {"error": {"code": self.code, "message": self.message}}
