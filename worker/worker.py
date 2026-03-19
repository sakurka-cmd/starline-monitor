#!/usr/bin/env python3
"""
StarLine Worker v10.0 - Credentials from database
appId/appSecret хранятся в таблице user_devices
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
from typing import Optional, List, Dict, Tuple

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
    poll_interval_seconds: int = 120

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
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL", "120")),
        )


class StarLineAuth:
    """Авторизация через официальное API StarLine"""
    
    ID_URL = "https://id.starline.ru"
    API_URL = "https://developer.starline.ru"
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "StarLineMonitor/10.0"
        })
        self.logger = logging.getLogger('StarLineAuth')
        
        # Tokens
        self.app_code: Optional[str] = None
        self.app_token: Optional[str] = None
        self.slid_token: Optional[str] = None
        self.slnet_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.expires: Optional[float] = None

    def get_app_code(self) -> bool:
        """Шаг 1: Получить код приложения"""
        try:
            url = f"{self.ID_URL}/apiV3/application/getCode"
            secret = hashlib.md5(self.app_secret.encode()).hexdigest()
            
            params = {
                "appId": self.app_id,
                "secret": secret
            }
            
            resp = self.session.get(url, params=params, timeout=30)
            data = resp.json()
            
            if data.get("state") == 1:
                self.app_code = data["desc"]["code"]
                self.logger.info(f"Got app_code: {self.app_code[:10]}...")
                return True
            else:
                self.logger.error(f"get_app_code failed: {data}")
                return False
                
        except Exception as e:
            self.logger.error(f"get_app_code error: {e}")
            return False

    def get_app_token(self) -> bool:
        """Шаг 2: Получить токен приложения"""
        if not self.app_code:
            return False
            
        try:
            url = f"{self.ID_URL}/apiV3/application/getToken"
            secret = hashlib.md5((self.app_secret + self.app_code).encode()).hexdigest()
            
            params = {
                "appId": self.app_id,
                "secret": secret
            }
            
            resp = self.session.get(url, params=params, timeout=30)
            data = resp.json()
            
            if data.get("state") == 1:
                self.app_token = data["desc"]["token"]
                self.logger.info(f"Got app_token: {self.app_token[:10]}...")
                return True
            else:
                self.logger.error(f"get_app_token failed: {data}")
                return False
                
        except Exception as e:
            self.logger.error(f"get_app_token error: {e}")
            return False

    def login_user(self, login: str, password: str, sms_code: str = None, 
                   captcha_sid: str = None, captcha_code: str = None) -> Tuple[int, Dict]:
        """Шаг 3: Авторизация пользователя"""
        if not self.app_token:
            return (-1, {"error": "No app_token"})
            
        try:
            url = f"{self.ID_URL}/apiV3/user/login"
            
            params = {"token": self.app_token}
            data = {
                "login": login,
                "pass": hashlib.sha1(password.encode()).hexdigest()
            }
            
            if sms_code:
                data["smsCode"] = sms_code
            if captcha_sid and captcha_code:
                data["captchaSid"] = captcha_sid
                data["captchaCode"] = captcha_code
            
            resp = self.session.post(url, params=params, data=data, timeout=30)
            result = resp.json()
            
            state = result.get("state", -1)
            desc = result.get("desc", {})
            
            if state == 1:
                self.slid_token = desc.get("user_token")
                self.logger.info(f"Got slid_token: {self.slid_token[:10]}...")
            else:
                self.logger.warning(f"login_user state={state}: {desc}")
            
            return (state, desc)
                
        except Exception as e:
            self.logger.error(f"login_user error: {e}")
            return (-1, {"error": str(e)})

    def get_slnet_token(self) -> bool:
        """Шаг 4: Обменять slid_token на slnet_token"""
        if not self.slid_token:
            return False
            
        try:
            url = f"{self.API_URL}/json/v2/auth.slid"
            
            data = {"slid_token": self.slid_token}
            resp = self.session.post(url, json=data, timeout=30)
            result = resp.json()
            
            self.logger.info(f"auth.slid response: {result}")
            self.logger.info(f"Cookies: {resp.cookies}")
            self.logger.info(f"Cookies dict: {dict(resp.cookies)}")
            self.logger.info(f"Response headers: {dict(resp.headers)}")
            
            code = result.get("code")
            if str(code) == "200":
                self.user_id = result.get("user_id")
                
                # Ищем slnet в cookies
                for cookie in resp.cookies:
                    self.logger.info(f"Cookie: {cookie.name}={cookie.value[:20]}...")
                    if cookie.name == 'slnet':
                        self.slnet_token = cookie.value
                        self.expires = cookie.expires if cookie.expires else time.time() + 14400
                
                # Также проверяем в заголовке Set-Cookie
                set_cookie = resp.headers.get('Set-Cookie', '')
                if 'slnet=' in set_cookie and not self.slnet_token:
                    import re
                    match = re.search(r'slnet=([^;]+)', set_cookie)
                    if match:
                        self.slnet_token = match.group(1)
                        self.expires = time.time() + 14400
                
                if self.slnet_token:
                    self.logger.info(f"Got slnet_token for user {self.user_id}")
                    return True
                else:
                    self.logger.error("slnet token not found in cookies or headers")
                    return False
            else:
                self.logger.error(f"auth.slid failed: code={code}, {result.get('codestring')}")
                return False
                
        except Exception as e:
            self.logger.error(f"get_slnet_token error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def authenticate(self, login: str, password: str) -> Tuple[bool, str]:
        """Полный процесс авторизации"""
        if not self.get_app_code():
            return (False, "Failed to get app_code")
        
        if not self.get_app_token():
            return (False, "Failed to get app_token")
        
        state, data = self.login_user(login, password)
        
        if state == 1:
            if self.get_slnet_token():
                return (True, "Authenticated successfully")
            else:
                return (False, "Failed to get slnet_token")
        elif state == 0 and "phone" in data:
            return (False, f"SMS code required for phone {data['phone']}")
        elif state == 0 and "captchaSid" in data:
            return (False, "Captcha required")
        elif state == 2:
            return (False, "2FA required")
        else:
            return (False, f"Auth failed: {data}")


class StarLineSession:
    """Сессия для работы с API StarLine"""
    
    API_URL = "https://developer.starline.ru"
    
    def __init__(self, user_id: str, slnet_token: str):
        self.user_id = user_id
        self.slnet_token = slnet_token
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "StarLineMonitor/10.0",
            "Cookie": f"slnet={slnet_token}"
        })
        
        self.logger = logging.getLogger('StarLineSession')

    def get_devices(self) -> List[Dict]:
        """Получить список устройств"""
        try:
            url = f"{self.API_URL}/json/v2/user/{self.user_id}/user_info"
            resp = self.session.get(url, timeout=30)
            data = resp.json()
            
            code = data.get("code")
            if code == 200:
                devices = data.get("devices", []) + data.get("shared_devices", [])
                self.logger.info(f"Found {len(devices)} devices")
                return devices
            elif code == 401:
                self.logger.error("Unauthorized - slnet_token expired")
            elif code == 429:
                self.logger.error("Rate limited (429)")
            else:
                self.logger.error(f"API error: code={code}")
                
        except Exception as e:
            self.logger.error(f"get_devices error: {e}")
        
        return []

    def get_device_obd(self, device_id: str) -> Optional[Dict]:
        """Получить OBD данные"""
        try:
            url = f"{self.API_URL}/json/v1/device/{device_id}/obd_params"
            resp = self.session.get(url, timeout=30)
            data = resp.json()
            
            if data.get("code") == 200:
                return data.get("obd_params", {})
        except Exception as e:
            self.logger.warning(f"get_device_obd error: {e}")
        return None


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

    def get_user_devices_grouped(self) -> Dict[str, List[Dict]]:
        """Получить устройства, сгруппированные по (app_id, starline_login)"""
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT ud.*, u.email as user_email
            FROM user_devices ud
            JOIN users u ON ud.user_id = u.id
            WHERE ud.is_active = 1
            AND ud.app_id IS NOT NULL AND ud.app_id != ''
            AND ud.app_secret IS NOT NULL AND ud.app_secret != ''
            ORDER BY ud.app_id, ud.starline_login
        """)
        devices = cursor.fetchall()
        
        # Группируем по ключу (app_id, starline_login)
        grouped = {}
        for dev in devices:
            key = f"{dev['app_id']}:{dev['starline_login']}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(dev)
        
        return grouped

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

    def update_tokens(self, device_ids: List[int], slnet_token: str, user_id: str):
        """Сохранить токены авторизации для всех устройств группы"""
        if not device_ids:
            return
        cursor = self.connection.cursor()
        placeholders = ','.join(['%s'] * len(device_ids))
        cursor.execute(f"""
            UPDATE user_devices SET
                slnet_token = %s,
                starline_user_id = %s
            WHERE id IN ({placeholders})
        """, [slnet_token, user_id] + device_ids)
        self.connection.commit()

    def save_state(self, device_id: str, device_data: Dict):
        """Сохранение состояния устройства"""
        if not device_data:
            return

        cursor = self.connection.cursor()

        car_state = device_data.get("car_state", {})
        arm_state = 1 if car_state.get("arm") else 0
        ign_state = 1 if car_state.get("ign") else 0

        temp_inner = device_data.get("ctemp")
        temp_engine = device_data.get("etemp")

        balance_info = device_data.get("balance", {})
        balance = balance_info.get("active", {}).get("value") if isinstance(balance_info, dict) else None

        position = device_data.get("position", {})
        latitude = position.get("x")
        longitude = position.get("y")
        speed = position.get("s")

        obd = device_data.get("obd_params", {}) or device_data.get("obd", {})
        mileage = obd.get("mileage", {}).get("val") if obd else None
        fuel_litres = obd.get("fuel", {}).get("val") if obd else None

        # Motohrs может быть в разных местах
        motohrs = (
            car_state.get("motohrs") or
            car_state.get("motohours") or
            obd.get("motohrs", {}).get("val") if obd else None or
            device_data.get("motohrs") or
            device_data.get("motohours")
        )
        battery_voltage = device_data.get("battery")
        gsm_level = device_data.get("gsm_lvl")

        self.logger.info(f"Device {device_id}: arm={arm_state}, ign={ign_state}, temp={temp_inner}/{temp_engine}, motohrs={motohrs}")

        raw_json = json.dumps(device_data, ensure_ascii=False, default=str)

        try:
            cursor.execute("""
                INSERT INTO device_states
                (device_id, timestamp, arm_state, ign_state, 
                 temp_inner, temp_engine, balance,
                 latitude, longitude, speed, 
                 mileage, fuel_litres, motohrs,
                 gsm_lvl, battery_voltage, raw_data)
                VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                int(device_id), arm_state, ign_state, temp_inner, temp_engine, balance,
                latitude, longitude, speed, mileage, fuel_litres, motohrs,
                gsm_level, battery_voltage, raw_json
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
        # Кэш сессий: ключ = (app_id, login) -> {session, expires, device_ids}
        self._sessions_cache: Dict[str, dict] = {}

    def initialize(self) -> bool:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s"
        )
        self.db = Database(self.config)
        return self.db.connect()

    def get_or_create_session(self, app_id: str, app_secret: str, 
                               login: str, password: str,
                               device_ids: List[int],
                               cached_slnet_token: str = None,
                               cached_user_id: str = None) -> Optional[StarLineSession]:
        """Получить сессию из кэша или создать новую"""
        cache_key = f"{app_id}:{login}"
        
        # 1. Проверяем内存 кэш
        if cache_key in self._sessions_cache:
            cached = self._sessions_cache[cache_key]
            if cached.get("expires", 0) > time.time():
                self.logger.info(f"Using memory cached session for {login}")
                return StarLineSession(cached["user_id"], cached["slnet_token"])
            else:
                self.logger.info(f"Memory cached session expired for {login}")
                del self._sessions_cache[cache_key]
        
        # 2. Проверяем кэшированный токен из БД
        if cached_slnet_token and cached_user_id:
            self.logger.info(f"Trying DB cached slnet_token for {login}")
            session = StarLineSession(cached_user_id, cached_slnet_token)
            # Проверяем валидность токена
            devices = session.get_devices()
            if devices:
                self.logger.info(f"DB cached token valid for {login}")
                # Кэшируем в памяти
                self._sessions_cache[cache_key] = {
                    "slnet_token": cached_slnet_token,
                    "user_id": cached_user_id,
                    "expires": time.time() + 14400,  # 4 часа
                    "device_ids": device_ids
                }
                return session
            else:
                self.logger.warning(f"DB cached token invalid for {login}")
        
        # 3. Создаём новую сессию через полную авторизацию
        self.logger.info(f"Creating new session for {login}")
        auth = StarLineAuth(app_id, app_secret)
        success, message = auth.authenticate(login, password)
        
        if success:
            # Кэшируем
            self._sessions_cache[cache_key] = {
                "slnet_token": auth.slnet_token,
                "user_id": auth.user_id,
                "expires": auth.expires or (time.time() + 14400),
                "device_ids": device_ids
            }
            
            # Сохраняем токены в БД
            self.db.update_tokens(device_ids, auth.slnet_token, auth.user_id)
            
            return StarLineSession(auth.user_id, auth.slnet_token)
        else:
            self.logger.error(f"Auth failed for {login}: {message}")
            return None

    def process_device_group(self, devices: List[Dict]):
        """Обработка группы устройств с одинаковыми appId и логином"""
        if not devices:
            return
        
        first = devices[0]
        app_id = first['app_id']
        app_secret = first['app_secret']
        starline_login = first['starline_login']
        starline_password = first['starline_password']
        device_ids = [d['id'] for d in devices]
        
        # Получаем кэшированные токены из БД
        cached_slnet_token = first.get('slnet_token')
        cached_user_id = first.get('starline_user_id')
        
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"Processing {len(devices)} devices for {starline_login} (appId: {app_id})")
        
        if cached_slnet_token:
            self.logger.info(f"Found cached slnet_token in DB")
        
        # Получаем сессию
        session = self.get_or_create_session(
            app_id, app_secret, 
            starline_login, starline_password,
            device_ids,
            cached_slnet_token,
            cached_user_id
        )
        
        if not session:
            for dev in devices:
                self.db.update_device_status(dev['id'], error="Auth failed")
            return
        
        # Получаем устройства от StarLine
        starline_devices = session.get_devices()
        if not starline_devices:
            self.logger.warning("No devices from StarLine API")
            return
        
        # Обрабатываем каждое локальное устройство
        for user_device in devices:
            device_name = user_device.get('name', 'Unknown')
            self.logger.info(f"\n--- Device: {device_name} ---")
            
            found = False
            for sl_dev in starline_devices:
                sl_device_id = sl_dev.get("device_id")
                sl_device_name = sl_dev.get("name") or sl_dev.get("alias") or str(sl_device_id)
                
                stored_id = user_device.get('starline_device_id')
                
                if (str(sl_device_id) == str(stored_id) or 
                    device_name.lower() in sl_device_name.lower()):
                    found = True
                    self.logger.info(f"Found: {sl_device_name} (ID: {sl_device_id})")
                    
                    # OBD данные
                    obd = session.get_device_obd(str(sl_device_id))
                    if obd:
                        sl_dev['obd_params'] = obd
                    
                    self.db.save_state(str(sl_device_id), sl_dev)
                    self.db.update_device_status(user_device['id'], str(sl_device_id), sl_device_name, None)
                    break
            
            if not found:
                self.logger.warning(f"Device not found: {device_name}")
                self.db.update_device_status(user_device['id'], error="Device not found in StarLine")

    def run_once(self):
        self.logger.info("=" * 50)
        self.logger.info(f"Worker started (interval: {self.config.poll_interval_seconds}s)")

        grouped_devices = self.db.get_user_devices_grouped()
        total_devices = sum(len(v) for v in grouped_devices.values())
        self.logger.info(f"Found {total_devices} devices in {len(grouped_devices)} sessions")
        
        if not grouped_devices:
            self.logger.warning("No devices with appId/appSecret configured!")
            self.logger.warning("Add devices via the web interface with StarLine credentials")

        for key, devices in grouped_devices.items():
            try:
                self.process_device_group(devices)
            except Exception as e:
                self.logger.error(f"Error processing {key}: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                for dev in devices:
                    self.db.update_device_status(dev['id'], error=str(e))

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
        self.logger.info("Worker daemon started v10.0 (credentials from DB)")
        self.logger.info("")

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

    parser = argparse.ArgumentParser(description="StarLine Worker v10.0")
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
