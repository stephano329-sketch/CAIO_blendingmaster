from sqlalchemy import String, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Veteran(Base):
    __tablename__ = "veterans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    career_years: Mapped[int] = mapped_column(Integer)
    domain_focus: Mapped[str | None] = mapped_column(String, nullable=True)
    decision_priorities: Mapped[list] = mapped_column(JSON, default=list)
