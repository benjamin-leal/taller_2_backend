"""Ejecutar solo contra una BD desechable indicada por TEST_DATABASE_URL."""

import os
import unittest
from uuid import uuid4

from sqlalchemy import create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@unittest.skipUnless(
    os.environ.get("TEST_DATABASE_URL"), "Requiere BD exclusiva de pruebas"
)
class PetsRepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = make_url(os.environ["TEST_DATABASE_URL"])
        assert url.database.startswith("taller_test_"), "No usar una BD de trabajo"
        os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
        from app.models import Student
        from app.pets.pets_repository import PetsRepository

        cls.Student = Student
        cls.Repository = PetsRepository
        cls.engine = create_engine(url)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        from app.shared.datetimes import utc_now

        self.db = Session(self.engine, expire_on_commit=False)
        self.sid = str(uuid4())
        self.now = utc_now()
        self.db.add(
            self.Student(
                id=self.sid,
                name="Prueba Pet",
                username=self.sid[:20],
                email=self.sid + "@example.com",
                age=22,
                createdAt=self.now,
                updatedAt=self.now,
            )
        )
        self.db.commit()
        self.repo = self.Repository(self.db)

    def tearDown(self):
        self.db.rollback()
        self.db.execute(delete(self.Student).where(self.Student.id == self.sid))
        self.db.commit()
        self.db.close()

    def pet(self, name="Luna"):
        from app.pets.pets_schemas import Pet

        return Pet(
            id=str(uuid4()),
            studentId=self.sid,
            name=name,
            species="gato",
            age=3,
            createdAt=self.now,
            updatedAt=self.now,
        )

    def test_crud_persists_between_sessions(self):
        pet = self.pet()
        saved = self.repo.save(pet)
        self.repo.commit()
        with Session(self.engine) as other:
            row = self.Repository(other).find_by_id(pet.id)
            self.assertEqual(row.name, "Luna")
            self.assertEqual(row.createdAt.microsecond, self.now.microsecond)
        self.assertEqual(len(self.repo.find_all_by_student(self.sid)), 1)
        self.assertEqual(
            self.repo.find_by_student_and_name(self.sid, "Luna").id, pet.id
        )
        self.repo.save(saved.model_copy(update={"name": "Sol"}))
        self.repo.commit()
        self.assertEqual(self.repo.find_by_id(pet.id).name, "Sol")
        self.repo.delete(pet.id)
        self.repo.commit()
        self.assertIsNone(self.repo.find_by_id(pet.id))
        self.assertIsNone(self.repo.find_by_id("invalid"))

    def test_duplicate_rolls_back(self):
        self.repo.save(self.pet())
        with self.assertRaises(IntegrityError):
            self.repo.save(self.pet())
        self.repo.rollback()
        self.assertEqual(self.repo.find_all_by_student(self.sid), [])

    def test_student_delete_cascades(self):
        pet = self.pet()
        self.repo.save(pet)
        self.repo.commit()
        self.db.execute(delete(self.Student).where(self.Student.id == self.sid))
        self.db.commit()
        with Session(self.engine) as other:
            self.assertIsNone(self.Repository(other).find_by_id(pet.id))
