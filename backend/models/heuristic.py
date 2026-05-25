from datetime import datetime
from sqlalchemy import String, JSON, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Heuristic(Base):
    __tablename__ = "heuristics"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    condition: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source_case_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft | approved | archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
