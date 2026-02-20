"""Onboarding callback handler (legacy — onboarding is now done via Mini App)."""
from telegram import Update
from telegram.ext import ContextTypes


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ob: callback queries — no-op, onboarding is in the Mini App."""
    query = update.callback_query
    await query.answer()
