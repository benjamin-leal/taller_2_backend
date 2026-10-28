from uuid import uuid4

from fastapi import Depends, HTTPException, status

from app.pets.pets_repository import PetsRepository, pets_repository
from app.pets.pets_schemas import CreatePetDto, Pet, PetList, UpdatePetDto
from app.shared.datetimes import utc_now
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

        return self.repository.save(pet)

    def update(self, student_id: str, pet_id: str, data: UpdatePetDto) -> Pet:
        existing = self.find_owned(student_id, pet_id)
        self.assert_no_conflicts(student_id, data, except_id=pet_id)

        updated = existing.model_copy(
            update={
                **data.model_dump(exclude_none=True),
                "updatedAt": utc_now(),
            }
        )

        return self.repository.save(updated)

    def delete(self, student_id: str, pet_id: str) -> Pet:
        existing = self.find_owned(student_id, pet_id)
        self.repository.delete(pet_id)

        return existing

    def delete_all_for_student(self, student_id: str) -> None:
        self.repository.delete_by_student(student_id)

    def find_owned(self, student_id: str, pet_id: str) -> Pet:
        self.students_service.find_by_id(student_id)

        pet = self.repository.find_by_id(pet_id)

        if pet is None or pet.studentId != student_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mascota no encontrada",
            )

        return pet

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


# ESPERO A: Persona 1 (compose base + repositorio de Pet).
#   Mientras no migre Pet al ORM, `pets_repository` sigue siendo el de
#   diccionarios. Cuando su PR (el extra de repositorio Pet) se fusione,
#   cambia SOLO esta línea para construir el repositorio con la sesión:
#       PetsRepository(db) y recibir `db: Session = Depends(get_db)` aquí.
# Consecuencia temporal: las mascotas creadas por POST /students viven en
# PostgreSQL, pero GET /students/{id}/pets aún lee del diccionario.
def get_pets_service(
    students: StudentsService = Depends(get_students_service),
) -> PetsService:
    return PetsService(pets_repository, students)