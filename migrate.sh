#!/bin/bash
# Миграция с версии 1.x на 2.0
# Запускать на сервере: ./migrate.sh

set -e

echo "=== StarLine Monitor Migration v1.x -> v2.0 ==="

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker not found"
    exit 1
fi

# Проверяем наличие docker-compose
if ! command -v docker-compose &> /dev/null; then
    if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
        echo "ERROR: docker-compose not found"
        exit 1
    fi
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo ""
echo "Step 1: Backing up database..."
read -p "MySQL root password: " -s MYSQL_ROOT_PASSWORD
echo ""

# Бэкап БД
docker exec starline-mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} starline_db > starline_backup_$(date +%Y%m%d_%H%M%S).sql
echo "Backup created: starline_backup_*.sql"

echo ""
echo "Step 2: Adding new columns and tables..."

# Добавляем новые колонки и таблицы
docker exec -i starline-mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} starline_db << 'EOSQL'

-- Добавить колонки в device_states если их нет
SET @dbname = DATABASE();
SET @tablename = 'device_states';

-- mileage
SET @col_exists = 0;
SELECT 1 INTO @col_exists FROM information_schema.columns 
WHERE table_schema = @dbname AND table_name = @tablename AND column_name = 'mileage';
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE device_states ADD COLUMN mileage INT DEFAULT NULL COMMENT "Пробег (км)"', 
    'SELECT "mileage column exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- fuel_litres
SET @col_exists = 0;
SELECT 1 INTO @col_exists FROM information_schema.columns 
WHERE table_schema = @dbname AND table_name = @tablename AND column_name = 'fuel_litres';
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE device_states ADD COLUMN fuel_litres DECIMAL(6,2) DEFAULT NULL COMMENT "Топливо (литры)"', 
    'SELECT "fuel_litres column exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- motohrs
SET @col_exists = 0;
SELECT 1 INTO @col_exists FROM information_schema.columns 
WHERE table_schema = @dbname AND table_name = @tablename AND column_name = 'motohrs';
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE device_states ADD COLUMN motohrs INT DEFAULT NULL COMMENT "Моточасы"', 
    'SELECT "motohrs column exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Добавить колонки для сессии в user_devices
SET @col_exists = 0;
SELECT 1 INTO @col_exists FROM information_schema.columns 
WHERE table_schema = @dbname AND table_name = 'user_devices' AND column_name = 'slnet_token';
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE user_devices ADD COLUMN slnet_token VARCHAR(255)', 
    'SELECT "slnet_token column exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = 0;
SELECT 1 INTO @col_exists FROM information_schema.columns 
WHERE table_schema = @dbname AND table_name = 'user_devices' AND column_name = 'starline_user_id';
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE user_devices ADD COLUMN starline_user_id VARCHAR(64)', 
    'SELECT "starline_user_id column exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Таблица типов обслуживания
CREATE TABLE IF NOT EXISTS service_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    default_interval_km INT COMMENT 'Интервал по пробегу',
    default_interval_hours INT COMMENT 'Интервал по моточасам'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица записей ТО
CREATE TABLE IF NOT EXISTS maintenance_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id BIGINT NOT NULL COMMENT 'StarLine device ID',
    service_type VARCHAR(100) NOT NULL COMMENT 'Тип обслуживания',
    description TEXT COMMENT 'Описание работ',
    mileage_at_service INT COMMENT 'Пробег при ТО',
    motohrs_at_service INT COMMENT 'Моточасы при ТО',
    service_date DATE NOT NULL COMMENT 'Дата ТО',
    next_service_mileage INT COMMENT 'Следующее ТО через км',
    next_service_motohrs INT COMMENT 'Следующее ТО через моточасы',
    cost DECIMAL(10,2) COMMENT 'Стоимость',
    notes TEXT COMMENT 'Заметки',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_date (device_id, service_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Стандартные типы ТО
INSERT IGNORE INTO service_types (name, default_interval_km, default_interval_hours) VALUES
('Замена масла двигателя', 10000, 250),
('Замена масла АКПП', 60000, NULL),
('Замена воздушного фильтра', 15000, NULL),
('Замена салонного фильтра', 15000, NULL),
('Замена топливного фильтра', 30000, NULL),
('Замена свечей зажигания', 30000, NULL),
('Замена ремня ГРМ', 60000, NULL),
('Замена цепи ГРМ', 100000, NULL),
('Замена тормозных колодок передних', 40000, NULL),
('Замена тормозных колодок задних', 60000, NULL),
('Замена тормозных дисков', 80000, NULL),
('Замена тормозной жидкости', 40000, NULL),
('Замена антифриза', 60000, NULL),
('Замена масла в мостах', 40000, NULL),
('Замена масла в раздатке', 40000, NULL),
('Замена масла в редукторе', 40000, NULL),
('Замена гидравлической жидкости ГУР', 60000, NULL),
('Техосмотр', NULL, NULL),
('Диагностика', NULL, NULL),
('Другое', NULL, NULL);

EOSQL

echo "Database schema updated."

echo ""
echo "Step 3: Updating containers..."

# Остановить контейнеры
$COMPOSE_CMD down

# Обновить код
git pull || echo "Not a git repo, manual update required"

# Пересобрать и запустить
$COMPOSE_CMD build --no-cache
$COMPOSE_CMD up -d

echo ""
echo "=== Migration Complete! ==="
echo ""
echo "New features available:"
echo "  - Mileage tracking"
echo "  - Fuel level monitoring"  
echo "  - Engine hours tracking"
echo "  - Maintenance records"
echo "  - Session caching (no captcha)"
echo ""
echo "Open http://YOUR_IP:3000 to continue"
