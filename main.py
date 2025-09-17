import os
import random
import json
from datetime import datetime
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- ENV VARIABLES ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Render URL: https://your-app.onrender.com

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- DATABASE SIMULATION ---
if not os.path.exists("users.json"):
    with open("users.json", "w") as f:
        json.dump({}, f)

if not os.path.exists("channels.json"):
    with open("channels.json", "w") as f:
        json.dump([], f)

# --- HELPERS ---
def load_users():
    with open("users.json", "r") as f:
        return json.load(f)

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f)

def load_channels():
    with open("channels.json", "r") as f:
        return json.load(f)

def save_channels(channels):
    with open("channels.json", "w") as f:
        json.dump(channels, f)

def check_daily_bonus(user):
    today = datetime.now().date()
    last_bonus = datetime.fromisoformat(user.get("last_bonus", "2000-01-01"))
    return last_bonus.date() < today

def give_daily_bonus(user):
    user["last_bonus"] = datetime.now().isoformat()
    user["spins"] = user.get("spins", 0) + 1

def check_channels_subscription(user_id):
    channels = load_channels()
    if not channels:
        return True
    for ch in channels:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# --- HANDLERS ---
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "", 200

@bot.message_handler(commands=["start"])
def start(message):
    users = load_users()
    user_id = str(message.from_user.id)

    # Referal link
    if len(message.text.split()) > 1:
        ref_id = message.text.split()[1]
        if ref_id != user_id:
            ref_user = users.get(ref_id)
            if ref_user:
                ref_user["spins"] = ref_user.get("spins", 0) + 1
                bot.send_message(ref_id, "✅ Sizning referalingiz orqali foydalanuvchi qo‘shildi! 1 ta spin qo‘shildi.")

    if user_id not in users:
        users[user_id] = {"spins": 1, "balance": 0, "last_bonus": "2000-01-01"}
    save_users(users)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎰 Spin qilish", callback_data="spin"))
    kb.add(InlineKeyboardButton("💰 Hisobim", callback_data="balance"))
    kb.add(InlineKeyboardButton("👥 Referal link", callback_data="ref"))
    kb.add(InlineKeyboardButton("🎁 Kunlik bonus", callback_data="daily_bonus"))
    kb.add(InlineKeyboardButton("💳 Pul yechish", callback_data="withdraw"))
    bot.send_message(message.chat.id, "Salom! 🎰 Spin botga xush kelibsiz!", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    users = load_users()
    user_id = str(call.from_user.id)
    user = users[user_id]

    if call.data == "spin":
        if user.get("spins", 0) <= 0:
            bot.answer_callback_query(call.id, "❌ Sizda spin yo'q")
            return
        if not check_channels_subscription(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Spin ishlashi uchun barcha kanalga obuna bo‘ling!")
            return

        try:
            bot.send_animation(call.message.chat.id, "https://i.gifer.com/7efs.gif")
        except:
            pass

        amounts = [1000,2000,3000,4000,5000,6000,7000,8000,9000,10000]
        prize = random.choice(amounts)
        user["balance"] += prize
        user["spins"] -= 1
        save_users(users)
        bot.send_message(call.message.chat.id, f"🎉 Siz {prize} so'm yutdingiz!")

    elif call.data == "balance":
        bal = user.get("balance", 0)
        spins = user.get("spins", 0)
        bot.send_message(call.message.chat.id, f"💰 Balans: {bal} so'm\n🎰 Spins: {spins}")

    elif call.data == "ref":
        bot.send_message(call.message.chat.id, f"Sizning referal link: https://t.me/Spinomad_bot?start={user_id}")

    elif call.data == "daily_bonus":
        if check_daily_bonus(user):
            give_daily_bonus(user)
            save_users(users)
            bot.answer_callback_query(call.id, "🎁 Kunlik bonus oldingiz! 1 spin qo‘shildi.")
        else:
            bot.answer_callback_query(call.id, "❌ Bugun bonus olgansiz, ertaga qayta urinib ko‘ring.")

    elif call.data == "withdraw":
        bot.send_message(call.message.chat.id, "Pul yechish uchun: /withdraw <karta> <miqdor>")

# --- PUL YECHISH ---
@bot.message_handler(commands=["withdraw"])
def withdraw(message):
    users = load_users()
    user_id = str(message.from_user.id)
    user = users[user_id]
    parts = message.text.split()
    if len(parts) != 3:
        bot.send_message(message.chat.id, "❌ Foydalanish: /withdraw <karta> <miqdor>")
        return
    card = parts[1]
    amount = int(parts[2])
    if amount < 100000:
        bot.send_message(message.chat.id, "❌ Minimal pul yechish: 100,000 so'm")
        return
    if amount > user.get("balance", 0):
        bot.send_message(message.chat.id, "❌ Balansingiz yetarli emas")
        return
    user["balance"] -= amount
    save_users(users)
    bot.send_message(message.chat.id, f"✅ {amount} so'm yechildi. 48 soat ichida {card} raqamiga tushadi.")

# --- ADMIN PANEL ---
@bot.message_handler(commands=["add_channel"])
def add_channel(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Foydalanish: /add_channel @channelusername")
        return
    channels = load_channels()
    if parts[1] not in channels:
        channels.append(parts[1])
        save_channels(channels)
        bot.reply_to(message, f"✅ Kanal qo‘shildi: {parts[1]}")

@bot.message_handler(commands=["remove_channel"])
def remove_channel(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    channels = load_channels()
    if parts[1] in channels:
        channels.remove(parts[1])
        save_channels(channels)
        bot.reply_to(message, f"❌ Kanal o‘chirildi: {parts[1]}")

@bot.message_handler(commands=["stats"])
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    users = load_users()
    bot.send_message(message.chat.id, f"👥 Umumiy foydalanuvchilar: {len(users)}")

# --- WEBHOOK ---
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
