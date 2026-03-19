#!/usr/bin/env python3
"""
StarLine Data Collector - приложение для сбора данных сигнализации и автомобиля
с сохранением в MySQL базу данных.

Автор: Z.ai
Версия: 1.0.0
"""

import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict
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
    app_secret: str = ""       # Пароль приложения (оригинал, не MD5)
    
    # Учётные данные пользователя StarLine
    user_login: str = ""       # Логин (email или телефон)
    user_password: str = ""    # Пароль (оригинал, не SHA1)
    
    # MySQL настройки
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "starline"
    mysql_password: str = ""
    mysql_database: str = "starline_db"
    
    # Настройки сбора данных
    poll_interval_seconds: int = 300  # Интервал опроса (5 минут)
    
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
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL", "300")),
        )
    
    @classmethod
    def from_file(cls, filepath: str) -> 'Config':
        """Загрузка конфигурации из JSON файла"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)


# =============================================================================
# API КЛИЕНТ STARLINE
# =============================================================================

class StarLineAPI:
    """Клиент для работы с StarLine API"""
    
    SLID_URL = "https://id.starline.ru"
    WEBAPI_URL = "https://developer.starline.ru"
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "StarLineDataCollector/1.0",
            "Accept": "application/json",
        })
        
        # Токены
        self.app_token: Optional[str] = None
        self.user_token: Optional[str] = None
        self.slnet_token: Optional[str] = None
        
        # Кэш устройств
        self.devices: List[Dict] = []
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
        
        self.logger.info("Получение кода приложения...")
        response = self.session.get(url, params=params)
        data = response.json()
        
        if data.get("state") != 1:
            raise Exception(f"Ошибка получения кода: {data.get('desc', {}).get('message')}")
        
        code = data["desc"]["code"]
        self.logger.debug(f"Код приложения получен: {code[:8]}...")
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
        
        self.logger.info("Получение токена приложения...")
        response = self.session.get(url, params=params)
        data = response.json()
        
        if data.get("state") != 1:
            raise Exception(f"Ошибка получения токена: {data.get('desc', {}).get('message')}")
        
        token = data["desc"]["token"]
        self.logger.debug(f"Токен приложения получен: {token[:16]}...")
        return token
    
    def _login_user(self) -> tuple:
        """Шаг 3: Аутентификация пользователя"""
        url = f"{self.SLID_URL}/apiV3/user/login"
        
        password_sha1 = hashlib.sha1(self.config.user_password.encode()).hexdigest()
        
        headers = {
            "token": self.app_token
        }
        
        data = {
            "login": self.config.user_login,
            "pass": password_sha1
        }
        
        self.logger.info("Аутентификация пользователя...")
        response = self.session.post(url, headers=headers, data=data)
        result = response.json()
        
        # Проверка на двухфакторную аутентификацию
        if result.get("state") == 2:
            raise Exception(
                f"Требуется двухфакторная аутентификация. "
                f"Код отправлен на: {result['desc'].get('phone')}"
            )
        
        if result.get("state") != 1:
            raise Exception(f"Ошибка аутентификации: {result.get('desc', {}).get('message')}")
        
        user_token = result["desc"]["user_token"]
        user_id = result["desc"]["id"]
        
        self.logger.info(f"Пользователь авторизован: ID={user_id}")
        return user_token, user_id
    
    def _auth_webapi(self) -> str:
        """Шаг 4: Авторизация в WebAPI"""
        url = f"{self.WEBAPI_URL}/json/v2/auth.slid"
        
        data = {
            "slid_token": self.user_token
        }
        
        self.logger.info("Авторизация в WebAPI...")
        response = self.session.post(url, json=data)
        
        # Извлечение slnet_token из cookie
        slnet_token = None
        for cookie in response.cookies:
            if cookie.name == "slnet_token":
                slnet_token = cookie.value
                break
        
        if not slnet_token:
            # Пробуем получить из ответа
            result = response.json()
            if result.get("state") != 1:
                raise Exception(f"Ошибка авторизации WebAPI: {result}")
            slnet_token = response.cookies.get("slnet_token")
        
        if not slnet_token:
            raise Exception("Не удалось получить slnet_token")
        
        self.logger.info(f"WebAPI авторизация успешна: {slnet_token[:16]}...")
        return slnet_token
    
    def authenticate(self) -> bool:
        """Полный цикл авторизации"""
        try:
            # Шаг 1: Получаем код приложения
            code = self._get_app_code()
            
            # Шаг 2: Получаем токен приложения
            self.app_token = self._get_app_token(code)
            
            # Шаг 3: Аутентификация пользователя
            self.user_token, self.user_id = self._login_user()
            
            # Шаг 4: Авторизация в WebAPI
            self.slnet_token = self._auth_webapi()
            
            # Установка cookie для последующих запросов
            self.session.cookies.set("slnet_token", self.slnet_token, 
                                     domain="developer.starline.ru")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка авторизации: {e}")
            return False
    
    def get_devices(self) -> List[Dict]:
        """Получение списка устройств пользователя"""
        if not self.user_id:
            raise Exception("Необходимо сначала выполнить авторизацию")
        
        url = f"{self.WEBAPI_URL}/json/v1/user/{self.user_id}/devices"
        
        self.logger.info("Получение списка устройств...")
        response = self.session.get(url)
        result = response.json()
        
        if result.get("state") != 1:
            raise Exception(f"Ошибка получения устройств: {result}")
        
        self.devices = result.get("desc", [])
        self.logger.info(f"Найдено устройств: {len(self.devices)}")
        
        return self.devices
    
    def get_device_data(self, device_id: str) -> Dict:
        """Получение полной информации о состоянии устройства"""
        url = f"{self.WEBAPI_URL}/json/v3/device/{device_id}/data"
        
        response = self.session.get(url)
        result = response.json()
        
        if result.get("state") != 1:
            self.logger.warning(f"Ошибка получения данных устройства {device_id}")
            return {}
        
        return result.get("desc", {})
    
    def get_device_position(self, device_id: str) -> Dict:
        """Получение данных о местоположении устройства"""
        url = f"{self.WEBAPI_URL}/json/v1/device/{device_id}/position"
        
        response = self.session.get(url)
        result = response.json()
        
        if result.get("state") != 1:
            return {}
        
        return result.get("desc", {})
    
    def get_obd_params(self, device_id: str) -> Dict:
        """Получение данных OBD из кеша"""
        url = f"{self.WEBAPI_URL}/json/device/{device_id}/obd_params"
        
        response = self.session.get(url)
        result = response.json()
        
        if result.get("state") != 1:
            return {}
        
        return result.get("desc", {})
    
    def get_obd_errors(self, device_id: str) -> List[Dict]:
        """Получение ошибок OBD"""
        url = f"{self.WEBAPI_URL}/json/device/{device_id}/obd_errors"
        
        response = self.session.get(url)
        result = response.json()
        
        if result.get("state") != 1:
            return []
        
        return result.get("desc", [])


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
            self.logger.info("Подключение к MySQL установлено")
            return True
        except Error as e:
            self.logger.error(f"Ошибка подключения к MySQL: {e}")
            return False
    
    def close(self):
        """Закрытие соединения"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.logger.info("Соединение с MySQL закрыто")
    
    def init_database(self):
        """Инициализация структуры базы данных"""
        cursor = self.connection.cursor()
        
        # Таблица устройств
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id VARCHAR(64) PRIMARY KEY,
                name VARCHAR(255),
                alias VARCHAR(255),
                device_type VARCHAR(64),
                firmware_version VARCHAR(64),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_device_type (device_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Таблица состояний сигнализации
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alarm_states (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                device_id VARCHAR(64) NOT NULL,
                timestamp DATETIME NOT NULL,
                
                -- Состояние охраны
                arm_state TINYINT DEFAULT 0 COMMENT '0=снято, 1=на охране',
                arm_datetime DATETIME COMMENT 'Время последней смены режима охраны',
                
                -- Состояние двигателя
                ign_state TINYINT DEFAULT 0 COMMENT '0=выключен, 1=запущен',
                ign_datetime DATETIME COMMENT 'Время последней смены состояния двигателя',
                run_time INT DEFAULT 0 COMMENT 'Время работы двигателя в секундах',
                
                -- Температура
                temp_inner DECIMAL(5,2) COMMENT 'Температура внутри',
                temp_engine DECIMAL(5,2) COMMENT 'Температура двигателя',
                temp_outdoor DECIMAL(5,2) COMMENT 'Температура на улице',
                
                -- Баланс SIM-карты
                balance DECIMAL(10,2) COMMENT 'Баланс в рублях',
                balance_currency VARCHAR(10),
                
                -- Дополнительные флаги
                door_driver TINYINT COMMENT 'Дверь водителя',
                door_passenger TINYINT COMMENT 'Дверь пассажира',
                door_rear_left TINYINT COMMENT 'Задняя левая дверь',
                door_rear_right TINYINT COMMENT 'Задняя правая дверь',
                hood TINYINT COMMENT 'Капот',
                trunk TINYINT COMMENT 'Багажник',
                handbrake TINYINT COMMENT 'Ручной тормоз',
                brake TINYINT COMMENT 'Тормоз',
                
                -- GSM/GPS
                gsm_level INT COMMENT 'Уровень GSM сигнала',
                gps_level INT COMMENT 'Уровень GPS сигнала',
                
                -- Сырые данные
                raw_data JSON COMMENT 'Полный ответ API',
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (device_id) REFERENCES devices(device_id),
                INDEX idx_device_timestamp (device_id, timestamp),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Таблица GPS позиций
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gps_positions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                device_id VARCHAR(64) NOT NULL,
                timestamp DATETIME NOT NULL,
                latitude DECIMAL(10, 8) NOT NULL,
                longitude DECIMAL(11, 8) NOT NULL,
                altitude DECIMAL(8, 2),
                speed DECIMAL(6, 2) COMMENT 'Скорость в км/ч',
                course DECIMAL(5, 2) COMMENT 'Направление в градусах',
                satellites INT,
                gps_valid TINYINT DEFAULT 1,
                address VARCHAR(500),
                raw_data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (device_id) REFERENCES devices(device_id),
                INDEX idx_device_timestamp (device_id, timestamp),
                INDEX idx_coords (latitude, longitude),
                SPATIAL INDEX idx_location ((POINT(longitude, latitude)))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Таблица OBD данных
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS obd_data (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                device_id VARCHAR(64) NOT NULL,
                timestamp DATETIME NOT NULL,
                fuel_level DECIMAL(5, 2) COMMENT 'Уровень топлива %',
                fuel_consumption DECIMAL(8, 3) COMMENT 'Расход топлива л/100км',
                mileage INT COMMENT 'Пробег в км',
                engine_rpm INT COMMENT 'Обороты двигателя',
                vehicle_speed INT COMMENT 'Скорость автомобиля км/ч',
                engine_load DECIMAL(5, 2) COMMENT 'Нагрузка на двигатель %',
                throttle_position DECIMAL(5, 2) COMMENT 'Положение дросселя %',
                coolant_temp DECIMAL(5, 2) COMMENT 'Температура ОЖ',
                intake_air_temp DECIMAL(5, 2) COMMENT 'Температура впускного воздуха',
                battery_voltage DECIMAL(5, 2) COMMENT 'Напряжение батареи В',
                raw_data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (device_id) REFERENCES devices(device_id),
                INDEX idx_device_timestamp (device_id, timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Таблица OBD ошибок
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS obd_errors (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                device_id VARCHAR(64) NOT NULL,
                timestamp DATETIME NOT NULL,
                error_code VARCHAR(10) NOT NULL,
                error_description VARCHAR(500),
                is_active TINYINT DEFAULT 1,
                raw_data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (device_id) REFERENCES devices(device_id),
                INDEX idx_device_timestamp (device_id, timestamp),
                INDEX idx_error_code (error_code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Таблица событий
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                device_id VARCHAR(64) NOT NULL,
                event_time DATETIME NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                event_name VARCHAR(255),
                event_data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (device_id) REFERENCES devices(device_id),
                INDEX idx_device_time (device_id, event_time),
                INDEX idx_event_type (event_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        self.connection.commit()
        self.logger.info("Структура базы данных инициализирована")
    
    def save_device(self, device_info: Dict):
        """Сохранение информации об устройстве"""
        cursor = self.connection.cursor()
        
        sql = """
            INSERT INTO devices (device_id, name, alias, device_type, firmware_version)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                alias = VALUES(alias),
                device_type = VALUES(device_type),
                firmware_version = VALUES(firmware_version),
                updated_at = CURRENT_TIMESTAMP
        """
        
        cursor.execute(sql, (
            device_info.get("device_id"),
            device_info.get("name"),
            device_info.get("alias"),
            device_info.get("device_type"),
            device_info.get("firmware_version")
        ))
        
        self.connection.commit()
    
    def save_alarm_state(self, device_id: str, state_data: Dict, timestamp: datetime):
        """Сохранение состояния сигнализации"""
        cursor = self.connection.cursor()
        
        # Парсинг данных состояния
        arm_state = state_data.get("arm")
        arm_dt = self._parse_datetime(state_data.get("arm_datetime"))
        ign_state = state_data.get("ign")
        ign_dt = self._parse_datetime(state_data.get("ign_datetime"))
        run_time = state_data.get("run_time", 0)
        
        # Температуры
        temps = state_data.get("temp", {})
        temp_inner = temps.get("inner")
        temp_engine = temps.get("engine")
        temp_outdoor = temps.get("outdoor")
        
        # Баланс
        balance = state_data.get("balance")
        balance_currency = state_data.get("balance_currency")
        
        # Двери и т.д.
        doors = state_data.get("doors", {})
        door_driver = doors.get("driver")
        door_passenger = doors.get("passenger")
        door_rear_left = doors.get("rear_left")
        door_rear_right = doors.get("rear_right")
        hood = doors.get("hood")
        trunk = doors.get("trunk")
        handbrake = doors.get("handbrake")
        brake = doors.get("brake")
        
        # GSM/GPS
        gsm = state_data.get("gsm", {})
        gsm_level = gsm.get("level")
        gps = state_data.get("gps", {})
        gps_level = gps.get("level")
        
        sql = """
            INSERT INTO alarm_states (
                device_id, timestamp, arm_state, arm_datetime,
                ign_state, ign_datetime, run_time,
                temp_inner, temp_engine, temp_outdoor,
                balance, balance_currency,
                door_driver, door_passenger, door_rear_left, door_rear_right,
                hood, trunk, handbrake, brake,
                gsm_level, gps_level, raw_data
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        cursor.execute(sql, (
            device_id, timestamp, arm_state, arm_dt,
            ign_state, ign_dt, run_time,
            temp_inner, temp_engine, temp_outdoor,
            balance, balance_currency,
            door_driver, door_passenger, door_rear_left, door_rear_right,
            hood, trunk, handbrake, brake,
            gsm_level, gps_level, json.dumps(state_data, ensure_ascii=False)
        ))
        
        self.connection.commit()
    
    def save_gps_position(self, device_id: str, position_data: Dict, timestamp: datetime):
        """Сохранение GPS позиции"""
        cursor = self.connection.cursor()
        
        location = position_data.get("location", {})
        lat = location.get("lat")
        lon = location.get("lon")
        altitude = location.get("altitude")
        
        if not lat or not lon:
            return
        
        speed = position_data.get("speed")
        course = position_data.get("course")
        satellites = position_data.get("satellites")
        gps_valid = position_data.get("valid", 1)
        
        sql = """
            INSERT INTO gps_positions (
                device_id, timestamp, latitude, longitude, altitude,
                speed, course, satellites, gps_valid, raw_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(sql, (
            device_id, timestamp, lat, lon, altitude,
            speed, course, satellites, gps_valid,
            json.dumps(position_data, ensure_ascii=False)
        ))
        
        self.connection.commit()
    
    def save_obd_data(self, device_id: str, obd_data: Dict, timestamp: datetime):
        """Сохранение OBD данных"""
        if not obd_data:
            return
        
        cursor = self.connection.cursor()
        
        sql = """
            INSERT INTO obd_data (
                device_id, timestamp, fuel_level, fuel_consumption, mileage,
                engine_rpm, vehicle_speed, engine_load, throttle_position,
                coolant_temp, intake_air_temp, battery_voltage, raw_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(sql, (
            device_id, timestamp,
            obd_data.get("fuel_level"),
            obd_data.get("fuel_consumption"),
            obd_data.get("mileage"),
            obd_data.get("engine_rpm"),
            obd_data.get("vehicle_speed"),
            obd_data.get("engine_load"),
            obd_data.get("throttle_position"),
            obd_data.get("coolant_temp"),
            obd_data.get("intake_air_temp"),
            obd_data.get("battery_voltage"),
            json.dumps(obd_data, ensure_ascii=False)
        ))
        
        self.connection.commit()
    
    def save_obd_errors(self, device_id: str, errors: List[Dict], timestamp: datetime):
        """Сохранение OBD ошибок"""
        if not errors:
            return
        
        cursor = self.connection.cursor()
        
        for error in errors:
            sql = """
                INSERT INTO obd_errors (
                    device_id, timestamp, error_code, error_description, is_active, raw_data
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(sql, (
                device_id, timestamp,
                error.get("code"),
                error.get("description"),
                error.get("is_active", 1),
                json.dumps(error, ensure_ascii=False)
            ))
        
        self.connection.commit()
    
    def _parse_datetime(self, dt_value) -> Optional[datetime]:
        """Парсинг datetime из различных форматов"""
        if not dt_value:
            return None
        
        if isinstance(dt_value, datetime):
            return dt_value
        
        if isinstance(dt_value, (int, float)):
            return datetime.fromtimestamp(dt_value)
        
        # Пробуем распарсить строку
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
            try:
                return datetime.strptime(dt_value, fmt)
            except (ValueError, TypeError):
                continue
        
        return None


# =============================================================================
# ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ
# =============================================================================

class StarLineCollector:
    """Главный класс приложения сбора данных"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api = StarLineAPI(config)
        self.storage = MySQLStorage(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.running = False
    
    def initialize(self) -> bool:
        """Инициализация приложения"""
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("/var/log/starline_collector.log")
            ]
        )
        
        # Подключение к БД
        if not self.storage.connect():
            self.logger.error("Не удалось подключиться к базе данных")
            return False
        
        # Инициализация структуры БД
        self.storage.init_database()
        
        # Авторизация в API
        if not self.api.authenticate():
            self.logger.error("Не удалось авторизоваться в StarLine API")
            return False
        
        return True
    
    def collect_data(self):
        """Сбор данных со всех устройств"""
        timestamp = datetime.now()
        
        try:
            # Получаем список устройств
            devices = self.api.get_devices()
            
            for device in devices:
                device_id = device.get("device_id")
                if not device_id:
                    continue
                
                self.logger.info(f"Сбор данных для устройства: {device.get('name', device_id)}")
                
                # Сохраняем информацию об устройстве
                self.storage.save_device(device)
                
                # Получаем и сохраняем состояние
                state_data = self.api.get_device_data(device_id)
                if state_data:
                    self.storage.save_alarm_state(device_id, state_data, timestamp)
                
                # Получаем и сохраняем позицию
                position_data = self.api.get_device_position(device_id)
                if position_data:
                    self.storage.save_gps_position(device_id, position_data, timestamp)
                
                # Получаем и сохраняем OBD данные
                obd_data = self.api.get_obd_params(device_id)
                if obd_data:
                    self.storage.save_obd_data(device_id, obd_data, timestamp)
                
                # Получаем и сохраняем OBD ошибки
                obd_errors = self.api.get_obd_errors(device_id)
                if obd_errors:
                    self.storage.save_obd_errors(device_id, obd_errors, timestamp)
            
            self.logger.info(f"Сбор данных завершён. Обработано устройств: {len(devices)}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при сборе данных: {e}")
    
    def run_once(self):
        """Однократный сбор данных"""
        if self.initialize():
            self.collect_data()
            self.storage.close()
    
    def run_daemon(self):
        """Запуск в режиме демона (постоянный сбор)"""
        import time
        import signal
        
        def signal_handler(sig, frame):
            self.logger.info("Получен сигнал остановки")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if not self.initialize():
            sys.exit(1)
        
        self.running = True
        self.logger.info(f"Запуск демона сбора данных (интервал: {self.config.poll_interval_seconds} сек)")
        
        while self.running:
            try:
                self.collect_data()
            except Exception as e:
                self.logger.error(f"Ошибка в цикле сбора: {e}")
            
            # Ожидание с возможностью прерывания
            for _ in range(self.config.poll_interval_seconds):
                if not self.running:
                    break
                time.sleep(1)
        
        self.storage.close()
        self.logger.info("Демон остановлен")


# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================

def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="StarLine Data Collector - сбор данных сигнализации"
    )
    parser.add_argument(
        "-c", "--config",
        default="/etc/starline_collector/config.json",
        help="Путь к файлу конфигурации"
    )
    parser.add_argument(
        "-d", "--daemon",
        action="store_true",
        help="Запуск в режиме демона"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Выполнить однократный сбор данных"
    )
    
    args = parser.parse_args()
    
    # Загрузка конфигурации
    if os.path.exists(args.config):
        config = Config.from_file(args.config)
    else:
        config = Config.from_env()
    
    # Проверка обязательных параметров
    if not all([config.app_id, config.app_secret, config.user_login, config.user_password]):
        print("Ошибка: Не указаны учётные данные StarLine API")
        print("Укажите их в конфигурационном файле или переменных окружения")
        sys.exit(1)
    
    # Запуск
    collector = StarLineCollector(config)
    
    if args.daemon:
        collector.run_daemon()
    else:
        collector.run_once()


if __name__ == "__main__":
    main()
