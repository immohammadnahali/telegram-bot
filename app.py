from flask import Flask, request
import requests
import os

# ========================
# 🔐 توکن ربات تلگرام
# ========================
TOKEN = os.environ.get("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/"

app = Flask(__name__)

# ========================
# داده‌های اولیه پوزیشن‌ها
# ========================
weights = [40.457, 104.81, 65.494, 48.54]              # وزن هر پوزیشن
buy_prices = [7197000, 14310000, 15273000, 15842000]  # قیمت خرید هر پوزیشن (ریال)
amounts = [328000000, 1500000000, 1000000000, 769000000]  # مقدار خرید هر پوزیشن (ریال)

# ========================
# تابع ارسال پیام به تلگرام
# ========================
def send_message(chat_id, text):
    requests.post(URL + "sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

# ========================
# تابع محاسبه سود/ضرر کل
# ========================
def calculate_profit(current_price):
    total_profit = 0
    for weight, buy_price, amount in zip(weights, buy_prices, amounts):
        profit = (current_price - buy_price) * weight
        total_profit += profit
    return total_profit

# ========================
# مسیر اصلی (برای تست در مرورگر)
# ========================
@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"

# ========================
# مسیر Webhook
# ========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # جواب سلام
        if text == "سلام":
            send_message(chat_id, "سلام 👋")

        # اگر عدد بود → قیمت روز دلار
        elif text.replace(",", "").isdigit():
            # حذف ویرگول‌ها و تبدیل به عدد
            current_price = int(text.replace(",", ""))
            profit = calculate_profit(current_price)
            send_message(chat_id, f"💰 سود/ضرر کل: {profit:,.0f} ریال")

        else:
            send_message(chat_id, "لطفاً 'سلام' یا قیمت روز طلا به ریال را وارد کنید.")

    return "ok"

# ========================
# اجرای محلی (برای تست مستقیم)
# ========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

