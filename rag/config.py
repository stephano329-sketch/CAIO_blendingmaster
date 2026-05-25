"""Shared RAG configuration paths and collection names."""
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHROMA_DB_PATH = Path(os.getenv("CHROMA_DB_PATH", str(PROJECT_ROOT / "chroma_db")))

PRIMARY_COLLECTION = "primary_rag"      # A(process) + B(production) + C(feedstock) + D(cases)
SECONDARY_COLLECTION = "secondary_rag"  # E (veteran tacit knowledge from interviews)

DOC_TYPE_PROCESS = "process"        # A-*
DOC_TYPE_PRODUCTION = "production"  # B-*
DOC_TYPE_FEEDSTOCK = "feedstock"    # C-*
DOC_TYPE_CASE = "case"              # D (cases.json)
