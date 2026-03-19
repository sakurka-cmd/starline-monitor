"""
StarLine Data Collector Worker
Периодический сбор данных со всех устройств пользователей
Запуск: python worker.py
"""

import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Optional, Dict, List

import mysql.connector
from mysql.connector import Error
import requests

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

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))  # 5 минут

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("StarLineWorker")


# =============================================================================
# STARLINE API КЛИЕНТ
# =============================================================================

class StarLineClient:
    """Клиент для работы с StarLine API"""
    
    SLID_URL = "https://id.starline.ru"
    WEBAPI_URL = "https://developer.starline.ru"
    
    def __init__(self, app_id: str, app_secret: str, login: str, password: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.login = login
        self.password = password
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "StarLineMonitor/1.0",
            "Accept": "application/json"
        })
        
        self.app_token = None
        self.user_token = None
        self.slnet_token = None
        self.user_id = None
    
    def authenticate(self) -> bool:
        """Полная авторизация в StarLine API"""
        try:
            # Шаг 1: Получение кода приложения
            code = self._get_app_code()
            
            # Шаг 2: Получение токена приложения
            self.app_token = self._get_app_token(code)
            
            # Шаг 3: Авторизация пользователя
            self.user_token, self.user_id = self._login_user()
            
            # Шаг 4: Авторизация в WebAPI
            self.slnet_token = self._auth_webapi()
            
            self.session.cookies.set(
                "slnet_token", 
                self.slnet_token, 
                domain="developer.starline.ru"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            return False
    
    def _get_app_code(self) -> str:
        """Получение кода приложения"""
        url = f"{self.SLID_URL}/apiV3/application/getCode"
        secret_md5 = hashlib.md5(self.app_secret.encode()).hexdigest()
        
        response = self.session.get(url, params={
            "appId": self.app_id,
            "secret": secret_md5
        })
        data = response.json()
        
        if data.get("state") != 1:
            raise Exception(f"getCode error: {data}")
        
        return data["desc"]["code"]
    
    def _get_app_token(self, code: str) -> str:
        """Получение токена приложения"""
        url = f"{self.SLID_URL}/apiV3/application/getToken"
        secret_combined = self.app_secret + code
        secret_md5 = hashlib.md5(secret_combined.encode()).hexdigest()
        
        response = self.session.get(url, params={
            "appId": self.app_id,
            "secret": secret_md5
        })
        data = response.json()
        
        if data.get("state") != 1:
            raise Exception(f"getToken error: {data}")
        
        return data["desc"]["token"]
    
    def _login_user(self) -> tuple:
        """Авторизация пользователя"""
        url = f"{self.SLID_URL}/apiV3/user/login"
        password_sha1 = hashlib.sha1(self.password.encode()).hexdigest()
        
        response = self.session.post(url, headers={"token": self.app_token}, data={
            "login": self.login,
            "pass": password_sha1
        })
        data = response.json()
        
        if data.get("state") == 2:
            raise Exception("Требуется двухфакторная аутентификация")
        
        if data.get("state") != 1:
            raise Exception(f"login error: {data}")
        
        return data["desc"]["user_token"], data["desc"]["id"]
    
    def _auth_webapi(self) -> str:
        """Авторизация в WebAPI"""
        url = f"{self.WEBAPI_URL}/json/v2/auth.slid"
        
        response = self.session.post(url, json={"slid_token": self.user_token})
        
        for cookie in response.cookies:
            if cookie.name == "slnet_token":
                return cookie.value
        
        raise Exception("Не получен slnet_token")
    
    def get_devices(self) -> List[Dict]:
        """Получение списка устройств"""
        url = f"{self.WEBAPI_URL}/json/v1/user/{self.user_id}/devices"
        response = self.session.get(url)
        data = response.json()
        
        if data.get("state") != 1:
            raise Exception(f"get_devices error: {data}")
        
        return data.get("desc", [])
    
    def get_device_data(self, device_id: str) -> Dict:
        """Получение данных устройства"""
        url = f"{self.WEBAPI_URL}/json/v3/device/{device_id}/data"
        response = self.session.get(url)
        data = response.json()
        
        if data.get("state") != 1:
            return {}
        
        return data.get("desc", {})


# =============================================================================
# БАЗА ДАННЫХ
# =============================================================================

def get_db_connection():
    """Получение соединения с БД"""
    return mysql.connector.connect(**DATABASE_CONFIG)


def get_all_active_devices():
    """Получение всех активных устройств из БД"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, user_id, name, app_id, app_secret, 
               starline_login, starline_password, starline_device_id
        FROM user_devices 
        WHERE is_active = 1
    """)
    
    devices = cursor.fetchall()
    conn.close()
    
    return devices


