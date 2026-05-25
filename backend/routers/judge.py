from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.schemas.judge import JudgeRequest, JudgeResponse
from backend.services.recommend_service import judge as judge_service

router = APIRouter()


@router.post("/judge", response_model=JudgeResponse, tags=["judge"])
def judge(req: JudgeRequest, db: Session = Depends(get_db)) -> JudgeResponse:
    """Run quality assessment and return 3 WAFI scenarios with rationale."""
    return judge_service(req, db)
