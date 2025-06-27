from fastapi import APIRouter, UploadFile, File
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import CRMEntry
import pandas as pd
import traceback
import io
import logging

logging.basicConfig(level=logging.INFO)

router = APIRouter()


def get_month_from_date_string(date_str):
    if not date_str or pd.isnull(date_str):
        return None

    try:
        date_str = str(date_str).strip()
        if date_str.lower() in ['nan', 'nat', 'none', '']:
            return None
        parsed_date = pd.to_datetime(date_str, errors='coerce')
        return parsed_date.month if pd.notnull(parsed_date) else None
    except:
        return None


@router.post("/upload_excel", tags=["CRM"])
async def upload_excel(files: list[UploadFile] = File(...)):
    all_entries = []
    debug_info = []
    month_names = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                   'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

    for file in files:
        try:
            content = await file.read()
            excel = pd.ExcelFile(io.BytesIO(content))
            logging.info(f"Файл {file.filename}: вкладки {excel.sheet_names}")
            for sheet_name in excel.sheet_names:
                df = pd.read_excel(excel, sheet_name=sheet_name)
                for _, row in df.iterrows():
                    row_data = row.to_dict()
                    row_data['month'] = sheet_name
                    all_entries.append({'data': row_data, 'source_file': file.filename})

        except Exception as e:
            debug_info.append({
                'file': file.filename,
                'error': str(e),
                'traceback': traceback.format_exc()
            })

    # Сохраняем в БД
    if not all_entries:
        return {"status": "no_valid_data", "debug": debug_info}

    db: Session = SessionLocal()
    try:
        saved_count = 0
        for entry in all_entries:
            db_entry = CRMEntry(data=entry['data'])
            db.add(db_entry)
            saved_count += 1

        db.commit()
        return {"status": "success", "saved": saved_count, "debug": debug_info}
    except Exception as e:
        db.rollback()
        debug_info.append({"error": str(e), "traceback": traceback.format_exc()})
        return {"status": "error", "debug": debug_info}
    finally:
        db.close()
