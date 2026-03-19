"""
StarLine Monitoring Backend v2.0
С поддержкой пробега, топлива, моточасов и ТО
"""
from datetime import datetime, timedelta, date
import hashlib
import os
import logging

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import mysql.connector
import jwt

# Config
DB = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "starline"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "starline_db"),
    "charset": "utf8mb4"
}
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-in-production")
JWT_ALGO = "HS256"

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="StarLine API v2")

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

class MaintenanceAdd(BaseModel):
    service_type: str
    description: Optional[str] = None
    mileage_at_service: Optional[int] = None
    motohrs_at_service: Optional[int] = None
    service_date: date
    next_service_mileage: Optional[int] = None
    next_service_motohrs: Optional[int] = None
    cost: Optional[float] = None
    notes: Optional[str] = None

class MaintenanceUpdate(BaseModel):
    service_type: Optional[str] = None
    description: Optional[str] = None
    mileage_at_service: Optional[int] = None
    motohrs_at_service: Optional[int] = None
    service_date: Optional[date] = None
    next_service_mileage: Optional[int] = None
    next_service_motohrs: Optional[int] = None
    cost: Optional[float] = None
    notes: Optional[str] = None

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

@app.on_event("startup")
def init():
    logging.info("DB initialized")

# ==================== AUTH ====================

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

# ==================== DEVICES ====================

