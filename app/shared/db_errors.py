"""Traducción de IntegrityError (SQLAlchemy/PostgreSQL) al 409 con formato `errors`.

AUTÓNOMO: no importa modelos ni sesión, así que se puede fusionar sin romper main.
"""
from typing import Final

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.shared.exceptions import conflict

# ESPERO A: Persona 3 (ORM base).
#   El define las constraints en los modelos y en la migración de Alembic.
#   Para que este mapa funcione, debe nombrarlas EXACTAMENTE así (name="..."):
#     - UniqueConstraint("email",              name="uq_students_email")
#     - UniqueConstraint("username",           name="uq_students_username")
#     - UniqueConstraint("studentId", "name",  name="uq_pets_student_name")
#   Si el usa otros nombres, solo se edita este diccionario (no hay que tocar nada más).
CONSTRAINT_ERRORS: Final[dict[str, tuple[str, str]]] = {
    "uq_students_email": ("email", "El correo electrónico ya está en uso"),
    "uq_students_username": ("username", "El nombre de usuario ya está en uso"),
    "uq_pets_student_name": ("name", "Ya tienes una mascota con ese nombre"),
}


def integrity_to_conflict(exc: IntegrityError) -> HTTPException:
    """Convierte IntegrityError en el 409 con el formato `errors` que ya usa la API."""
    diag = getattr(exc.orig, "diag", None)
    constraint = getattr(diag, "constraint_name", None)
    field, message = CONSTRAINT_ERRORS.get(constraint or "", (None, None))

    if field is None or message is None:
        return conflict({"body": {"message": "Conflicto con datos existentes"}})

    return conflict({field: {"message": message}})