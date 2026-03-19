#!/usr/bin/env python3
"""
StarLine Worker v2.0 - Сбор данных из StarLine API

Архитектура:
- Читает пользователей из БД (таблица users с StarLine credentials)
- Для каждого пользователя авторизуется и получает устройства
- Сохраняет состояния в device_states

Запуск:
  python worker.py --daemon     # Режим демона
  python worker.py              # Однократный запуск
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
    """Конфигурация - ТОЛЬКО MySQL, StarLine берется из БД пользователей"""
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
    """Клиент StarLine API с исправлениями"""
    
    SLID_URL = "https://id.starline.ru"
    WEBAPI_URL = "https://developer.starline.ru"
    
    def __init__(self, app_id: str, app_secret: str, user_login: str, user_password: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.user_login = user_login
        self.user_password = user_password
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "StarLineWorker/2.0",
            "Accept": "application/json",
        })
        
        self.app_token: Optional[str] = None
        self.user_token: Optional[str] = None
        self.slnet_token: Optional[str] = None
        self.user_id: Optional[str] = None
        
        self.logger = logging.getLogger('StarLineAPI')
    
    def authenticate(self) -> bool:
        """Полная авторизация в StarLine"""
        try:
            # Шаг 1: Код приложения
            url = f"{self.SLID_URL}/apiV3/application/getCode"
            secret_md5 = hashlib.md5(self.app_secret.encode()).hexdigest()
            
            resp = self.session.get(url, params={"appId": self.app_id, "secret": secret_md5})
            data = resp.json()
            
            if data.get("state") != 1:
                self.logger.error(f"Ошибка getCode: {data}")
                return False
            
            code = data["desc"]["code"]
            self.logger.info(f"Код приложения: {code[:8]}...")
            
            # Шаг 2: Токен приложения
            url = f"{self.SLID_URL}/apiV3/application/getToken"
            secret_md5 = hashlib.md5((self.app_secret + code).encode()).hexdigest()
            
            resp = self.session.get(url, params={"appId": self.app_id, "secret": secret_md5})
            data = resp.json()
            
            if data.get("state") != 1:
                self.logger.error(f"Ошибка getToken: {data}")
                return False
            
            self.app_token = data["desc"]["token"]
            self.logger.info(f"Токен приложения: {self.app_token[:16]}...")
            
            # Шаг 3: Авторизация пользователя
            url = f"{self.SLID_URL}/apiV3/user/login"
            password_sha1 = hashlib.sha1(self.user_password.encode()).hexdigest()
            
            resp = self.session.post(
                url,
                headers={"token": self.app_token},
                data={"login": self.user_login, "pass": password_sha1}
            )
            data = resp.json()
            
            if data.get("state") == 2:
                self.logger.error(f"Требуется 2FA: {data['desc'].get('phone')}")
                return False
            
            if data.get("state") != 1:
                self.logger.error(f"Ошибка login: {data}")
                return False
            
            self.user_token = data["desc"]["user_token"]
            self.user_id = data["desc"]["id"]
            self.logger.info(f"Login OK, user_id={self.user_id}")
            
            # Шаг 4: WebAPI авторизация
            url = f"{self.WEBAPI_URL}/json/v2/auth.slid"
            
            resp = self.session.post(url, json={"slid_token": self.user_token})
            
            # ИСПРАВЛЕНИЕ: ищем cookie 'slnet'
            self.slnet_token = None
            
            for cookie in resp.cookies:
                if cookie.name == "slnet":  # <-- ИСПРАВЛЕНО!
                    self.slnet_token = cookie.value
                    break
            
            if not self.slnet_token:
                set_cookie = resp.headers.get('set-cookie', '')
                match = re.search(r'slnet=([^;]+)', set_cookie)
                if match:
                    self.slnet_token = match.group(1)
            
            if not self.slnet_token:
                self.logger.error("Не удалось получить slnet token")
                return False
            
            self.session.cookies.set("slnet", self.slnet_token, domain="developer.starline.ru")
            self.logger.info(f"slnet token: {self.slnet_token[:16]}...")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка авторизации: {e}")
            return False
    
    def get_devices(self) -> List[Dict]:
        """Получение списка устройств"""
        if not self.user_id:
            return []
        
        url = f"{self.WEBAPI_URL}/json/v1/user/{self.user_id}/devices"
        
        resp = self.session.get(url)
        result = resp.json()
        
        # ИСПРАВЛЕНИЕ: разные форматы ответа
        devices = []
        
        if "devices" in result and isinstance(result["devices"], list):
            devices = result["devices"]
        elif "desc" in result:
            if isinstance(result["desc"], list):
                devices = result["desc"]
            elif isinstance(result["desc"], dict) and "devices" in result["desc"]:
                devices = result["desc"]["devices"]
        
        self.logger.info(f"Found {len(devices)} StarLine devices")
        
        return devices
    
    def get_device_data(self, device_id: str) -> Dict:
        """Получение данных устройства"""
        url = f"{self.WEBAPI_URL}/json/v3/device/{device_id}/data"
        
        resp = self.session.get(url)
        result = resp.json()
        
        if result.get("state") != 1:
            return {}
        
        return result.get("desc", {})


# =============================================================================
# БАЗА ДАННЫХ
# =============================================================================

class Database:
    """Работа с MySQL базой данных"""
    
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
            self.logger.error(f"MySQL connection error: {e}")
            return False
    
    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    def get_users_with_starline(self) -> List[Dict]:
        """Получение пользователей с настроенными StarLine credentials"""
        cursor = self.connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, email, name,
                   starline_app_id, starline_app_secret,
                   starline_login, starline_password, starline_user_id
            FROM users
            WHERE starline_app_id IS NOT NULL
              AND starline_app_secret IS NOT NULL
              AND starline_login IS NOT NULL
              AND starline_password IS NOT NULL
        """)
        
        return cursor.fetchall()
    
    def update_user_starline_id(self, user_id: int, starline_user_id: str):
        """Обновление StarLine user ID"""
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE users SET starline_user_id = %s WHERE id = %s",
            (starline_user_id, user_id)
        )
        self.connection.commit()
    
    def get_user_devices(self, user_id: int) -> List[Dict]:
        """Получение устройств пользователя"""
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM user_devices WHERE user_id = %s AND is_active = 1",
            (user_id,)
        )
        return cursor.fetchall()
    
    def save_device(self, device_id: str, name: str, device_type: str = None):
        """Сохранение устройства в глобальный реестр"""
        cursor = self.connection.cursor()
        
        sql = """
            INSERT INTO devices (device_id, name, device_type)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE name = VALUES(name), updated_at = NOW()
        """
        cursor.execute(sql, (device_id, name, device_type))
        self.connection.commit()
    
    def save_user_device(self, user_id: int, device_id: str, device_name: str, device_type: str = None):
        """Сохранение/обновление устройства пользователя"""
        cursor = self.connection.cursor()
        
        sql = """
            INSERT INTO user_devices (user_id, device_id, device_name, device_type, last_sync)
            VALUES (%s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE 
                device_name = VALUES(device_name),
                device_type = VALUES(device_type),
                last_sync = NOW(),
                is_active = 1
        """
        cursor.execute(sql, (user_id, device_id, device_name, device_type))
        self.connection.commit()
    
    def save_state(self, device_id: str, state_data: Dict):
        """Сохранение состояния устройства"""
        if not state_data:
            return
        
        cursor = self.connection.cursor()
        
        temps = state_data.get("temp", {})
        gsm = state_data.get("gsm", {})
        gps = state_data.get("gps", {})
        
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
                state_data.get("arm", 0),
                state_data.get("ign", 0),
                state_data.get("run_time", 0),
                temps.get("inner"),
                temps.get("engine"),
                temps.get("outdoor"),
                state_data.get("balance"),
                gsm.get("level"),
                gps.get("level"),
                state_data.get("battery_voltage"),
                json.dumps(state_data, ensure_ascii=False)
            ))
            self.connection.commit()
        except Error as e:
            self.logger.error(f"Error saving state: {e}")


