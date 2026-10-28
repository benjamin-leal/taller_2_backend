# ESPERO A: Persona 3 (modelos + migración Alembic) y Persona 1 (compose con PostgreSQL).
#   Estas pruebas NO corren hasta que:
#     1) el PR de la Persona 3 esté en main (get_db, StudentModel, PetModel, migración),
#     2) la base esté arriba:  docker compose up -d db   (compose de la Persona 1),
#     3) se haya corrido:      alembic upgrade head
#   Si falta algo de esto, fallarán por import o por conexión: no es un bug del código.
"""Pruebas de transacción y cascade. Requieren PostgreSQL levantado (docker compose up -d db)
y las migraciones aplicadas (alembic upgrade head). Ejecutar desde la raíz del repo."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import get_db  # ajustar
from app.main import app
from app.pets.pets_model import PetModel  # ajustar

client = TestClient(app)


def student_payload(**overrides):
    base = {"name": "Ana Pérez", "username": "ana_perez", "email": "ana@example.com", "age": 20}
    return {**base, **overrides}


@pytest.fixture(autouse=True)
def clean_db():
    def wipe():
        for s in client.get("/api/students").json()["data"]["items"]:
            client.delete(f"/api/students/{s['id']}")

    wipe()
    yield
    wipe()


def test_create_student_with_pets_is_atomic_ok():
    res = client.post(
        "/api/students",
        json=student_payload(pets=[{"name": "Firulais", "species": "perro", "age": 3}]),
    )
    assert res.status_code == 201

    db = next(get_db())
    assert db.scalar(select(func.count()).select_from(PetModel)) == 1


def test_rollback_when_a_pet_fails():
    """Dos mascotas con el mismo nombre -> 409 y el estudiante NO debe quedar creado."""
    res = client.post(
        "/api/students",
        json=student_payload(
            pets=[
                {"name": "Luna", "species": "gato"},
                {"name": "Luna", "species": "perro"},
            ]
        ),
    )
    assert res.status_code == 409
    assert "name" in res.json()["errors"]

    assert client.get("/api/students").json()["data"]["total"] == 0
    db = next(get_db())
    assert db.scalar(select(func.count()).select_from(PetModel)) == 0


def test_duplicate_email_returns_409():
    client.post("/api/students", json=student_payload())
    res = client.post("/api/students", json=student_payload(username="otro_user"))
    assert res.status_code == 409
    assert res.json()["errors"]["email"]["message"] == "El correo electrónico ya está en uso"


def test_delete_student_cascades_to_pets():
    created = client.post(
        "/api/students",
        json=student_payload(pets=[{"name": "Rex", "species": "perro"}]),
    ).json()["data"]

    assert client.delete(f"/api/students/{created['id']}").status_code == 200

    db = next(get_db())
    assert db.scalar(select(func.count()).select_from(PetModel)) == 0