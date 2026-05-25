from datetime import datetime
from sqlalchemy import String, JSON, DateTime, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Case(Base):
    __tablename__ = "cases"

    case_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_f_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season: Mapped[str] = mapped_column(String, index=True)
    tank_history_flag: Mapped[str] = mapped_column(String, index=True)
    target_cfpp: Mapped[float] = mapped_column(Float)
    decision: Mapped[str] = mapped_column(String, index=True)
    rule_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    narrative: Mapped[str | None] = mapped_column(String, nullable=True)

    blend_components: Mapped[dict] = mapped_column(JSON)
    key_metrics: Mapped[dict] = mapped_column(JSON)
    reason_codes: Mapped[list] = mapped_column(JSON)
    check_priority: Mapped[list] = mapped_column(JSON)
    risk_codes: Mapped[list] = mapped_column(JSON)
    actual_outcome: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
