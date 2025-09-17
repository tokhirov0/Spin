import os
from flask import Flask, request
import telebot
from telebot import types
from dotenv import load_dotenv

# --- Config ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL = os.getenv("CHANNEL")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- Ma'lumotlar bazasi oddiy dictionary (test uchun) ---
users = {}
balances = {}

# --- Webhook sozlash ---
bot.remove_webhook()
bot.set_webhook(url=f"{RENDER_URL}{BOT_TOKEN}")

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def get_message():
    json_str = request.stream.read().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def index():
    return "Bot ishlayapti ✅", 200


# --- Kanalga obuna tekshirish ---
def check_subscription(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except:
        return False


# --- Start ---
@bot.message_handler(commands=["start"])
def start(message):
    if not check_subscription(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Obuna bo‘lish", url=f"https://t.me/{CHANNEL.replace('@','')}"))
        bot.send_message(message.chat.id, "❌ Botdan foydalanish uchun kanalga obuna bo‘ling!", reply_markup=markup)
        return

    users[message.chat.id] = message.from_user.username
    balances[message.chat.id] = balances.get(message.chat.id, 0)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎰 Spin aylantirish", "💰 Balansim")
    markup.add("💸 Pul yechish", "👑 Admin panel")

    bot.send_message(message.chat.id, "Salom! 👋 Botga xush kelibsiz.", reply_markup=markup)


# --- Spin aylantirish ---
@bot.message_handler(func=lambda msg: msg.text == "🎰 Spin aylantirish")
def spin_game(message):
    if not check_subscription(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Avval kanalga obuna bo‘ling!")
        return

    with open("spin.gif", "rb") as gif:
        bot.send_animation(message.chat.id, gif, caption="🎰 Spin aylanmoqda...")

    # oddiy bonus qo‘shamiz
    balances[message.chat.id] = balances.get(message.chat.id, 0) + 5000
    bot.send_message(message.chat.id, f"✅ Sizga 5000 so‘m qo‘shildi!\n💰 Balans: {balances[message.chat.id]} so‘m")


# --- Balans ---
@bot.message_handler(func=lambda msg: msg.text == "💰 Balansim")
def balance(message):
    bal = balances.get(message.chat.id, 0)
    bot.send_message(message.chat.id, f"💰 Sizning balansingiz: {bal} so‘m")


# --- Pul yechish ---
@bot.message_handler(func=lambda msg: msg.text == "💸 Pul yechish")
def withdraw(message):
    bot.send_message(message.chat.id, "💵 Yechib olish summasini kiriting (minimal 100 000 so‘m):")
    bot.register_next_step_handler(message, process_withdraw)


def process_withdraw(message):
    try:
        amount = int(message.text)
    except:
        bot.send_message(message.chat.id, "❌ Iltimos, faqat raqam kiriting!")
        return

    if amount < 100000:
        bot.send_message(message.chat.id, "❌ Minimal summa 100 000 so‘m!")
        return

    bal = balances.get(message.chat.id, 0)
    if amount > bal:
        bot.send_message(message.chat.id, f"❌ Sizda yetarli mablag‘ yo‘q!\n💰 Balans: {bal} so‘m")
        return

    balances[message.chat.id] -= amount
    bot.send_message(message.chat.id, f"✅ Pul yechish so‘rovi yuborildi: {amount} so‘m")

    # Admin xabari
    bot.send_message(ADMIN_ID, f"💸 Yangi pul yechish so‘rovi!\n👤 Foydalanuvchi: @{users.get(message.chat.id)}\n💰 Miqdor: {amount} so‘m")


# --- Admin panel ---
@bot.message_handler(func=lambda msg: msg.text == "👑 Admin panel")
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Siz admin emassiz!")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 Statistika", "📢 Kanalni o‘zgartirish")
    markup.add("🔙 Orqaga")

    bot.send_message(message.chat.id, "👑 Admin panelga xush kelibsiz!", reply_markup=markup)


@bot.message_handler(func=lambda msg: msg.text == "📊 Statistika")
def stats(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, f"👥 Umumiy foydalanuvchilar: {len(users)}")


@bot.message_handler(func=lambda msg: msg.text == "📢 Kanalni o‘zgartirish")
def change_channel(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "✍️ Yangi kanal username kiriting (masalan, @yangi_kanal):")
        bot.register_next_step_handler(message, set_new_channel)


def set_new_channel(message):
    global CHANNEL
    if message.from_user.id == ADMIN_ID:
        CHANNEL = message.text
        bot.send_message(message.chat.id, f"✅ Kanal yangilandi: {CHANNEL}")
