from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import CRMEntry

router = APIRouter()

@router.get("/crm", tags=["CRM"])
def get_crm(db: Session = Depends(SessionLocal)):
    entries = db.query(CRMEntry).all()
    result = {}

    for entry in entries:
        data = entry.data
        month = data.get('month', 'Без месяца')  # если месяца нет, будет эта категория

        if month not in result:
            result[month] = []

        # убираем поле 'month', чтобы внутри не дублировалось
        cleaned_data = {k: v for k, v in data.items() if k != 'month'}
        result[month].append(cleaned_data)

    return result