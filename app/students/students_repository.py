from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Student as StudentModel
from app.students.students_schemas import Student


class StudentsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_all(self) -> list[Student]:
        statement = select(StudentModel).order_by(StudentModel.createdAt.desc())
        students = self.db.scalars(statement).all()
        return [Student.model_validate(student) for student in students]

    def find_by_id(self, student_id: str) -> Student | None:
        student = self.db.get(StudentModel, student_id)
        if student is None:
            return None
        return Student.model_validate(student)

    def find_by_email(self, email: str) -> Student | None:
        statement = select(StudentModel).where(StudentModel.email == email)
        student = self.db.scalars(statement).first()
        if student is None:
            return None
        return Student.model_validate(student)

    def find_by_username(self, username: str) -> Student | None:
        statement = select(StudentModel).where(
            StudentModel.username == username
        )
        student = self.db.scalars(statement).first()
        if student is None:
            return None
        return Student.model_validate(student)

    def save(self, student: Student) -> Student:
        student_db = self.db.get(StudentModel, student.id)

        if student_db is None:
            student_db = StudentModel(
                id=student.id,
                name=student.name,
                username=student.username,
                email=str(student.email),
                age=student.age,
                createdAt=student.createdAt,
                updatedAt=student.updatedAt,
            )
            self.db.add(student_db)
        else:
            student_db.name = student.name
            student_db.username = student.username
            student_db.email = str(student.email)
            student_db.age = student.age
            student_db.updatedAt = student.updatedAt

        self.db.flush()
        return Student.model_validate(student_db)

    def delete(self, student_id: str) -> None:
        student = self.db.get(StudentModel, student_id)
        if student is not None:
            self.db.delete(student)
            self.db.flush()
