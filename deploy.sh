#!/bin/bash
# ============================================================
# deploy.sh — запускается НА СЕРВЕРЕ
# Поднимает Docker контейнеры и регистрирует webhook
# ============================================================
set -e

cd /root/ai-trainer

echo "============================================"
echo "  Деплой на сервере"
echo "============================================"

# 1. Остановить старые контейнеры если запущены
echo ""
echo "🛑 [1/4] Останавливаю старые контейнеры..."
docker compose -f docker/docker-compose.prod.yml down --remove-orphans 2>/dev/null || true

# 2. Собрать и запустить
echo ""
echo "🐳 [2/4] Собираю Docker образы и запускаю сервисы..."
docker compose -f docker/docker-compose.prod.yml up -d --build

# 3. Ждём пока сервисы запустятся
echo ""
echo "⏳ [3/4] Жду запуска сервисов..."
sleep 10

# Проверяем что бэкенд отвечает
for i in {1..12}; do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend запущен!"
    break
  fi
  echo "   Ожидание... ($i/12)"
  sleep 5
done

# 4. Регистрируем Telegram webhook
echo ""
echo "🤖 [4/4] Регистрирую Telegram webhook..."
source .env
RESULT=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://constcoachai.ru/webhook/telegram&secret_token=${TELEGRAM_WEBHOOK_SECRET}")
echo "   Ответ Telegram: $RESULT"

echo ""
echo "============================================"
echo "  ✅ Деплой завершён!"
echo "  🌐 Сайт:  https://constcoachai.ru"
echo "  🤖 Бот:   @RusscoachAI_bot"
echo "============================================"
echo ""
echo "Статус контейнеров:"
docker compose -f docker/docker-compose.prod.yml ps
