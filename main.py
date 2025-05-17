import os
import json
import uuid
import random
from datetime import datetime
import pytz
import psycopg2
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables (set in Render)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DIFY_API_KEY = os.getenv("DIFY_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
POSTGRES_URL = os.getenv("POSTGRES_URL")
DIFY_API_URL = os.getenv("DIFY_API_URL", "https://your-dify-app.onrender.com/v1/chat-messages")
ESCALATION_CHAT_ID = "-1002587300255"

# Set timezone to UTC+07:00 (Asia/Bangkok)
TIMEZONE = pytz.timezone("Asia/Bangkok")

# List of CS bot names
BOT_NAMES = ["Selena", "Emma", "Liam", "Olivia", "Noah", "Ava", "Sophia", "James"]

# Database connection
def get_db_connection():
    return psycopg2.connect(POSTGRES_URL)

# Get or assign random bot name for a chat
def get_bot_name(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT bot_name FROM conversations WHERE chat_id = %s LIMIT 1", (chat_id,))
    result = cursor.fetchone()
    if result:
        bot_name = result[0]
    else:
        bot_name = random.choice(BOT_NAMES)
        cursor.execute("INSERT INTO conversations (chat_id, bot_name) VALUES (%s, %s) ON CONFLICT (chat_id) DO UPDATE SET bot_name = %s", (chat_id, bot_name, bot_name))
        conn.commit()
    cursor.close()
    conn.close()
    return bot_name

# Initialize conversation record
def add_conversation_record(chat_id, message_text, response_text):
    conn = get_db_connection()
    cursor = conn.cursor()
    key = f"{chat_id}_{datetime.now(TIMEZONE).isoformat()}"
    data = f"User: {message_text} Support: {response_text}"
    cursor.execute(
        "INSERT INTO conversations (key, data, chat_id) VALUES (%s, %s, %s) ON CONFLICT (key) DO UPDATE SET data = %s",
        (key, data, chat_id, data)
    )
    conn.commit()
    cursor.close()
    conn.close()

# Search conversation history
def search_conversation_records(chat_id, limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT data FROM conversations WHERE chat_id = %s AND data IS NOT NULL ORDER BY key ASC LIMIT %s",
        (chat_id, limit)
    )
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return [row[0] for row in results]

# Format date for escalation message in UTC+07:00
def format_date(timestamp):
    dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    dt = dt.astimezone(TIMEZONE)
    return dt.strftime("%d.%m.%Y %H:%M")

# Call Dify API
async def call_dify_api(message_text, first_name, bot_name):
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {"bot_name": bot_name},
        "query": message_text,
        "response_mode": "blocking",
        "conversation_id": "",
        "user": first_name
    }
    try:
        response = requests.post(DIFY_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("answer", "")
    except requests.RequestException as e:
        logger.error(f"Dify API error: {e}")
        return "Error processing request. Escalating to technical team."

# Call OpenRouter API for escalation summary
async def call_openrouter_api(conversation_history):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "yourwebsite.com",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant who reads a full support conversation history and provides a concise summary of the user's unresolved issue."
            },
            {
                "role": "user",
                "content": f"Here is the full support thread:\n\n{conversation_history}\n\nPlease provide a concise summary of the user's unresolved issue."
            }
        ]
    }
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        logger.error(f"OpenRouter API error: {e}")
        return "Unable to summarize issue."

# Handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    bot_name = get_bot_name(chat_id)
    await update.message.reply_text(f"Hi, {bot_name} here! How can I assist you today?", parse_mode="HTML")

# Handle /command1@difykgbot command
async def command1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    bot_name = get_bot_name(chat_id)
    await update.message.reply_text(f"Hi, {bot_name} here! How can I assist you today?", parse_mode="HTML")

