# Destino en el repo: app/models.py
# AJUSTAR: campos, tipos de id (int/uuid) y reglas de unicidad a lo que
# tenga el template en Student y Pet.
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)  # AJUSTAR

    # Borrar un Student borra sus Pet (a nivel ORM y a nivel BD)
    pets: Mapped[list["Pet"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Pet(Base):
    __tablename__ = "pets"
    __table_args__ = (
        # AJUSTAR: un estudiante no puede repetir nombre de mascota
        UniqueConstraint("student_id", "name", name="uq_pet_student_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False)  # AJUSTAR
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )

    student: Mapped["Student"] = relationship(back_populates="pets")
