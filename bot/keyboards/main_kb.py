from telegram import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo
)


def main_keyboard(miniapp_url: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("💪 Тренировка", web_app=WebAppInfo(url=f"{miniapp_url}/"))],
            [
                KeyboardButton("📊 Прогресс", web_app=WebAppInfo(url=f"{miniapp_url}/progress")),
                KeyboardButton("🥗 Питание", web_app=WebAppInfo(url=f"{miniapp_url}/nutrition")),
            ],
            [
                KeyboardButton("🤖 AI-тренер", web_app=WebAppInfo(url=f"{miniapp_url}/chat")),
                KeyboardButton("⚙️ Настройки", web_app=WebAppInfo(url=f"{miniapp_url}/settings")),
            ],
        ],
        resize_keyboard=True,
    )


def open_app_button(path: str = "/") -> InlineKeyboardMarkup:
    from app.core.config import settings
    base_url = settings.telegram_webhook_url.replace("/webhook/telegram", "")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📱 Открыть приложение",
            web_app=WebAppInfo(url=f"{base_url}{path}")
        )],
    ])
