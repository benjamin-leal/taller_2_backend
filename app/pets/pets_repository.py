from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Pet as PetModel
from app.pets.pets_schemas import Pet


class PetsRepository:
    """Comparte la sesión de la petición; el servicio confirma la transacción."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def find_all_by_student(self, student_id: str) -> list[PetModel]:
        return list(
            self.db.scalars(select(PetModel).where(PetModel.studentId == student_id))
        )

    def find_by_id(self, pet_id: str) -> PetModel | None:
        try:
            pet_id = str(UUID(pet_id))
        except ValueError:
            return None
        return self.db.get(PetModel, pet_id)

    def find_by_student_and_name(self, student_id: str, name: str) -> PetModel | None:
        return self.db.scalar(
            select(PetModel).where(
                PetModel.studentId == student_id, PetModel.name == name
            )
        )

    def save(self, pet: Pet) -> Pet:
        values = pet.model_dump(exclude={"createdAt", "updatedAt"})
        row = self.db.merge(
            PetModel(**values, createdAt=pet.createdAt, updatedAt=pet.updatedAt)
        )
        self.db.flush()
        return Pet.model_validate(row)

    def delete(self, pet_id: str) -> None:
        self.db.execute(delete(PetModel).where(PetModel.id == pet_id))

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
