# ========== FastAPI: Урок 10 — Аутентификация и авторизация (JWT + OAuth2) ==========

# ========================================
# ЧАСТЬ 1: АУТЕНТИФИКАЦИЯ vs АВТОРИЗАЦИЯ
# ========================================

# Аутентификация — подтверждение личности (кто ты?)
# Авторизация — проверка прав (что тебе можно?)

# Пример из жизни:
# - Аутентификация: показываешь паспорт на входе
# - Авторизация: бейджик, который пускает только в определённые комнаты

# В веб-API это работает так:
# 1. Клиент отправляет логин/пароль → сервер проверяет (аутентификация)
# 2. Сервер выдаёт токен → клиент прикрепляет его к каждому запросу
# 3. Сервер проверяет токен и решает, можно ли выполнить действие (авторизация)

# ========================================
# ЧАСТЬ 2: СЕССИИ vs ТОКЕНЫ
# ========================================

# Сессии (session-based auth):
# - Сервер хранит состояние (кто залогинен) в памяти/БД
# - Клиент получает session_id (куку)
# - Минус: сервер должен помнить все сессии, плохо масштабируется

# Токены (token-based auth):
# - Сервер НЕ хранит состояние
# - Клиент получает подписанный токен (JWT)
# - Сервер только проверяет подпись токена
# - Плюс: легко масштабировать, не нужна общая память между серверами

# ========================================
# ЧАСТЬ 3: JWT (JSON Web Token)
# ========================================

# JWT — это строка из трёх частей, разделённых точкой:
# eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJsaW5hciJ9.abc123signature

# Три части:
# 1. Header — алгоритм подписи и тип токена
#    {"alg": "HS256", "typ": "JWT"}
#
# 2. Payload (claims) — данные: кто это, когда истекает
#    {"sub": "linar", "exp": 1700000000}
#
# 3. Signature — подпись, чтобы нельзя было подделать
#    HMACSHA256(base64(header) + "." + base64(payload), secret_key)

# Ключевые моменты:
# - JWT НЕ шифруется по умолчанию (только подписывается)
# - Любой может декодировать payload, но не может изменить без secret_key
# - Поэтому в JWT НЕ кладут пароли и секретные данные
# - "sub" (subject) — стандартное поле для идентификатора пользователя
# - "exp" (expiration) — время истечения токена (Unix timestamp)

# ========================================
# ЧАСТЬ 4: OAuth2 Password Flow
# ========================================

# OAuth2 — протокол авторизации. Password Flow — один из его вариантов:
#
# 1. Клиент отправляет POST /login с username + password
# 2. Сервер проверяет → возвращает access_token (JWT)
# 3. Клиент добавляет заголовок: Authorization: Bearer <token>
# 4. Сервер проверяет токен на каждом защищённом маршруте

# ========================================
# ЧАСТЬ 5: РЕАЛИЗАЦИЯ В FASTAPI
# ========================================

# Установка зависимостей:
# pip install python-jose[cryptography] passlib[bcrypt]

# --- Модель пользователя в БД ---

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)

# --- Хеширование паролей ---

# Пароли НИКОГДА не хранятся в открытом виде.
# Используем bcrypt через библиотеку passlib.

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Хеширование пароля:
hashed = pwd_context.hash("mypassword")
# Результат: "$2b$12$LJ3m4ys3Lg..." — длинная строка

# Проверка пароля:
is_correct = pwd_context.verify("mypassword", hashed)  # True
is_wrong = pwd_context.verify("wrong", hashed)          # False

# --- Pydantic модели ---

from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str

class Token(BaseModel):
    access_token: str
    token_type: str

# --- Создание JWT ---

from datetime import datetime, timedelta
from jose import jwt

SECRET_KEY = "your-secret-key-change-in-production"  # в проде — длинная случайная строка
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Пример вызова:
token = create_access_token(
    data={"sub": "linar"},
    expires_delta=timedelta(minutes=30)
)
# Результат: "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJsaW5hciIsImV4cCI6MTcwMDAwMDAwMH0.xxx"

# --- Декодирование и проверка JWT ---

from jose import JWTError

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

