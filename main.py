import os
import telebot
from telebot import types
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL = os.getenv("CHANNEL")  # masalan: @mening_kanalim

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Ma'lumotlarni xotirada saqlash (oddiy misol uchun dict ishlatyapmiz)
users = {}
withdraw_requests = []
user_spins = {}

MIN_WITHDRAW = 100000

# 🔹 Start komandasi
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id

    # Kanal tekshirish
    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("✅ Obuna bo‘lish", url=f"https://t.me/{CHANNEL.replace('@','')}")
        markup.add(btn)
        bot.send_message(user_id, "Botdan foydalanish uchun kanalga obuna bo‘ling:", reply_markup=markup)
        return

    users[user_id] = {"balance": 0}
    markup = main_menu()
    bot.send_message(user_id, "Assalomu alaykum!\nBot menyusidan foydalaning 👇", reply_markup=markup)

# 🔹 Asosiy menyu
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎡 Spin", "💳 Pul yechish")
    markup.add("👤 Referal link", "ℹ️ Balans")
    return markup

# 🔹 Kanalga obuna tekshirish
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL, user_id).status
        return status in ["member", "administrator", "creator"]
    except:
        return False

# 🔹 Tugmalarni ushlash
@bot.message_handler(func=lambda message: True)
def menu_handler(message):
    user_id = message.chat.id

    if message.text == "🎡 Spin":
        play_spin(user_id)

    elif message.text == "💳 Pul yechish":
        bot.send_message(user_id, f"Yechib olmoqchi bo‘lgan summani kiriting (kamida {MIN_WITHDRAW} so‘m):")
        bot.register_next_step_handler(message, withdraw_request)

    elif message.text == "👤 Referal link":
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        bot.send_message(user_id, f"Sizning referal linkingiz:\n{ref_link}")

    elif message.text == "ℹ️ Balans":
        balance = users.get(user_id, {}).get("balance", 0)
        bot.send_message(user_id, f"Sizning balansingiz: {balance} so‘m")

# 🔹 Spin funksiyasi
def play_spin(user_id):
    spins = user_spins.get(user_id, 3)  # har bir userga 3 ta spin
    if spins <= 0:
        bot.send_message(user_id, "❌ Sizning spinningiz tugagan.")
        return

    import random
    win = random.choice([0, 0, 0, 5000, 10000, 20000])
    user_spins[user_id] = spins - 1
    users[user_id]["balance"] += win

    gif = open("spin.gif", "rb")
    bot.send_animation(user_id, gif, caption=f"🎰 Natija: {win} so‘m\nQolgan spinlar: {user_spins[user_id]}")

# 🔹 Pul yechish so‘rovi
def withdraw_request(message):
    user_id = message.chat.id
    try:
        amount = int(message.text)
        if amount < MIN_WITHDRAW:
            bot.send_message(user_id, f"❌ Minimal yechish miqdori {MIN_WITHDRAW} so‘m!")
            return

        balance = users.get(user_id, {}).get("balance", 0)
        if balance < amount:
            bot.send_message(user_id, "❌ Sizda yetarli mablag‘ yo‘q.")
            return

        withdraw_requests.append((user_id, amount))
        users[user_id]["balance"] -= amount
        bot.send_message(user_id, "✅ So‘rovingiz yuborildi. Admin tasdiqlashi kerak.")

        # Adminni xabardor qilish
        bot.send_message(ADMIN_ID, f"💳 Yangi pul yechish so‘rovi!\nID: {user_id}\nMiqdor: {amount} so‘m")

    except ValueError:
        bot.send_message(user_id, "❌ Iltimos, to‘g‘ri raqam kiriting.")

# 🔹 Admin panel
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id != ADMIN_ID:
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👥 Foydalanuvchilar soni", "📊 Pul so‘rovlari")
    markup.add("📢 Xabar yuborish", "🔗 Kanal sozlash")
    bot.send_message(ADMIN_ID, "Admin paneliga xush kelibsiz 👑", reply_markup=markup)

@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID)
def admin_handler(message):
    if message.text == "👥 Foydalanuvchilar soni":
        bot.send_message(ADMIN_ID, f"Bot foydalanuvchilari soni: {len(users)} ta")

    elif message.text == "📊 Pul so‘rovlari":
        if not withdraw_requests:
            bot.send_message(ADMIN_ID, "Hozircha so‘rovlar yo‘q.")
        else:
            text = "Pul yechish so‘rovlari:\n"
            for uid, amount in withdraw_requests:
                text += f"👤 {uid} → {amount} so‘m\n"
            bot.send_message(ADMIN_ID, text)

    elif message.text == "📢 Xabar yuborish":
        bot.send_message(ADMIN_ID, "Yubormoqchi bo‘lgan xabaringizni kiriting:")
        bot.register_next_step_handler(message, broadcast)

    elif message.text == "🔗 Kanal sozlash":
        bot.send_message(ADMIN_ID, "Yangi kanal username-ni yuboring (masalan: @mening_kanalim):")
        bot.register_next_step_handler(message, set_channel)

def broadcast(message):
    text = message.text
    for uid in users.keys():
        try:
            bot.send_message(uid, f"📢 Admin xabari:\n\n{text}")
        except:
            pass
    bot.send_message(ADMIN_ID, "✅ Xabar yuborildi.")

def set_channel(message):
    global CHANNEL
    CHANNEL = message.text.strip()
    bot.send_message(ADMIN_ID, f"✅ Kanal yangilandi: {CHANNEL}")

# 🔹 Flask server (Render uchun)
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_str = request.stream.read().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=os.getenv("RENDER_URL") + BOT_TOKEN)
    return "Webhook set!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
