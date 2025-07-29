import os
import django
import random
import logging
import re
from decouple import config

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gostans.settings')
django.setup()

from django.core.cache import cache

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
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
    logger.info(f"User {name} started the bot.")

    button = KeyboardButton("📱 Share Phone Number | 📱 Telefon raqamni ulashish", request_contact=True)
    markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(get_welcome_card(name), reply_markup=markup)


async def resend_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    # Try to find the last phone number used by this user
    phone = cache.get(f"user_phone_{user_id}")
        
    if not phone:
        await update.message.reply_text("❌ Phone number not found. Please press /start and share your phone number.")
        return

    # Generate new OTP
    otp = str(random.randint(100000, 999999))

    cache.set(f"telegram_otp_{phone}", otp, timeout=300)
    cache.set(f"telegram_login_{otp}", {
        "user_id": user_id,
        "phone": phone,
        "name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
        "email": f"telegram@{user.username or user_id}.com",
    }, timeout=300)

    login_url = f"https://gostans.com/login?otp={otp}"
    otp_escaped = escape_markdown_v2(otp)
    login_url_escaped = escape_markdown_v2(login_url)
    login_display = escape_markdown_v2("gostans.com/login")

    otp_message = (
        f"🔄 Yangi kod: `{otp_escaped}`\n"
        f"🔗 Kirish: [{login_display}]({login_url_escaped})"
    )

    logger.info(f"Resent OTP {otp} to user_id={user_id} for phone={phone}")
    await update.message.reply_text(otp_message, parse_mode="MarkdownV2")


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        logger.warning("No contact received.")
        await update.message.reply_text("⚠️ Iltimos, tugmani bosib telefon raqamingizni yuboring.")
        return

    phone = contact.phone_number
    user = update.effective_user
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    user_id = user.id
    email = f"telegram@{full_name.replace(' ', '').lower()}.com"
    
    otp = str(random.randint(100000, 999999))

    cache.set(f"user_phone_{user_id}", phone, timeout=300)
    cache.set(f"telegram_otp_{phone}", otp, timeout=300)
    cache.set(f"telegram_login_{otp}", {
        "user_id": user_id,
        "phone": phone,
        "name": full_name,
        "email": email,
    }, timeout=300)

    logger.info(f"OTP {otp} generated and cached for {phone} (user_id={user_id})")
     # Immediately get cache to confirm
    cached_otp = cache.get(f"telegram_otp_{phone}")
    cached_login_data = cache.get(f"telegram_login_{otp}")

    logger.info(f"Cached OTP for {phone}: {cached_otp}")
    logger.info(f"Cached login data for OTP {otp}: {cached_login_data}")
    
    login_url = f"https://gostans.com/login?otp={otp}"
    otp_escaped = escape_markdown_v2(otp)
    login_url_escaped = escape_markdown_v2(login_url)
    login_display = escape_markdown_v2("gostans.com/login")

    otp_message = (
        f"🔒 Code: `{otp_escaped}`\n"
        f"🔗 Click and Login: [{login_display}]({login_url_escaped})"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Resend Code", callback_data="resend_otp")]
    ])

    await update.message.reply_text(otp_message, parse_mode="MarkdownV2",reply_markup=keyboard)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Amal bekor qilindi / Operation cancelled.")
    logger.info("User cancelled the operation.")


async def handle_resend_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback

    user = query.from_user
    user_id = user.id

    # Search for the phone number in cache
    phone = cache.get(f"user_phone_{user_id}")


    if not phone:
        await query.edit_message_text("❌ Phone number not found. Please press /start and share your phone number.")
        return

    otp = str(random.randint(100000, 999999))

    cache.set(f"telegram_otp_{phone}", otp, timeout=300)
    cache.set(f"telegram_login_{otp}", {
        "user_id": user_id,
        "phone": phone,
        "name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
        "email": f"telegram@{user.username or user_id}.com",
    }, timeout=300)

    login_url = f"https://gostans.com/login?otp={otp}"
    otp_escaped = escape_markdown_v2(otp)
    login_url_escaped = escape_markdown_v2(login_url)
    login_display = escape_markdown_v2("gostans.com/login")

    otp_message = (
        f"🔄 Yangi kod: `{otp_escaped}`\n"
        f"🔗 Kirish: [{login_display}]({login_url_escaped})"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Resend Code", callback_data="resend_otp")]
    ])

    await query.edit_message_text(text=otp_message, parse_mode="MarkdownV2", reply_markup=keyboard)


def main():
    logger.info("🚀 Starting Telegram bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(CommandHandler("resend", resend_otp))
    app.add_handler(CommandHandler("cancel", cancel))   
    app.add_handler(CallbackQueryHandler(handle_resend_callback, pattern="^resend_otp$"))

    logger.info("✅ Bot is now polling Telegram for updates.")
    app.run_polling()


if __name__ == "__main__":
    main()
