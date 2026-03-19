"""
StarLine Monitoring Backend - Fixed version
Работает со схемой Worker (device_id = StarLine ID BIGINT)
"""
from datetime import datetime, timedelta
import hashlib
import os
import logging

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import mysql.connector
import jwt

# Config
DB = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "starline"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "starline_db")
}
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-in-production")
JWT_ALGO = "HS256"

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="StarLine API")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
security = HTTPBearer()

# Models
class UserReg(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class DeviceAdd(BaseModel):
    name: str
    app_id: str
    app_secret: str
    starline_login: str
    starline_password: str

# Utils
def db():
    return mysql.connector.connect(**DB)

def hp(p): return hashlib.sha256(p.encode()).hexdigest()

def mk_token(uid, email):
    return jwt.encode({"user_id": uid, "email": email, "exp": datetime.utcnow() + timedelta(hours=24)}, JWT_SECRET, algorithm=JWT_ALGO)

def check_token(t):
    try: return jwt.decode(t, JWT_SECRET, algorithms=[JWT_ALGO])
    except: raise HTTPException(401, "Invalid token")

async def me(c=Depends(security)): return check_token(c.credentials)

# Init DB - НЕ создаём таблицы, они уже есть от Worker
@app.on_event("startup")
def init():
    logging.info("DB initialized")

# Auth
@app.post("/api/auth/register")
def reg(u: UserReg):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email=%s", (u.email,))
    if c.fetchone(): raise HTTPException(400, "Email exists")
    c.execute("INSERT INTO users (email,password_hash,name) VALUES (%s,%s,%s)", (u.email, hp(u.password), u.name))
    conn.commit()
    uid = c.lastrowid
    conn.close()
    return {"token": mk_token(uid, u.email), "user": {"id": uid, "email": u.email, "name": u.name}}

@app.post("/api/auth/login")
def login(u: UserLogin):
    conn = db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT id,email,name FROM users WHERE email=%s AND password_hash=%s", (u.email, hp(u.password)))
    r = c.fetchone()
    conn.close()
    if not r: raise HTTPException(401, "Invalid credentials")
    return {"token": mk_token(r['id'], r['email']), "user": r}

@app.get("/api/auth/me")
def get_me(user=Depends(me)):
    conn = db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT id,email,name,created_at FROM users WHERE id=%s", (user['user_id'],))
    r = c.fetchone()
    conn.close()
    return r

# Devices - возвращаем устройства с последним состоянием
@app.get("/api/devices")
def list_dev(user=Depends(me)):
    conn = db()
    c = conn.cursor(dictionary=True)
    # Получаем user_devices с последним состоянием из device_states
    c.execute("""
        SELECT ud.id, ud.name, ud.starline_device_id, ud.device_name, ud.is_active, 
               ud.last_update, ud.created_at,
               ds.arm_state, ds.ign_state, ds.temp_inner, ds.temp_engine, 
               ds.balance, ds.latitude, ds.longitude, ds.timestamp as state_timestamp
        FROM user_devices ud
        LEFT JOIN device_states ds ON ud.starline_device_id = ds.device_id
        LEFT JOIN (
            SELECT device_id, MAX(timestamp) as max_ts 
            FROM device_states 
            GROUP BY device_id
        ) latest ON ds.device_id = latest.device_id AND ds.timestamp = latest.max_ts
        WHERE ud.user_id = %s AND ud.is_active = 1
        ORDER BY ud.created_at DESC
    """, (user['user_id'],))
    r = c.fetchall()
    conn.close()
    return r

@app.post("/api/devices")
def add_dev(d: DeviceAdd, user=Depends(me)):
    conn = db()
    c = conn.cursor()
    c.execute("""INSERT INTO user_devices 
        (user_id,name,app_id,app_secret,starline_login,starline_password) 
        VALUES (%s,%s,%s,%s,%s,%s)""", 
        (user['user_id'], d.name, d.app_id, d.app_secret, d.starline_login, d.starline_password))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return {"message": "OK", "device_id": rid}

@app.delete("/api/devices/{did}")
def del_dev(did: int, user=Depends(me)):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT id FROM user_devices WHERE id=%s AND user_id=%s", (did, user['user_id']))
    if not c.fetchone(): raise HTTPException(404, "Not found")
    c.execute("DELETE FROM user_devices WHERE id=%s", (did,))
    conn.commit()
    conn.close()
    return {"message": "Deleted"}

@app.get("/api/devices/{did}/latest")
def latest(did: int, user=Depends(me)):
    conn = db()
    c = conn.cursor(dictionary=True)
    # Получаем устройство
    c.execute("SELECT id,name,starline_device_id,device_name,last_update FROM user_devices WHERE id=%s AND user_id=%s", (did, user['user_id']))
    dev = c.fetchone()
    if not dev: raise HTTPException(404, "Not found")
    
    # Ищем состояние по starline_device_id (BIGINT!)
    starline_id = dev['starline_device_id']
    if starline_id:
        c.execute("SELECT * FROM device_states WHERE device_id=%s ORDER BY timestamp DESC LIMIT 1", (starline_id,))
        st = c.fetchone()
    else:
        st = None
    
    conn.close()
    return {"device": dev, "state": st}

@app.get("/api/devices/{did}/state")
def history(did: int, hours: int = 24, user=Depends(me)):
    conn = db()
    c = conn.cursor(dictionary=True)
    # Получаем starline_device_id
    c.execute("SELECT starline_device_id FROM user_devices WHERE id=%s AND user_id=%s", (did, user['user_id']))
    dev = c.fetchone()
    if not dev: raise HTTPException(404, "Not found")
    
    starline_id = dev['starline_device_id']
    if not starline_id:
        conn.close()
        return []
    
    # Ищем по StarLine ID (BIGINT)
    c.execute("""
        SELECT timestamp,arm_state,ign_state,temp_inner,temp_engine,balance,latitude,longitude,speed 
        FROM device_states 
        WHERE device_id=%s AND timestamp>=DATE_SUB(NOW(),INTERVAL %s HOUR) 
        ORDER BY timestamp DESC
    """, (starline_id, hours))
    r = c.fetchall()
    conn.close()
    return r

@app.get("/api/stats")
def stats(user=Depends(me)):
    conn = db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT COUNT(*) as cnt FROM user_devices WHERE user_id=%s AND is_active=1", (user['user_id'],))
    devs = c.fetchone()['cnt']
    c.execute("""
        SELECT COUNT(*) as cnt FROM device_states ds 
        JOIN user_devices ud ON ds.device_id = ud.starline_device_id 
        WHERE ud.user_id=%s AND DATE(ds.timestamp)=CURDATE()
    """, (user['user_id'],))
    recs = c.fetchone()['cnt']
    conn.close()
    return {"devices_count": devs, "records_today": recs}

@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
