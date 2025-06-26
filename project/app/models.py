from sqlalchemy import Column, Integer, String,JSON
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)



class CRMEntry(Base):
    __tablename__ = "crm_entries"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(JSON)

