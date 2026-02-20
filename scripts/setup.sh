#!/bin/bash
# ============================================
# AI Personal Trainer — First-time setup script
# ============================================

set -e

echo "🚀 Setting up AI Personal Trainer..."

# 1. Copy env file
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✅ Created .env from .env.example — FILL IT IN before running!"
fi

# 2. Start infrastructure
echo "📦 Starting PostgreSQL and Redis..."
cd docker && docker-compose up -d postgres redis
cd ..

# 3. Wait for postgres
echo "⏳ Waiting for PostgreSQL..."
until docker exec ai_trainer_db pg_isready -U postgres; do
  sleep 1
done

# 4. Backend setup
echo "🐍 Setting up Python backend..."
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 5. Run migrations
echo "🗄️ Running database migrations..."
alembic upgrade head

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your keys (TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, etc.)"
echo "2. Run backend:  cd backend && uvicorn app.main:app --reload"
echo "3. Run miniapp:  cd miniapp && npm install && npm run dev"
echo "4. Setup webhook: python scripts/set_webhook.py"
