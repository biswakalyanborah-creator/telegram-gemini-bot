import os
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from google import genai

# Flask server for UptimeRobot 24/7 hosting
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- CONFIGURATION ---
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
            await update.message.reply_text(f"Error: {e}")
        return

    # Regular Freemium Logic
    today = str(update.message.date.date())
    if user_id not in user_message_counts:
        user_message_counts[user_id] = {"date": today, "count": 0}

    if user_message_counts[user_id]["date"] != today:
        user_message_counts[user_id]["date"] = today
        user_message_counts[user_id]["count"] = 0

    if user_message_counts[user_id]["count"] >= DAILY_LIMIT:
        await update.message.reply_text(
            f"⚠️ Aapki aaj ki limit (10 free messages) khatam ho chuki hai!\n\n"
            f"Unlimited access ke liye yahan pay karein:\n{PAYMENT_LINK}\n\n"
            f"Payment karne ke baad Admin ko screenshot bhejein."
        )
        return

    user_message_counts[user_id]["count"] += 1
    remaining = DAILY_LIMIT - user_message_counts[user_id]["count"]

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_message
        )
        await update.message.reply_text(
            f"{response.text}\n\n💬 (Aaj ke bache hue free messages: {remaining})"
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

if __name__ == '__main__':
    keep_alive()
    
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot is starting polling...")
    application.run_polling()
    
