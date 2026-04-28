import os
import django
import telebot
from telebot import types
import os
from dotenv import load_dotenv
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from django.core.signing import Signer
from my_ap_1.models import TelegramProfile

BOT_TOKEN = "8520448611:AAHoMVJirzATOaYzWKPkuDygwjy7vA8HRlw"
SITE_URL = "https://barakaev.uz"

bot = telebot.TeleBot(BOT_TOKEN)
signer = Signer()


@bot.message_handler(commands=["start"])
def start(message):
    btn = types.KeyboardButton("📱 Telefon raqam yuborish", request_contact=True)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(btn)

    bot.send_message(
        message.chat.id,
        "Assalomu alaykum! Baraka Marketga tezkor ro‘yxatdan o‘tish uchun telefon raqamingizni yuboring.",
        reply_markup=markup
    )


@bot.message_handler(content_types=["contact"])
def contact_handler(message):
    telegram_id = message.from_user.id
    phone = message.contact.phone_number
    full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()

    username = f"tg_{telegram_id}"

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "first_name": message.from_user.first_name or "",
            "last_name": message.from_user.last_name or "",
        }
    )

    TelegramProfile.objects.update_or_create(
        telegram_id=telegram_id,
        defaults={
            "user": user,
            "phone": phone,
            "full_name": full_name,
        }
    )

    token = signer.sign(str(telegram_id))
    login_url = f"{SITE_URL}/telegram-login/{token}/"

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚀 Baraka Marketga kirish", url=login_url))

    bot.send_message(
        message.chat.id,
        "✅ Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz!\n\nSaytga kirish uchun tugmani bosing:",
        reply_markup=markup
    )


print("Telegram bot ishga tushdi...")
bot.infinity_polling()


load_dotenv()

BOT_TOKEN = os.getenv("8520448611:AAHoMVJirzATOaYzWKPkuDygwjy7vA8HRlw")
SITE_URL = os.getenv("https://barakaev.uz")