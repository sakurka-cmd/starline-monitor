"""
StarLine Monitoring Backend - FastAPI Application
Запуск: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from datetime import datetime, timedelta
from typing import Optional, List
import hashlib
import json
import secrets
import logging
import os

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import mysql.connector
from mysql.connector import Error
import jwt

# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================

DATABASE_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "starline"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "starline_db")
}

JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="StarLine Monitoring API",
    description="API для мониторинга устройств StarLine",
    version="1.0.0"
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


# =============================================================================
# МОДЕЛИ ДАННЫХ
# =============================================================================

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class DeviceCreate(BaseModel):
    name: str
    app_id: str
    app_secret: str
    starline_login: str
    starline_password: str


# =============================================================================
# УТИЛИТЫ
# =============================================================================

def get_db_connection():
    """Получение соединения с БД"""
    try:
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        return conn
    except Error as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_jwt_token(user_id: int, email: str) -> str:
    """Создание JWT токена"""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict:
    """Проверка JWT токена"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Получение текущего пользователя из токена"""
    token = credentials.credentials
    return verify_jwt_token(token)


# =============================================================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Создание таблиц при запуске"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_email (email)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # Таблица устройств StarLine
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_devices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            name VARCHAR(255) NOT NULL,
            app_id VARCHAR(255) NOT NULL,
            app_secret VARCHAR(255) NOT NULL,
            starline_login VARCHAR(255) NOT NULL,
            starline_password VARCHAR(255) NOT NULL,
            starline_device_id VARCHAR(64),
            device_name VARCHAR(255),
            device_type VARCHAR(64),
            is_active TINYINT DEFAULT 1,
            last_update TIMESTAMP NULL,
            last_error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # Таблица состояний устройств
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_states (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            device_id INT NOT NULL,
            timestamp DATETIME NOT NULL,
            arm_state TINYINT,
            ign_state TINYINT,
            temp_inner DECIMAL(5,2),
            temp_engine DECIMAL(5,2),
            balance DECIMAL(10,2),
            gsm_level INT,
            gps_level INT,
            latitude DECIMAL(10,8),
            longitude DECIMAL(11,8),
            speed DECIMAL(6,2),
            raw_data JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES user_devices(id) ON DELETE CASCADE,
            INDEX idx_device_timestamp (device_id, timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")


# =============================================================================
# API: АВТОРИЗАЦИЯ
# =============================================================================

@app.post("/api/auth/register")
async def register(user: UserRegister):
    """Регистрация нового пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE email = %s", (user.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    password_hash = hash_password(user.password)
    cursor.execute(
        "INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s)",
        (user.email, password_hash, user.name)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    
    token = create_jwt_token(user_id, user.email)
    
    return {
        "message": "User registered successfully",
        "token": token,
        "user": {"id": user_id, "email": user.email, "name": user.name}
    }


@app.post("/api/auth/login")
async def login(user: UserLogin):
    """Авторизация пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    password_hash = hash_password(user.password)
    cursor.execute(
        "SELECT id, email, name FROM users WHERE email = %s AND password_hash = %s",
        (user.email, password_hash)
    )
    db_user = cursor.fetchone()
    conn.close()
    
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_jwt_token(db_user['id'], db_user['email'])
    
    return {"token": token, "user": db_user}


@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute(
        "SELECT id, email, name, created_at FROM users WHERE id = %s",
        (current_user['user_id'],)
    )
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


# =============================================================================
# API: УСТРОЙСТВА
# =============================================================================

@app.get("/api/devices")
async def get_devices(current_user: dict = Depends(get_current_user)):
    """Получение списка устройств пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, name, starline_device_id, device_name, is_active, 
               last_update, created_at
        FROM user_devices 
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (current_user['user_id'],))
    
    devices = cursor.fetchall()
    conn.close()
    
    return devices


@app.post("/api/devices")
async def add_device(device: DeviceCreate, current_user: dict = Depends(get_current_user)):
    """Добавление нового устройства"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO user_devices (user_id, name, app_id, app_secret, 
            starline_login, starline_password)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        current_user['user_id'],
        device.name,
        device.app_id,
        device.app_secret,
        device.starline_login,
        device.starline_password
    ))
    
    conn.commit()
    device_id = cursor.lastrowid
    conn.close()
    
    return {"message": "Device added successfully", "device_id": device_id}


@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: int, current_user: dict = Depends(get_current_user)):
    """Удаление устройства"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id FROM user_devices WHERE id = %s AND user_id = %s",
        (device_id, current_user['user_id'])
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Device not found")
    
    cursor.execute("DELETE FROM user_devices WHERE id = %s", (device_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Device deleted successfully"}


@app.get("/api/devices/{device_id}/state")
async def get_device_state(
    device_id: int,
    hours: int = 24,
    current_user: dict = Depends(get_current_user)
):
    """Получение истории состояния устройства"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute(
        "SELECT id FROM user_devices WHERE id = %s AND user_id = %s",
        (device_id, current_user['user_id'])
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Device not found")
    
    cursor.execute("""
        SELECT timestamp, arm_state, ign_state, temp_inner, temp_engine,
               balance, latitude, longitude, speed
        FROM device_states
        WHERE device_id = %s AND timestamp >= DATE_SUB(NOW(), INTERVAL %s HOUR)
        ORDER BY timestamp DESC
    """, (device_id, hours))
    
    states = cursor.fetchall()
    conn.close()
    
    return states


@app.get("/api/devices/{device_id}/latest")
async def get_latest_state(device_id: int, current_user: dict = Depends(get_current_user)):
    """Получение последнего состояния устройства"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute(
        "SELECT id, name, starline_device_id, device_name, last_update FROM user_devices WHERE id = %s AND user_id = %s",
        (device_id, current_user['user_id'])
    )
    device = cursor.fetchone()
    if not device:
        conn.close()
        raise HTTPException(status_code=404, detail="Device not found")
    
    cursor.execute("""
        SELECT * FROM device_states
        WHERE device_id = %s
        ORDER BY timestamp DESC
        LIMIT 1
    """, (device_id,))
    
    state = cursor.fetchone()
    conn.close()
    
    return {"device": device, "state": state}


# =============================================================================
# API: СТАТИСТИКА
# =============================================================================

@app.get("/api/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    """Получение статистики пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute(
        "SELECT COUNT(*) as count FROM user_devices WHERE user_id = %s",
        (current_user['user_id'],)
    )
    devices_count = cursor.fetchone()['count']
    
    cursor.execute("""
        SELECT COUNT(*) as count FROM device_states ds
        JOIN user_devices ud ON ds.device_id = ud.id
        WHERE ud.user_id = %s AND DATE(ds.timestamp) = CURDATE()
    """, (current_user['user_id'],))
    records_today = cursor.fetchone()['count']
    
    conn.close()
    
    return {"devices_count": devices_count, "records_today": records_today}


@app.get("/api/health")
async def health_check():
    """Проверка здоровья API"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
