"""Initialize SQLite schema and load synthetic cases.

Usage:
    python -m backend.db.init_db
"""
import json
from pathlib import Path

from backend.db.database import engine, SessionLocal
from backend.models import Base, Case

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "synthetic"
CASES_PATH = DATA_DIR / "cases.json"


def create_schema() -> None:
    Base.metadata.create_all(engine)
    print(f"[init_db] Schema created at {engine.url}")


def load_cases() -> int:
    if not CASES_PATH.exists():
        print(f"[init_db] cases.json not found at {CASES_PATH}, skipping load")
        return 0

    with CASES_PATH.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    session = SessionLocal()
    inserted = 0
    try:
        for c in cases:
            if session.get(Case, c["case_id"]):
                continue
            ctx = c.get("context", {})
            session.add(
                Case(
                    case_id=c["case_id"],
                    source_f_index=c.get("source_f_index"),
                    season=ctx.get("season", "unknown"),
                    tank_history_flag=ctx.get("tank_history_flag", "unknown"),
                    target_cfpp=ctx.get("target_cfpp", 0.0),
                    decision=c.get("decision", "normal"),
                    rule_summary=c.get("rule_summary"),
                    narrative=c.get("narrative"),
                    blend_components=ctx.get("blend_components", {}),
                    key_metrics=ctx.get("key_metrics", {}),
                    reason_codes=c.get("reason_codes", []),
                    check_priority=c.get("check_priority", []),
                    risk_codes=c.get("risk_codes", []),
                    actual_outcome=c.get("actual_outcome"),
                )
            )
            inserted += 1
        session.commit()
    finally:
        session.close()

    print(f"[init_db] Loaded {inserted} cases from cases.json")
    return inserted


def main() -> None:
    create_schema()
    load_cases()


if __name__ == "__main__":
    main()
