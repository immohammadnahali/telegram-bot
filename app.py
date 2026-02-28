from flask import Flask, request
import requests
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import threading


TOKEN = os.environ.get("BOT_TOKEN")
NAVASAN_API_KEYS = [
    os.environ.get("NAVASAN_API_KEY_1"),
    os.environ.get("NAVASAN_API_KEY_2"),
]

current_api_index = 0
api_lock = threading.Lock()

# برای موقتاً خارج کردن API خراب
api_disabled_until = {}  # {index: timestamp}
API_DISABLE_DURATION = 3600  # 1 ساعت غیرفعال بشه اگر کوتا تموم کرد



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
CACHE_DURATION = 3600  # 1 ساعت

# ----------------------
# دریافت قیمت از API
# ----------------------
def get_market_prices():
    global cache_data, current_api_index

    current_time = time.time()

    # ---------- CACHE ----------
    if current_time - cache_data["timestamp"] < CACHE_DURATION:
        return cache_data["gold"], cache_data["usd"], cache_data["updated_at"]

    # ---------- API FAILOVER LOOP ----------
    for _ in range(len(NAVASAN_API_KEYS)):

        with api_lock:
            api_index = current_api_index
            current_api_index = (current_api_index + 1) % len(NAVASAN_API_KEYS)

        # اگر این API موقتاً غیرفعاله ردش کن
        disabled_until = api_disabled_until.get(api_index)
        if disabled_until and current_time < disabled_until:
            continue

        api_key = NAVASAN_API_KEYS[api_index]

        try:
            url = f"https://api.navasan.tech/latest/?api_key={api_key}"
            response = requests.get(url, timeout=10)

            # اگر quota تموم کرده
            if response.status_code == 429:
                print(f"API {api_index} quota exceeded. Disabling temporarily.")
                api_disabled_until[api_index] = current_time + API_DISABLE_DURATION
                continue

            if response.status_code != 200:
                print(f"API {api_index} returned status {response.status_code}")
                continue

            data = response.json()

            gold_price = data.get("18ayar", {}).get("value")
            usd_price = data.get("usd_sell", {}).get("value")

            if gold_price and usd_price:
                gold_price = int(gold_price)
                usd_price = int(usd_price)
                updated_at = datetime.now(
                    ZoneInfo("Asia/Tehran")
                ).strftime("%H:%M")

                cache_data.update({
                    "gold": gold_price,
                    "usd": usd_price,
                    "timestamp": current_time,
                    "updated_at": updated_at
                })

                return gold_price, usd_price, updated_at

        except Exception as e:
            print(f"API {api_index} Error:", e)
            continue

    # ---------- اگر همه API ها شکست خوردن ----------
    print("All APIs failed.")
    return None, None, None

# ----------------------
# محاسبه سود و ارزش کل
# ----------------------
def calculate_profit_and_value(current_price):
    total_profit = sum((current_price - bp) * w for bp, w in zip(buy_prices, weights))
    total_value = sum(current_price * w for w in weights)
    return total_profit, total_value

# ----------------------
# کیبورد اصلی
# ----------------------
def main_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "📊 قیمت و سود", "callback_data": "price"},
                {"text": "🥇 قیمت طلا", "callback_data": "gold"}
            ]
        ]
    }

# ----------------------
# ارسال یا ویرایش پیام
# ----------------------
def send_message(chat_id, text, keyboard=None, message_id=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        payload["reply_markup"] = keyboard

    if message_id:
        # ویرایش پیام قبلی
        requests.post(URL + "editMessageText", json={**payload, "message_id": message_id})
    else:
        # ارسال پیام جدید
        requests.post(URL + "sendMessage", json=payload)

# ----------------------
# روت تست
# ----------------------
@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"

@app.route("/gold")
def gold():
    price = get_market_prices()[0]
    return str(price)

# ----------------------
# webhook
# ----------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    # -------------------
    # هندل دکمه‌ها
    # -------------------
    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        data_value = callback["data"]

        # جلوگیری از لودینگ بی‌نهایت دکمه
        requests.post(URL + "answerCallbackQuery", json={"callback_query_id": callback["id"]})

        gold_18, usd_price, updated_at = get_market_prices()
        if not gold_18:
            send_message(chat_id, "❌ خطا در دریافت قیمت", main_keyboard(), message_id)
            return "ok"

        if data_value == "gold":
            send_message(
                chat_id,
                f"🥇 طلای ۱۸ عیار: {gold_18:,} ریال\n💵 دلار: {usd_price:,} ریال\n⏱ آخرین بروزرسانی: {updated_at}",
                main_keyboard(),
                message_id
            )
        elif data_value == "price":
            profit, total_value = calculate_profit_and_value(gold_18)
            send_message(
                chat_id,
                f"🥇 طلای ۱۸ عیار: {gold_18:,} ریال\n💵 دلار: {usd_price:,} ریال\n💰 سود/ضرر کل: {profit:,.0f} ریال\n📊 ارزش کل دارایی: {total_value:,.0f} ریال\n⏱ آخرین بروزرسانی: {updated_at}",
                main_keyboard(),
                message_id
            )
        return "ok"

    # -------------------
    # هندل پیام متنی
    # -------------------
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        message_id = data["message"]["message_id"]

        gold_18, usd_price, updated_at = get_market_prices()

        if text == "/start":
            send_message(chat_id, "👋 خوش آمدید\nیکی از گزینه‌ها را انتخاب کنید:", main_keyboard())
        elif text == "/gold":
            if gold_18:
                send_message(chat_id, f"🥇 طلای ۱۸ عیار: {gold_18:,} ریال\n💵 دلار: {usd_price:,} ریال\n⏱ آخرین بروزرسانی: {updated_at}", main_keyboard())
            else:
                send_message(chat_id, "❌ خطا در دریافت قیمت", main_keyboard())
        elif text in ["/price", "قیمت"]:
            if gold_18:
                profit, total_value = calculate_profit_and_value(gold_18)
                send_message(chat_id, f"🥇 طلای ۱۸ عیار: {gold_18:,} ریال\n💵 دلار: {usd_price:,} ریال\n💰 سود/ضرر کل: {profit:,.0f} ریال\n📊 ارزش کل دارایی: {total_value:,.0f} ریال\n⏱ آخرین بروزرسانی: {updated_at}", main_keyboard())
            else:
                send_message(chat_id, "❌ خطا در دریافت قیمت", main_keyboard())
        elif text.replace(",", "").isdigit():
            current_price = int(text.replace(",", ""))
            profit, total_value = calculate_profit_and_value(current_price)
            send_message(chat_id, f"💰 سود/ضرر کل: {profit:,.0f} ریال\n📊 ارزش کل دارایی: {total_value:,.0f} ریال", main_keyboard())
        else:
            send_message(chat_id, "دستور نامعتبر است.\nبرای دریافت قیمت بنویس: /price", main_keyboard())

    return "ok"

