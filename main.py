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
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, Float, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session

app = FastAPI()

engine = create_engine("sqlite:////app/db/students.db")

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

class StudentDataBase(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    grade = Column(Float, nullable=False)
    age = Column(Integer, default=18)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Student(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    grade: float = Field(..., ge=0, le=5)
    age: int = Field(default=18, ge=14, le=100)

class StudentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    grade: float | None = Field(default=None, ge=0, le=5)

@app.get('/students')
def get_students(db: Session = Depends(get_db)):
    students = db.query(StudentDataBase).all()
    return [{"id": student.id, "name": student.name, "grade": student.grade, "age": student.age} for student in students]

@app.get('/students/{id}')
def get_student(id: int, db: Session = Depends(get_db)):
    if id < 1:
        raise HTTPException(status_code=400, detail="Invalid student identifier")
    student = db.query(StudentDataBase).filter(StudentDataBase.id == id).first()
    if student:
        return {"id": student.id, "name": student.name, "grade": student.grade, "age": student.age}
    raise HTTPException(status_code=404, detail="Student not found")

@app.post('/students', status_code=201)
def add_student(new_student: Student, db: Session = Depends(get_db)):
    student = StudentDataBase(name=new_student.name, grade=new_student.grade, age=new_student.age)
    db.add(student)
    db.commit()
    return {"id": student.id, "name": student.name, "grade": student.grade, "age": student.age}

@app.put('/students/{id}')
def update_student(id: int, new_student: StudentUpdate, db: Session = Depends(get_db)):
    if id < 1:
        raise HTTPException(status_code=404, detail="Invalid student identifier")
    student = db.query(StudentDataBase).filter(StudentDataBase.id == id).first()
    if student:
        if new_student.name is not None:
            student.name = new_student.name
        if new_student.grade is not None:
            student.grade = new_student.grade
        db.commit()
        return {"id": student.id, "name": student.name, "grade": student.grade, "age": student.age}
    raise HTTPException(status_code=404, detail="Student not found")

@app.delete('/students/{id}', status_code=204)
def delete_student(id: int, db: Session = Depends(get_db)):
    if id < 1:
        raise HTTPException(status_code=400 detail="Invalid student identifier")
    student = db.query(StudentDataBase).filter(StudentDataBase.id == id).first()
    if student:
        db.delete(student)
        db.commit()
        return {}
    raise HTTPException(status_code=404, detail="Student not found")