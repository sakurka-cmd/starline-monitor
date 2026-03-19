#!/usr/bin/env python3
"""
StarLine Worker - исправленная версия для сбора данных сигнализации
Версия: 2.0.0

ИСПРАВЛЕНИЯ:
1. Cookie имя: slnet (не slnet_token)
2. Парсинг устройств: поддерживает devices[] и desc[]
3. Детальное логирование каждого шага

Запуск:
  python worker_fixed.py --config config.json --daemon
"""

import hashlib
import json
import logging
import os
import sys
import time
import signal
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

import mysql.connector
import requests
from mysql.connector import Error


# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================

@dataclass
class Config:
    """Конфигурация приложения"""
    # StarLine API credentials
    app_id: str = ""
    app_secret: str = ""
    
    # Учётные данные пользователя StarLine
    user_login: str = ""
    user_password: str = ""
    
    # MySQL настройки
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "starline"
    mysql_password: str = ""
    mysql_database: str = "starline_db"
    
    # Интервал опроса
    poll_interval_seconds: int = 60
    
    @classmethod
    def from_env(cls) -> 'Config':
        return cls(
            app_id=os.getenv("STARLINE_APP_ID", ""),
            app_secret=os.getenv("STARLINE_APP_SECRET", ""),
            user_login=os.getenv("STARLINE_USER_LOGIN", ""),
            user_password=os.getenv("STARLINE_USER_PASSWORD", ""),
            mysql_host=os.getenv("MYSQL_HOST", "localhost"),
            mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
            mysql_user=os.getenv("MYSQL_USER", "starline"),
            mysql_password=os.getenv("MYSQL_PASSWORD", ""),
            mysql_database=os.getenv("MYSQL_DATABASE", "starline_db"),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL", "60")),
        )
    
    @classmethod
    def from_file(cls, filepath: str) -> 'Config':
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)


# =============================================================================
# STARLINE API КЛИЕНТ
# =============================================================================

