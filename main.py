import os
import json
from datetime import datetime, timedelta
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ===== CONFIGURATION =====
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")  # Ab token Render ke Environment Variable se aayega
VIDEO_API_URL = "https://api-inference.huggingface.co/models/cerspense/zeroscope_v2_500w"

headers = {"Authorization": f"Bearer {HF_TOKEN}"}

ADMIN_IDS = [8533127502]  # Aapki Admin ID
DB_FILE = "premium_users.json"
user_usage = {}
DAILY_FREE_LIMIT = 2

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"monthly": {}, "lifetime": []}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_video(prompt_text):
    payload = {"inputs": prompt_text}
    try:
        response = requests.post(VIDEO_API_URL, headers=headers, json=payload, timeout=120)
        if response.status_code == 200:
            return response.content
        else:
            print(f"Video Error Status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"API Request Exception: {e}")
        return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Bisroid Ai Bot!\n\n"
        f"🎁 Free users ke liye rozane {DAILY_FREE_LIMIT} videos ki limit hai.\n"
        "✨ Unlimited access ke liye /premium type karein."
    )

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 **Bisroid Ai Pro / Premium**\n\n"
        "Unlimited AI Video Generation ke liye Pro banayein!\n"
        "👉 Payment link: https://razorpay.me/@biswakalyanborah\n\n"
        "Payment karne ke baad apna screenshot aur Telegram ID Admin ko bhejein!"
    )

async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Yeh command sirf Admin chala sakta hai.")
        return
    if not context.args:
        await update.message.reply_text("Kripya User ID dein. Jaise: /addpremium 987654321")
        return
    try:
        target_id = str(context.args[0])
        db = load_db()
        expiry_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        db["monthly"][target_id] = expiry_date
        save_db(db)
        await update.message.reply_text(f"✅ User `{target_id}` ko **1 Month** ke liye Premium de diya gaya hai.\nExpiry: {expiry_date}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def add_lifetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Yeh command sirf Admin chala sakta hai.")
        return
    if not context.args:
        await update.message.reply_text("Kripya User ID dein. Jaise: /addlifetime 987654321")
        return
    try:
        target_id = int(context.args[0])
        db = load_db()
        if target_id not in db["lifetime"]:
            db["lifetime"].append(target_id)
            save_db(db)
            await update.message.reply_text(f"✅ User `{target_id}` ko **Lifetime** Premium bana diya gaya hai.")
        else:
            await update.message.reply_text("⚠️ Yeh user pehle se hi Lifetime list me hai.")
    except ValueError:
        await update.message.reply_text("❌ Galat User ID format. Kripya sirf numbers dalein.")

async def remove_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Yeh command sirf Admin chala sakta hai.")
        return
    if not context.args:
        await update.message.reply_text("Kripya User ID dein. Jaise: /removepremium 987654321")
        return
    target_id = context.args[0]
    db = load_db()
    removed = False
    if target_id in db["monthly"]:
        del db["monthly"][target_id]
        removed = True
    try:
        int_target = int(target_id)
        if int_target in db["lifetime"]:
            db["lifetime"].remove(int_target)
            removed = True
    except ValueError:
        pass
    if removed:
        save_db(db)
        await update.message.reply_text(f"🗑️ User `{target_id}` ka premium access hata diya gaya hai.")
    else:
        await update.message.reply_text("⚠️ Yeh user premium list me nahi mila.")

async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    str_user_id = str(user_id)
    user_prompt = " ".join(context.args)

    if not user_prompt:
        await update.message.reply_text("Kripya video ka prompt dein, jaise: /video a futuristic city")
        return

    db = load_db()
    is_premium = False

    if user_id in ADMIN_IDS:
        is_premium = True
    elif user_id in db["lifetime"]:
        is_premium = True
    elif str_user_id in db["monthly"]:
        expiry_str = db["monthly"][str_user_id]
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() < expiry_date:
                is_premium = True
            else:
                del db["monthly"][str_user_id]
                save_db(db)
        except Exception:
            pass

    if not is_premium:
        from datetime import date
        today = str(date.today())
        if user_id not in user_usage or user_usage[user_id]["date"] != today:
            user_usage[user_id] = {"date": today, "count": 0}
        if user_usage[user_id]["count"] >= DAILY_FREE_LIMIT:
            await update.message.reply_text(
                "🚨 Aapki Aaj ki Free Limit Khatam Ho Chuki Hai!\n\n"
                "✨ Unlimited access ke liye /premium type karein."
            )
            return
        user_usage[user_id]["count"] += 1

    await update.message.reply_text("🎬 Video generate ho raha hai, isme 1-2 minute ka samay lag sakta hai...")
    
    video_bytes = generate_video(user_prompt)
    
    if video_bytes:
        with open("generated_video.mp4", "wb") as f:
            f.write(video_bytes)
        with open("generated_video.mp4", "rb") as video_file:
            await update.message.reply_video(video=video_file, caption=f"Prompt: {user_prompt}")
    else:
        await update.message.reply_text("⚠️ Hugging Face model abhi loading state me hai ya token expire ho gaya hai. Kripya Render environment variables check karein!")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("premium", premium_command))
    app.add_handler(CommandHandler("addpremium", add_premium))
    app.add_handler(CommandHandler("addlifetime", add_lifetime))
    app.add_handler(CommandHandler("removepremium", remove_premium))
    app.add_handler(CommandHandler("video", video_command))
    
    print("Bot is running perfectly...")
    app.run_polling()

if __name__ == "__main__":
    main()
