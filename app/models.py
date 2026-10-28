from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("age >= 18 AND age <= 99", name="ck_student_age"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(nullable=False)
    updatedAt: Mapped[datetime] = mapped_column(nullable=False)

    pets: Mapped[list["Pet"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Pet(Base):
    __tablename__ = "pets"
    __table_args__ = (
        UniqueConstraint("studentId", "name", name="uq_pet_student_name"),
        CheckConstraint(
            "age IS NULL OR (age >= 0 AND age <= 100)",
            name="ck_pet_age",
        ),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    studentId: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(nullable=False)
    updatedAt: Mapped[datetime] = mapped_column(nullable=False)

    student: Mapped["Student"] = relationship(back_populates="pets")
