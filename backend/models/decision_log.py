from datetime import datetime
from sqlalchemy import String, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    log_id: Mapped[str] = mapped_column(String, primary_key=True)
    input: Mapped[dict] = mapped_column(JSON)
    ai_recommendation: Mapped[dict] = mapped_column(JSON)
    selected_scenario: Mapped[str | None] = mapped_column(String, nullable=True)
    actual_outcome: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
