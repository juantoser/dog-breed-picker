from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    foundry_endpoint: str | None = None
    foundry_deployment: str | None = None
    foundry_api_version: str = "2024-10-21"
    foundry_max_tokens: int = 2000
    recommender_mode: Literal["stub", "foundry"] = "stub"

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
