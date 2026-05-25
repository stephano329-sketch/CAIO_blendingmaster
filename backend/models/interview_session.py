from datetime import datetime
from sqlalchemy import String, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    veteran_id: Mapped[str] = mapped_column(String, index=True)
    case_responses: Mapped[list] = mapped_column(JSON, default=list)
    extracted_heuristic_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="in_progress")  # in_progress | completed | abandoned
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
