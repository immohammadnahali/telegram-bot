from flask import Flask, request
import requests
import os

TOKEN = os.environ.get("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/"

app = Flask(__name__)

# داده‌ها
weights = [40.457, 104.81, 65.494, 48.54]
buy_prices = [7197000, 14310000, 15273000, 15842000]
amounts = [328000000, 1500000000, 1000000000, 769000000]

def send_message(chat_id, text):
    requests.post(URL + "sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def calculate_profit_and_value(current_price):
    total_profit = 0
    total_value = 0

    for weight, buy_price in zip(weights, buy_prices):
        profit = (current_price - buy_price) * weight
        value = current_price * weight

        total_profit += profit
        total_value += value

    return total_profit, total_value

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "سلام":
            send_message(chat_id, "سلام 👋")

        elif text.replace(",", "").isdigit():
            current_price = int(text.replace(",", ""))

            profit, total_value = calculate_profit_and_value(current_price)

            send_message(
                chat_id,
                f"💰 سود/ضرر کل: {profit:,.0f} ریال\n"
                f"📊 ارزش کل دارایی: {total_value:,.0f} ریال"
            )

        else:
            send_message(chat_id, "قیمت روز را به صورت عدد وارد کنید.")

    return "ok"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
