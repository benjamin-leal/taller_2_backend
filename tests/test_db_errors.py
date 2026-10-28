"""No necesita base de datos: simula el error que entrega psycopg."""
from sqlalchemy.exc import IntegrityError

from app.shared.db_errors import integrity_to_conflict


class _Diag:
    def __init__(self, name: str) -> None:
        self.constraint_name = name


class _Orig(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.diag = _Diag(name)


def _exc(name: str) -> IntegrityError:
    return IntegrityError("INSERT ...", {}, _Orig(name))


def test_email_constraint_maps_to_email_field():
    err = integrity_to_conflict(_exc("uq_students_email"))
    assert err.status_code == 409
    assert err.detail["errors"] == {
        "email": {"message": "El correo electrónico ya está en uso"}
    }


def test_pet_constraint_maps_to_name_field():
    err = integrity_to_conflict(_exc("uq_pets_student_name"))
    assert err.detail["errors"]["name"]["message"] == "Ya tienes una mascota con ese nombre"


def test_unknown_constraint_falls_back_to_generic_409():
    err = integrity_to_conflict(_exc("otra_cosa"))
    assert err.status_code == 409
    assert "body" in err.detail["errors"]