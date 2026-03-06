from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Gibt den Status aller Subsysteme zurück. Kein Auth erforderlich."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    overall = "healthy" if db_status == "ok" else "degraded"

    return {
        "status": overall,
        "db": db_status,
        "version": "0.1.0",
    }
