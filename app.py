from flask import Flask, request
import requests
import os
import time
from datetime import datetime
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ.get("BOT_TOKEN")
NAVASAN_API_KEY = os.environ.get("NAVASAN_API_KEY")

URL = f"https://api.telegram.org/bot{TOKEN}/"

app = Flask(__name__)

weights = [40.457, 104.81, 65.494, 48.54]
buy_prices = [7197000, 14310000, 15273000, 15842000]

# کش قیمت‌ها
cache_data = {
    "gold": None,
    "usd": None,
    "timestamp": 0,
    "updated_at": ""
}

CACHE_DURATION = 3600  # 1 ساعت (به ثانیه)

from datetime import datetime

def get_market_prices():
    global cache_data

    current_time = time.time()

    # اگر کش معتبر است
    if current_time - cache_data["timestamp"] < CACHE_DURATION:
        return (
            cache_data["gold"],
            cache_data["usd"],
            cache_data["updated_at"]
        )

    try:
        url = f"https://api.navasan.tech/latest/?api_key={NAVASAN_API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()

        gold_price = data.get("18ayar", {}).get("value")
        usd_price = data.get("usd_sell", {}).get("value")

        if gold_price and usd_price:
            gold_price = int(gold_price)
            usd_price = int(usd_price)

            update_time = datetime.now(ZoneInfo("Asia/Tehran")).strftime("%H:%M")

            cache_data["gold"] = gold_price
            cache_data["usd"] = usd_price
            cache_data["timestamp"] = current_time
            cache_data["updated_at"] = update_time

            return gold_price, usd_price, update_time

        return None, None, None

    except Exception as e:
        print("API Error:", e)
        return None, None, None



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


def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = keyboard

    requests.post(URL + "sendMessage", json=payload)


@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"


@app.route("/gold")
def gold():
    price = get_gold_price()
    return str(price)

        # webhook

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    # -------------------
    # هندل دکمه‌های شیشه‌ای
    # -------------------
    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        data_value = callback["data"]

        # جلوگیری از لودینگ بی‌نهایت دکمه
        requests.post(URL + "answerCallbackQuery", json={
            "callback_query_id": callback["id"]
        })

        gold_18, usd_price, updated_at = get_market_prices()

        if not gold_18:
            send_message(chat_id, "❌ خطا در دریافت قیمت")
            return "ok"

        if data_value == "gold":
            send_message(
                chat_id,
                f"🥇 طلای ۱۸ عیار: {gold_18:,} ریال\n"
                f"💵 دلار: {usd_price:,} ریال\n\n"
                f"⏱ آخرین بروزرسانی: {updated_at}"
            )

        elif data_value == "price":
            profit, total_value = calculate_profit_and_value(gold_18)

            send_message(
                chat_id,
                f"🥇 طلای ۱۸ عیار: {gold_18:,} ریال\n"
                f"💵 دلار: {usd_price:,} ریال\n\n"
                f"💰 سود/ضرر کل: {profit:,.0f} ریال\n"
                f"📊 ارزش کل دارایی: {total_value:,.0f} ریال\n\n"
                f"⏱ آخرین بروزرسانی: {updated_at}"
            )

        return "ok"

    # -------------------
    # هندل پیام‌های معمولی
    # -------------------
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "📊 قیمت و سود", "callback_data": "price"},
                        {"text": "🥇 قیمت طلا", "callback_data": "gold"}
                    ]
                ]
            }

            send_message(
                chat_id,
                "👋 خوش آمدید\nیکی از گزینه‌ها را انتخاب کنید:",
                keyboard
            )

        elif text == "/gold":
            gold_18, usd_price, updated_at = get_market_prices()

            if gold_18:
                send_message(
                    chat_id,
                    f"🥇 طلای ۱۸ عیار: {gold_18:,} ریال\n"
                    f"💵 دلار: {usd_price:,} ریال\n\n"
                    f"⏱ آخرین بروزرسانی: {updated_at}"
                )
            else:
                send_message(chat_id, "❌ خطا در دریافت قیمت")

        elif text in ["قیمت", "/price"]:
            gold_18, usd_price, updated_at = get_market_prices()

            if gold_18:
                profit, total_value = calculate_profit_and_value(gold_18)

                send_message(
                    chat_id,
                    f"🥇 طلای ۱۸ عیار: {gold_18:,} ریال\n"
                    f"💵 دلار: {usd_price:,} ریال\n\n"
                    f"💰 سود/ضرر کل: {profit:,.0f} ریال\n"
                    f"📊 ارزش کل دارایی: {total_value:,.0f} ریال\n\n"
                    f"⏱ آخرین بروزرسانی: {updated_at}"
                )
            else:
                send_message(chat_id, "❌ خطا در دریافت قیمت")

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



