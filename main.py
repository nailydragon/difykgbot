# main.py
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import os

BOT_TOKEN = os.environ["7663978407:AAHy49TWkU4BM1Y89MBXvEhQ8m9uN4aPq24"]  # Read from environment variable

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /listcommands to see available commands.")

async def listcommands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = """
---- <Common Commands> ----
/listcommands
/listwinners
/onlinemember
/provider
/balance
/domain
/whitelist
/prompts
/help

---- <Super Commands> ----
/onbot
/offbot
/currency
/list_all_winloss
/list_total_winloss
/list_total_deposit
/list_total_withdraw
/list_total_register

Send Request: https://forms.gle/Qz3qfYRkLXrJf9VU6
"""
    await update.message.reply_text(message)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("listcommands", listcommands))
app.run_polling()
