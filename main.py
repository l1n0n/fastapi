# ========== Практика 8 ==========

# Добавь валидацию к моделям Student и StudentUpdate с помощью Field.
#
# Требования к валидации:
# - name: от 1 до 50 символов
# - grade: от 0 до 5
# - age: от 14 до 100 (по умолчанию 18)
#
# 1. Импортируй Field из pydantic
# 2. Добавь Field с ограничениями ко всем полям Student и StudentUpdate
# 3. Остальной код уже рабочий — не трогай

from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, Float, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import *

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/login')

engine = create_engine("sqlite:////app/db/students.db")

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

class UserDataBase(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)

class UserCreate(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None

class UserOut(BaseModel):
    id: int
    username: str

class Token(BaseModel):
    access_token: str
    token_type: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
SECRET_KEY = "my-secret-key"

Base.metadata.create_all(bind=engine)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    encode = data.copy()
    expires = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    encode.update({"exp": expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        name: str = data.get("sub")
        if name is not None:
            return name
        return None
    except JWTError:
        return None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    username = decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Token expired", headers={"WWW-Authenticate": "Bearer"})
    user = db.query(UserDataBase).filter(UserDataBase.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized user")
    return user

@app.get('/users')
def get_users(db: Session = Depends(get_db)):
    users = db.query(UserDataBase).all()
    return [{"id": user.id, "username": user.username} for user in users]

@app.put('/users/{id}', dependencies=[Depends(get_current_user)], response_model=UserOut)
def update_user(id: int, new_user: UserUpdate, db: Session = Depends(get_db)):
    if id < 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid user identifier")
    user = db.query(UserDataBase).filter(UserDataBase.id == id).first()
    if user:
        if new_user.username is not None:
            user.username = new_user.username
        if new_user.password is not None:
            user.hashed_password = pwd_context.hash(new_user.password)
        db.commit()
        return {"id": user.id, "username": user.username}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@app.delete('/users/{id}', status_code=204, dependencies=[Depends(get_current_user)])
def delete_user(id: int, db: Session = Depends(get_db)):
    if id < 1:
        raise HTTPException(status_code=400, detail="Invalid user identifier")
    user = db.query(UserDataBase).filter(UserDataBase.id == id).first()
    if user:
        db.delete(user)
        db.commit()
        return {}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@app.post('/register', response_model=UserOut, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(UserDataBase).filter(UserDataBase.username == user.username).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail = "Username is already taken"
        )
    hash = pwd_context.hash(user.password)
    user_db = UserDataBase(username=user.username, hashed_password=hash)
    db.add(user_db)
    db.commit()
    db.refresh(user_db)
    return {"id": user_db.id, "username": user_db.username}

@app.post('/login', response_model=Token)
def login(data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDataBase).filter(UserDataBase.username == data.username).first()
    if user is None or not pwd_context.verify(data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=15))
    return {"access_token": token, "token_type": "bearer"}