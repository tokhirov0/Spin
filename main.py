import os
import random
import time
from flask import Flask, request
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Foydalanuvchi ma'lumotlari
users = {}  # user_id: {'balance': int, 'spins': int, 'referrals': set()}

# Baraban spin (animatsiya bilan)
def spin_baraban_animation():
    outcomes = ['💰1000','💰5000','💰10000','💰50000','💰100000','❌0']
    animation = ['🎰|','🎰/','🎰-','🎰\\']  # oddiy animatsiya
    for i in range(6):
        yield random.choice(animation)
        time.sleep(0.2)
    result = random.choice(outcomes)
    amount = int(result.replace('💰','')) if '💰' in result else 0
    yield result, amount

# /start handler
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    ref_id = None
    if message.text and len(message.text.split()) > 1:
        try:
            ref_id = int(message.text.split()[1])
        except:
            ref_id = None
    if user_id not in users:
        users[user_id] = {'balance':0,'spins':1,'referrals': set()}
        if ref_id and ref_id in users and user_id != ref_id:
            users[ref_id]['spins'] +=1
            users[ref_id]['referrals'].add(user_id)
            bot.send_message(ref_id, f"🟢 Sizning referalingiz kirdi! +1 spin berildi.")

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎰 Spin urish", callback_data="spin"),
        types.InlineKeyboardButton("💰 Hisob", callback_data="balance")
    )
    markup.add(
        types.InlineKeyboardButton("🎁 Daily bonus", callback_data="daily"),
        types.InlineKeyboardButton("💳 Pul yechish", callback_data="withdraw")
    )
    markup.add(types.InlineKeyboardButton("🔗 Referral link", url=f"https://t.me/Spinomad_bot?start={user_id}"))

    bot.send_message(user_id, "Salom! 🎉 Zamonaviy Spin o‘yiniga xush kelibsiz!", reply_markup=markup)

# Callback handler
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    if user_id not in users:
        users[user_id] = {'balance':0,'spins':1,'referrals': set()}

    if call.data == "spin":
        if users[user_id]['spins'] <=0:
            bot.answer_callback_query(call.id, "❌ Sizda spin yo‘q.")
            return
        users[user_id]['spins'] -=1

        msg = bot.send_message(user_id, "🎰 Spin boshlanmoqda...")
        for frame in spin_baraban_animation():
            if isinstance(frame, tuple):
                result, amount = frame
                users[user_id]['balance'] += amount
                bot.edit_message_text(chat_id=user_id, message_id=msg.message_id,
                                      text=f"🎰 Natija: {result}\n💰 Qo‘shildi: {amount} so‘m")
            else:
                bot.edit_message_text(chat_id=user_id, message_id=msg.message_id,
                                      text=f"{frame}")

    elif call.data == "balance":
        bal = users[user_id]['balance']
        spins = users[user_id]['spins']
        bot.answer_callback_query(call.id, f"💰 Hisobingiz: {bal} so‘m\n🎰 Spiningiz: {spins}")
    elif call.data == "daily":
        users[user_id]['spins'] +=1
        bot.answer_callback_query(call.id, "🎁 Har kunlik bonus: +1 spin!")
    elif call.data == "withdraw":
        if users[user_id]['balance'] < 100000:
            bot.answer_callback_query(call.id, "❌ Minimal pul yechish: 100,000 so‘m")
            return
        msg = bot.send_message(user_id, "💳 Pul yechish uchun karta raqamingizni kiriting:")
        bot.register_next_step_handler(msg, process_card)

def process_card(message):
    user_id = message.from_user.id
    card = message.text.strip()
    msg = bot.send_message(user_id, f"Karta qabul qilindi ✅. Hisobingizdan yechmoqchi bo‘lgan summani kiriting (min 100,000 so‘m):")
    bot.register_next_step_handler(msg, process_amount, card)

def process_amount(message, card):
    user_id = message.from_user.id
    try:
        amount = int(message.text.strip())
    except:
        bot.send_message(user_id, "❌ Iltimos, raqam kiriting.")
        return
    if amount < 100000:
        bot.send_message(user_id, "❌ Minimal pul yechish 100,000 so‘m")
        return
    if amount > users[user_id]['balance']:
        bot.send_message(user_id, "❌ Hisobingizda yetarli mablag‘ yo‘q")
        return
    users[user_id]['balance'] -= amount
    bot.send_message(user_id, f"✅ {amount} so‘m muvaffaqiyatli yechildi. 48 soat ichida hisobingizga tushadi.\n💰 Qolgan balans: {users[user_id]['balance']} so‘m")

# Flask webhook
@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/", methods=['GET'])
def index():
    return "Bot ishlamoqda ✅", 200

# Webhook Render URL ga o‘rnatish
if __name__ == "__main__":
    import requests
    RENDER_URL = "https://spin-3n80.onrender.com"
    url = f"{RENDER_URL}/{BOT_TOKEN}"
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={url}")
        print("✅ Webhook o‘rnatildi")
    except Exception as e:
        print(f"❌ Webhook xato: {e}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
