"""Pruebas de integración contra una BD desechable indicada por TEST_DATABASE_URL.

Ejemplo:
    TEST_DATABASE_URL=postgresql+psycopg://usuario:clave@localhost:5432/taller_test_api
"""

import asyncio
import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

TEST_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_URL:
    pytest.skip(
        "Define TEST_DATABASE_URL con una base exclusiva de pruebas",
        allow_module_level=True,
    )
assert make_url(TEST_URL).database.startswith("taller_test_"), "No usar BD de trabajo"
# app.database lee DATABASE_URL al importarse: debe apuntar a la BD de pruebas
os.environ["DATABASE_URL"] = make_url(TEST_URL).render_as_string(hide_password=False)

from alembic.config import Config  # noqa: E402

from alembic import command  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Pet, Student  # noqa: E402


@pytest.fixture(scope="module")
def engine():
    engine = create_engine(os.environ["DATABASE_URL"])
    config = Config("alembic.ini")  # alembic/env.py lee DATABASE_URL (la de pruebas)
    command.upgrade(config, "head")
    command.check(config)
    yield engine
    engine.dispose()


@pytest.fixture
def api(engine):
    def clear():
        with engine.begin() as conn:
            conn.execute(delete(Pet))
            conn.execute(delete(Student))

    clear()
    app = create_app()

    def session():
        with Session(engine, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[get_db] = session

    def request(method, path, **kwargs):
        async def call():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(call())

    yield request
    clear()


def payload(**changes):
    return {
        "name": "Ana Pérez",
        "username": "ana",
        "email": "ana@example.com",
        "age": 22,
        **changes,
    }


def create(api, **changes):
    response = api("POST", "/api/students", json=payload(**changes))
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_student_crud_persists(api, engine):
    student = create(api)
    sid = student["id"]
    with Session(engine) as db:
        assert db.get(Student, sid).name == "Ana Pérez"
    assert (
        api("GET", f"/api/students/{sid}").json()["data"]["email"] == "ana@example.com"
    )
    response = api("PATCH", f"/api/students/{sid}", json={"name": "Ana María"})
    assert response.status_code == 200
    assert api("GET", "/api/students").json()["data"]["items"][0]["name"] == "Ana María"
    assert api("DELETE", f"/api/students/{sid}").status_code == 200
    assert api("GET", f"/api/students/{sid}").status_code == 404


def test_create_with_pets_and_cascade(api, engine):
    sid = create(api, pets=[{"name": "Luna", "species": "gato"}])["id"]
    response = api("GET", f"/api/students/{sid}/pets")
    assert response.status_code == 200
    assert response.json()["data"]["items"][0]["name"] == "Luna"
    assert api("DELETE", f"/api/students/{sid}").status_code == 200
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Pet)) == 0


def test_duplicate_pet_rolls_back_entire_request(api, engine):
    response = api(
        "POST",
        "/api/students",
        json=payload(
            pets=[
                {"name": "Luna", "species": "gato"},
                {"name": "Luna", "species": "perro"},
            ]
        ),
    )
    assert response.status_code == 409
    assert "name" in response.json()["errors"]
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Student)) == 0
        assert db.scalar(select(func.count()).select_from(Pet)) == 0
    assert create(api)["username"] == "ana"


def test_pet_crud_and_ownership(api, engine):
    sid = create(api)["id"]
    other = create(api, username="otro", email="otro@example.com")["id"]
    base = f"/api/students/{sid}/pets"
    response = api("POST", base, json={"name": "Luna", "species": "gato", "age": 3})
    assert response.status_code == 201
    pet = response.json()["data"]
    pid = pet["id"]
    with Session(engine) as db:
        assert db.get(Pet, pid).studentId == sid
    assert (
        api(
            "PATCH", f"/api/students/{other}/pets/{pid}", json={"name": "Robada"}
        ).status_code
        == 404
    )
    assert api("DELETE", f"/api/students/{other}/pets/{pid}").status_code == 404
    assert (
        api("PATCH", f"{base}/{pid}", json={"name": "Sol", "age": 4}).status_code == 200
    )
    assert api("GET", base).json()["data"]["items"][0]["name"] == "Sol"
    assert api("DELETE", f"{base}/{pid}").status_code == 200
    assert api("GET", base).json()["data"]["total"] == 0


@pytest.mark.parametrize(
    "field,value", [("email", "ana@example.com"), ("username", "ana")]
)
def test_duplicate_student_returns_field_error(api, field, value):
    create(api)
    values = payload(username="otro", email="otro@example.com")
    values[field] = value
    response = api("POST", "/api/students", json=values)
    assert response.status_code == 409
    assert field in response.json()["errors"]


def test_pet_duplicates_on_create_and_update(api):
    sid = create(api)["id"]
    base = f"/api/students/{sid}/pets"
    a = api("POST", base, json={"name": "Luna", "species": "gato"})
    assert a.status_code == 201
    assert (
        api("POST", base, json={"name": "Luna", "species": "gato"}).status_code == 409
    )
    b = api("POST", base, json={"name": "Sol", "species": "perro"}).json()["data"]
    assert api("PATCH", base + "/" + b["id"], json={"name": "Luna"}).status_code == 409
    assert api("GET", base).json()["data"]["total"] == 2


@pytest.mark.parametrize("sid", ["invalid", str(uuid4())])
def test_missing_students_are_404(api, sid):
    assert api("GET", f"/api/students/{sid}").status_code == 404
    assert (
        api(
            "POST",
            f"/api/students/{sid}/pets",
            json={"name": "Luna", "species": "gato"},
        ).status_code
        == 404
    )


def test_invalid_pet_id_is_404(api):
    sid = create(api)["id"]
    assert (
        api(
            "PATCH", f"/api/students/{sid}/pets/invalid", json={"name": "Sol"}
        ).status_code
        == 404
    )


def test_validation_contract(api):
    assert api("POST", "/api/students", json=payload(age=17)).status_code == 400
    assert api("POST", "/api/students", json=payload(extra="no")).status_code == 400


def test_health_queries_database(api):
    response = api("GET", "/api/health")
    assert response.status_code == 200
    assert response.json()["data"] == {"database": "ok"}