# StarLine Monitoring Web Application

Полноценное веб-приложение для мониторинга автомобилей со StarLine.

## Архитектура

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Next.js UI    │────▶│   FastAPI API   │────▶│     MySQL       │
│   (порт 3000)   │     │   (порт 8000)   │     │   (порт 3306)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  Python Worker  │
                        │  (сбор данных)  │
                        └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  StarLine API   │
                        └─────────────────┘
```

## Установка

### 1. База данных MySQL

```bash
# Установка MySQL
sudo apt install mysql-server -y

# Создание базы и пользователя
sudo mysql -u root -p
```

```sql
CREATE DATABASE starline_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'starline'@'localhost' IDENTIFIED BY 'ВАШ_ПАРОЛЬ';
GRANT ALL PRIVILEGES ON starline_db.* TO 'starline'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 2. Backend (FastAPI)

```bash
# Копирование файлов
mkdir -p ~/starline-app/backend
cp starline-backend/main.py ~/starline-app/backend/
cp starline-backend/requirements.txt ~/starline-app/backend/

# Создание виртуального окружения
cd ~/starline-app/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройка переменных окружения
export MYSQL_PASSWORD="ВАШ_ПАРОЛЬ_MYSQL"
export JWT_SECRET="случайная_строка_32_символа"

# Запуск
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. Worker (Сбор данных)

```bash
# Копирование
mkdir -p ~/starline-app/worker
cp starline-worker/worker.py ~/starline-app/worker/

# Используем то же виртуальное окружение
cd ~/starline-app/worker
source ~/starline-app/backend/venv/bin/activate

# Настройка
export MYSQL_PASSWORD="ВАШ_ПАРОЛЬ_MYSQL"

# Запуск (в фоне)
nohup python worker.py > worker.log 2>&1 &
```

### 4. Frontend (Next.js)

```bash
# Установка зависимостей
cd /home/z/my-project
bun install

# Настройка API URL
export NEXT_PUBLIC_API_URL="http://localhost:8000"

# Запуск
bun run dev
```

## Автозапуск через systemd

### Backend сервис

Создайте `/etc/systemd/system/starline-api.service`:

```ini
[Unit]
Description=StarLine API Backend
After=network.target mysql.service

[Service]
Type=simple
User=ВАШ_ПОЛЬЗОВАТЕЛЬ
WorkingDirectory=/home/ВАШ_ПОЛЬЗОВАТЕЛЬ/starline-app/backend
Environment="MYSQL_PASSWORD=ВАШ_ПАРОЛЬ"
Environment="JWT_SECRET=ВАШ_СЕКРЕТ"
ExecStart=/home/ВАШ_ПОЛЬЗОВАТЕЛЬ/starline-app/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Worker сервис

Создайте `/etc/systemd/system/starline-worker.service`:

```ini
[Unit]
Description=StarLine Data Collector Worker
After=network.target mysql.service starline-api.service

[Service]
Type=simple
User=ВАШ_ПОЛЬЗОВАТЕЛЬ
WorkingDirectory=/home/ВАШ_ПОЛЬЗОВАТЕЛЬ/starline-app/worker
Environment="MYSQL_PASSWORD=ВАШ_ПАРОЛЬ"
Environment="POLL_INTERVAL=300"
ExecStart=/home/ВАШ_ПОЛЬЗОВАТЕЛЬ/starline-app/backend/venv/bin/python worker.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Активация

```bash
sudo systemctl daemon-reload
sudo systemctl enable starline-api starline-worker
sudo systemctl start starline-api starline-worker
```

## Использование

1. Откройте http://localhost:3000
2. Зарегистрируйтесь
3. Добавьте устройство (понадобятся AppId и Secret от my.starline.ru)
4. Данные начнут собираться автоматически

## Получение доступа к StarLine API

1. Зайдите на https://my.starline.ru
2. В настройках выберите русский язык
3. Раздел "Разработчикам" → "Создать приложение"
4. Заполните форму и дождитесь одобрения
5. Получите AppId и Secret

## API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | /api/auth/register | Регистрация |
| POST | /api/auth/login | Вход |
| GET | /api/auth/me | Текущий пользователь |
| GET | /api/devices | Список устройств |
| POST | /api/devices | Добавить устройство |
| DELETE | /api/devices/{id} | Удалить устройство |
| GET | /api/devices/{id}/state | История состояний |
| GET | /api/devices/{id}/latest | Последнее состояние |
| GET | /api/stats | Статистика |
