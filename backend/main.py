"""FastAPI entry point for Blending Master (Phase 1: judge + cases endpoints)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import judge as judge_router
from backend.routers import cases as cases_router
from backend.routers import consult as consult_router
from backend.routers import rag as rag_router
from backend.routers import dashboard as dashboard_router
from backend.routers import knowledge as knowledge_router
from backend.routers import interview as interview_router

app = FastAPI(
    title="Blending Master API",
    version="0.1.0",
    description="Diesel quality assessment + WAFI scenario recommendation (Phase 1)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(judge_router.router)
app.include_router(cases_router.router)
app.include_router(consult_router.router)
app.include_router(rag_router.router)
app.include_router(dashboard_router.router)
app.include_router(knowledge_router.router)
app.include_router(interview_router.router)


@app.get("/", tags=["meta"])
def root():
    return {
        "service": "Blending Master API",
        "version": "0.1.0",
        "phase": "2 - Backend core + ML + RAG (/consult)",
        "docs": "/docs",
    }


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
