#!/bin/bash
# ============================================================
# upload.sh — запускается на ТВОЁМ MAC
# Собирает фронтенд и заливает всё на сервер
# Использование: bash upload.sh
# ============================================================
set -e

SERVER="root@85.239.49.32"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  Деплой на constcoachai.ru"
echo "============================================"

# 1. Собрать фронтенд
echo ""
echo "🔨 [1/4] Собираю фронтенд..."
cd "$PROJECT_DIR/miniapp"
npm run build
cd "$PROJECT_DIR"

# 2. Копировать dist в backend для включения в Docker образ
echo ""
echo "📁 [2/4] Копирую сборку фронтенда в backend..."
rm -rf "$PROJECT_DIR/backend/static_miniapp"
cp -r "$PROJECT_DIR/miniapp/dist" "$PROJECT_DIR/backend/static_miniapp"

# 3. Залить проект на сервер
echo ""
echo "📤 [3/4] Загружаю файлы на сервер (85.239.49.32)..."
rsync -avz --progress \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.git' \
  --exclude '.env' \
  --exclude 'miniapp/dist' \
  "$PROJECT_DIR/" "$SERVER:/root/ai-trainer/"

# Отдельно загружаем production .env как .env
echo ""
echo "🔑 Загружаю production .env..."
scp "$PROJECT_DIR/.env.production" "$SERVER:/root/ai-trainer/.env"

# 4. Запустить деплой на сервере
echo ""
echo "🚀 [4/4] Запускаю деплой на сервере..."
ssh "$SERVER" "cd /root/ai-trainer && bash deploy.sh"

echo ""
echo "============================================"
echo "  ✅ Готово! Сайт: https://constcoachai.ru"
echo "============================================"
