"""서버 로그(logs/app.log) 설정. 자세한 오류는 여기에만 남긴다 (NF2004)."""
import logging

from services.config import settings

_LOG_PATH = settings.path("logs", "app.log")
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """파일에 기록하는 로거를 돌려준다."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.FileHandler(_LOG_PATH, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
