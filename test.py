# ========== FastAPI: Урок 9 — HTTP-статусы и обработка ошибок ==========

# ТЕОРИЯ:
# Когда клиент делает запрос, сервер возвращает:
# 1. HTTP-статус (число) — результат операции
# 2. Тело ответа (JSON) — данные

# Основные статусы:
# 200 — OK (всё хорошо)
# 201 — Created (ресурс создан)
# 204 — No Content (успех, но тело пустое — обычно для DELETE)
# 400 — Bad Request (невалидные данные от клиента)
# 404 — Not Found (ресурс не найден)
# 409 — Conflict (конфликт, например дубликат)
# 500 — Internal Server Error (ошибка на сервере)

# Как в FastAPI:

from fastapi import FastAPI, HTTPException, status

app = FastAPI()

# По умолчанию все маршруты возвращают 200.
# Чтобы изменить — status_code в декораторе:

@app.post("/items", status_code=201)
def create_item(item: dict):
    return item

# Для ошибок — HTTPException:

@app.get("/items/{id}")
def get_item(id: int):
    if id < 1:
        raise HTTPException(
            status_code=400,
            detail="ID должен быть положительным"
        )
    if id > 100:
        raise HTTPException(
            status_code=404,
            detail=f"Item {id} не найден"
        )
    return {"id": id, "name": "test"}

# Можно использовать status.HTTP_404_NOT_FOUND вместо числа:
from fastapi import status

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Студент не найден"
)

# Разница:
# return {"error": "..."}           → вернёт 200 с текстом ошибки (плохо)
# raise HTTPException(404, "...")   → вернёт 404 (правильно)

# --- Dependency Injection ---

# Ты уже используешь Depends для get_db.
# Но Depends можно использовать для любой логики, которая нужна
# перед выполнением маршрута.

# Пример: проверка наличия студента перед любым маршрутом

from fastapi import Depends

def get_student_or_404(id: int, db: Session = Depends(get_db)):
    student = db.query(StudentDB).filter(StudentDB.id == id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")
    return student  # возвращает объект студента

# Теперь маршрут становится проще:
@app.get("/students/{id}")
def get_student(student: StudentDB = Depends(get_student_or_404)):
    return student  # студент уже найден, 404 уже проверен

# Этот паттерн называется dependency injection:
# - переиспользуемая логика выносится в функцию
# - маршрут получает результат через Depends


# ========== ПРАКТИКА ==========

# Переделай свой CRUD для студентов:
#
# 1. POST /students → status_code=201
# 2. DELETE /students/{id} → при успехе status_code=204, тело пустое
# 3. GET/PUT/DELETE — при ненайденном студенте HTTPException(404)
# 4. GET/PUT/DELETE — при невалидном id HTTPException(400)
# 5. Убери все return {"error": ...}, замени на raise HTTPException
# 6. Напиши функцию get_student_or_404 и используй её через Depends
#    в GET/PUT/DELETE /students/{id}
# 7. Используй status.HTTP_404_NOT_FOUND вместо голого числа 404
