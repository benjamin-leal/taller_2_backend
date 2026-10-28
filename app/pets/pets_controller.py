from fastapi import APIRouter, Depends

from app.pets.pets_schemas import CreatePetDto, Pet, PetList, UpdatePetDto
from app.pets.pets_service import PetsService, get_pets_service

router = APIRouter(
    prefix="/api/students/{studentId}/pets",
    tags=["Pets"],
)


@router.get("")
def find_all(
    studentId: str, service: PetsService = Depends(get_pets_service)
) -> PetList:
    return service.find_all_for_student(studentId)


@router.post("", status_code=201)
def create(
    studentId: str,
    body: CreatePetDto,
    service: PetsService = Depends(get_pets_service),
) -> Pet:
    return service.create(studentId, body)


@router.patch("/{petId}")
def update(
    studentId: str,
    petId: str,
    body: UpdatePetDto,
    service: PetsService = Depends(get_pets_service),
) -> Pet:
    return service.update(studentId, petId, body)


@router.delete("/{petId}")
def delete(
    studentId: str,
    petId: str,
    service: PetsService = Depends(get_pets_service),
) -> Pet:
    return service.delete(studentId, petId)