# Handle /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    bot_name = get_bot_name(chat_id)
    help_text = (
        f"Hi, {bot_name} here! Here are the available commands:\n"
        "/start - Start a conversation with me.\n"
        "/command1@difykgbot - Prompt for assistance.\n"
        "/help - Show this help message.\n\n"
        "Just send a message with your question, and I'll do my best to help!"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")

# Handle Telegram messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    message_text = message.text or message.caption or ""
    first_name = message.from_user.first_name
    username = message.from_user.username or "Unknown"
    group_title = message.chat.title or "Unknown"
    message_id = message.message_id
    execution_id = str(uuid.uuid4())[:6]
    bot_name = get_bot_name(chat_id)

    # Call Dify API
    dify_response = await call_dify_api(message_text, first_name, bot_name)
    
    # Store conversation
    add_conversation_record(chat_id, message_text, dify_response)

    # Check if escalation is needed
    if "escalating" in dify_response.lower():
        # Search conversation history
        conversation_history = "\n".join(search_conversation_records(chat_id))
        
        # Get summary from OpenRouter
        summary = await call_openrouter_api(conversation_history)
        
        # Format escalation message
        escalation_message = (
            f"Hello team, we received a query from \n"
            f"<b>Group: {group_title}</b>\n"
            f"User: {username}\n"
            f"On time: {format_date(message.date)}\n\n"
            f"<b>Query Clarify:</b> {summary}\n\n"
            f"Client Query ID: KG-{execution_id}\n\n"
            f"I couldn't solve this query. Please assist or follow up."
        )
        
        # Send escalation message to technical team
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(
            chat_id=ESCALATION_CHAT_ID,
            text=escalation_message,
            parse_mode="HTML"
        )
        
        # Notify user
        await message.reply_text(
            f"Hi, {bot_name} here! I'm escalating this to our technical team for further assistance. You'll hear back soon with Query ID: KG-{execution_id}.",
            parse_mode="HTML",
            reply_to_message_id=message_id
        )
    else:
        # Check for troubleshooting follow-up
        if any(phrase in message_text.lower() for phrase in ["still can't", "why still can", "still doesn't work"]):
            conversation_state = (
                f"chatId={chat_id}|waitingForFollowUp=true|"
                f"originalQuery={message_text}|"
                f"troubleshootingSteps={'No steps provided' if 'Let’s try' not in dify_response else dify_response.split('Let’s try ')[1].split('.')[0]}|"
                f"context={message_text}"
            )
            add_conversation_record(chat_id, message_text, conversation_state)
            
            if "still doesn't work" in message_text.lower() and "why" not in message_text.lower():
                # Get summary for escalation
                conversation_history = "\n".join(search_conversation_records(chat_id))
                summary = await call_openrouter_api(conversation_history)
                
                # Format escalation message
                escalation_message = (
                    f"Hello team, we received a query from \n"
                    f"<b>Group: {group_title}</b>\n"
                    f"User: {username}\n"
                    f"On time: {format_date(message.date)}\n\n"
                    f"<b>Query Clarify:</b> {summary}\n\n"
                    f"Client Query ID: KG-{execution_id}\n\n"
                    f"I couldn't solve this query. Please assist or follow up."
                )
                
                # Send escalation message
                bot = Bot(token=TELEGRAM_TOKEN)
                await bot.send_message(
                    chat_id=ESCALATION_CHAT_ID,
                    text=escalation_message,
                    parse_mode="HTML"
                )
                
                # Notify user
                await message.reply_text(
                    f"Hi, {bot_name} here! I'm escalating this to my supports team for further assistance. You'll hear back from them soon.\nYour Query ID: KG-{execution_id}.",
                    parse_mode="HTML",
                    reply_to_message_id=message_id
                )
                
                # Delete conversation record
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM conversations WHERE chat_id = %s", (chat_id,))
                conn.commit()
                cursor.close()
                conn.close()
            else:
                # Reply with Dify response
                await message.reply_text(f"Hi, {bot_name} here! {dify_response}", parse_mode="Markdown", reply_to_message_id=message_id)
        else:
            # Reply with Dify response
            await message.reply_text(f"Hi, {bot_name} here! {dify_response}", parse_mode="Markdown", reply_to_message_id=message_id)

# Main function
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("command1", command1, filters=filters.RegexCommandsFilter(regex_commands=["command1@difykgbot"])))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
