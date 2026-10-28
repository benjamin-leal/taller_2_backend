"""Regresiones de arranque; no conectan ni modifican una base de datos."""

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StartupTests(unittest.TestCase):
    def run_python(self, code):
        env = os.environ.copy()
        env["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost:5432/test"
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_api_imports(self):
        self.run_python("from app.main import app; assert app.routes")

    def test_database_driver_and_models(self):
        self.run_python(
            "from app.database import engine, Base; import app.models; "
            'assert engine.dialect.driver == "psycopg"; '
            'assert {"students", "pets"} <= set(Base.metadata.tables)'
        )


if __name__ == "__main__":
    unittest.main()
