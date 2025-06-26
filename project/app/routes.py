from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from . import models, schemas, database, auth
from fastapi import APIRouter

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



