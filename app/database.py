"""Configuración PostgreSQL y sesiones compartidas por FastAPI y Alembic."""

from collections.abc import Generator
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import Session


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    POSTGRES_USER: str = Field(min_length=1)
    POSTGRES_PASSWORD: SecretStr = Field(min_length=1, repr=False)
    POSTGRES_DB: str = Field(min_length=1)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)

    @property
    def url(self) -> URL:
        # URL.create conserva contraseñas con @, %, /, etc. sin concatenarlas.
        return URL.create(
            "postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD.get_secret_value(),
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        )


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        DatabaseSettings().url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


def get_session() -> Generator[Session]:
    # Cada petición tiene su sesión; cerrar revierte cambios no confirmados.
    # El servicio será responsable de delimitar y confirmar su transacción.
    with Session(get_engine()) as session:
        yield session
