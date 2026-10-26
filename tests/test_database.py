import asyncio
import os
from uuid import uuid4

import httpx
import pytest
from alembic.config import Config
from sqlalchemy import create_engine, delete, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.database import DatabaseSettings, get_session
from app.main import create_app
from app.models import PetModel, StudentModel
from app.students.students_schemas import Student


def test_connection_url_preserves_special_characters():
    settings = DatabaseSettings(
        _env_file=None,
        POSTGRES_USER="jose",
        POSTGRES_PASSWORD="p@ss:/%#word",
        POSTGRES_DB="taller",
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5433,
    )
    assert settings.url.password == "p@ss:/%#word"
    assert settings.url.port == 5433
    assert settings.url.database == "taller"
    assert "p@ss:/%#word" not in repr(settings)


@pytest.fixture(scope="module")
def engine():
    name = os.environ.get("TEST_POSTGRES_DB")
    if not name:
        pytest.skip("Define TEST_POSTGRES_DB para probar PostgreSQL real")
    assert name.startswith("taller_test_"), "Usa una BD de pruebas aislada"
    engine = create_engine(DatabaseSettings().url.set(database=name))
    assert engine.url.database.startswith("taller_test_"), (
        "Usa una BD de pruebas aislada"
    )
    config = Config("alembic.ini")
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        command.check(config)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(
            bind=connection, join_transaction_mode="create_savepoint"
        ) as session:
            yield session
        transaction.rollback()


def student(**values):
    return StudentModel(
        name="José Sepúlveda",
        username="jose",
        email="jose@example.com",
        age=22,
        **values,
    )


def test_migration_creates_tables(engine):
    assert {"students", "pets", "alembic_version"} <= set(
        inspect(engine).get_table_names()
    )


def test_models_save_relationship_and_match_api_schema(session):
    owner = student(pets=[PetModel(name="Luna", species="gato")])
    session.add(owner)
    session.flush()
    session.expire_all()
    loaded = session.scalar(select(StudentModel))
    assert Student.model_validate(loaded).name == "José Sepúlveda"
    assert loaded.pets[0].studentId == loaded.id
    assert loaded.pets[0].age is None
    assert loaded.createdAt.tzinfo is not None


@pytest.mark.parametrize("field", ["username", "email"])
def test_student_unique_fields(session, field):
    session.add(student())
    session.flush()
    other = student()
    other.username = "otro"
    other.email = "otro@example.com"
    setattr(other, field, "jose" if field == "username" else "jose@example.com")
    session.add(other)
    with pytest.raises(IntegrityError):
        session.flush()


def test_duplicate_pet_rolls_back_student(session):
    owner = student(
        pets=[
            PetModel(name="Luna", species="gato"),
            PetModel(name="Luna", species="perro"),
        ]
    )
    session.add(owner)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
    assert session.scalar(select(StudentModel)) is None
    assert session.scalar(select(PetModel)) is None


def test_pet_name_allowed_for_different_owners(session):
    first = student(pets=[PetModel(name="Luna", species="gato")])
    second = StudentModel(
        name="Ana Pérez",
        username="ana",
        email="ana@example.com",
        age=21,
        pets=[PetModel(name="Luna", species="gato")],
    )
    session.add_all([first, second])
    session.flush()
    assert len(session.scalars(select(PetModel)).all()) == 2


def test_deleting_student_cascades_in_database(session):
    owner = student(pets=[PetModel(name="Luna", species="gato")])
    session.add(owner)
    session.flush()
    session.execute(delete(StudentModel).where(StudentModel.id == owner.id))
    assert session.scalar(select(PetModel)) is None


def test_pet_requires_existing_student(session):
    session.add(PetModel(name="Luna", species="gato", studentId=str(uuid4())))
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("age", [17, 100])
def test_student_age_constraint(session, age):
    owner = student()
    owner.age = age
    session.add(owner)
    with pytest.raises(IntegrityError):
        session.flush()


def test_health_route_uses_database(session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    response = health_request(app)
    assert response.status_code == 200
    assert response.json()["data"] == {"database": "ok"}


def test_health_failure_does_not_expose_credentials():
    unavailable = create_engine(
        "postgresql+psycopg://secret_user:secret_pass@127.0.0.1:1/missing",
        connect_args={"connect_timeout": 1},
    )
    app = create_app()

    def failed_session():
        with Session(unavailable) as session:
            yield session

    app.dependency_overrides[get_session] = failed_session
    try:
        response = health_request(app)
        assert response.status_code == 503
        assert "secret_pass" not in response.text
        assert "secret_user" not in response.text
    finally:
        unavailable.dispose()


def health_request(app):
    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.get("/api/health/database")

    return asyncio.run(request())
