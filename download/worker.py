#!/usr/bin/env python3
"""
StarLine Worker - Сбор данных сигнализации StarLine
Версия: 2.0.0 (Исправленная)

ИСПРАВЛЕНИЯ:
1. Cookie имя: slnet (не slnet_token)
2. Парсинг устройств: поддерживает devices[] и desc[]
3. Детальное логирование каждого шага

Запуск:
  python worker.py --config config.json          # Однократный запуск
  python worker.py --config config.json --daemon # Режим демона
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
    # StarLine API credentials (получить на https://my.starline.ru)
    app_id: str = ""           # Идентификатор приложения
    app_secret: str = ""       # Пароль приложения
    
    # Учётные данные пользователя StarLine
    user_login: str = ""       # Логин (email или телефон)
    user_password: str = ""    # Пароль
    
    # MySQL настройки
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "starline"
    mysql_password: str = ""
    mysql_database: str = "starline_db"
    
    # Интервал опроса в секундах
    poll_interval_seconds: int = 60
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Загрузка конфигурации из переменных окружения"""
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
        """Загрузка конфигурации из JSON файла"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)


# =============================================================================
# STARLINE API КЛИЕНТ
# =============================================================================

class StarLineAPI:
    """
    Клиент для работы с StarLine API
    
    Процесс авторизации:
    1. getCode - получить код приложения
    2. getToken - получить токен приложения
    3. user/login - авторизация пользователя
    4. auth.slid - получить slnet cookie для WebAPI
    5. user/{uid}/devices - получить список устройств
    """
    
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
        self.slnet_token: Optional[str] = None
        self.user_id: Optional[str] = None
        
        # Кэш устройств
        self.devices: List[Dict] = []
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _get_app_code(self) -> str:
        """Шаг 1: Получение кода приложения"""
        url = f"{self.SLID_URL}/apiV3/application/getCode"
        
        # MD5 от app_secret
        secret_md5 = hashlib.md5(self.config.app_secret.encode()).hexdigest()
        
        params = {
            "appId": self.config.app_id,
            "secret": secret_md5
        }
        
        self.logger.info("=" * 50)
        self.logger.info("[ШАГ 1] Получение кода приложения...")
        self.logger.info(f"URL: {url}")
        
        response = self.session.get(url, params=params)
        data = response.json()
        
        self.logger.info(f"Ответ: state={data.get('state')}")
        
        if data.get("state") != 1:
            error_msg = data.get("desc", {}).get("message", "Неизвестная ошибка")
            raise Exception(f"Ошибка получения кода: {error_msg}\nПолный ответ: {json.dumps(data, ensure_ascii=False)}")
        
        code = data["desc"]["code"]
        self.logger.info(f"[ШАГ 1] ✓ УСПЕХ - код: {code[:8]}...{code[-4:]}")
        
        return code
    
    def _get_app_token(self, code: str) -> str:
        """Шаг 2: Получение токена приложения"""
        url = f"{self.SLID_URL}/apiV3/application/getToken"
        
        # MD5 от (app_secret + code)
        secret_combined = self.config.app_secret + code
        secret_md5 = hashlib.md5(secret_combined.encode()).hexdigest()
        
        params = {
            "appId": self.config.app_id,
            "secret": secret_md5
        }
        
        self.logger.info("=" * 50)
        self.logger.info("[ШАГ 2] Получение токена приложения...")
        
        response = self.session.get(url, params=params)
        data = response.json()
        
        self.logger.info(f"Ответ: state={data.get('state')}")
        
        if data.get("state") != 1:
            raise Exception(f"Ошибка получения токена: {data}")
        
        token = data["desc"]["token"]
        self.app_token = token
        self.logger.info(f"[ШАГ 2] ✓ УСПЕХ - токен: {token[:16]}...{token[-4:]}")
        
        return token
    
    def _login_user(self) -> tuple:
        """Шаг 3: Аутентификация пользователя"""
        url = f"{self.SLID_URL}/apiV3/user/login"
        
        # SHA1 от пароля
        password_sha1 = hashlib.sha1(self.config.user_password.encode()).hexdigest()
        
        headers = {
            "token": self.app_token
        }
        
        data = {
            "login": self.config.user_login,
            "pass": password_sha1
        }
        
        self.logger.info("=" * 50)
        self.logger.info(f"[ШАГ 3] Аутентификация пользователя: {self.config.user_login}")
        
        response = self.session.post(url, headers=headers, data=data)
        result = response.json()
        
        self.logger.info(f"Ответ: state={result.get('state')}")
        
        # Проверка на двухфакторную аутентификацию
        if result.get("state") == 2:
            phone = result.get('desc', {}).get('phone', 'неизвестно')
            raise Exception(
                f"⚠ ТРЕБУЕТСЯ ДВУХФАКТОРНАЯ АУТЕНТИФИКАЦИЯ!\n"
                f"Код отправлен на: {phone}\n"
                f"Отключите 2FA в настройках StarLine или используйте другой аккаунт."
            )
        
        if result.get("state") != 1:
            error_msg = result.get("desc", {}).get("message", "Неизвестная ошибка")
            raise Exception(f"Ошибка аутентификации: {error_msg}\nПолный ответ: {json.dumps(result, ensure_ascii=False)}")
        
        user_token = result["desc"]["user_token"]
        user_id = result["desc"]["id"]
        
        self.user_token = user_token
        self.user_id = user_id
        
        self.logger.info(f"[ШАГ 3] ✓ УСПЕХ - user_id: {user_id}")
        self.logger.info(f"        user_token: {user_token[:16]}...{user_token[-4:]}")
        
        return user_token, user_id
    
    def _auth_webapi(self) -> str:
        """
        Шаг 4: Авторизация в WebAPI
        
        ВАЖНО: Cookie называется 'slnet', а не 'slnet_token'!
        """
        url = f"{self.WEBAPI_URL}/json/v2/auth.slid"
        
        data = {
            "slid_token": self.user_token
        }
        
        self.logger.info("=" * 50)
        self.logger.info("[ШАГ 4] Авторизация в WebAPI...")
        self.logger.info(f"URL: {url}")
        
        response = self.session.post(url, json=data)
        
        self.logger.info(f"HTTP статус: {response.status_code}")
        
        # ============================================
        # ИСПРАВЛЕНИЕ: Ищем cookie 'slnet' (не slnet_token)
        # ============================================
        
        slnet_token = None
        
        # Способ 1: Из cookies объекта response
        self.logger.info("Поиск cookie в ответе...")
        for cookie in response.cookies:
            self.logger.info(f"  Найдена cookie: {cookie.name} = {cookie.value[:20] if len(cookie.value) > 20 else cookie.value}...")
            if cookie.name == "slnet":  # <-- ИСПРАВЛЕНО! Было "slnet_token"
                slnet_token = cookie.value
                self.logger.info(f"  ✓ Найдена slnet cookie!")
                break
        
        # Способ 2: Из заголовка Set-Cookie
        if not slnet_token:
            set_cookie_header = response.headers.get('set-cookie', '')
            if set_cookie_header:
                self.logger.info(f"Заголовок Set-Cookie: {set_cookie_header[:200]}...")
                
                # Ищем slnet=...
                match = re.search(r'slnet=([^;]+)', set_cookie_header)
                if match:
                    slnet_token = match.group(1)
                    self.logger.info("  ✓ Найдена slnet в Set-Cookie заголовке!")
        
        # Способ 3: Проверяем тело ответа
        try:
            result = response.json()
            self.logger.info(f"Тело ответа: {json.dumps(result, ensure_ascii=False)[:200]}...")
            
            if result.get("state") != 1 and not slnet_token:
                self.logger.warning(f"WebAPI вернул state={result.get('state')}")
        except:
            pass
        
        if not slnet_token:
            # Показываем все найденные cookies для отладки
            all_cookies = [f"{c.name}={c.value[:20]}..." for c in response.cookies]
            raise Exception(
                f"❌ НЕ УДАЛОСЬ ПОЛУЧИТЬ slnet TOKEN!\n"
                f"Найденные cookies: {all_cookies}\n"
                f"Заголовок Set-Cookie: {response.headers.get('set-cookie', 'отсутствует')}\n"
                f"Проверьте правильность app_id и app_secret"
            )
        
        self.slnet_token = slnet_token
        self.logger.info(f"[ШАГ 4] ✓ УСПЕХ - slnet: {slnet_token[:16]}...{slnet_token[-4:]}")
        
        # Устанавливаем cookie для сессии
        self.session.cookies.set("slnet", slnet_token, domain="developer.starline.ru")
        
        return slnet_token
    
    def authenticate(self) -> bool:
        """Полный цикл авторизации"""
        try:
            # Шаг 1: Код приложения
            code = self._get_app_code()
            
            # Шаг 2: Токен приложения
            self._get_app_token(code)
            
            # Шаг 3: Авторизация пользователя
            self._login_user()
            
            # Шаг 4: WebAPI авторизация
            self._auth_webapi()
            
            self.logger.info("=" * 50)
            self.logger.info("✓ АВТОРИЗАЦИЯ ПРОШЛА УСПЕШНО!")
            self.logger.info("=" * 50)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка авторизации: {e}")
            return False
    
    def get_devices(self) -> List[Dict]:
        """
        Шаг 5: Получение списка устройств
        
        ИСПРАВЛЕНИЕ: Поддерживаем разные форматы ответа API
        """
        if not self.user_id:
            raise Exception("Необходимо сначала авторизоваться")
        
        url = f"{self.WEBAPI_URL}/json/v1/user/{self.user_id}/devices"
        
        self.logger.info("=" * 50)
        self.logger.info("[ШАГ 5] Получение списка устройств...")
        self.logger.info(f"URL: {url}")
        self.logger.info(f"Cookies: slnet={self.slnet_token[:16]}...")
        
        # Делаем запрос с cookie slnet
        response = self.session.get(url)
        
        self.logger.info(f"HTTP статус: {response.status_code}")
        
        result = response.json()
        
        # Логируем полный ответ для отладки (первая часть)
        result_str = json.dumps(result, ensure_ascii=False)
        self.logger.info(f"Ответ API (первые 500 символов): {result_str[:500]}...")
        
        # ============================================
        # ИСПРАВЛЕНИЕ: Парсим разные форматы ответа
        # ============================================
        
        devices = []
        
        # Формат 1: {"devices": [...], "code": 200}
        if "devices" in result:
            if isinstance(result["devices"], list):
                devices = result["devices"]
                self.logger.info(f"Найден формат: devices[] = {len(devices)} устройств")
        
        # Формат 2: {"desc": [...]}
        if not devices and "desc" in result:
            if isinstance(result["desc"], list):
                devices = result["desc"]
                self.logger.info(f"Найден формат: desc[] = {len(devices)} устройств")
            elif isinstance(result["desc"], dict):
                # Формат 2b: {"desc": {"devices": [...]}}
                if "devices" in result["desc"]:
                    devices = result["desc"]["devices"]
                    self.logger.info(f"Найден формат: desc.devices[] = {len(devices)} устройств")
        
        # Проверяем на ошибку
        if not devices and result.get("state") == 0:
            error_code = result.get("code", "неизвестно")
            raise Exception(f"API вернул ошибку! code={error_code}, ответ: {result_str[:500]}")
        
        # Сохраняем в кэш
        self.devices = devices
        
        # Логируем найденные устройства
        self.logger.info("-" * 40)
        if devices:
            self.logger.info(f"✓ НАЙДЕНО УСТРОЙСТВ: {len(devices)}")
            for i, dev in enumerate(devices, 1):
                dev_id = dev.get("device_id") or dev.get("id", "без ID")
                dev_name = dev.get("name") or dev.get("alias", "Без названия")
                dev_type = dev.get("device_type") or dev.get("type", "неизвестно")
                self.logger.info(f"  {i}. {dev_name}")
                self.logger.info(f"     ID: {dev_id}")
                self.logger.info(f"     Тип: {dev_type}")
        else:
            self.logger.warning("⚠ НЕ НАЙДЕНО НИ ОДНОГО УСТРОЙСТВА!")
            self.logger.warning("Возможные причины:")
            self.logger.warning("  1. У вас действительно нет устройств в StarLine")
            self.logger.warning("  2. Устройства привязаны к другому аккаунту")
            self.logger.warning("  3. Не прошел полный ответ API (проверьте выше)")
        
        self.logger.info("=" * 50)
        
        return devices
    
    def get_device_data(self, device_id: str) -> Dict:
        """Получение полной информации о состоянии устройства"""
        url = f"{self.WEBAPI_URL}/json/v3/device/{device_id}/data"
        
        self.logger.info(f"Получение данных устройства {device_id}...")
        
        response = self.session.get(url)
        result = response.json()
        
        if result.get("state") != 1:
            self.logger.warning(f"Ошибка получения данных: {result.get('code', 'неизвестно')}")
            return {}
        
        data = result.get("desc", {})
        self.logger.info(f"Получены данные: arm={data.get('arm')}, ign={data.get('ign')}")
        
        return data
    
    def get_device_position(self, device_id: str) -> Dict:
        """Получение данных о местоположении"""
        url = f"{self.WEBAPI_URL}/json/v1/device/{device_id}/position"
        
        response = self.session.get(url)
        result = response.json()
        
        if result.get("state") != 1:
            return {}
        
        return result.get("desc", {})


# =============================================================================
# БАЗА ДАННЫХ MYSQL
# =============================================================================

class MySQLStorage:
    """Класс для работы с MySQL базой данных"""
    
    def __init__(self, config: Config):
        self.config = config
        self.connection = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def connect(self) -> bool:
        """Подключение к базе данных"""
        try:
            self.connection = mysql.connector.connect(
                host=self.config.mysql_host,
                port=self.config.mysql_port,
                user=self.config.mysql_user,
                password=self.config.mysql_password,
                database=self.config.mysql_database,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            self.logger.info(f"✓ Подключено к MySQL: {self.config.mysql_database}")
            return True
        except Error as e:
            self.logger.error(f"❌ Ошибка подключения к MySQL: {e}")
            return False
    
    def close(self):
        """Закрытие соединения"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.logger.info("Соединение с MySQL закрыто")
    
    def save_device(self, device_info: Dict):
        """Сохранение информации об устройстве"""
        cursor = self.connection.cursor()
        
        device_id = device_info.get("device_id") or device_info.get("id")
        name = device_info.get("name") or device_info.get("alias")
        alias = device_info.get("alias")
        device_type = device_info.get("device_type") or device_info.get("type")
        
        sql = """
            INSERT INTO devices (device_id, name, alias, device_type)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                alias = VALUES(alias),
                device_type = VALUES(device_type),
                updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            cursor.execute(sql, (device_id, name, alias, device_type))
            self.connection.commit()
            self.logger.info(f"Сохранено устройство: {name} ({device_id})")
        except Error as e:
            self.logger.error(f"Ошибка сохранения устройства: {e}")
    
    def save_state(self, device_id: str, state_data: Dict):
        """Сохранение состояния устройства"""
        if not state_data:
            return
        
        cursor = self.connection.cursor()
        
        # Парсинг данных
        arm_state = state_data.get("arm", 0)
        ign_state = state_data.get("ign", 0)
        run_time = state_data.get("run_time", 0)
        
        temps = state_data.get("temp", {})
        temp_inner = temps.get("inner")
        temp_engine = temps.get("engine")
        temp_outdoor = temps.get("outdoor")
        
        balance = state_data.get("balance")
        
        gsm = state_data.get("gsm", {})
        gsm_level = gsm.get("level")
        
        gps = state_data.get("gps", {})
        gps_level = gps.get("level")
        
        battery = state_data.get("battery_voltage")
        
        sql = """
            INSERT INTO device_states (
                device_id, timestamp,
                arm_state, ign_state, run_time,
                temp_inner, temp_engine, temp_outdoor,
                balance, gsm_level, gps_level,
                battery_voltage, raw_data
            ) VALUES (
                %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        try:
            cursor.execute(sql, (
                device_id,
                arm_state, ign_state, run_time,
                temp_inner, temp_engine, temp_outdoor,
                balance, gsm_level, gps_level,
                battery, json.dumps(state_data, ensure_ascii=False)
            ))
            self.connection.commit()
            self.logger.info(f"Сохранено состояние: {device_id} (arm={arm_state}, ign={ign_state})")
        except Error as e:
            self.logger.error(f"Ошибка сохранения состояния: {e}")
    
    def update_user_device(self, device_id: str, device_name: str):
        """Обновление записи в user_devices"""
        cursor = self.connection.cursor()
        
        sql = """
            UPDATE user_devices 
            SET device_name = %s, last_sync = NOW()
            WHERE device_id = %s
        """
        
        try:
            cursor.execute(sql, (device_name, device_id))
            self.connection.commit()
        except Error as e:
            self.logger.error(f"Ошибка обновления user_devices: {e}")


# =============================================================================
# ГЛАВНЫЙ КЛАСС WORKER
# =============================================================================

class Worker:
    """Главный класс Worker для сбора данных"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api = None
        self.storage = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.running = False
    
    def initialize(self) -> bool:
        """Инициализация Worker"""
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
            ]
        )
        
        self.logger.info("=" * 60)
        self.logger.info("StarLine Worker v2.0 - Запуск")
        self.logger.info("=" * 60)
        
        # Подключение к БД
        self.storage = MySQLStorage(self.config)
        if not self.storage.connect():
            return False
        
        # Инициализация API
        self.api = StarLineAPI(self.config)
        
        return True
    
    def collect_data(self):
        """Сбор данных со всех устройств"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info(f"Начало сбора данных: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 60)
        
        # Авторизация
        if not self.api.authenticate():
            self.logger.error("❌ Авторизация не удалась!")
            return
        
        # Получение устройств
        devices = self.api.get_devices()
        
        if not devices:
            self.logger.warning("Нет устройств для обработки")
            return
        
        # Обработка каждого устройства
        self.logger.info(f"\nОбработка {len(devices)} устройств...")
        
        for i, device in enumerate(devices, 1):
            device_id = device.get("device_id") or device.get("id")
            device_name = device.get("name") or device.get("alias") or device_id
            
            self.logger.info(f"\n--- Устройство {i}/{len(devices)}: {device_name} ---")
            
            if not device_id:
                self.logger.warning("Пропуск: нет device_id")
                continue
            
            # Сохраняем информацию об устройстве
            self.storage.save_device(device)
            
            # Получаем состояние
            state_data = self.api.get_device_data(device_id)
            if state_data:
                self.storage.save_state(device_id, state_data)
            
            # Обновляем user_devices
            self.storage.update_user_device(device_id, device_name)
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info(f"✓ Сбор завершен: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 60)
    
    def run_once(self):
        """Однократный запуск"""
        if self.initialize():
            try:
                self.collect_data()
            finally:
                self.storage.close()
    
    def run_daemon(self):
        """Запуск в режиме демона"""
        import signal
        
        def signal_handler(sig, frame):
            self.logger.info("\nПолучен сигнал остановки...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if not self.initialize():
            sys.exit(1)
        
        self.running = True
        self.logger.info(f"\nWorker запущен в режиме демона")
        self.logger.info(f"Интервал опроса: {self.config.poll_interval_seconds} секунд")
        self.logger.info("Нажмите Ctrl+C для остановки\n")
        
        while self.running:
            try:
                self.collect_data()
            except Exception as e:
                self.logger.error(f"Ошибка в цикле сбора: {e}")
            
            if not self.running:
                break
            
            self.logger.info(f"\nОжидание {self.config.poll_interval_seconds} секунд...")
            
            # Ожидание с возможностью прерывания
            for _ in range(self.config.poll_interval_seconds):
                if not self.running:
                    break
                time.sleep(1)
        
        self.storage.close()
        self.logger.info("Worker остановлен")


# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================

def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="StarLine Worker - сбор данных сигнализации",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры запуска:
  python worker.py -c config.json           # Однократный запуск
  python worker.py -c config.json -d        # Режим демона

Пример config.json:
{
    "app_id": "ваш_application_id",
    "app_secret": "ваш_application_secret",
    "user_login": "ваш_логин_starline",
    "user_password": "ваш_пароль_starline",
    "mysql_host": "localhost",
    "mysql_user": "starline",
    "mysql_password": "starline123",
    "mysql_database": "starline_db",
    "poll_interval_seconds": 60
}
        """
    )
    
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Путь к файлу конфигурации (по умолчанию: config.json)"
    )
    parser.add_argument(
        "-d", "--daemon",
        action="store_true",
        help="Запуск в режиме демона (постоянный опрос)"
    )
    
    args = parser.parse_args()
    
    # Загрузка конфигурации
    if os.path.exists(args.config):
        config = Config.from_file(args.config)
        print(f"Загружена конфигурация из: {args.config}")
    else:
        config = Config.from_env()
        print("Загружена конфигурация из переменных окружения")
    
    # Проверка обязательных параметров
    missing = []
    if not config.app_id:
        missing.append("app_id")
    if not config.app_secret:
        missing.append("app_secret")
    if not config.user_login:
        missing.append("user_login")
    if not config.user_password:
        missing.append("user_password")
    
    if missing:
        print(f"\n❌ Ошибка: не указаны обязательные параметры: {', '.join(missing)}")
        print(f"\nСоздайте файл {args.config} со следующим содержимым:")
        print('''{
    "app_id": "ВАШ_APPLICATION_ID",
    "app_secret": "ВАШ_APPLICATION_SECRET", 
    "user_login": "ВАШ_ЛОГIN_STARLINE",
    "user_password": "ВАШ_ПАРОЛЬ_STARLINE",
    "mysql_host": "localhost",
    "mysql_user": "starline",
    "mysql_password": "starline123",
    "mysql_database": "starline_db",
    "poll_interval_seconds": 60
}''')
        sys.exit(1)
    
    # Запуск
    worker = Worker(config)
    
    if args.daemon:
        worker.run_daemon()
    else:
        worker.run_once()


if __name__ == "__main__":
    main()
