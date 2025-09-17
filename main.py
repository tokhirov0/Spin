import os
import random
from flask import Flask, request
import telebot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Ma'lumotlar saqlash (sinov uchun RAMda)
users = {}  # user_id: {'balance': int, 'spins': int, 'referrals': set()}

# Spin baraban
def spin_baraban():
    outcomes = ['💰1000', '💰5000', '💰10000', '💰50000', '💰100000', '❌0']
    result = random.choice(outcomes)
    amount = int(result.replace('💰','')) if '💰' in result else 0
    return result, amount

# /start handler
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    ref_id = None
    # Referral
    if message.text and len(message.text.split()) > 1:
        ref_id = int(message.text.split()[1])
    if user_id not in users:
        users[user_id] = {'balance':0, 'spins':1, 'referrals': set()}
        if ref_id and ref_id in users:
            users[ref_id]['spins'] +=1
            users[ref_id]['referrals'].add(user_id)
            bot.send_message(ref_id, f"🟢 Sizning referralingiz kirdi! +1 spin berildi.")

    bot.send_message(user_id, "Salom! 🎉 Spin o‘yiniga xush kelibsiz!\n/spin - Spin urish\n/balance - Hisob\n/withdraw - Pul yechish")

# /balance handler
@bot.message_handler(commands=['balance'])
def balance_handler(message):
    user_id = message.from_user.id
    bal = users.get(user_id, {'balance':0})['balance']
    spins = users.get(user_id, {'spins':0})['spins']
    bot.send_message(user_id, f"💰 Hisobingiz: {bal} so‘m\n🎰 Spiningiz: {spins}")

# /spin handler
@bot.message_handler(commands=['spin'])
def spin_handler(message):
    user_id = message.from_user.id
    if users.get(user_id, {'spins':0})['spins'] <=0:
        bot.send_message(user_id, "❌ Sizda spin yo‘q. Referal orqali yoki /daily bonus bilan olishingiz mumkin.")
        return
    users[user_id]['spins'] -=1
    result, amount = spin_baraban()
    users[user_id]['balance'] += amount
    bot.send_message(user_id, f"🎰 Natija: {result}\n💰 Qo‘shildi: {amount} so‘m")

# /daily handler
@bot.message_handler(commands=['daily'])
def daily_handler(message):
    user_id = message.from_user.id
    users.setdefault(user_id, {'balance':0,'spins':0,'referrals': set()})
    users[user_id]['spins'] +=1
    bot.send_message(user_id, "🎁 Har kunlik bonus: +1 spin!")

# /withdraw handler
@bot.message_handler(commands=['withdraw'])
def withdraw_handler(message):
    user_id = message.from_user.id
    user = users.get(user_id)
    if not user or user['balance'] < 100000:
        bot.send_message(user_id, "❌ Minimal pul yechish: 100,000 so‘m")
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
    amount = int(message.text.strip())
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

# Webhookni Render URL ga o‘rnatish
if __name__ == "__main__":
    import requests
    RENDER_URL = "https://spin-3n80.onrender.com"  # Sizning Render URL
    url = f"{RENDER_URL}/{BOT_TOKEN}"
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={url}")
        print("✅ Webhook o‘rnatildi")
    except Exception as e:
        print(f"❌ Webhook xato: {e}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
