from fastapi import APIRouter, UploadFile, File
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import CRMEntry
import pandas as pd
import json
from datetime import datetime, timedelta
import io
import traceback

router = APIRouter()


def get_month_from_date_string(date_str):
    """
    Извлекает месяц из строки с датой
    """
    if not date_str or pd.isnull(date_str):
        return None

    try:
        # Преобразуем в строку и очищаем
        date_str = str(date_str).strip()

        if not date_str or date_str.lower() in ['nan', 'nat', 'none', '']:
            return None

        # Парсим дату с помощью pandas
        parsed_date = pd.to_datetime(date_str, errors='coerce')

        if pd.notnull(parsed_date):
            return parsed_date.month

        return None
    except:
        return None


@router.post("/upload_excel", tags=["CRM"])
async def upload_excel(files: list[UploadFile] = File(...)):
    all_entries = []
    debug_info = []

    for file in files:
        try:
            content = file.file.read()
            excel = pd.ExcelFile(io.BytesIO(content))

            for sheet_name in excel.sheet_names:
                df = pd.read_excel(excel, sheet_name=sheet_name)

                # Список месяцев для поиска в названиях колонок
                month_names = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                               'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

                months_in_columns = [m for m in month_names if any(m in str(col) for col in df.columns)]

                if months_in_columns:
                    # Обработка файлов с месяцами в названиях колонок
                    for month in months_in_columns:
                        month_cols = [col for col in df.columns if month in str(col)]
                        base_cols = [col for col in df.columns if all(m not in str(col) for m in month_names)]

                        for _, row in df.iterrows():
                            base_data = {str(col): row[col] for col in base_cols}
                            month_data = {
                                str(col).replace(f'_{month}', '').replace(f' {month}', '').strip(): row[col]
                                for col in month_cols
                            }

                            data_entry = {**base_data, **month_data, 'month': month}
                            all_entries.append({
                                'data': data_entry,
                                'source_file': file.filename
                            })
                else:
                    # Обработка файлов без месяцев в названиях колонок
                    for _, row in df.iterrows():
                        data_entry = row.to_dict()

                        # Ищем месяц в каждой строке
                        found_month = None

                        # Проверяем каждое поле в строке на наличие даты
                        for col_name, cell_value in row.items():
                            month_val = get_month_from_date_string(cell_value)
                            if month_val is not None:
                                found_month = month_val
                                break  # Берем первый найденный месяц

                        # Добавляем месяц в данные
                        data_entry['month'] = found_month

                        all_entries.append({
                            'data': data_entry,
                            'source_file': file.filename
                        })

        except Exception as e:
            debug_info.append({
                'file': file.filename,
                'error': str(e),
                'traceback': traceback.format_exc()
            })

    # Сохранение в базу данных
    try:
        if all_entries:
            # Сохраняем напрямую без дополнительных преобразований
            db: Session = SessionLocal()
            try:
                saved_count = 0
                for entry in all_entries:
                    # Еще раз проверяем month перед сохранением
                    if entry['data'].get('month') is None:
                        # Последняя попытка найти месяц
                        for key, value in entry['data'].items():
                            if key != 'month':  # Исключаем само поле month
                                month_val = get_month_from_date_string(value)
                                if month_val is not None:
                                    entry['data']['month'] = month_val
                                    break

                    # Создаем запись в БД
                    db_entry = CRMEntry(data=entry['data'])
                    db.add(db_entry)
                    saved_count += 1

                db.commit()
                return {"status": "success", "saved": saved_count, "debug": debug_info}

            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()
        else:
            return {"status": "no_valid_data", "debug": debug_info}

    except Exception as e:
        debug_info.append({
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        return {"status": "error", "debug": debug_info}