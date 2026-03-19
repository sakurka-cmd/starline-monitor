#!/usr/bin/env python3
"""
StarLine Worker v3.1 - Исправленная версия

ИСПРАВЛЕНО: user_id берётся из ответа auth.slid, а не из login!

Запуск:
  python worker.py --daemon
"""

import hashlib
import json
import logging
import os
import re
import sys
import time
import signal
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict

import mysql.connector
import requests
from mysql.connector import Error


# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================

@dataclass
class Config:
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "starline"
    mysql_password: str = "starline123"
    mysql_database: str = "starline_db"
    poll_interval_seconds: int = 60
    
    @classmethod
    def from_file(cls, filepath: str) -> 'Config':
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def from_env(cls) -> 'Config':
        return cls(
            mysql_host=os.getenv("MYSQL_HOST", "localhost"),
            mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
            mysql_user=os.getenv("MYSQL_USER", "starline"),
            mysql_password=os.getenv("MYSQL_PASSWORD", "starline123"),
            mysql_database=os.getenv("MYSQL_DATABASE", "starline_db"),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL", "60")),
        )


# =============================================================================
# STARLINE API
# =============================================================================

class StarLineAPI:
    """Клиент StarLine API"""
    
    SLID_URL = "https://id.starline.ru"
    WEBAPI_URL = "https://developer.starline.ru"
    
    def __init__(self, app_id: str, app_secret: str, login: str, password: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.login = login
        self.password = password
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "StarLineWorker/3.1",
            "Accept": "application/json",
        })
        
        self.app_token: Optional[str] = None
        self.user_token: Optional[str] = None
        self.slnet_token: Optional[str] = None
        self.user_id: Optional[str] = None  # WebAPI user_id!
        
        self.logger = logging.getLogger('StarLineAPI')
    
    def authenticate(self) -> bool:
        """Полная авторизация"""
        try:
            # ===== ШАГ 1: Код приложения =====
            url = f"{self.SLID_URL}/apiV3/application/getCode"
            secret_md5 = hashlib.md5(self.app_secret.encode()).hexdigest()
            
            resp = self.session.get(url, params={
                "appId": self.app_id,
                "secret": secret_md5
            })
            data = resp.json()
            
            if data.get("state") != 1:
                self.logger.error(f"getCode failed: {data}")
                return False
            
            code = data["desc"]["code"]
            self.logger.info(f"Step 1 OK: code={code[:8]}...")
            
            # ===== ШАГ 2: Токен приложения =====
            url = f"{self.SLID_URL}/apiV3/application/getToken"
            secret_md5 = hashlib.md5((self.app_secret + code).encode()).hexdigest()
            
            resp = self.session.get(url, params={
                "appId": self.app_id,
                "secret": secret_md5
            })
            data = resp.json()
            
            if data.get("state") != 1:
                self.logger.error(f"getToken failed: {data}")
                return False
            
            self.app_token = data["desc"]["token"]
            self.logger.info(f"Step 2 OK: token={self.app_token[:16]}...")
            
            # ===== ШАГ 3: Авторизация пользователя =====
            url = f"{self.SLID_URL}/apiV3/user/login"
            password_sha1 = hashlib.sha1(self.password.encode()).hexdigest()
            
            resp = self.session.post(
                url,
                headers={"token": self.app_token},
                data={"login": self.login, "pass": password_sha1}
            )
            data = resp.json()
            
            # Проверка 2FA
            if data.get("state") == 2:
                self.logger.error(f"2FA required: {data['desc'].get('phone')}")
                return False
            
            if data.get("state") != 1:
                self.logger.error(f"Login failed: {data}")
                return False
            
            self.user_token = data["desc"]["user_token"]
            login_user_id = data["desc"]["id"]  # Временно сохраняем
            self.logger.info(f"Step 3 OK: login user_id={login_user_id}")
            
            # ===== ШАГ 4: WebAPI авторизация =====
            url = f"{self.WEBAPI_URL}/json/v2/auth.slid"
            
            resp = self.session.post(url, json={"slid_token": self.user_token})
            
            # Парсим ответ auth.slid
            result = resp.json()
            self.logger.info(f"auth.slid response: {json.dumps(result, ensure_ascii=False)}")
            
            # ИСПРАВЛЕНИЕ: user_id берём из ответа auth.slid!
            # Формат ответа: {"code": "200", "user_id": "1797157", ...}
            if result.get("code") == "200" or result.get("code") == 200:
                self.user_id = result.get("user_id")
                self.logger.info(f"WebAPI user_id from auth.slid: {self.user_id}")
            
            # Если не нашли - используем из логина
            if not self.user_id:
                self.user_id = login_user_id
                self.logger.warning(f"Using login user_id: {self.user_id}")
            
            # Ищем cookie slnet
            self.slnet_token = None
            
            for cookie in resp.cookies:
                self.logger.info(f"Found cookie: {cookie.name}")
                if cookie.name == "slnet":
                    self.slnet_token = cookie.value
                    break
            
            # Пробуем в заголовке
            if not self.slnet_token:
                set_cookie = resp.headers.get('set-cookie', '')
                match = re.search(r'slnet=([^;]+)', set_cookie)
                if match:
                    self.slnet_token = match.group(1)
            
            if not self.slnet_token:
                self.logger.error("slnet token not found!")
                return False
            
            self.session.cookies.set("slnet", self.slnet_token, domain="developer.starline.ru")
            self.logger.info(f"Step 4 OK: slnet={self.slnet_token[:16]}...")
            self.logger.info(f"Final WebAPI user_id: {self.user_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Auth error: {e}")
            return False
    
    def get_devices(self) -> List[Dict]:
        """Получение списка устройств"""
        if not self.user_id:
            return []
        
        url = f"{self.WEBAPI_URL}/json/v1/user/{self.user_id}/devices"
        
        self.logger.info(f"Requesting devices for user_id={self.user_id}")
        
        resp = self.session.get(url)
        result = resp.json()
        
        self.logger.info(f"Devices response: {json.dumps(result, ensure_ascii=False)[:500]}")
        
        # Парсим разные форматы
        devices = []
        
        if "devices" in result and isinstance(result["devices"], list):
            devices = result["devices"]
        elif "desc" in result:
            if isinstance(result["desc"], list):
                devices = result["desc"]
            elif isinstance(result["desc"], dict) and "devices" in result["desc"]:
                devices = result["desc"]["devices"]
        
        self.logger.info(f"Found {len(devices)} devices")
        return devices
    
    def get_device_data(self, device_id: str) -> Dict:
        """Получение данных устройства"""
        url = f"{self.WEBAPI_URL}/json/v3/device/{device_id}/data"
        
        resp = self.session.get(url)
        result = resp.json()
        
        self.logger.info(f"Device data response: {json.dumps(result, ensure_ascii=False)[:500]}")
        
        # API возвращает code: 200 или state: 1
        code = result.get("code")
        state = result.get("state")
        
        if code not in [200, "200"] and state != 1:
            self.logger.warning(f"Device data error: code={code}, state={state}")
            return {}
        
        return result.get("desc", {})


