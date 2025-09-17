import os
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import time

# ================= CONFIG =================
BOT_TOKEN = "8059024060:AAHq7F5WPKGLeo6a3GyHTH32oeXySe1D2WI"
RENDER_URL = "https://smm-4.onrender.com"  # Render URL
ADMIN_ID = 6733100026
MIN_WITHDRAW = 100_000

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Foydalanuvchi ma'lumotlari
users = {}  # {user_id: {"balance":0, "spins":0, "referrals":0, "withdraws":[]}}
referrals = {}  # {referrer_id: count}
# =========================================

def get_user_data(user_id):
    if user_id not in users:
        users[user_id] = {"balance":0, "spins":0, "referrals":0, "withdraws":[]}
    return users[user_id]

def spin_baraban():
    return random.randint(1000, 10000)

def generate_main_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("🎰 Spin", callback_data="spin"),
        InlineKeyboardButton("💰 Hisob", callback_data="balance"),
        InlineKeyboardButton("👥 Referral", callback_data="referral"),
        InlineKeyboardButton("💳 Pul yechish", callback_data="withdraw")
    )
    return markup

# ================= FLASK WEBHOOK =================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.stream.read().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

# ================= HANDLERLAR =================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    get_user_data(user_id)
    
    # Referral
    ref = message.text.split()[1:]
    if ref:
        try:
            ref_id = int(ref[0])
            if ref_id != user_id:
                referrals.setdefault(ref_id, 0)
                referrals[ref_id] += 1
                users[ref_id]["spins"] += 1
                bot.send_message(ref_id, "🎉 Sizning referalingiz qo'shildi! 1 ta spin imkoniyatingiz oshdi.")
        except:
            pass

    bot.send_message(user_id, "Salom! Botga xush kelibsiz.", reply_markup=generate_main_keyboard(user_id))

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id
    data = call.data
    user_data = get_user_data(user_id)
    
    if data == "spin":
        if user_data["spins"] > 0:
            bot.answer_callback_query(call.id)
            # Baraban animatsiyasi
            message = bot.send_message(user_id, "🎰 Baraban aylanmoqda...")
            symbols = ["🍒", "🍋", "🔔", "⭐", "💎"]
            for _ in range(10):
                display = f"{random.choice(symbols)} | {random.choice(symbols)} | {random.choice(symbols)}"
                bot.edit_message_text(display, user_id, message.message_id)
                time.sleep(0.3)
            earned = spin_baraban()
            user_data["balance"] += earned
            user_data["spins"] -= 1
            bot.edit_message_text(f"🎉 Tabrik! Siz {earned} so'm yutdingiz!\n💰 Balans: {user_data['balance']} so'm\nSpins: {user_data['spins']}", user_id, message.message_id, reply_markup=generate_main_keyboard(user_id))
        else:
            bot.answer_callback_query(call.id, "⚠️ Sizda spin yo'q!")
    
    elif data == "balance":
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, f"💰 Sizning balansingiz: {user_data['balance']} so'm\nSpinlar: {user_data['spins']}")
    
    elif data == "referral":
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, f"👥 Sizning referral link: https://t.me/YourBotUsername?start={user_id}")
    
    elif data == "withdraw":
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, "💳 Pul yechish uchun karta raqamingizni kiriting:")
        bot.register_next_step_handler_by_chat_id(user_id, card_number_handler)

def card_number_handler(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    card = message.text
    bot.send_message(user_id, f"✅ Kartangiz qabul qilindi: {card}\nEndi nech so'm yechib olmoqchisiz?")
    bot.register_next_step_handler_by_chat_id(user_id, withdraw_amount_handler, card)

def withdraw_amount_handler(message, card):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    try:
        amount = int(message.text)
    except:
        bot.send_message(user_id, "❌ Iltimos raqam kiriting.")
        return
    if amount < MIN_WITHDRAW:
        bot.send_message(user_id, f"❌ Minimal yechish: {MIN_WITHDRAW} so'm")
    elif amount > user_data["balance"]:
        bot.send_message(user_id, f"❌ Sizning balansingiz yetarli emas: {user_data['balance']} so'm")
    else:
        user_data["balance"] -= amount
        user_data["withdraws"].append({"amount":amount, "card":card, "status":"Pending"})
        bot.send_message(user_id, f"✅ {amount} so'm yechildi.\n48 soat ichida hisobingizga tushadi.\nQolgan balans: {user_data['balance']} so'm")

# ================= MAIN =================
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
