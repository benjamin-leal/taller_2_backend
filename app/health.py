from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_session

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("/database")
def database_health(
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(503, detail="Base de datos no disponible") from None
    return {"database": "ok"}
