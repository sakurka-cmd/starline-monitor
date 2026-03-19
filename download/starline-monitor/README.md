# StarLine Monitor - Инструкция по установке

## Вариант 1: Только обновление Worker (рекомендуется)

Если у вас уже работает Backend + Frontend, нужно только обновить Worker.

### Шаг 1: Остановите текущий Worker

```bash
# Если Worker запущен как сервис
sudo systemctl stop starline-collector

# Или если запущен вручную - просто Ctrl+C
```

### Шаг 2: Скачайте исправленный Worker

Скопируйте файл `worker_fixed.py` на сервер:

```bash
# На сервере
cd ~/starline-app/worker/
# Сохраните старую версию
mv worker.py worker_old.py
# Загрузите новую версию (скопируйте содержимое)
nano worker.py
# Вставьте содержимое worker_fixed.py и сохраните (Ctrl+O, Enter, Ctrl+X)
```

### Шаг 3: Основные исправления в коде

Если хотите вручную исправить свой существующий код, вот ключевые изменения:

#### 1. Cookie имя (самое важное!)

**БЫЛО (неправильно):**
```python
if cookie.name == "slnet_token":
    slnet_token = cookie.value
```

**СТАЛО (правильно):**
```python
if cookie.name == "slnet":  # ИСПРАВЛЕНО!
    slnet_token = cookie.value
```

#### 2. Парсинг устройств

**БЫЛО:**
```python
self.devices = result.get("desc", [])
```

**СТАЛО:**
```python
# Поддерживаем разные форматы ответа
devices = []
if "devices" in result:
    devices = result["devices"]
elif "desc" in result:
    if isinstance(result["desc"], list):
        devices = result["desc"]
    elif isinstance(result["desc"], dict) and "devices" in result["desc"]:
        devices = result["desc"]["devices"]

self.devices = devices
```

#### 3. Детальное логирование

Добавьте логирование cookies:
```python
for cookie in response.cookies:
    self.logger.info(f"Cookie: {cookie.name} = {cookie.value[:20]}...")
```

### Шаг 4: Запустите тест

```bash
cd ~/starline-app/worker/
source ~/starline-app/backend/venv/bin/activate
python worker.py -c config.json
```

Вы должны увидеть:
```
[Шаг 1] OK - код: ...
[Шаг 2] OK - токен: ...
[Шаг 3] OK - user_id=...
[Шаг 4] OK - slnet: ...
[Шаг 5] Найдено устройств: X
  Устройство 1: Название (ID: ...)
```

---

## Вариант 2: Полная установка новой системы

Если хотите установить новую систему мониторинга (Next.js + Prisma):

### Шаг 1: Установите Node.js и bun

```bash
curl -fsSL https://bun.sh/install | bash
source ~/.bashrc
```

### Шаг 2: Создайте проект

```bash
mkdir -p ~/starline-monitor
cd ~/starline-monitor

# Инициализация проекта
bun init
```

### Шаг 3: Установите зависимости

```bash
bun add prisma @prisma/client
bun add -D typescript @types/node
```

### Шаг 4: Настройте Prisma

```bash
bunx prisma init --datasource-provider sqlite
```

Отредактируйте `prisma/schema.prisma` (см. файл в архиве).

### Шаг 5: Примените миграции

```bash
bunx prisma migrate dev --name init
```

### Шаг 6: Скопируйте файлы

Скопируйте из архива:
- `src/app/page.tsx` - главный интерфейс
- `src/app/api/*` - API маршруты
- `src/lib/db.ts` - подключение к БД
- `src/lib/auth.ts` - авторизация

### Шаг 7: Запустите

```bash
bun run dev
```

Откройте http://ваш-ip:3000

---

## Получение StarLine API credentials

1. Зайдите на https://my.starline.ru
2. Разработчикам → API
3. Создайте новое приложение
4. Скопируйте:
   - Application ID
   - Application Secret

---

## Тестирование API вручную

Вы можете протестировать API вручную с помощью curl:

```bash
# 1. Получить код
curl "https://id.starline.ru/apiV3/application/getCode?appId=YOUR_ID&secret=MD5_OF_SECRET"

# 2. Получить токен (используйте код из шага 1)
curl "https://id.starline.ru/apiV3/application/getToken?appId=YOUR_ID&secret=MD5_OF_SECRET+CODE"

# 3. Логин (используйте токен из шага 2)
curl -X POST "https://id.starline.ru/apiV3/user/login" \
  -H "token: YOUR_APP_TOKEN" \
  -d "login=YOUR_LOGIN&pass=SHA1_OF_PASSWORD"

# 4. WebAPI авторизация (используйте user_token из шага 3)
curl -X POST "https://developer.starline.ru/json/v2/auth.slid" \
  -H "Content-Type: application/json" \
  -d '{"slid_token":"YOUR_USER_TOKEN"}' \
  -v 2>&1 | grep -i "set-cookie"

# 5. Получить устройства (используйте slnet cookie и user_id из шага 3)
curl "https://developer.starline.ru/json/v1/user/YOUR_USER_ID/devices" \
  -H "Cookie: slnet=YOUR_SLNET_TOKEN"
```

---

## Частые проблемы

### "Found 0 devices"
- Проверьте, что cookie называется `slnet` (не `slnet_token`)
- Проверьте ответ API - устройства могут быть в `result["devices"]` или `result["desc"]`
- Убедитесь, что у вас реально есть устройства в аккаунте StarLine

### CAPTCHA
- Слишком частые запросы могут вызвать CAPTCHA
- Увеличьте `poll_interval_seconds` до 300 (5 минут)

### 2FA (Двухфакторная аутентификация)
- Если включена 2FA, Worker не сможет авторизоваться автоматически
- Отключите 2FA в настройках StarLine или используйте другой аккаунт

---

## Контакты и поддержка

При возникновении проблем проверьте логи:
```bash
# Если Worker запущен как сервис
sudo journalctl -u starline-collector -f

# Если вручную - логи в stdout
python worker.py -c config.json
```
