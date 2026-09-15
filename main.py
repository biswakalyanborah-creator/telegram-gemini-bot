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
    return "Bot is running with Pro Features!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- CONFIGURATION & DATABASES ---
ADMIN_USER_IDS = [int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))]
DAILY_LIMIT = 5  # Free trial limit
PAYMENT_LINK = os.environ.get("PAYMENT_LINK", "https://razorpay.me/@your_link_here")

user_data = {}  # Stores usage counts, referral counts, and pro status
gemini_client = genai.Client()

async def send_long_message(update: Update, text: str):
    """Bade messages ko 4000 characters ke tukdo me split karke bhejta hai"""
    max_length = 4000
    for i in range(0, len(text), max_length):
        await update.message.reply_text(text[i:i + max_length])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text or update.message.caption or ""
    today = str(update.message.date.date())

    # Initialize user profile
    if user_id not in user_data:
        user_data[user_id] = {
            "date": today, 
            "count": 0, 
            "is_pro": False, 
            "bonus_messages": 0
        }

    # Reset daily limits on a new day
    if user_data[user_id]["date"] != today:
        user_data[user_id]["date"] = today
        user_data[user_id]["count"] = 0

    # Admin Bypass & Special Commands Handler
    if user_id in ADMIN_USER_IDS:
        if user_message.startswith("/activate "):
            try:
                target_id = int(user_message.split(" ")[1])
                if target_id in user_data:
                    user_data[target_id]["is_pro"] = True
                    await update.message.reply_text(f"✅ Success! User {target_id} is now upgraded to PRO.")
                else:
                    await update.message.reply_text("❌ User database me nahi mila.")
            except Exception as e:
                await update.message.reply_text(f"Format error: /activate <user_id>")
            return

    # User Commands
    if user_message == "/start":
        welcome_text = (
            "🤖 **Welcome to Ultimate Gemini AI Bot!**\n\n"
            f"🎁 Free Trial: **{DAILY_LIMIT} messages/day**\n"
            "⚡ Features: Text & Image Analysis, Lightning fast responses.\n\n"
            "🔥 **Want Unlimited Access?**\n"
            f"Get Pro Plan for just ₹99/month here:\n{PAYMENT_LINK}\n\n"
            "💡 *After payment, send your screenshot to the Admin for instant activation, or type /status to check your quota.*"
        )
        await update.message.reply_text(welcome_text, parse_mode="Markdown")
        return

    if user_message == "/status":
        u = user_data[user_id]
        status_type = "👑 PRO (Unlimited)" if u["is_pro"] else "🆓 Free Tier"
        remaining = max(0, DAILY_LIMIT + u["bonus_messages"] - u["count"])
        await update.message.reply_text(
            f"📊 **Your Account Status**\n\n"
            f"Plan: {status_type}\n"
            f"Messages left today: {remaining}\n"
            f"Referral Bonus Messages: {u['bonus_messages']}"
        )
        return

    # Check Pro Status or Limits
    is_pro = user_data[user_id]["is_pro"]
    total_allowed = DAILY_LIMIT + user_data[user_id]["bonus_messages"]

    if not is_pro and user_data[user_id]["count"] >= total_allowed:
        paywall_text = (
            "🚨 **Aapki Aaj ki Free Limit Khatam Ho Chuki Hai!**\n\n"
            "✨ *Non-stop AI power ke liye abhi Pro banayein:*\n"
            f"👉 [Click Here to Pay & Unlock Pro]({PAYMENT_LINK})\n\n"
            "📸 *Payment ke baad screenshot aur apni Telegram ID Admin ko bhejein taaki turant activation ho sake!*\n"
            "💬 Type `/status` to check details."
        )
        await update.message.reply_text(paywall_text, parse_mode="Markdown")
        return

    # Increment count for normal users
    if not is_pro:
        user_data[user_id]["count"] += 1
        remaining = total_allowed - user_data[user_id]["count"]
    else:
        remaining = "Unlimited 👑"

    # Multimodal handling (Image + Text) or Normal Text
    try:
        if update.message.photo:
            # Handle Image analysis for Pro/Free users
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            
            prompt_text = user_message if user_message else "Describe this image in detail."
            
            response = gemini_client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[
                    prompt_text,
                    {"mime_type": "image/jpeg", "data": bytes(photo_bytes)}
                ]
            )
        else:
            # Standard Text Generation
            response = gemini_client.models.generate_content(
                model='gemini-3.6-flash',
                contents=user_message
            )

        reply_output = f"{response.text}\n\n💬 (Quota left: {remaining})"
        await send_long_message(update, reply_output)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error occurred with AI model: {e}")

if __name__ == '__main__':
    keep_alive()
    
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Handle both text and photo inputs
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & (~filters.COMMAND), handle_message))
    application.add_handler(MessageHandler(filters.COMMAND, handle_message))
    
    print("Bot with Pro features is starting...")
    application.run_polling()
                    