@app.get("/api/devices")
def list_dev(user=Depends(me)):
    conn = db()
    c = conn.cursor(dictionary=True)
    c.execute("""
        SELECT 
            ud.id, ud.name, ud.starline_device_id, ud.device_name, ud.is_active, 
            ud.last_update, ud.created_at,
            ds.arm_state, ds.ign_state, ds.temp_inner, ds.temp_engine, 
            ds.balance, ds.latitude, ds.longitude, ds.timestamp as state_timestamp,
            ds.mileage, ds.fuel_litres, ds.motohrs, ds.speed, ds.battery_voltage, ds.gsm_lvl
        FROM user_devices ud
        LEFT JOIN (
            SELECT device_id, arm_state, ign_state, temp_inner, temp_engine, 
                   balance, latitude, longitude, timestamp, mileage, fuel_litres, motohrs, speed, battery_voltage, gsm_lvl,
                   ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY timestamp DESC) as rn
            FROM device_states
        ) ds ON ud.starline_device_id = ds.device_id AND ds.rn = 1
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
    c.execute("INSERT INTO user_devices (user_id,name,app_id,app_secret,starline_login,starline_password) VALUES (%s,%s,%s,%s,%s,%s)", (user['user_id'], d.name, d.app_id, d.app_secret, d.starline_login, d.starline_password))
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
    c.execute("SELECT id,name,starline_device_id,device_name,last_update FROM user_devices WHERE id=%s AND user_id=%s", (did, user['user_id']))
    dev = c.fetchone()
    if not dev: raise HTTPException(404, "Not found")
    
    starline_id = dev['starline_device_id']
    if starline_id:
        c.execute("""
            SELECT * FROM device_states 
            WHERE device_id=%s 
            ORDER BY timestamp DESC LIMIT 1
        """, (starline_id,))
        st = c.fetchone()
    else:
        st = None
    
    conn.close()
    
    # Merge state data into device object for easier frontend use
    if st:
        dev['arm_state'] = st.get('arm_state')
        dev['ign_state'] = st.get('ign_state')
        dev['temp_inner'] = st.get('temp_inner')
        dev['temp_engine'] = st.get('temp_engine')
        dev['balance'] = st.get('balance')
        dev['latitude'] = st.get('latitude')
        dev['longitude'] = st.get('longitude')
        dev['state_timestamp'] = st.get('timestamp')
        dev['mileage'] = st.get('mileage')
        dev['fuel_litres'] = st.get('fuel_litres')
        dev['motohrs'] = st.get('motohrs')
        dev['speed'] = st.get('speed')
        dev['battery_voltage'] = st.get('battery_voltage')
        dev['gsm_lvl'] = st.get('gsm_lvl')
    
    return {"device": dev, "state": st}

@app.get("/api/devices/{did}/state")
def history(did: int, hours: int = 24, user=Depends(me)):
    conn = db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT starline_device_id FROM user_devices WHERE id=%s AND user_id=%s", (did, user['user_id']))
    dev = c.fetchone()
    if not dev: raise HTTPException(404, "Not found")
    
    starline_id = dev['starline_device_id']
    if not starline_id:
        conn.close()
        return []
    
    c.execute("""
        SELECT timestamp, arm_state, ign_state, temp_inner, temp_engine, 
               balance, latitude, longitude, speed, mileage, fuel_litres, motohrs, battery_voltage, gsm_lvl
        FROM device_states 
        WHERE device_id=%s AND timestamp>=DATE_SUB(NOW(),INTERVAL %s HOUR) 
        ORDER BY timestamp DESC
    """, (starline_id, hours))
    r = c.fetchall()
    conn.close()
    return r

# ==================== STATISTICS ====================

@app.get("/api/devices/{did}/stats")
def stats(did: int, days: int = 7, user=Depends(me)):
    """Статистика по устройству за период"""
    conn = db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT starline_device_id FROM user_devices WHERE id=%s AND user_id=%s", (did, user['user_id']))
    dev = c.fetchone()
    if not dev: raise HTTPException(404, "Not found")
    
    starline_id = dev['starline_device_id']
    if not starline_id:
        conn.close()
        return {}
    
    # Текущие показатели
    c.execute("""
        SELECT mileage, fuel_litres, motohrs, timestamp
        FROM device_states 
        WHERE device_id=%s AND mileage IS NOT NULL
        ORDER BY timestamp DESC LIMIT 1
    """, (starline_id,))
    current = c.fetchone()
    
    # Показатели N дней назад
    c.execute("""
        SELECT mileage, motohrs, timestamp
        FROM device_states 
        WHERE device_id=%s AND mileage IS NOT NULL
        AND timestamp <= DATE_SUB(NOW(), INTERVAL %s DAY)
        ORDER BY timestamp DESC LIMIT 1
    """, (starline_id, days))
    previous = c.fetchone()
    
    result = {
        "current": current,
        "previous": previous,
    }
    
    if current and previous:
        if current.get('mileage') and previous.get('mileage'):
            result['mileage_diff'] = current['mileage'] - previous['mileage']
        if current.get('motohrs') and previous.get('motohrs'):
            result['motohrs_diff'] = current['motohrs'] - previous['motohrs']
    
    # Средний расход топлива
    c.execute("""
        SELECT AVG(fuel_litres) as avg_fuel, MIN(fuel_litres) as min_fuel, MAX(fuel_litres) as max_fuel
        FROM device_states 
        WHERE device_id=%s AND fuel_litres IS NOT NULL
        AND timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
    """, (starline_id, days))
    fuel_stats = c.fetchone()
    result['fuel_stats'] = fuel_stats
    
    conn.close()
    return result

@app.get("/api/devices/{did}/track")
def get_device_track(did: int, hours: int = 24, user=Depends(me)):
    """Получить трек перемещения устройства за последние N часов"""
    conn = db()
    c = conn.cursor(dictionary=True)
    
    # Получаем starline_device_id
    c.execute("SELECT starline_device_id FROM user_devices WHERE id=%s AND user_id=%s", (did, user['user_id']))
    dev = c.fetchone()
    if not dev:
        conn.close()
        raise HTTPException(404, "Device not found")
    
    starline_id = dev['starline_device_id']
    if not starline_id:
        conn.close()
        return []
    
    # Получаем точки трека где были координаты
    c.execute("""
        SELECT 
            latitude, longitude, timestamp, speed, ign_state,
            arm_state, temp_inner, battery_voltage
        FROM device_states 
        WHERE device_id=%s 
        AND latitude IS NOT NULL 
        AND longitude IS NOT NULL
        AND timestamp >= DATE_SUB(NOW(), INTERVAL %s HOUR)
        ORDER BY timestamp ASC
    """, (starline_id, hours))
    
    track = c.fetchall()
    conn.close()
    
    # Фильтруем - убираем точки где координаты не менялись (стоял на месте)
    filtered_track = []
    last_lat, last_lon = None, None
    
    for point in track:
        lat = point['latitude']
        lon = point['longitude']
        
        # Добавляем точку если:
        # - это первая точка
        # - координаты изменились
        # - зажигание было включено (движение)
        # - или прошло больше 5 минут с последней точки
        if last_lat is None:
            filtered_track.append(point)
            last_lat, last_lon = lat, lon
        elif point['ign_state'] == 1:
            # При движении добавляем все точки
            filtered_track.append(point)
            last_lat, last_lon = lat, lon
        elif abs(lat - last_lat) > 0.0001 or abs(lon - last_lon) > 0.0001:
            # Координаты изменились
            filtered_track.append(point)
            last_lat, last_lon = lat, lon
    
    return filtered_track

# ==================== MAINTENANCE ====================

@app.get("/api/service-types")
def get_service_types():
    """Получить список типов обслуживания"""
    conn = db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT * FROM service_types ORDER BY name")
    r = c.fetchall()
    conn.close()
    return r

@app.get("/api/devices/{did}/maintenance")
def get_maintenance(did: int, user=Depends(me)):
    """Получить записи ТО для устройства"""
    conn = db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT starline_device_id FROM user_devices WHERE id=%s AND user_id=%s", (did, user['user_id']))
    dev = c.fetchone()
    if not dev: raise HTTPException(404, "Not found")
    
    starline_id = dev['starline_device_id']
    if not starline_id:
        conn.close()
        return []
    
    c.execute("""
        SELECT m.*, 
               ds_current.mileage as current_mileage,
               ds_current.motohrs as current_motohrs
        FROM maintenance_records m
        LEFT JOIN (
            SELECT device_id, mileage, motohrs 
            FROM device_states 
            WHERE device_id = %s 
            ORDER BY timestamp DESC LIMIT 1
        ) ds_current ON 1=1
        WHERE m.device_id = %s
        ORDER BY m.service_date DESC
    """, (starline_id, starline_id))
    records = c.fetchall()
    
    # Вычисляем пробег/моточасы с последнего ТО для каждой записи
    for record in records:
        if record.get('current_mileage') and record.get('mileage_at_service'):
            record['km_since_service'] = record['current_mileage'] - record['mileage_at_service']
        if record.get('current_motohrs') and record.get('motohrs_at_service'):
            record['hours_since_service'] = record['current_motohrs'] - record['motohrs_at_service']
    
    conn.close()
    return records

@app.post("/api/devices/{did}/maintenance")
def add_maintenance(did: int, m: MaintenanceAdd, user=Depends(me)):
    """Добавить запись ТО"""
    conn = db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT starline_device_id FROM user_devices WHERE id=%s AND user_id=%s", (did, user['user_id']))
    dev = c.fetchone()
    if not dev: raise HTTPException(404, "Not found")
    
    starline_id = dev['starline_device_id']
    if not starline_id:
        conn.close()
        raise HTTPException(400, "Device not synced with StarLine yet")
    
    # Если пробег/моточасы не указаны, берём текущие
    mileage = m.mileage_at_service
    motohrs = m.motohrs_at_service
    
    if mileage is None or motohrs is None:
        c.execute("""
            SELECT mileage, motohrs FROM device_states 
            WHERE device_id=%s ORDER BY timestamp DESC LIMIT 1
        """, (starline_id,))
        current = c.fetchone()
        if current:
            if mileage is None:
                mileage = current['mileage']
            if motohrs is None:
                motohrs = current['motohrs']
    
    # Если интервал не указан, берём из service_types
    next_km = m.next_service_mileage
    next_hours = m.next_service_motohrs
    
    if next_km is None or next_hours is None:
        c.execute("SELECT default_interval_km, default_interval_hours FROM service_types WHERE name=%s", (m.service_type,))
        st = c.fetchone()
        if st:
            if next_km is None and st['default_interval_km']:
                next_km = st['default_interval_km']
            if next_hours is None and st['default_interval_hours']:
                next_hours = st['default_interval_hours']
    
    c.execute("""
        INSERT INTO maintenance_records 
        (device_id, service_type, description, mileage_at_service, motohrs_at_service,
         service_date, next_service_mileage, next_service_motohrs, cost, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (starline_id, m.service_type, m.description, mileage, motohrs,
          m.service_date, next_km, next_hours, m.cost, m.notes))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return {"id": rid, "message": "OK"}

@app.put("/api/devices/{did}/maintenance/{mid}")
def update_maintenance(did: int, mid: int, m: MaintenanceUpdate, user=Depends(me)):
    """Обновить запись ТО"""
    conn = db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT starline_device_id FROM user_devices WHERE id=%s AND user_id=%s", (did, user['user_id']))
    dev = c.fetchone()
    if not dev: raise HTTPException(404, "Not found")
    
    starline_id = dev['starline_device_id']
    
    c.execute("SELECT id FROM maintenance_records WHERE id=%s AND device_id=%s", (mid, starline_id))
    if not c.fetchone():
        conn.close()
        raise HTTPException(404, "Record not found")
    
    updates = []
    values = []
    if m.service_type:
        updates.append("service_type = %s")
        values.append(m.service_type)
    if m.description is not None:
        updates.append("description = %s")
        values.append(m.description)
    if m.mileage_at_service is not None:
        updates.append("mileage_at_service = %s")
        values.append(m.mileage_at_service)
    if m.motohrs_at_service is not None:
        updates.append("motohrs_at_service = %s")
        values.append(m.motohrs_at_service)
    if m.service_date:
        updates.append("service_date = %s")
        values.append(m.service_date)
    if m.next_service_mileage is not None:
        updates.append("next_service_mileage = %s")
        values.append(m.next_service_mileage)
    if m.next_service_motohrs is not None:
        updates.append("next_service_motohrs = %s")
        values.append(m.next_service_motohrs)
    if m.cost is not None:
        updates.append("cost = %s")
        values.append(m.cost)
    if m.notes is not None:
        updates.append("notes = %s")
        values.append(m.notes)
    
    if updates:
        values.extend([mid, starline_id])
        c.execute(f"UPDATE maintenance_records SET {', '.join(updates)} WHERE id=%s AND device_id=%s", values)
        conn.commit()
    
    conn.close()
    return {"message": "OK"}

@app.delete("/api/devices/{did}/maintenance/{mid}")
def delete_maintenance(did: int, mid: int, user=Depends(me)):
    """Удалить запись ТО"""
    conn = db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT starline_device_id FROM user_devices WHERE id=%s AND user_id=%s", (did, user['user_id']))
    dev = c.fetchone()
    if not dev: raise HTTPException(404, "Not found")
    
    starline_id = dev['starline_device_id']
    
    c.execute("DELETE FROM maintenance_records WHERE id=%s AND device_id=%s", (mid, starline_id))
    conn.commit()
    conn.close()
    return {"message": "Deleted"}

@app.get("/api/devices/{did}/maintenance/upcoming")
def get_upcoming(did: int, user=Depends(me)):
    """Получить предстоящие ТО"""
    conn = db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT starline_device_id FROM user_devices WHERE id=%s AND user_id=%s", (did, user['user_id']))
    dev = c.fetchone()
    if not dev: raise HTTPException(404, "Not found")
    
    starline_id = dev['starline_device_id']
    if not starline_id:
        conn.close()
        return []
    
    # Текущие показатели
    c.execute("""
        SELECT mileage, motohrs FROM device_states 
        WHERE device_id=%s ORDER BY timestamp DESC LIMIT 1
    """, (starline_id,))
    current = c.fetchone()
    
    if not current:
        conn.close()
        return []
    
    # Последние ТО каждого типа
    c.execute("""
        SELECT m.*, 
               m.mileage_at_service + m.next_service_mileage as next_mileage_due,
               m.motohrs_at_service + m.next_service_motohrs as next_motohrs_due
        FROM maintenance_records m
        WHERE m.device_id = %s
        AND m.id IN (
            SELECT MAX(id) FROM maintenance_records 
            WHERE device_id = %s AND service_type = m.service_type
        )
    """, (starline_id, starline_id))
    records = c.fetchall()
    
    upcoming = []
    for record in records:
        km_left = None
        hours_left = None
        
        if record.get('next_mileage_due') and current.get('mileage'):
            km_left = record['next_mileage_due'] - current['mileage']
        
        if record.get('next_motohrs_due') and current.get('motohrs'):
            hours_left = record['next_motohrs_due'] - current['motohrs']
        
        # Если осталось меньше 10% от интервала или уже просрочено
        is_due = False
        if km_left is not None and km_left <= (record.get('next_service_mileage') or 0) * 0.1:
            is_due = True
        if hours_left is not None and hours_left <= (record.get('next_service_motohrs') or 0) * 0.1:
            is_due = True
        if km_left is not None and km_left < 0:
            is_due = True
        if hours_left is not None and hours_left < 0:
            is_due = True
        
        if is_due or (km_left is not None and km_left < 2000) or (hours_left is not None and hours_left < 50):
            upcoming.append({
                **record,
                'km_left': km_left,
                'hours_left': hours_left,
                'is_overdue': (km_left is not None and km_left < 0) or (hours_left is not None and hours_left < 0)
            })
    
    # Сортируем по срочности
    upcoming.sort(key=lambda x: (x.get('km_left') or 999999, x.get('hours_left') or 999999))
    
    conn.close()
    return upcoming

# ==================== HEALTH ====================

@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
