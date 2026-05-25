import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use a separate test DB so we don't pollute the dev DB
TEST_DB = Path(__file__).resolve().parents[2] / "test_blending_master.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

from backend.main import app  # noqa: E402
from backend.db.database import engine, get_db  # noqa: E402
from backend.models import Base, Case  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    s = SessionLocal()
    try:
        s.add(
            Case(
                case_id="TEST-001",
                source_f_index=0,
                season="winter",
                tank_history_flag="clean",
                target_cfpp=-8.0,
                decision="normal",
                rule_summary="test fixture",
                narrative="test",
                blend_components={"lgo": 0.6, "hgo": 0.15, "lco": 0.1, "kero": 0.12, "biodiesel": 0.03},
                key_metrics={
                    "density_15c": 840.0,
                    "n_paraffin_c10_c15": 10.0,
                    "n_paraffin_c16_c20": 9.0,
                    "n_paraffin_c21_plus": 2.0,
                    "aromatic_content": 24.0,
                    "sulfur_ppm": 8.0,
                    "cetane_index": 49.0,
                    "wafi_type": "A",
                    "wafi_ppm": 200.0,
                },
                reason_codes=["metric_level"],
                check_priority=["blend_ratio", "retest"],
                risk_codes=[],
                actual_outcome=None,
            )
        )
        s.commit()
    finally:
        s.close()
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()
    # Windows holds file locks until the engine disposes; ignore residual failures
    try:
        if TEST_DB.exists():
            TEST_DB.unlink()
    except PermissionError:
        pass


@pytest.fixture
def client():
    return TestClient(app)
