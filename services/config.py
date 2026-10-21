"""config.yaml과 .env를 읽어 프로그램 전체가 함께 쓰는 설정(settings)을 만든다."""
import copy
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# 프로젝트 맨 위 폴더 (이 파일의 두 단계 위)
ROOT = Path(__file__).resolve().parent.parent

load_dotenv(ROOT / ".env")


class Settings(dict):
    """설정 묶음. settings["chunk"]["size"]처럼 읽는다. 출력할 때 키 값은 감춘다."""

    @property
    def api_key(self) -> str:
        # NF2003: API 키는 환경변수에서만 읽는다
        return os.getenv("GMS_API_KEY", "").strip()

    @property
    def base_url(self) -> str:
        return os.getenv("GMS_BASE_URL", "").strip()

    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def path(self, *parts: str) -> Path:
        """프로젝트 기준 경로를 만든다."""
        return ROOT.joinpath(*parts)

    def __repr__(self) -> str:
        # NF2004: 키 값은 절대 보여주지 않고 "있음/없음"만 표시
        shown = copy.deepcopy(dict(self))
        shown["secrets"] = {
            "GMS_API_KEY": "설정됨" if self.has_api_key() else "없음",
            "GMS_BASE_URL": self.base_url or "없음",
        }
        return yaml.safe_dump(shown, allow_unicode=True, sort_keys=False)

    __str__ = __repr__


def load_settings() -> Settings:
    """config.yaml을 읽어 Settings로 돌려준다."""
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return Settings(yaml.safe_load(f))


settings = load_settings()
