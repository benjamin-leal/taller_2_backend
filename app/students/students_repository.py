from sqlalchemy import select
from sqlalchemy.orm import Session

# ESPERO A: Persona 3 (ORM base).
#   El crea `StudentModel` en este módulo, con los atributos id, name, username,
#   email, age, createdAt, updatedAt (mismos nombres que `Student` en students_schemas.py)
#   y la relación `pets`. Si lo nombra o ubica distinto, solo se cambia este import.
from app.students.students_model import StudentModel


class StudentsRepository:
    """Repositorio de Student sobre SQLAlchemy."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def find_all(self) -> list[StudentModel]:
        stmt = select(StudentModel).order_by(StudentModel.createdAt.desc())
        return list(self.db.scalars(stmt))

    def find_by_id(self, student_id: str) -> StudentModel | None:
        return self.db.get(StudentModel, student_id)

    def find_by_email(self, email: str) -> StudentModel | None:
        return self.db.scalar(select(StudentModel).where(StudentModel.email == email))

    def find_by_username(self, username: str) -> StudentModel | None:
        return self.db.scalar(
            select(StudentModel).where(StudentModel.username == username)
        )

    def add(self, student: StudentModel) -> None:
        self.db.add(student)

    def delete(self, student: StudentModel) -> None:
        self.db.delete(student)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()