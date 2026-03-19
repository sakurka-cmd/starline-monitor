# StarLine Monitoring System - Docker Setup

## Структура проекта

```
starline-app/
├── docker-compose.yml
├── init-db/
│   └── 01-init.sql
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── worker/
│   ├── Dockerfile
│   ├── worker.py
│   ├── config.json
│   └── requirements.txt
└── frontend/
    ├── Dockerfile
    └── ... (Next.js app)
```

## Быстрый старт

### 1. Создайте структуру директорий

```bash
cd ~
mkdir -p starline-docker/{init-db,backend,worker,frontend}
cd starline-docker
```

### 2. Скопируйте файлы

Создайте следующие файлы:

**docker-compose.yml** - главный файл оркестрации

**init-db/01-init.sql** - инициализация БД

**backend/Dockerfile** - для FastAPI

**backend/main.py** - код бэкенда (исправленная версия)

**backend/requirements.txt**:
```
fastapi
uvicorn
mysql-connector-python
pyjwt
pydantic[email]
```

**worker/Dockerfile** - для Worker

**worker/worker.py** - код worker (worker_final.py)

**worker/config.json**:
```json
{
    "mysql_host": "mysql",
    "mysql_port": 3306,
    "mysql_user": "starline",
    "mysql_password": "starline123",
    "mysql_database": "starline_db",
    "poll_interval_seconds": 60
}
```

**worker/requirements.txt**:
```
mysql-connector-python
requests
```

**frontend/Dockerfile** - для Next.js

### 3. Запуск

```bash
# Сборка и запуск всех сервисов
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f worker
docker-compose logs -f backend
```

### 4. Проверка

```bash
# Проверка работы сервисов
docker-compose ps

# API health check
curl http://localhost:8000/api/health

# Frontend
open http://localhost:3000
```

## Управление

```bash
# Остановить все сервисы
docker-compose down

# Остановить и удалить данные
docker-compose down -v

# Перезапустить конкретный сервис
docker-compose restart worker

# Пересобрать конкретный сервис
docker-compose up -d --build worker
```

## Переменные окружения

Отредактируйте `docker-compose.yml`:

- `JWT_SECRET` - секрет для JWT токенов (ОБЯЗАТЕЛЬНО измените!)
- `NEXT_PUBLIC_API_URL` - URL API для фронтенда (укажите ваш IP)
- `POLL_INTERVAL` - интервал опроса StarLine (секунды)

## Порты

- **3000** - Frontend (Next.js)
- **8000** - Backend (FastAPI)
- **3306** - MySQL (можно убрать из docker-compose.yml если не нужен внешний доступ)

## После запуска

1. Откройте http://localhost:3000
2. Зарегистрируйте пользователя
3. Добавьте StarLine устройство (app_id, app_secret, login, password)
4. Worker автоматически начнёт собирать данные через 60 секунд

## Troubleshooting

```bash
# Если MySQL не готов, перезапустите зависимые сервисы
docker-compose restart backend worker

# Проверить подключение к MySQL
docker-compose exec mysql mysql -u starline -pstarline123 starline_db

# Посмотреть таблицы
docker-compose exec mysql mysql -u starline -pstarline123 starline_db -e "SHOW TABLES;"
```
