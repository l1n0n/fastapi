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

class UserOut(BaseModel):
    id: int
    username: str

class Token(BaseModel):
    access_token: str
    type: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
SECRET_KEY = "my-secret-key"

Base.metadata.create_all(bind=engine)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    encode = data.copy()
    expires = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    encode.update({"expires": expires})
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

def get_student_or_404(id: int, db: Session = Depends(get_db)):
    student = db.query(UserDataBase).filter(UserDataBase.id == id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student
class Student(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    grade: float = Field(..., ge=0, le=5)
    age: int = Field(default=18, ge=14, le=100)

class StudentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    grade: float | None = Field(default=None, ge=0, le=5)

@app.get('/students')
def get_students(db: Session = Depends(get_db)):
    students = db.query(UserDataBase).all()
    return [{"id": student.id, "name": student.name, "grade": student.grade, "age": student.age} for student in students]

@app.get('/students/{id}')
def get_student(student: UserDataBase = Depends(get_student_or_404)):
    return student

@app.post('/students', status_code=201)
def add_student(new_student: Student, db: Session = Depends(get_db)):
    student = UserDataBase(name=new_student.name, grade=new_student.grade, age=new_student.age)
    db.add(student)
    db.commit()
    return {"id": student.id, "name": student.name, "grade": student.grade, "age": student.age}

@app.put('/students/{id}')
def update_student(id: int, new_student: StudentUpdate, db: Session = Depends(get_db)):
    if id < 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid student identifier")
    student = db.query(UserDataBase).filter(UserDataBase.id == id).first()
    if student:
        if new_student.name is not None:
            student.name = new_student.name
        if new_student.grade is not None:
            student.grade = new_student.grade
        db.commit()
        return {"id": student.id, "name": student.name, "grade": student.grade, "age": student.age}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

@app.delete('/students/{id}', status_code=204)
def delete_student(id: int, db: Session = Depends(get_db)):
    if id < 1:
        raise HTTPException(status_code=400, detail="Invalid student identifier")
    student = db.query(UserDataBase).filter(UserDataBase.id == id).first()
    if student:
        db.delete(student)
        db.commit()
        return {}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

@app.post('/register', response_model=UserOut, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(UserDataBase).filter(UserDataBase.username == user.username).first()
    if existing_user is None:
        raise HTTPException(
            status_code=409,
            detail = "Username is already taken"
        )
    hash = pwd_context.hash(user.password)
    user_db = UserDataBase(username=user.username, hashed_password=hash)
    db.add(user_db)
    db.commit()
    db.refresh(user_db)
    return user_db

@app.post('/login', response_model=Token)
def login(data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDataBase).filter(UserDataBase.username == data.username).first()
    if user is None or pwd_context.verify(data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=15))
    return {"access_token": token, "token_type": "bearer"}