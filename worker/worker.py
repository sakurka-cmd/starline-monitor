#!/usr/bin/env python3
"""
StarLine Worker v4.1 - С сохранением сессии, пробега, топлива, моточасов
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


class StarLineAPI:
    SLID_URL = "https://id.starline.ru"
    WEBAPI_URL = "https://developer.starline.ru"

    def __init__(self, app_id: str, app_secret: str, login: str, password: str, 
                 slnet_token: str = None, user_id: str = None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.login = login
        self.password = password

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })

        self.slnet_token = slnet_token
        self.user_id = user_id
        self.logger = logging.getLogger('StarLineAPI')

        if slnet_token:
            self.session.cookies.set("slnet", slnet_token, domain="developer.starline.ru")

    def check_session(self) -> bool:
        """Проверка валидности текущей сессии"""
        if not self.slnet_token or not self.user_id:
            self.logger.info("No saved session found")
            return False
        
        try:
            url = f"{self.WEBAPI_URL}/json/v1/user/{self.user_id}/devices"
            resp = self.session.get(url)
            result = resp.json()
            
            if result.get("code") in [200, "200"]:
                self.logger.info("Session is valid")
                return True
            else:
                self.logger.info(f"Session invalid: {result.get('code')}")
        except Exception as e:
            self.logger.warning(f"Session check failed: {e}")
        
        return False

    def authenticate(self) -> bool:
        """Полная авторизация"""
        try:
            # Step 1: Get code
            url = f"{self.SLID_URL}/apiV3/application/getCode"
            secret_md5 = hashlib.md5(self.app_secret.encode()).hexdigest()

            resp = self.session.get(url, params={"appId": self.app_id, "secret": secret_md5})
            data = resp.json()

            if data.get("state") != 1:
                self.logger.error(f"getCode failed: {data}")
                return False

            code = data["desc"]["code"]
            self.logger.info(f"Step 1 OK: code={code[:8]}...")

            # Step 2: Get app token
            url = f"{self.SLID_URL}/apiV3/application/getToken"
            secret_md5 = hashlib.md5((self.app_secret + code).encode()).hexdigest()

            resp = self.session.get(url, params={"appId": self.app_id, "secret": secret_md5})
            data = resp.json()

            if data.get("state") != 1:
                self.logger.error(f"getToken failed: {data}")
                return False

            app_token = data["desc"]["token"]
            self.logger.info(f"Step 2 OK: token={app_token[:16]}...")

            # Step 3: User login
            url = f"{self.SLID_URL}/apiV3/user/login"
            password_sha1 = hashlib.sha1(self.password.encode()).hexdigest()

            resp = self.session.post(
                url,
                headers={"token": app_token},
                data={"login": self.login, "pass": password_sha1}
            )
            data = resp.json()

            if data.get("state") == 2:
                self.logger.error(f"2FA required: {data['desc'].get('phone')}")
                return False

            if data.get("state") != 1:
                self.logger.error(f"Login failed: {data}")
                return False

            user_token = data["desc"]["user_token"]
            self.logger.info(f"Step 3 OK: login user_id={data['desc']['id']}")

            # Step 4: WebAPI auth
            url = f"{self.WEBAPI_URL}/json/v2/auth.slid"
            resp = self.session.post(url, json={"slid_token": user_token})

            result = resp.json()
            self.logger.info(f"auth.slid response: code={result.get('code')}")

            if result.get("code") in ["200", 200]:
                self.user_id = result.get("user_id")
                self.logger.info(f"WebAPI user_id: {self.user_id}")

            if not self.user_id:
                self.user_id = data["desc"]["id"]

            # Extract slnet token
            for cookie in resp.cookies:
                if cookie.name == "slnet":
                    self.slnet_token = cookie.value
                    break

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

            return True

        except Exception as e:
            self.logger.error(f"Auth error: {e}")
            return False

    def get_devices(self) -> List[Dict]:
        if not self.user_id:
            return []

        url = f"{self.WEBAPI_URL}/json/v1/user/{self.user_id}/devices"
        resp = self.session.get(url)
        result = resp.json()

        self.logger.info(f"Devices response: code={result.get('code')}")

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
        """Получение полных данных устройства"""
        data = {}

        # Endpoint 1: /json/v3/device/{id}/data - основная информация
        url1 = f"{self.WEBAPI_URL}/json/v3/device/{device_id}/data"
        resp1 = self.session.get(url1)
        result1 = resp1.json()

        if result1.get("code") in [200, "200"]:
            data.update(result1.get("data", {}))

        # Endpoint 2: /json/device/{id}/state - состояние
        url2 = f"{self.WEBAPI_URL}/json/device/{device_id}/state"
        resp2 = self.session.get(url2)
        result2 = resp2.json()

        if result2.get("code") in [200, "200"]:
            state_data = result2.get("state", {})
            if isinstance(state_data, dict):
                data.update(state_data)

        return data


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

    def get_session(self, device_id: int) -> Dict:
        """Получить сохранённую сессию"""
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT slnet_token, starline_user_id FROM user_devices WHERE id = %s
        """, (device_id,))
        row = cursor.fetchone()
        return row or {}

    def save_session(self, device_id: int, slnet_token: str, user_id: str):
        """Сохранить сессию"""
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE user_devices 
            SET slnet_token = %s, starline_user_id = %s
            WHERE id = %s
        """, (slnet_token, user_id, device_id))
        self.connection.commit()
        self.logger.info(f"Session saved for device {device_id}")

    def update_device_status(self, device_id: int, starline_device_id: str = None,
                             device_name: str = None, error: str = None):
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE user_devices SET
                starline_device_id = %s,
                device_name = %s,
                last_update = NOW(),
                last_error = %s
            WHERE id = %s
        """, (starline_device_id, device_name, error, device_id))
        self.connection.commit()

    def save_device_info(self, device_id: str, name: str, alias: str = None, 
                         device_type: str = None, firmware: str = None):
        """Сохранить/обновить информацию об устройстве"""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO devices (device_id, name, alias, device_type, firmware_version)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                name = VALUES(name), 
                alias = COALESCE(VALUES(alias), alias),
                device_type = COALESCE(VALUES(device_type), device_type),
                firmware_version = COALESCE(VALUES(firmware_version), firmware_version),
                updated_at = NOW()
        """, (device_id, name, alias, device_type, firmware))
        self.connection.commit()

    def save_state(self, device_id: str, state_data: Dict):
        """Сохранение состояния в device_states"""
        if not state_data:
            return

        cursor = self.connection.cursor()

        # Парсим car_state
        car_state = state_data.get("car_state", {})
        arm_state = 1 if car_state.get("arm") else 0
        ign_state = 1 if car_state.get("ign") else 0

        # Температуры
        temp_inner = state_data.get("ctemp")
        temp_engine = state_data.get("etemp")

        # Баланс
        balance_info = state_data.get("balance", {})
        if isinstance(balance_info, dict):
            balance = balance_info.get("active", {}).get("value")
        else:
            balance = None

        # GPS позиция
        position = state_data.get("position", {})
        latitude = position.get("x")
        longitude = position.get("y")
        speed = position.get("s")

        # OBD данные - пробег, топливо
        obd = state_data.get("obd", {})
        mileage = obd.get("mileage") if obd else None
        
        # Топливо из obd_params или obd
        obd_params = state_data.get("obd_params", {})
        fuel_data = obd_params.get("fuel", {})
        fuel_litres = fuel_data.get("val") if fuel_data else obd.get("fuel_litres") if obd else None

        # Моточасы из common или state
        common = state_data.get("common", {})
        motohrs = common.get("motohrs") if common else None
        if motohrs is None and "state" in state_data:
            motohrs = state_data.get("state", {}).get("motohrs")
        
        # Напряжение батареи
        battery_voltage = state_data.get("battery") or (common.get("battery") if common else None)
        
        # GSM уровень
        gsm_level = state_data.get("gsm_lvl") or (common.get("gsm_lvl") if common else None)

        self.logger.info(f"arm={arm_state}, ign={ign_state}, temp_in={temp_inner}, temp_eng={temp_engine}")
        self.logger.info(f"mileage={mileage}km, fuel={fuel_litres}L, motohrs={motohrs}h")

        # Сериализуем в JSON
        raw_json = json.dumps(state_data, ensure_ascii=False, default=str)

        try:
            cursor.execute("""
                INSERT INTO device_states
                (device_id, timestamp, arm_state, ign_state, 
                 temp_inner, temp_engine, balance,
                 latitude, longitude, speed, 
                 mileage, fuel_litres, motohrs,
                 gsm_level, battery_voltage, raw_data)
                VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                int(device_id),
                arm_state,
                ign_state,
                temp_inner,
                temp_engine,
                balance,
                latitude,
                longitude,
                speed,
                mileage,
                fuel_litres,
                motohrs,
                gsm_level,
                battery_voltage,
                raw_json
            ))
            self.connection.commit()
            self.logger.info(f"✓ State saved: {device_id}")
        except Error as e:
            self.logger.error(f"Save state error: {e}")


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

        session = self.db.get_session(user_device['id'])
        
        api = StarLineAPI(
            app_id=user_device['app_id'],
            app_secret=user_device['app_secret'],
            login=user_device['starline_login'],
            password=user_device['starline_password'],
            slnet_token=session.get('slnet_token'),
            user_id=str(session.get('starline_user_id', ''))
        )

        if not api.check_session():
            self.logger.info("Session invalid, re-authenticating...")
            if not api.authenticate():
                self.db.update_device_status(user_device['id'], error="Auth failed")
                return
            self.db.save_session(user_device['id'], api.slnet_token, str(api.user_id))
        else:
            self.logger.info("Using cached session")

        devices = api.get_devices()

        if not devices:
            self.db.update_device_status(user_device['id'], error="No devices")
            return

        for device in devices:
            device_id = device.get("device_id") or device.get("id")
            if not device_id:
                continue

            device_name = device.get("name") or device.get("alias") or str(device_id)
            device_alias = device.get("alias")
            device_type = device.get("type")
            firmware = device.get("firmware_version")

            self.logger.info(f"  Device: {device_name} (ID: {device_id})")

            # Сохраняем информацию об устройстве
            self.db.save_device_info(str(device_id), device_name, device_alias, 
                                      str(device_type) if device_type else None, firmware)

            # Получаем и сохраняем состояние
            state = api.get_device_data(str(device_id))
            if state:
                self.db.save_state(str(device_id), state)

            self.db.update_device_status(
                user_device['id'],
                starline_device_id=str(device_id),
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

        self.logger.info("Done.")

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
                self.logger.info(f"Sleeping {self.config.poll_interval_seconds}s...")
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

    parser = argparse.ArgumentParser(description="StarLine Worker v4.1")
    parser.add_argument("-c", "--config", default="config.json")
    parser.add_argument("-d", "--daemon", action="store_true", help="Run as daemon")
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
