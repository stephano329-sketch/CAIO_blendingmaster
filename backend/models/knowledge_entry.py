from datetime import datetime
from sqlalchemy import String, JSON, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class KnowledgeEntry(Base):
    """Saved veteran knowledge from /moai interview Q1-Q5 flow.

    One entry = one case judged by a veteran with judgment + reasons + priorities
    + risks + free-form memo. Backing store for the 경험치 DB page.
    """

    __tablename__ = "knowledge_entries"

    entry_id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[str] = mapped_column(String, index=True)
    season: Mapped[str] = mapped_column(String, index=True)

    blend_components: Mapped[dict] = mapped_column(JSON)
    cfpp: Mapped[float] = mapped_column(Float)
    cp: Mapped[float] = mapped_column(Float)
    pp: Mapped[float] = mapped_column(Float)
    ai_draft_decision: Mapped[str | None] = mapped_column(String, nullable=True)

    q1_decision: Mapped[str] = mapped_column(String, index=True)
    q2_reasons: Mapped[list] = mapped_column(JSON, default=list)
    q3_priorities: Mapped[list] = mapped_column(JSON, default=list)
    q4_risks: Mapped[list] = mapped_column(JSON, default=list)
    q5_memo: Mapped[str] = mapped_column(String, default="")

    author: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
