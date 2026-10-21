"""채팅 모델과 임베딩 모델을 만든다. SSAFY GMS(OpenAI 호환) 주소와 키를 환경변수에서 넘긴다."""
from functools import lru_cache

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from services.config import settings
from services.http import with_retry


class ApiKeyMissing(Exception):
    """GMS_API_KEY가 비어 있을 때 쓰는 오류."""


def _check_key() -> None:
    if not settings.has_api_key():
        raise ApiKeyMissing()


@lru_cache(maxsize=4)
def get_chat(temperature: float) -> ChatOpenAI:
    """채팅 모델. 같은 온도면 한 번 만든 것을 다시 쓴다."""
    _check_key()
    return ChatOpenAI(
        model=settings["llm"]["chat_model"],
        temperature=temperature,
        api_key=settings.api_key,
        base_url=settings.base_url or None,
        timeout=float(settings["http"]["timeout_sec"]) * 4,
        max_retries=0,  # 재시도는 services/http.py 규칙으로 한 곳에서
    )


@lru_cache(maxsize=1)
def get_embeddings() -> OpenAIEmbeddings:
    """임베딩 모델(글을 숫자 목록으로 바꾸는 모델)."""
    _check_key()
    return OpenAIEmbeddings(
        model=settings["llm"]["embedding_model"],
        api_key=settings.api_key,
        base_url=settings.base_url or None,
        max_retries=0,
    )


def ask_llm(prompt: str, temperature: float | None = None) -> str:
    """프롬프트 하나를 보내고 답 글자만 돌려준다. 실패하면 재시도 규칙을 따른다."""
    if temperature is None:
        temperature = float(settings["llm"]["tool_temperature"])
    chat = get_chat(temperature)
    msg = with_retry(lambda: chat.invoke(prompt), "LLM 호출")
    return msg.content if isinstance(msg.content, str) else str(msg.content)
