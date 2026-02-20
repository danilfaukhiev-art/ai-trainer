# AI Personal Trainer

Telegram Bot + Mini App с AI-персональным тренером.

## Структура проекта

```
project/
├── backend/          # FastAPI + Python
│   ├── app/
│   │   ├── api/routes/     # Эндпоинты
│   │   ├── core/           # Config, Auth
│   │   ├── db/             # PostgreSQL, Redis
│   │   ├── models/         # SQLAlchemy модели
│   │   ├── services/       # Бизнес-логика, AI, Storage
│   │   └── workers/        # Async video worker
│   └── migrations/         # Alembic миграции
├── bot/              # Telegram Bot handlers
├── miniapp/          # React + Vite Mini App
├── docker/           # Docker Compose
└── scripts/          # Setup, seeding, webhook
```

## Быстрый старт

### 1. Инфраструктура
```bash
cp .env.example .env
# Заполни .env: TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, etc.

cd docker && docker-compose up -d postgres redis
```

### 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python ../scripts/seed_exercises.py
uvicorn app.main:app --reload
```

### 3. Mini App
```bash
cd miniapp
npm install
npm run dev
```

### 4. Webhook (production)
```bash
python scripts/set_webhook.py
```

## ENV переменные

| Переменная | Описание |
|-----------|---------|
| `TELEGRAM_BOT_TOKEN` | Токен от @BotFather |
| `TELEGRAM_WEBHOOK_URL` | https://your-domain.com/webhook/telegram |
| `OPENAI_API_KEY` | OpenAI API key |
| `DATABASE_URL` | PostgreSQL async URL |
| `REDIS_URL` | Redis URL |
| `S3_*` | S3 credentials для storage |

## API Endpoints

```
POST /api/auth/telegram          Auth через Telegram initData
GET  /api/onboarding/status      Статус онбординга
POST /api/onboarding/step        Следующий шаг онбординга
GET  /api/workouts/today         Тренировка на сегодня
POST /api/workouts/{id}/complete Завершить тренировку
GET  /api/progress               История прогресса
POST /api/ai/chat                Чат с AI-тренером
```