# =============================================================================
# БАЗА ДАННЫХ
# =============================================================================

class Database:
    def __init__(self, config: Config):
        self.config = config
        self.connection = None
        self.logger = logging.getLogger('Database')
    
    def connect(self) -> bool:
        try:
            self.connection = mysql.connector.connect(
                host=self.config.mysql_host,
                port=self.config.mysql_port,
                user=self.config.mysql_user,
                password=self.config.mysql_password,
                database=self.config.mysql_database,
                charset='utf8mb4'
            )
            self.logger.info("Connected to MySQL")
            return True
        except Error as e:
            self.logger.error(f"MySQL error: {e}")
            return False
    
    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    def get_user_devices(self) -> List[Dict]:
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT ud.*, u.email as user_email
            FROM user_devices ud
            JOIN users u ON ud.user_id = u.id
            WHERE ud.is_active = 1
        """)
        return cursor.fetchall()
    
    def update_device_status(self, device_id: int, starline_device_id: str = None, 
                             device_name: str = None, error: str = None):
        cursor = self.connection.cursor()
        sql = """
            UPDATE user_devices SET
                starline_device_id = %s,
                device_name = %s,
                last_update = NOW(),
                last_error = %s
            WHERE id = %s
        """
        cursor.execute(sql, (starline_device_id, device_name, error, device_id))
        self.connection.commit()
    
    def save_device(self, device_id: str, name: str, device_type: str = None):
        cursor = self.connection.cursor()
        sql = """
            INSERT INTO devices (device_id, name, device_type)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE name = VALUES(name), updated_at = NOW()
        """
        cursor.execute(sql, (device_id, name, device_type))
        self.connection.commit()
    
    def save_state(self, device_id: str, state_data: Dict):
        if not state_data:
            return
        
        cursor = self.connection.cursor()
        
        # Логируем для отладки
        self.logger.info(f"State data keys: {list(state_data.keys())}")
        
        # Температуры могут быть в temp или в других полях
        temps = state_data.get("temp", {})
        if not temps and "temperature" in state_data:
            temps = state_data.get("temperature", {})
        
        gsm = state_data.get("gsm", {})
        gps = state_data.get("gps", {})
        
        # Получаем значения с дефолтами
        arm_state = state_data.get("arm", state_data.get("arm_state", 0))
        ign_state = state_data.get("ign", state_data.get("ign_state", 0))
        run_time = state_data.get("run_time", 0)
        balance = state_data.get("balance")
        battery = state_data.get("battery_voltage", state_data.get("battery"))
        
        # Сериализуем raw_data в строку JSON
        raw_json = json.dumps(state_data, ensure_ascii=False, default=str)
        
        sql = """
            INSERT INTO device_states 
            (device_id, timestamp, arm_state, ign_state, run_time,
             temp_inner, temp_engine, temp_outdoor, balance,
             gsm_level, gps_level, battery_voltage, raw_data)
            VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            cursor.execute(sql, (
                device_id,
                arm_state,
                ign_state,
                run_time,
                temps.get("inner"),
                temps.get("engine"),
                temps.get("outdoor"),
                balance,
                gsm.get("level"),
                gps.get("level"),
                battery,
                raw_json
            ))
            self.connection.commit()
            self.logger.info(f"State saved: {device_id}")
        except Error as e:
            self.logger.error(f"Save state error: {e}")


