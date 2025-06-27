from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from . import models, schemas, database, auth
from fastapi import APIRouter
import pandas as pd
import io
import traceback
from sqlalchemy.exc import SQLAlchemyError
from fastapi.responses import JSONResponse
import json
from datetime import datetime

router = APIRouter()


@router.post("/register", response_model=schemas.UserOut)
def register(user_data: schemas.UserCreate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(
        (models.User.username == user_data.username) |
        (models.User.email == user_data.email)
    ).first()
    if user:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    hashed_pw = auth.get_password_hash(user_data.password)
    new_user = models.User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_pw
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=schemas.Token)
def login(user_data: schemas.UserLogin, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not user or not auth.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = auth.create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/users", response_model=list[schemas.UserOut])
def get_users(db: Session = Depends(database.get_db)):
    return db.query(models.User).all()

@router.post("/upload_excel")
def upload_excel(files: list[UploadFile] = File(...), db: Session = Depends(database.get_db)):
    all_entries = []
    debug_info = []
    for file in files:
        try:
            content = file.file.read()
            excel = pd.ExcelFile(io.BytesIO(content))
            for sheet_name in excel.sheet_names:
                df = pd.read_excel(excel, sheet_name=sheet_name)
                # Определяем, есть ли месячные колонки
                months = [m for m in [
                    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
                ] if any(m in str(col) for col in df.columns)]
                if months:
                    for month in months:
                        month_cols = [col for col in df.columns if month in str(col)]
                        base_cols = [col for col in df.columns if all(m not in str(col) for m in months)]
                        for idx, row in df.iterrows():
                            base_data = {col: row[col] for col in base_cols}
                            month_data = {col.replace(f'_{month}', '').replace(f' {month}', '').strip(): row[col] for col in month_cols}
                            entry = {**base_data, **month_data, 'month': month, 'source_file': file.filename}
                            all_entries.append(entry)
                else:
                    for idx, row in df.iterrows():
                        entry = row.to_dict()
                        entry['month'] = None
                        entry['source_file'] = file.filename
                        all_entries.append(entry)
        except Exception as e:
            debug_info.append({
                'file': file.filename,
                'error': str(e),
                'traceback': traceback.format_exc()
            })

    # Объединяем все данные по одинаковым колонкам
    try:
        if all_entries:
            df_all = pd.DataFrame(all_entries)
            # Сериализация дат и временных меток
            def json_serial(obj):
                if isinstance(obj, (datetime, pd.Timestamp)):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            records = json.loads(df_all.to_json(orient='records', date_format='iso'))
            for rec in records:
                crm_entry = models.CRMEntry(data=rec)
                db.add(crm_entry)
            db.commit()
        else:
            return JSONResponse(status_code=400, content={"detail": "No valid data found in uploaded files", "debug": debug_info})
    except Exception as e:
        debug_info.append({'error': str(e), 'traceback': traceback.format_exc()})
        return JSONResponse(status_code=500, content={"detail": "Error during saving data", "debug": debug_info})
    return {"status": "success", "saved": len(all_entries), "debug": debug_info}

@router.get("/crm")
def get_crm(db: Session = Depends(database.get_db)):
    entries = db.query(models.CRMEntry).all()
    return [entry.data for entry in entries]



