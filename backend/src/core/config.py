import logging
from typing import Any, Dict, List, Optional

from pydantic import AnyHttpUrl, BaseSettings, Field, PostgresDsn, validator


class Settings(BaseSettings):
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    # SERVER_NAME: Optional[str] = Field(..., env="NGINX_HOST")
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    LOG_LEVEL: int = Field(default=logging.INFO, env="LOG_LEVEL")

    VERSION: str = Field(default="", env="VERSION")
    DEBUG: bool = Field(default=True, env="DEBUG")

    POSTGRES_USER: str = Field(default="", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(default="", env="POSTGRES_PASSWORD")
    POSTGRES_HOST: str = Field(default="", env="POSTGRES_HOST")
    POSTGRES_PORT: str = Field(default="", env="POSTGRES_PORT")
    POSTGRES_DB: str = Field(default="", env="POSTGRES_DB")

    REDIS_HOST: str = Field(default="", env="REDIS_HOST")
    REDIS_PORT: str = Field(default="", env="REDIS_PORT")

    DB_POOL_SIZE: int = Field(default=83, env="DB_POOL_SIZE")
    WEB_CONCURRENCY: int = Field(default=9, env="WEB_CONCURRENCY")
    MAX_OVERFLOW: int = Field(default=64, env="MAX_OVERFLOW")
    POOL_SIZE: Optional[int]
    POSTGRES_URL: Optional[str]
    
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    PINECONE_API_KEY:str = Field(default="", env="PINECONE_API_KEY")
    PINECONE_ENV:str = Field(default="", env="PINECONE_ENV")
    TAUTULLI_API_KEY:str = Field(default="", env="TAUTULLI_API_KEY")
    TAUTULLI_URL:str = Field(default="tautulli", env="TAUTULLI_URL")
    TVDB_API_KEY:str = Field(default="", env="TVDB_API_KEY")
    PLEX_URL:str = Field(default="plex", env="PLEX_URL")
    PLEX_TOKEN:str = Field(default="", env="PLEX_TOKEN")
    @validator("POOL_SIZE", pre=True)
    def build_pool(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, int):
            return v

        return max(values.get("DB_POOL_SIZE") // values.get("WEB_CONCURRENCY"), 5)  # type: ignore

    @validator("POSTGRES_URL", pre=True)
    def build_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v

        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_HOST"),
            port=str(values.get("POSTGRES_PORT")),
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )


settings = Settings()
