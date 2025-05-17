# main.py
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import os

BOT_TOKEN = os.environ["BOT_TOKEN"] # Read from environment variable

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /listcommands to see available commands.")

async def listcommands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = """
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

Have Any Request? Send it via: https://forms.gle/Qz3qfYRkLXrJf9VU6
"""
    await update.message.reply_text(message)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("listcommands", listcommands))
app.run_polling()