def update_device_info(device_id: int, starline_device_id: str, device_name: str):
    """Обновление информации об устройстве"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE user_devices 
        SET starline_device_id = %s, device_name = %s, last_update = NOW(), last_error = NULL
        WHERE id = %s
    """, (starline_device_id, device_name, device_id))
    
    conn.commit()
    conn.close()


def set_device_error(device_id: int, error: str):
    """Установка ошибки устройства"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE user_devices 
        SET last_update = NOW(), last_error = %s
        WHERE id = %s
    """, (error, device_id))
    
    conn.commit()
    conn.close()


def save_device_state(device_id: int, state: Dict, timestamp: datetime):
    """Сохранение состояния устройства"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Извлечение данных
    temps = state.get("temp", {})
    gps_data = state.get("gps", {})
    location = state.get("location", {})
    
    cursor.execute("""
        INSERT INTO device_states (
            device_id, timestamp, 
            arm_state, ign_state,
            temp_inner, temp_engine,
            balance, gsm_level, gps_level,
            latitude, longitude, speed,
            raw_data
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        device_id, timestamp,
        state.get("arm"),
        state.get("ign"),
        temps.get("inner"),
        temps.get("engine"),
        state.get("balance"),
        gps_data.get("level"),
        state.get("gps", {}).get("level"),
        location.get("lat"),
        location.get("lon"),
        state.get("speed"),
        json.dumps(state, ensure_ascii=False)
    ))
    
    conn.commit()
    conn.close()


# =============================================================================
# ГЛАВНЫЙ ЦИКЛ
# =============================================================================

def collect_all_devices():
    """Сбор данных со всех устройств"""
    devices = get_all_active_devices()
    
    if not devices:
        logger.info("Нет активных устройств для сбора данных")
        return
    
    logger.info(f"Начинаем сбор данных для {len(devices)} устройств")
    
    # Группируем по учётным данным (один клиент может собирать несколько устройств)
    credentials_map = {}
    for device in devices:
        key = (device['app_id'], device['app_secret'], device['starline_login'], device['starline_password'])
        if key not in credentials_map:
            credentials_map[key] = []
        credentials_map[key].append(device)
    
    for creds, devices_list in credentials_map.items():
        app_id, app_secret, login, password = creds
        
        try:
            client = StarLineClient(app_id, app_secret, login, password)
            
            if not client.authenticate():
                for device in devices_list:
                    set_device_error(device['id'], "Ошибка авторизации")
                continue
            
            # Получаем все устройства пользователя
            starline_devices = client.get_devices()
            timestamp = datetime.now()
            
            for device in devices_list:
                # Ищем соответствующее устройство StarLine
                target_device = None
                
                if device['starline_device_id']:
                    for sd in starline_devices:
                        if sd.get('device_id') == device['starline_device_id']:
                            target_device = sd
                            break
                else:
                    # Если device_id не указан, берём первое
                    if starline_devices:
                        target_device = starline_devices[0]
                
                if not target_device:
                    set_device_error(device['id'], "Устройство не найдено в StarLine")
                    continue
                
                # Обновляем ID устройства если не был задан
                if not device['starline_device_id']:
                    update_device_info(
                        device['id'], 
                        target_device['device_id'],
                        target_device.get('name')
                    )
                
                # Получаем и сохраняем данные
                state = client.get_device_data(target_device['device_id'])
                
                if state:
                    save_device_state(device['id'], state, timestamp)
                    update_device_info(
                        device['id'],
                        target_device['device_id'],
                        target_device.get('name')
                    )
                    logger.info(f"Сохранены данные для: {device['name']}")
                else:
                    set_device_error(device['id'], "Нет данных от устройства")
                    
        except Exception as e:
            logger.error(f"Ошибка обработки группы устройств: {e}")
            for device in devices_list:
                set_device_error(device['id'], str(e))
    
    logger.info("Сбор данных завершён")


def main():
    """Главный цикл воркера"""
    logger.info(f"StarLine Worker запущен (интервал: {POLL_INTERVAL} сек)")
    
    while True:
        try:
            collect_all_devices()
        except Exception as e:
            logger.error(f"Ошибка в цикле сбора: {e}")
        
        logger.info(f"Ожидание {POLL_INTERVAL} секунд...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
