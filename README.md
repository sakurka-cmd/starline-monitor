# StarLine Monitor v2.0

Система мониторинга StarLine с поддержкой:
- 🚗 Отслеживание состояния охраны, зажигания
- 🌡️ Температуры салона и двигателя
- ⛽ Уровень топлива
- 📊 Пробег и моточасы
- 📍 GPS позиционирование
- 🔧 Учёт технического обслуживания

## Быстрый старт

### 1. Клонирование

```bash
git clone https://github.com/sakurka-cmd/starline-monitor.git
cd starline-monitor
```

### 2. Настройка

```bash
cp .env.example .env
nano .env
```

Измените пароли и укажите IP вашего сервера в `API_URL`.

### 3. Запуск

```bash
docker-compose up -d
```

### 4. Использование

Откройте в браузере: `http://YOUR_IP:3000`

1. Зарегистрируйтесь
2. Добавьте устройство (потребуются credentials от StarLine API)
3. Данные начнут поступать через ~1 минуту

## Получение StarLine API credentials

1. Зайдите на https://my.starline.ru
2. Раздел "Разработчикам" → "API"
3. Создайте приложение
4. Скопируйте **Application ID** и **Secret**

## Структура проекта

```
starline-monitor/
├── docker-compose.yml      # Оркестрация контейнеров
├── backend/                # FastAPI REST API
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── worker/                 # Сбор данных со StarLine
│   ├── worker.py
│   ├── config.json
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # Next.js интерфейс
│   ├── src/
│   ├── Dockerfile
│   └── package.json
└── init-db/                # Инициализация БД
    └── 01-init.sql
```

## API Endpoints

### Auth
- `POST /api/auth/register` - Регистрация
- `POST /api/auth/login` - Вход
- `GET /api/auth/me` - Профиль

### Devices
- `GET /api/devices` - Список устройств
- `POST /api/devices` - Добавить устройство
- `DELETE /api/devices/{id}` - Удалить
- `GET /api/devices/{id}/latest` - Последнее состояние
- `GET /api/devices/{id}/state` - История (параметр `hours`)
- `GET /api/devices/{id}/stats` - Статистика

### Maintenance
- `GET /api/devices/{id}/maintenance` - Записи ТО
- `POST /api/devices/{id}/maintenance` - Добавить ТО
- `PUT /api/devices/{id}/maintenance/{mid}` - Обновить
- `DELETE /api/devices/{id}/maintenance/{mid}` - Удалить
- `GET /api/devices/{id}/maintenance/upcoming` - Предстоящие ТО
- `GET /api/service-types` - Типы обслуживания

## Миграция с версии 1.x

Если у вас уже установлена версия 1.x:

### Вариант A: Обновление с сохранением данных

```bash
# 1. Остановить текущую версию
docker-compose down

# 2. Создать бэкап БД
docker exec starline-mysql mysqldump -u root -pYOUR_ROOT_PASSWORD starline_db > backup.sql

# 3. Обновить код
git pull

# 4. Запустить новую версию
docker-compose up -d

# 5. Добавить новые колонки
docker exec -i starline-mysql mysql -u root -pYOUR_ROOT_PASSWORD starline_db << 'EOF'
ALTER TABLE device_states ADD COLUMN mileage INT DEFAULT NULL;
ALTER TABLE device_states ADD COLUMN fuel_litres DECIMAL(6,2) DEFAULT NULL;
ALTER TABLE device_states ADD COLUMN motohrs INT DEFAULT NULL;

ALTER TABLE user_devices ADD COLUMN slnet_token VARCHAR(255);
ALTER TABLE user_devices ADD COLUMN starline_user_id VARCHAR(64);

CREATE TABLE IF NOT EXISTS maintenance_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id BIGINT NOT NULL,
    service_type VARCHAR(100) NOT NULL,
    description TEXT,
    mileage_at_service INT,
    motohrs_at_service INT,
    service_date DATE NOT NULL,
    next_service_mileage INT,
    next_service_motohrs INT,
    cost DECIMAL(10,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_date (device_id, service_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS service_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    default_interval_km INT,
    default_interval_hours INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO service_types (name, default_interval_km, default_interval_hours) VALUES
('Замена масла двигателя', 10000, 250),
('Замена масла АКПП', 60000, NULL),
('Замена воздушного фильтра', 15000, NULL),
('Замена салонного фильтра', 15000, NULL),
('Замена топливного фильтра', 30000, NULL),
('Замена свечей зажигания', 30000, NULL),
('Замена ремня ГРМ', 60000, NULL),
('Замена тормозных колодок передних', 40000, NULL),
('Замена тормозных колодок задних', 60000, NULL),
('Замена тормозной жидкости', 40000, NULL),
('Замена антифриза', 60000, NULL),
('Другое', NULL, NULL);
EOF

# 6. Пересобрать контейнеры
docker-compose build --no-cache
docker-compose up -d
```

### Вариант B: Чистая установка

```bash
# 1. Остановить и удалить всё
docker-compose down -v

# 2. Удалить старые образы
docker rmi $(docker images -q 'starline*')

# 3. Обновить код
git pull

# 4. Запустить заново
docker-compose up -d --build
```

## Устранение неполадок

### Капча при авторизации

Если StarLine требует капчу:
1. Worker сохраняет сессию и переиспользует её
2. При первом запуске может потребоваться ввести капчу вручную на my.starline.ru
3. Увеличьте `poll_interval_seconds` до 300 (5 минут)

### Нет данных

```bash
# Проверить логи worker
docker-compose logs -f worker

# Проверить устройство в БД
docker exec -it starline-mysql mysql -u starline -pstarline123 starline_db -e "SELECT * FROM user_devices;"
```

### Ошибки БД

```bash
# Пересоздать БД
docker-compose down -v
docker-compose up -d
```

## Разработка

```bash
# Backend локально
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend локально
cd frontend
npm install
npm run dev

# Worker локально
cd worker
pip install -r requirements.txt
python worker.py -c config.json --daemon
```

## Лицензия

MIT
