from uuid import uuid4

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# ESPERO A: Persona 3 (ORM base). El crea el engine, SessionLocal y `get_db()`
#   (generador que entrega una Session y la cierra) en este módulo.
from app.db.session import get_db

# ESPERO A: Persona 3 (ORM base). El define `PetModel` con FK a students.id
#   (ondelete="CASCADE") y la relación inversa; los atributos deben llamarse
#   igual que en `Pet` de pets_schemas.py (studentId, createdAt, updatedAt...).
from app.pets.pets_model import PetModel
from app.shared.datetimes import utc_now
from app.shared.db_errors import integrity_to_conflict
from app.shared.exceptions import conflict
from app.shared.types import FieldErrors

# ESPERO A: Persona 3. Ver comentario en students_repository.py.
#   Además, `StudentModel.pets` debe tener cascade="all, delete-orphan":
#   de eso depende que delete() borre las mascotas sin código extra.
from app.students.students_model import StudentModel
from app.students.students_repository import StudentsRepository
from app.students.students_schemas import (
    CreateStudentDto,
    Student,
    StudentList,
    UpdateStudentDto,
)


class StudentsService:
    def __init__(self, repository: StudentsRepository) -> None:
        self.repository = repository

    def find_all(self) -> StudentList:
        students = [Student.model_validate(s) for s in self.repository.find_all()]

        return StudentList(total=len(students), items=students)

    def find_by_id(self, student_id: str) -> Student:
        return Student.model_validate(self._get_or_404(student_id))

    def create(self, data: CreateStudentDto) -> Student:
        self.assert_no_conflicts(data)

        now = utc_now()
        student = StudentModel(
            id=str(uuid4()),
            name=data.name,
            username=data.username,
            email=data.email,
            age=data.age,
            createdAt=now,
            updatedAt=now,
            # Las mascotas van por la relación: SQLAlchemy las inserta junto con el
            # estudiante en el MISMO commit (una sola transacción).
            pets=[
                PetModel(
                    id=str(uuid4()),
                    name=pet.name,
                    species=pet.species,
                    age=pet.age,
                    createdAt=now,
                    updatedAt=now,
                )
                for pet in data.pets
            ],
        )

        self.repository.add(student)
        self._commit_or_conflict()

        return Student.model_validate(student)

    def update(self, student_id: str, data: UpdateStudentDto) -> Student:
        student = self._get_or_404(student_id)
        self.assert_no_conflicts(data, except_id=student_id)

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(student, field, value)
        student.updatedAt = utc_now()

        self._commit_or_conflict()

        return Student.model_validate(student)

    def delete(self, student_id: str) -> Student:
        student = self._get_or_404(student_id)
        deleted = Student.model_validate(student)  # antes del delete: después se expira

        self.repository.delete(student)  # las mascotas caen por cascade
        self.repository.commit()

        return deleted

    def assert_no_conflicts(
        self,
        data: CreateStudentDto | UpdateStudentDto,
        except_id: str | None = None,
    ) -> None:
        errors: FieldErrors = {}

        if data.email:
            existing = self.repository.find_by_email(data.email)
            if existing and existing.id != except_id:
                errors["email"] = {"message": "El correo electrónico ya está en uso"}

        if data.username:
            existing = self.repository.find_by_username(data.username)
            if existing and existing.id != except_id:
                errors["username"] = {"message": "El nombre de usuario ya está en uso"}

        if errors:
            raise conflict(errors)

    def _get_or_404(self, student_id: str) -> StudentModel:
        student = self.repository.find_by_id(student_id)

        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estudiante no encontrado",
            )

        return student

    def _commit_or_conflict(self) -> None:
        try:
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()  # si una mascota falla, el estudiante NO queda
            raise integrity_to_conflict(exc) from exc


def get_students_service(db: Session = Depends(get_db)) -> StudentsService:
    return StudentsService(StudentsRepository(db))