#!/bin/bash
# ============================================================
# server-setup.sh — запускается НА СЕРВЕРЕ один раз
# Устанавливает Docker и все зависимости
# Использование: bash server-setup.sh
# ============================================================
set -e

echo "============================================"
echo "  Настройка сервера для constcoachai.ru"
echo "============================================"

# 1. Обновление системы
echo ""
echo "🔄 [1/3] Обновляю систему..."
apt-get update -y && apt-get upgrade -y
apt-get install -y ca-certificates curl rsync ufw

# 2. Установка Docker
echo ""
echo "🐳 [2/3] Устанавливаю Docker..."
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Проверка
docker --version
docker compose version

# 3. Настройка файервола
echo ""
echo "🔒 [3/3] Настраиваю файервол..."
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable

echo ""
echo "============================================"
echo "  ✅ Сервер готов!"
echo ""
echo "  Следующий шаг — запусти на своём Mac:"
echo "  bash upload.sh"
echo "============================================"
