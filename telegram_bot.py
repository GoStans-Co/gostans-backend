import os
import django
import random
import logging
import re
from decouple import config
import asyncio


from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gostans.settings')
django.setup()

from django.core.cache import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = config("TELEGRAM_BOT_TOKEN")


def get_welcome_card(name="User"):
    return (
        f"🇺🇿\n"
        f"Salom {name} 👋\n"
        f"@GoStans'ning rasmiy botiga xush kelibsiz\n\n"
        f"⬇️ Kontaktingizni yuboring (tugmani bosib)\n\n"
        f"🇺🇸\n"
        f"Hi {name} 👋\n"
        f"Welcome to @GoStans's official bot\n\n"
        f"⬇️ Send your contact (by clicking the button)"
    )

def escape_markdown_v2(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "User"
    button = KeyboardButton("📱 Share Phone Number | 📱 Telefon raqamni ulashish", request_contact=True)
    markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(get_welcome_card(name), reply_markup=markup)


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("⚠️ Iltimos, tugmani bosib telefon raqamingizni yuboring / Please press the button to share your phone number.")
        return

    phone = contact.phone_number
    user = update.effective_user
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    user_id = user.id
    email = f"telegram@{full_name.replace(' ', '').lower()}.com"  # placeholder email

    otp = str(random.randint(100000, 999999))

    cache.set(f"telegram_otp_{phone}", otp, timeout=300)
    cache.set(f"telegram_login_{otp}", {
        "user_id": user_id,
        "phone": phone,
        "name": full_name,
        "email": email,
    }, timeout=300)

    logger.info(f"📦 OTP stored for phone {phone}: {otp}")
    login_url = f"https://gostans.com/login?otp={otp}"
    otp_escaped = escape_markdown_v2(otp)
    login_url_escaped = escape_markdown_v2(login_url)
    login_display = escape_markdown_v2("gostans.com/login")

    otp_message = (
        f"🔒 Code: `{otp_escaped}`\n"
        f"🔗 Click and Login: [{login_display}]({login_url_escaped})"
    )

    await update.message.reply_text(otp_message, parse_mode="MarkdownV2")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Amal bekor qilindi / Operation cancelled.")
    return ConversationHandler.END


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(CommandHandler("cancel", cancel))

    logger.info("✅ Bot is running...")
    logger.info("🚀 Bot started successfully and is polling Telegram...")

    async def run():
        # 🚨 This line clears any existing webhook and drops pending updates
        await app.bot.delete_webhook(drop_pending_updates=True)
        await app.run_polling()

    asyncio.run(run())