class StarLineAPI:
    """Клиент для работы с StarLine API - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    
    SLID_URL = "https://id.starline.ru"
    WEBAPI_URL = "https://developer.starline.ru"
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "StarLineWorker/2.0",
            "Accept": "application/json",
        })
        
        # Токены
        self.app_token: Optional[str] = None
        self.user_token: Optional[str] = None
        self.slnet_token: Optional[str] = None  # ИСПРАВЛЕНО: slnet, не slnet_token
        self.user_id: Optional[str] = None
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _get_app_code(self) -> str:
        """Шаг 1: Получение кода приложения"""
        url = f"{self.SLID_URL}/apiV3/application/getCode"
        secret_md5 = hashlib.md5(self.config.app_secret.encode()).hexdigest()
        
        params = {
            "appId": self.config.app_id,
            "secret": secret_md5
        }
        
        self.logger.info("[Шаг 1] Получение кода приложения...")
        response = self.session.get(url, params=params)
        data = response.json()
        
        if data.get("state") != 1:
            raise Exception(f"Ошибка получения кода: {data}")
        
        code = data["desc"]["code"]
        self.logger.info(f"[Шаг 1] OK - код: {code[:8]}...")
        return code
    
    def _get_app_token(self, code: str) -> str:
        """Шаг 2: Получение токена приложения"""
        url = f"{self.SLID_URL}/apiV3/application/getToken"
        secret_combined = self.config.app_secret + code
        secret_md5 = hashlib.md5(secret_combined.encode()).hexdigest()
        
        params = {
            "appId": self.config.app_id,
            "secret": secret_md5
        }
        
        self.logger.info("[Шаг 2] Получение токена приложения...")
        response = self.session.get(url, params=params)
        data = response.json()
        
        if data.get("state") != 1:
            raise Exception(f"Ошибка получения токена: {data}")
        
        token = data["desc"]["token"]
        self.logger.info(f"[Шаг 2] OK - токен: {token[:16]}...")
        return token
    
    def _login_user(self) -> tuple:
        """Шаг 3: Аутентификация пользователя"""
        url = f"{self.SLID_URL}/apiV3/user/login"
        password_sha1 = hashlib.sha1(self.config.user_password.encode()).hexdigest()
        
        headers = {"token": self.app_token}
        data = {
            "login": self.config.user_login,
            "pass": password_sha1
        }
        
        self.logger.info("[Шаг 3] Аутентификация пользователя...")
        response = self.session.post(url, headers=headers, data=data)
        result = response.json()
        
        # Двухфакторная аутентификация
        if result.get("state") == 2:
            raise Exception(
                f"Требуется 2FA! Код отправлен на: {result['desc'].get('phone')}"
            )
        
        if result.get("state") != 1:
            raise Exception(f"Ошибка аутентификации: {result}")
        
        user_token = result["desc"]["user_token"]
        user_id = result["desc"]["id"]
        
        self.logger.info(f"[Шаг 3] OK - user_id={user_id}")
        return user_token, user_id
    
    def _auth_webapi(self) -> str:
        """Шаг 4: Авторизация в WebAPI - ИСПРАВЛЕНО"""
        url = f"{self.WEBAPI_URL}/json/v2/auth.slid"
        
        data = {"slid_token": self.user_token}
        
        self.logger.info("[Шаг 4] Авторизация в WebAPI...")
        response = self.session.post(url, json=data)
        
        # ИСПРАВЛЕНО: Ищем cookie с именем 'slnet' (не slnet_token)
        slnet_token = None
        
        # Способ 1: Из cookies response
        for cookie in response.cookies:
            self.logger.debug(f"Cookie: {cookie.name} = {cookie.value[:20] if len(cookie.value) > 20 else cookie.value}...")
            if cookie.name == "slnet":
                slnet_token = cookie.value
                break
        
        # Способ 2: Из заголовка Set-Cookie
        if not slnet_token:
            set_cookie = response.headers.get('set-cookie', '')
            self.logger.debug(f"Set-Cookie header: {set_cookie[:100]}...")
            
            # Ищем slnet=...
            import re
            match = re.search(r'slnet=([^;]+)', set_cookie)
            if match:
                slnet_token = match.group(1)
        
        # Способ 3: Из тела ответа
        if not slnet_token:
            try:
                result = response.json()
                self.logger.debug(f"Response body: {json.dumps(result)[:200]}...")
                if result.get("state") != 1:
                    raise Exception(f"WebAPI ошибка: {result}")
            except:
                pass
        
        if not slnet_token:
            raise Exception("Не удалось получить slnet token из ответа!")
        
        self.logger.info(f"[Шаг 4] OK - slnet: {slnet_token[:16]}...")
        
        # Устанавливаем cookie для сессии
        self.session.cookies.set("slnet", slnet_token, domain="developer.starline.ru")
        
        return slnet_token
    
    def authenticate(self) -> bool:
        """Полный цикл авторизации"""
        try:
            code = self._get_app_code()
            self.app_token = self._get_app_token(code)
            self.user_token, self.user_id = self._login_user()
            self.slnet_token = self._auth_webapi()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка авторизации: {e}")
            return False
    
    def get_devices(self) -> List[Dict]:
        """Получение списка устройств - ИСПРАВЛЕНО"""
        if not self.user_id:
            raise Exception("Не авторизован")
        
        url = f"{self.WEBAPI_URL}/json/v1/user/{self.user_id}/devices"
        
        self.logger.info("[Шаг 5] Получение списка устройств...")
        
        # Важно: отправляем cookie slnet
        response = self.session.get(url)
        
        self.logger.debug(f"Response status: {response.status_code}")
        self.logger.debug(f"Response cookies: {dict(response.cookies)}")
        
        result = response.json()
        self.logger.debug(f"Response: {json.dumps(result)[:500]}...")
        
        # ИСПРАВЛЕНО: Парсим разные форматы ответа
        devices = []
        
        # Формат 1: {"devices": [...]}
        if "devices" in result:
            devices = result["devices"]
            self.logger.info(f"[Шаг 5] Найдено устройств (format 1): {len(devices)}")
        
        # Формат 2: {"desc": [...]}
        elif "desc" in result:
            if isinstance(result["desc"], list):
                devices = result["desc"]
            elif isinstance(result["desc"], dict) and "devices" in result["desc"]:
                devices = result["desc"]["devices"]
            self.logger.info(f"[Шаг 5] Найдено устройств (format 2): {len(devices)}")
        
        # Формат 3: {"state": 1, ...} - ошибка
        elif result.get("state") != 1:
            self.logger.error(f"Ошибка API: {result}")
        
        # Логируем каждое устройство
        for i, dev in enumerate(devices):
            dev_id = dev.get("device_id") or dev.get("id")
            dev_name = dev.get("name") or dev.get("alias") or "Без имени"
            self.logger.info(f"  Устройство {i+1}: {dev_name} (ID: {dev_id})")
        
        return devices
    
    def get_device_data(self, device_id: str) -> Dict:
        """Получение данных устройства"""
        url = f"{self.WEBAPI_URL}/json/v3/device/{device_id}/data"
        
        response = self.session.get(url)
        result = response.json()
        
        if result.get("state") != 1:
            return {}
        
        return result.get("desc", {})


# =============================================================================
# БАЗА ДАННЫХ
# =============================================================================

class Database:
    """Работа с базой данных"""
    
    def __init__(self, config: Config):
        self.config = config
        self.connection = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
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
            self.logger.info("Подключено к MySQL")
            return True
        except Error as e:
            self.logger.error(f"Ошибка MySQL: {e}")
            return False
    
    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    def get_user_devices(self) -> List[Dict]:
        """Получение устройств пользователей из БД"""
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT ud.id, ud.device_id, ud.starline_login, ud.starline_password,
                   u.id as user_id
            FROM user_devices ud
            JOIN users u ON ud.user_id = u.id
            WHERE ud.is_active = 1
        """)
        return cursor.fetchall()
    
    def save_state(self, device_id: str, data: Dict):
        """Сохранение состояния устройства"""
        cursor = self.connection.cursor()
        
        # Проверяем существование записи
        cursor.execute("""
            SELECT id FROM device_states 
            WHERE device_id = %s 
            ORDER BY timestamp DESC LIMIT 1
        """, (device_id,))
        
        existing = cursor.fetchone()
        
        if existing:
            # Обновляем
            sql = """
                UPDATE device_states SET
                    timestamp = NOW(),
                    arm_state = %s, ign_state = %s,
                    temp_inner = %s, temp_engine = %s, temp_outdoor = %s,
                    balance = %s, gsm_level = %s, gps_level = %s,
                    battery_voltage = %s, raw_data = %s
                WHERE id = %s
            """
            cursor.execute(sql, (
                data.get("arm", 0),
                data.get("ign", 0),
                data.get("temp", {}).get("inner"),
                data.get("temp", {}).get("engine"),
                data.get("temp", {}).get("outdoor"),
                data.get("balance"),
                data.get("gsm", {}).get("level"),
                data.get("gps", {}).get("level"),
                data.get("battery_voltage"),
                json.dumps(data, ensure_ascii=False),
                existing[0]
            ))
        else:
            # Вставляем новую
            sql = """
                INSERT INTO device_states 
                (device_id, timestamp, arm_state, ign_state, temp_inner, 
                 temp_engine, temp_outdoor, balance, gsm_level, gps_level,
                 battery_voltage, raw_data)
                VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                device_id,
                data.get("arm", 0),
                data.get("ign", 0),
                data.get("temp", {}).get("inner"),
                data.get("temp", {}).get("engine"),
                data.get("temp", {}).get("outdoor"),
                data.get("balance"),
                data.get("gsm", {}).get("level"),
                data.get("gps", {}).get("level"),
                data.get("battery_voltage"),
                json.dumps(data, ensure_ascii=False)
            ))
        
        self.connection.commit()
        self.logger.info(f"Сохранено состояние для {device_id}")


# =============================================================================
# WORKER
# =============================================================================

class Worker:
    """Главный класс Worker"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db = Database(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.running = False
    
    def initialize(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        
        return self.db.connect()
    
    def process_user_devices(self, user_login: str, user_password: str, 
                             app_id: str, app_secret: str):
        """Обработка устройств одного пользователя"""
        
        # Создаем конфиг для этого пользователя
        user_config = Config(
            app_id=app_id,
            app_secret=app_secret,
            user_login=user_login,
            user_password=user_password,
            mysql_host=self.config.mysql_host,
            mysql_port=self.config.mysql_port,
            mysql_user=self.config.mysql_user,
            mysql_password=self.config.mysql_password,
            mysql_database=self.config.mysql_database,
        )
        
        api = StarLineAPI(user_config)
        
        if not api.authenticate():
            self.logger.error(f"Не удалось авторизовать {user_login}")
            return
        
        devices = api.get_devices()
        
        if not devices:
            self.logger.warning(f"Нет устройств для {user_login}")
            return
        
        for device in devices:
            device_id = device.get("device_id") or device.get("id")
            if not device_id:
                continue
            
            self.logger.info(f"Получение данных для {device_id}...")
            
            data = api.get_device_data(device_id)
            if data:
                self.db.save_state(device_id, data)
    
    def run_once(self):
        """Однократный запуск"""
        self.logger.info("=== Запуск сбора данных ===")
        
        # Используем конфиг напрямую
        if self.config.app_id and self.config.user_login:
            self.process_user_devices(
                self.config.user_login,
                self.config.user_password,
                self.config.app_id,
                self.config.app_secret
            )
        else:
            self.logger.warning("Не настроены учетные данные StarLine")
    
    def run_daemon(self):
        """Запуск в режиме демона"""
        def signal_handler(sig, frame):
            self.logger.info("Остановка...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        self.running = True
        self.logger.info(f"Worker запущен (интервал: {self.config.poll_interval_seconds}s)")
        
        while self.running:
            try:
                self.run_once()
            except Exception as e:
                self.logger.error(f"Ошибка: {e}")
            
            for _ in range(self.config.poll_interval_seconds):
                if not self.running:
                    break
                time.sleep(1)
        
        self.db.close()
        self.logger.info("Worker остановлен")


# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="StarLine Worker")
    parser.add_argument("-c", "--config", help="Путь к config.json")
    parser.add_argument("-d", "--daemon", action="store_true", help="Режим демона")
    args = parser.parse_args()
    
    # Загрузка конфига
    if args.config and os.path.exists(args.config):
        config = Config.from_file(args.config)
    else:
        config = Config.from_env()
    
    # Проверка
    if not all([config.app_id, config.app_secret, config.user_login, config.user_password]):
        print("Ошибка: укажите учетные данные StarLine в config.json или переменных окружения")
        print("""
Пример config.json:
{
    "app_id": "ваш_app_id",
    "app_secret": "ваш_app_secret",
    "user_login": "ваш_логин",
    "user_password": "ваш_пароль",
    "mysql_host": "localhost",
    "mysql_user": "starline",
    "mysql_password": "starline123",
    "mysql_database": "starline_db",
    "poll_interval_seconds": 60
}
""")
        sys.exit(1)
    
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
