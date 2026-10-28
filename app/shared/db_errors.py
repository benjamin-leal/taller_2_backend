"""Traducción de IntegrityError (SQLAlchemy/PostgreSQL) al 409 con formato `errors`.
"""

from typing import Final

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.shared.exceptions import conflict

CONSTRAINT_ERRORS: Final[dict[str, tuple[str, str]]] = {
    "students_email_key": ("email", "El correo electrónico ya está en uso"),
    "students_username_key": ("username", "El nombre de usuario ya está en uso"),
    "uq_pet_student_name": ("name", "Ya tienes una mascota con ese nombre"),
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