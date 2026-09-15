from flask import Flask
from threading import Thimportread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from google import genai

# Flask server for UptimeRobot 24/7 hosting
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- CONFIGURATION FOR BUYERS ---
ADMIN_USER_IDS = [int(os.getenv("ADMIN_TELEGRAM_ID", "0"))] 
DAILY_LIMIT = 10
PAYMENT_LINK = os.getenv("PAYMENT_LINK", "https://razorpay.me/@your_link_here")

user_message_counts = {}
gemini_client = genai.Client()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    # Admin Bypass Logic
    if user_id in ADMIN_USER_IDS:
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_message
            )
            await update.message.reply_text(response.text)
        except Exception as e:
            print(f"Error: {e}")
            await update.message.reply_text("An error occurred with the AI model.")
        return

    # Freemium User Logic
    current_count = user_message_counts.get(user_id, 0)

    if current_count >= DAILY_LIMIT:
        limit_message = (
            f"⚠️ You've reached your daily limit of {DAILY_LIMIT} messages.\n\n"
            f"To get unlimited access, please upgrade:\n{PAYMENT_LINK}"
        )
        await update.message.reply_text(limit_message)
        return

    user_message_counts[user_id] = current_count + 1
    remaining = DAILY_LIMIT - user_message_counts[user_id]

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_message
        )
        reply_text = f"{response.text}\n\n📊 Remaining messages today: {remaining}/{DAILY_LIMIT}"
        await update.message.reply_text(reply_text)
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("An error occurred with the AI model.")

def main():
    keep_alive()
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    ap


