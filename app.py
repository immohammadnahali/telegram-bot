from flask import Flask, request
import requests
import os
from bs4 import BeautifulSoup

# گرفتن متغیر محیطی توکن
TOKEN = os.environ.get("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/"

app = Flask(__name__)

# داده‌های پوزیشن‌ها
weights = [40.457, 104.81, 65.494, 48.54]
buy_prices = [7197000, 14310000, 15273000, 15842000]


# گرفتن قیمت طلای ۱۸ از tala.ir
def get_gold_price():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get("https://www.tala.ir/", headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        gold_div = soup.find("div", id="geram18")
        if not gold_div:
            return None

        price_span = gold_div.find("span", class_="price")
        if not price_span:
            return None

        price_text = price_span.text.replace(",", "").strip()
        return int(price_text)

    except Exception as e:
        print("Scraping Error:", e)
        return None


# محاسبه سود و ارزش کل
def calculate_profit_and_value(current_price):
    total_profit = 0
    total_value = 0

    for weight, buy_price in zip(weights, buy_prices):
        profit = (current_price - buy_price) * weight
        value = current_price * weight

        total_profit += profit
        total_value += value

    return total_profit, total_value


# ارسال پیام به تلگرام
def send_message(chat_id, text):
    requests.post(URL + "sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })


@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"


# تست گرفتن قیمت مستقیم
@app.route("/gold")
def gold():
    price = get_gold_price()
    return str(price)


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # سلام
        if text == "سلام":
            send_message(chat_id, "سلام 👋")

        # گرفتن قیمت از سایت
        elif text == "قیمت":
            gold_18 = get_gold_price()

            if gold_18:
                profit, total_value = calculate_profit_and_value(gold_18)

                send_message(
                    chat_id,
                    f"🥇 طلای ۱۸ عیار: {gold_18:,} ریال\n\n"
                    f"💰 سود/ضرر کل: {profit:,.0f} ریال\n"
                    f"📊 ارزش کل دارایی: {total_value:,.0f} ریال"
                )
            else:
                send_message(chat_id, "❌ خطا در دریافت قیمت طلا از سایت")

        # اگر کاربر خودش قیمت وارد کند
        elif text.replace(",", "").isdigit():
            current_price = int(text.replace(",", ""))

            profit, total_value = calculate_profit_and_value(current_price)

            send_message(
                chat_id,
                f"💰 سود/ضرر کل: {profit:,.0f} ریال\n"
                f"📊 ارزش کل دارایی: {total_value:,.0f} ریال"
            )

        else:
            send_message(chat_id, "دستور نامعتبر است.\nبرای دریافت قیمت بنویس: قیمت")

    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
