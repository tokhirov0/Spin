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
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 5000))

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- DATABASE ---
if not os.path.exists("users.json"):
    with open("users.json", "w") as f:
        json.dump({}, f)

# --- HELPERS ---
def load_users():
    with open("users.json", "r") as f:
        return json.load(f)

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f)

def give_daily_bonus(user):
    today = datetime.now().date()
    last_bonus = datetime.fromisoformat(user.get("last_bonus", "2000-01-01"))
    if last_bonus.date() < today:
        user["spins"] = user.get("spins", 0) + 1
        user["last_bonus"] = datetime.now().isoformat()

# --- WEBHOOK ---
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "", 200

@app.route("/")
def index():
    return "Bot ishlayapti!"

# --- START ---
@bot.message_handler(commands=["start"])
def start(message):
    users = load_users()
    user_id = str(message.from_user.id)
    ref_id = None

    # Referral
    if len(message.text.split()) > 1:
        ref_id = message.text.split()[1]
        if ref_id != user_id and ref_id in users:
            users[ref_id]["spins"] = users[ref_id].get("spins", 0) + 1
            bot.send_message(ref_id, f"Sizning referalingiz {message.from_user.first_name} 1 spin imkoniyati oldi!")

    if user_id not in users:
        users[user_id] = {"spins": 1, "balance": 0, "last_bonus": "2000-01-01"}
    
    # Daily bonus
    give_daily_bonus(users[user_id])
    save_users(users)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎰 Spin qilish", callback_data="spin"))
    kb.add(InlineKeyboardButton("💰 Hisobim", callback_data="balance"))
    kb.add(InlineKeyboardButton("👥 Referal", callback_data="ref"))
    kb.add(InlineKeyboardButton("💵 Pul yechish", callback_data="withdraw"))
    
    bot.send_message(message.chat.id, "Salom! Spin botga xush kelibsiz!", reply_markup=kb)

# --- CALLBACK ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    users = load_users()
    user_id = str(call.from_user.id)
    user = users[user_id]

    if call.data == "spin":
        if user.get("spins", 0) <= 0:
            bot.answer_callback_query(call.id, "Sizda spin yo'q 😢")
            return

        user["spins"] -= 1
        save_users(users)

        # Gif baraban
        with open("baraban.gif", "rb") as f:
            bot.send_animation(call.message.chat.id, f)

        # Natija
        amounts = [1000,2000,3000,4000,5000,6000,7000,8000,9000,10000]
        prize = random.choice(amounts)
        user["balance"] = user.get("balance",0) + prize
        save_users(users)
        bot.send_message(call.message.chat.id, f"🎉 Tabrik! Siz {prize} so'm yutdingiz!")

    elif call.data == "balance":
        bal = user.get("balance", 0)
        spins = user.get("spins", 0)
        bot.send_message(call.message.chat.id, f"Sizning balans: {bal} so'm\nSpins: {spins}")

    elif call.data == "ref":
        bot.send_message(call.message.chat.id, f"Sizning referal link: https://t.me/Spinomad_bot?start={user_id}")

    elif call.data == "withdraw":
        bal = user.get("balance",0)
        if bal < 100000:
            bot.send_message(call.message.chat.id, "Minimal pul yechish: 100.000 so'm")
            return
        msg = bot.send_message(call.message.chat.id, "Karta raqamingizni kiriting:")
        bot.register_next_step_handler(msg, process_withdraw, user_id)

def process_withdraw(message, user_id):
    users = load_users()
    user = users[user_id]
    card = message.text
    msg = bot.send_message(message.chat.id, f"Nech so'm yechmoqchisiz? Balansingiz: {user['balance']} so'm")
    bot.register_next_step_handler(msg, confirm_withdraw, user_id, card)

def confirm_withdraw(message, user_id, card):
    users = load_users()
    user = users[user_id]
    try:
        amount = int(message.text)
    except:
        bot.send_message(message.chat.id, "Iltimos raqam kiriting!")
        return
    if amount > user["balance"]:
        bot.send_message(message.chat.id, "Sizning balansingiz yetarli emas!")
        return
    if amount < 100000:
        bot.send_message(message.chat.id, "Minimal pul yechish 100.000 so'm")
        return
    user["balance"] -= amount
    save_users(users)
    bot.send_message(message.chat.id, f"✅ Muvaffaqiyatli! {amount} so'm 48 soat ichida {card} ga tushadi.")

# --- ADMIN PANEL ---
@bot.message_handler(commands=["add_channel"])
def add_channel(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Foydalanish: /add_channel @channelusername")
        return

# --- SET WEBHOOK ---
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

# --- RUN ---
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=PORT)
