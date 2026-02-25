from flask import Flask, request
import requests
import os

TOKEN = os.environ.get("BOT_TOKEN")
NAVASAN_API_KEY = os.environ.get("NAVASAN_API_KEY")

URL = f"https://api.telegram.org/bot{TOKEN}/"

app = Flask(__name__)

weights = [40.457, 104.81, 65.494, 48.54]
buy_prices = [7197000, 14310000, 15273000, 15842000]


def get_gold_price():
    try:
        url = f"https://api.navasan.tech/latest/?api_key={NAVASAN_API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()

        gold_price = data.get("18ayar", {}).get("value")

        if gold_price:
            return int(gold_price)

        return None

    except Exception as e:
        print("API Error:", e)
        return None


def calculate_profit_and_value(current_price):
    total_profit = 0
    total_value = 0

    for weight, buy_price in zip(weights, buy_prices):
        profit = (current_price - buy_price) * weight
        value = current_price * weight

        total_profit += profit
        total_value += value

    return total_profit, total_value


def send_message(chat_id, text):
    requests.post(URL + "sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })


@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"


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

        # start
        if text == "/start":
            send_message(
                chat_id,
                "👋 خوش آمدید\n\n"
                "دستورات ربات:\n"
                "/price - نمایش قیمت و سود\n"
                "/gold - نمایش فقط قیمت طلا"
            )

        # فقط قیمت طلا
        elif text == "/gold":
            gold_18 = get_gold_price()
            if gold_18:
                send_message(chat_id, f"🥇 طلای ۱۸ عیار: {gold_18:,} ریال")
            else:
                send_message(chat_id, "❌ خطا در دریافت قیمت")

        # قیمت + سود
        elif text in ["قیمت", "/price"]:
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
                send_message(chat_id, "❌ خطا در دریافت قیمت طلا از API")

        # ورود دستی قیمت
        elif text.replace(",", "").isdigit():
            current_price = int(text.replace(",", ""))
            profit, total_value = calculate_profit_and_value(current_price)

            send_message(
                chat_id,
                f"💰 سود/ضرر کل: {profit:,.0f} ریال\n"
                f"📊 ارزش کل دارایی: {total_value:,.0f} ریال"
            )

        else:
            send_message(chat_id, "دستور نامعتبر است.\nبرای دریافت قیمت بنویس: /price")

    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
