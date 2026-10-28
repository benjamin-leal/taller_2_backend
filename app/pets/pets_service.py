from uuid import uuid4

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.pets.pets_repository import PetsRepository
from app.pets.pets_schemas import CreatePetDto, Pet, PetList, UpdatePetDto
from app.shared.datetimes import utc_now
from app.shared.db_errors import integrity_to_conflict
from app.shared.exceptions import conflict
from app.students.students_service import StudentsService, get_students_service


class PetsService:
    def __init__(self, repository: PetsRepository, students: StudentsService) -> None:
        self.repository = repository
        self.students_service = students

    def find_all_for_student(self, student_id: str) -> PetList:
        self.students_service.find_by_id(student_id)

        pets = sorted(
            self.repository.find_all_by_student(student_id),
            key=lambda pet: pet.createdAt,
            reverse=True,
        )

        return PetList(total=len(pets), items=pets)

    def create(self, student_id: str, data: CreatePetDto) -> Pet:
        self.students_service.find_by_id(student_id)
        self.assert_no_conflicts(student_id, data)

        now = utc_now()
        pet = Pet(
            id=str(uuid4()),
            studentId=student_id,
            name=data.name,
            species=data.species,
            age=data.age,
            createdAt=now,
            updatedAt=now,
        )

        return self._save(pet)

    def update(self, student_id: str, pet_id: str, data: UpdatePetDto) -> Pet:
        existing = self.find_owned(student_id, pet_id)
        self.assert_no_conflicts(student_id, data, except_id=pet_id)

        updated = existing.model_copy(
            update={
                **data.model_dump(exclude_none=True),
                "updatedAt": utc_now(),
            }
        )

        return self._save(updated)

    def delete(self, student_id: str, pet_id: str) -> Pet:
        existing = self.find_owned(student_id, pet_id)
        try:
            self.repository.delete(pet_id)
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise integrity_to_conflict(exc) from exc

        return existing

    def find_owned(self, student_id: str, pet_id: str) -> Pet:
        self.students_service.find_by_id(student_id)

        pet = self.repository.find_by_id(pet_id)

        if pet is None or pet.studentId != student_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mascota no encontrada",
            )

        return Pet.model_validate(pet)

    def _save(self, pet: Pet) -> Pet:
        try:
            saved = self.repository.save(pet)
            self.repository.commit()
            return saved
        except IntegrityError as exc:
            self.repository.rollback()
            raise integrity_to_conflict(exc) from exc

    def assert_no_conflicts(
        self,
        student_id: str,
        data: CreatePetDto | UpdatePetDto,
        except_id: str | None = None,
    ) -> None:
        if not data.name:
            return

        existing = self.repository.find_by_student_and_name(student_id, data.name)

        if existing and existing.id != except_id:
            raise conflict(
                {"name": {"message": "Ya tienes una mascota con ese nombre"}}
            )


def get_pets_service(
    db: Session = Depends(get_db),
    students: StudentsService = Depends(get_students_service),
) -> PetsService:
    return PetsService(PetsRepository(db), students)