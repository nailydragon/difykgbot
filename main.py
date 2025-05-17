import os
import random
import requests
from flask import Flask, request

app = Flask(__name__)

# Read from environment variables
BOT_TOKEN = os.environ["BOT_TOKEN"]
DIFY_API_KEY = os.environ["DIFY_API_KEY"]
DIFY_APP_ID = os.environ["DIFY_APP_ID"]

# 🧠 Random bot names
BOT_NAMES = ["Sophy", "Rith", "Malis", "Kosal", "Dara", "Selena", "Maii", "Borey", "Raksa", "James", "Michelle", "Phanith", "Malisa", "Marima", "Nicky", "Dellis"]

@app.route("/")
def home():
    return "KG Telegram Bot is running!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    
    # Parse user message
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user_text = message.get("text", "").strip().lower()

    if not chat_id or not user_text:
        return "Invalid data", 400

    # 🎯 Respond with command list
    if user_text in ["/listcommands", "/help"]:
        command_list_text = """
---- <Common Commands> ----

LIST COMMANDS:
/listcommands
LIST WINNERS:
/listwinners
ONLINE MEMBER:
/onlinemember
CHECK PROVIDERS STATUS:
/provider
CHECK MAIN ACCOUNT BALANCE:
/balance
CHECK ALL VALID DOMAIN:
/domain
CHECK WHITE LIST:
/whitelist
PROMPTS OR COMMANDS:
/prompts
HOW TO USE BOT:
/help

CHECK-MEMBER
BOT-NEWONE

---- <Super Commands> ----

Active Bot:
/onbot
Suspend Bot:
/offbot
Supported Currency:
/currency
Providers Winloss Report:
/list_all_winloss
Total Winloss Report:
/list_total_winloss
Total Deposit Report:
/list_total_deposit
Total Withdraw Report:
/list_total_withdraw
Total Register Report:
/list_total_register

Have Any Request? Send it via:
https://forms.gle/Qz3qfYRkLXrJf9VU6
"""
        reply_payload = {
            "chat_id": chat_id,
            "text": command_list_text
        }
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=reply_payload)
        return "ok"

    # 🧠 Pick a random bot name
    bot_name = random.choice(BOT_NAMES)

    # 🔁 Send user query to Dify
    dify_payload = {
        "inputs": {
            "bot_name": bot_name
        },
        "query": user_text,
        "response_mode": "blocking",
        "conversation_id": str(chat_id),
        "user": str(chat_id),
        "app_id": DIFY_APP_ID
    }

    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post("https://api.dify.ai/v1/chat-messages", headers=headers, json=dify_payload)
        answer = res.json().get("answer", "Sorry, something went wrong.")
    except Exception as e:
        answer = f"⚠️ Error contacting AI: {str(e)}"

    # 💬 Send AI reply to Telegram
    reply_payload = {
        "chat_id": chat_id,
        "text": answer
    }
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=reply_payload)

    return "ok"