# --- Зависимость: получение текущего пользователя ---

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# OAuth2PasswordBearer — это зависимость, которая:
# 1. Ищет заголовок Authorization: Bearer <token>
# 2. Извлекает токен
# 3. Если заголовка нет — возвращает 401

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    username = decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user

# --- Маршрут регистрации ---

@app.post("/register", response_model=UserOut, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Проверяем, занят ли username
    existing = db.query(UserDB).filter(UserDB.username == user.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    hashed = pwd_context.hash(user.password)
    db_user = UserDB(username=user.username, hashed_password=hashed)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Маршрут логина ---

from fastapi.security import OAuth2PasswordRequestForm

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Ищем пользователя
    user = db.query(UserDB).filter(UserDB.username == form_data.username).first()

    # Проверяем пароль
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Создаём токен
    token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer"}

# --- Защищённый маршрут ---

@app.get("/me", response_model=UserOut)
def get_me(current_user: UserDB = Depends(get_current_user)):
    return current_user

# Как это работает:
# 1. Клиент вызывает POST /login → получает токен
# 2. Клиент вызывает GET /me с заголовком Authorization: Bearer <token>
# 3. FastAPI вызывает get_current_user → decode_access_token → ищет в БД
# 4. Если всё ок — маршрут получает current_user
# 5. Если токен невалидный/истёк — 401

# --- Защита существующих маршрутов ---

# Чтобы защитить любой маршрут, просто добавь зависимость:
@app.get("/students")
def get_students(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Только авторизованные пользователи могут получить список
    ...

# ========================================
# ЧАСТЬ 6: ИТОГОВАЯ СХЕМА
# ========================================

# Клиент                         Сервер
#   |                               |
#   |--- POST /login -------------->|  Проверяет логин/пароль
#   |<-- {access_token: "xxx"} ----|  Возвращает JWT
#   |                               |
#   |--- GET /students ------------>|  Заголовок: Authorization: Bearer xxx
#   |    (с токеном)               |  → decode_access_token
#   |                               |  → get_current_user (из БД)
#   |                               |  → проверка прав
#   |<-- [{students}] -------------|  Возвращает данные
#   |                               |
#   |--- GET /students/999 -------->|  Токен истёк
#   |<-- 401 Unauthorized ---------|  Отказ

# ========================================
# ЧАСТЬ 7: ВАЖНЫЕ ДЕТАЛИ
# ========================================

# 1. SECRET_KEY должен быть длинным и случайным:
#    import secrets
#    SECRET_KEY = secrets.token_urlsafe(32)

# 2. В продакшене храни SECRET_KEY в переменных окружения, не в коде:
#    import os
#    SECRET_KEY = os.environ["SECRET_KEY"]

# 3. Токен истекает → клиенту нужно снова вызвать /login
#    (или реализовать refresh token — это следующий уровень)

# 4. HTTPS обязателен — без него токен можно перехватить

# 5. Никогда не храни пароль в открытом виде — только хеш bcrypt


# ========== ПРАКТИКА ==========

# Добавь аутентификацию к своему CRUD для студентов.
#
# 1. Установи зависимости: pip install python-jose[cryptography] passlib[bcrypt]
#    (добавь их в requirements.txt и пересобери Docker)
#
# 2. Создай таблицу users в БД (id, username, hashed_password)
#
# 3. Реализуй хеширование паролей через passlib (bcrypt)
#
# 4. Реализуй создание и проверку JWT через python-jose:
#    - SECRET_KEY, ALGORITHM, время жизни токена
#    - функция create_access_token
#    - функция decode_access_token
#
# 5. Создай Pydantic модели: UserCreate, UserOut, Token
#
# 6. Реализуй маршруты:
#    - POST /register — регистрация (username, password) → хеширует пароль, сохраняет в БД
#    - POST /login — проверяет логин/пароль → возвращает JWT
#
# 7. Создай зависимость get_current_user:
#    - извлекает токен из заголовка Authorization: Bearer
#    - декодирует JWT
#    - ищет пользователя в БД
#    - при ошибке → 401
#
# 8. Защити все маршруты /students через Depends(get_current_user)
#    (GET, POST, PUT, DELETE — всё требует авторизации)
#
# 9. Добавь проверку уникальности username при регистрации (409 если занят)
