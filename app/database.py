# Destino en el repo: app/database.py
import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Dentro de Docker el host es el nombre del servicio de la BD (en el compose
# actual: db). Fuera de Docker es localhost. Ejemplo local:
# postgresql+psycopg://taller_user:<clave>@localhost:5432/taller_backend
DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Una sesión por request. NO hace commit: quien modifica datos
    (servicio/repositorio) llama db.commit() o db.rollback(),
    así la transacción de POST /students queda en una sola unidad."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
