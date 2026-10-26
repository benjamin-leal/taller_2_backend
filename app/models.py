"""Modelos persistentes; los DTO de la API siguen en sus módulos actuales."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.shared.datetimes import utc_now


class Base(DeclarativeBase):
    pass


class StudentModel(Base):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("username", name="uq_students_username"),
        UniqueConstraint("email", name="uq_students_email"),
        CheckConstraint("age BETWEEN 18 AND 99", name="ck_students_age"),
    )

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(254))
    age: Mapped[int]
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime(timezone=True), default=utc_now
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    pets: Mapped[list["PetModel"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PetModel(Base):
    __tablename__ = "pets"
    __table_args__ = (
        UniqueConstraint("student_id", "name", name="uq_pets_student_name"),
        CheckConstraint("age BETWEEN 0 AND 100", name="ck_pets_age"),
    )

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    studentId: Mapped[str] = mapped_column(
        "student_id",
        Uuid(as_uuid=False),
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(50))
    species: Mapped[str] = mapped_column(String(50))
    age: Mapped[int | None]
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime(timezone=True), default=utc_now
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    student: Mapped[StudentModel] = relationship(back_populates="pets")
