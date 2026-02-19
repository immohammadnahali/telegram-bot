from flask import Flask, request
import requests
import os

# گرفتن متغیرهای محیطی
TOKEN = os.environ.get("BOT_TOKEN")
BRS_API_KEY = os.environ.get("BRS_API_KEY")

URL = f"https://api.telegram.org/bot{TOKEN}/"

app = Flask(__name__)

# داده‌های پوزیشن‌ها
weights = [40.457, 104.81, 65.494, 48.54]
buy_prices = [7197000, 14310000, 15273000, 15842000]


# ارسال پیام به تلگرام
def send_message(chat_id, text):
    requests.post(URL + "sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })


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


# گرفتن قیمت‌ها از API
def get_market_prices():
    url = f"https://BrsApi.ir/Api/Market/Market_CGCC.php?key={BRS_API_KEY}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            dollar = int(data["dollar"]["price"])
            gold_18 = int(data["gold18"]["price"])
            ounce = int(data["ounce"]["price"])

            return dollar, gold_18, ounce
        else:
            return None, None, None

    except Exception:
        return None, None, None


@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # سلام
        if text == "سلام":
            send_message(chat_id, "سلام 👋")

        # دستور گرفتن قیمت از API
        elif text == "قیمت":
            dollar, gold_18, ounce = get_market_prices()

            if gold_18:
                profit, total_value = calculate_profit_and_value(gold_18)

                send_message(
                    chat_id,
                    f"💵 دلار: {dollar:,} ریال\n"
                    f"🌍 انس جهانی: {ounce:,} دلار\n"
                    f"🥇 طلای ۱۸ عیار: {gold_18:,} ریال\n\n"
                    f"💰 سود/ضرر کل: {profit:,.0f} ریال\n"
                    f"📊 ارزش کل دارایی: {total_value:,.0f} ریال"
                )
            else:
                send_message(chat_id, "❌ خطا در دریافت قیمت‌ها از سرور")

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