# =============================================================================
# WORKER
# =============================================================================

class Worker:
    def __init__(self, config: Config):
        self.config = config
        self.db: Optional[Database] = None
        self.logger = logging.getLogger('Worker')
        self.running = False
    
    def initialize(self) -> bool:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s"
        )
        
        self.db = Database(self.config)
        return self.db.connect()
    
    def process_device(self, user_device: Dict):
        self.logger.info(f"\nProcessing: {user_device['name']} (user: {user_device['user_email']})")
        
        api = StarLineAPI(
            app_id=user_device['app_id'],
            app_secret=user_device['app_secret'],
            login=user_device['starline_login'],
            password=user_device['starline_password']
        )
        
        if not api.authenticate():
            self.db.update_device_status(user_device['id'], error="Auth failed")
            return
        
        devices = api.get_devices()
        
        if not devices:
            self.logger.warning(f"No devices found for {user_device['name']}")
            self.db.update_device_status(user_device['id'], error="No devices found")
            return
        
        for device in devices:
            device_id = device.get("device_id") or device.get("id")
            if not device_id:
                continue
            
            device_name = device.get("name") or device.get("alias") or device_id
            device_type = device.get("device_type") or device.get("type")
            
            self.logger.info(f"  Device: {device_name} (ID: {device_id})")
            
            self.db.save_device(device_id, device_name, device_type)
            
            state = api.get_device_data(device_id)
            if state:
                self.db.save_state(device_id, state)
                self.logger.info(f"    arm={state.get('arm')}, ign={state.get('ign')}")
            
            self.db.update_device_status(
                user_device['id'],
                starline_device_id=device_id,
                device_name=device_name,
                error=None
            )
    
    def run_once(self):
        self.logger.info("=" * 50)
        self.logger.info(f"Worker started (interval: {self.config.poll_interval_seconds}s)")
        
        user_devices = self.db.get_user_devices()
        self.logger.info(f"Found {len(user_devices)} StarLine accounts")
        
        for user_device in user_devices:
            try:
                self.process_device(user_device)
            except Exception as e:
                self.logger.error(f"Error: {e}")
                self.db.update_device_status(user_device['id'], error=str(e))
        
        self.logger.info("Done. Sleeping...")
    
    def run_daemon(self):
        def handler(sig, frame):
            self.logger.info("Stopping...")
            self.running = False
        
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
        
        if not self.initialize():
            sys.exit(1)
        
        self.running = True
        self.logger.info("Worker daemon started")
        
        while self.running:
            try:
                self.run_once()
            except Exception as e:
                self.logger.error(f"Error: {e}")
            
            for _ in range(self.config.poll_interval_seconds):
                if not self.running:
                    break
                time.sleep(1)
        
        self.db.close()
        self.logger.info("Worker stopped")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="StarLine Worker v3.1")
    parser.add_argument("-c", "--config", default="config.json")
    parser.add_argument("-d", "--daemon", action="store_true")
    args = parser.parse_args()
    
    if os.path.exists(args.config):
        config = Config.from_file(args.config)
    else:
        config = Config.from_env()
    
    worker = Worker(config)
    
    if not worker.initialize():
        sys.exit(1)
    
    if args.daemon:
        worker.run_daemon()
    else:
        worker.run_once()
        worker.db.close()


if __name__ == "__main__":
    main()