# =============================================================================
# WORKER
# =============================================================================

class Worker:
    """Главный класс Worker"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db: Optional[Database] = None
        self.logger = logging.getLogger('Worker')
        self.running = False
    
    def initialize(self) -> bool:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        
        self.db = Database(self.config)
        return self.db.connect()
    
    def process_user(self, user: Dict):
        """Обработка одного пользователя"""
        self.logger.info(f"Processing user: {user['email']}")
        
        # Создаем API клиент с credentials пользователя
        api = StarLineAPI(
            app_id=user['starline_app_id'],
            app_secret=user['starline_app_secret'],
            user_login=user['starline_login'],
            user_password=user['starline_password']
        )
        
        # Авторизация
        if not api.authenticate():
            self.logger.error(f"Auth failed for {user['email']}")
            return
        
        # Сохраняем StarLine user ID
        if api.user_id and api.user_id != user.get('starline_user_id'):
            self.db.update_user_starline_id(user['id'], api.user_id)
        
        # Получаем устройства
        devices = api.get_devices()
        
        for device in devices:
            device_id = device.get("device_id") or device.get("id")
            if not device_id:
                continue
            
            device_name = device.get("name") or device.get("alias") or device_id
            device_type = device.get("device_type") or device.get("type")
            
            # Сохраняем устройство
            self.db.save_device(device_id, device_name, device_type)
            self.db.save_user_device(user['id'], device_id, device_name, device_type)
            
            # Получаем и сохраняем состояние
            state = api.get_device_data(device_id)
            if state:
                self.db.save_state(device_id, state)
                self.logger.info(f"Saved state for {device_name}: arm={state.get('arm')}, ign={state.get('ign')}")
    
    def run_once(self):
        """Однократный сбор данных"""
        self.logger.info("=" * 50)
        self.logger.info(f"Worker started (interval: {self.config.poll_interval_seconds}s)")
        
        # Получаем всех пользователей с настроенным StarLine
        users = self.db.get_users_with_starline()
        
        self.logger.info(f"Processing {len(users)} devices from DB")
        
        for user in users:
            try:
                self.process_user(user)
            except Exception as e:
                self.logger.error(f"Error processing {user['email']}: {e}")
        
        self.logger.info("Sleeping...")
    
    def run_daemon(self):
        """Запуск в режиме демона"""
        def handler(sig, frame):
            self.logger.info("Stopping...")
            self.running = False
        
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
        
        if not self.initialize():
            sys.exit(1)
        
        self.running = True
        
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


# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="StarLine Worker v2.0")
    parser.add_argument("-c", "--config", default="config.json")
    parser.add_argument("-d", "--daemon", action="store_true", help="Run as daemon")
    args = parser.parse_args()
    
    # Загрузка конфига (только MySQL!)
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
