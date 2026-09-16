import os
import json
from datetime import datetime, timedelta
import requests
import time
import threading
import http.server
import socketserver
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# ===== RENDER PORT FIX (DUMMY WEB SERVER) =====
PORT = int(os.getenv("PORT", 10000))

class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bisroid Ai Bot is running and alive!")

def run_web_server():
    try:
        with socketserver.TCPServer(("", PORT), HealthCheckHandler) as httpd:
            print(f"Web server running on port {PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Web server error: {e}")

threading.Thread(target=run_web_server, daemon=True).start()

# ===== CONFIGURATION =====
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

VIDEO_API_URL = "https://api-inference.huggingface.co/models/cerspense/zeroscope_v2_500w"
# Updated to a more stable and fast image model
IMAGE_API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

ADMIN_IDS = [8533127502]
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
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(VIDEO_API_URL, headers=headers, json=payload, timeout=180)
            if response.status_code == 200:
                return response.content
            elif response.status_code == 503:
                time.sleep(20)
                continue
            else:
                return None
        except Exception:
            time.sleep(10)
    return None

def generate_image(prompt_text):
    payload = {"inputs": prompt_text}
    max_retries = 4
    for attempt in range(max_retries):
        try:
            response = requests.post(IMAGE_API_URL, headers=headers, json=payload, timeout=90)
            if response.status_code == 200:
                return response.content
            elif response.status_code == 503:
                print(f"Image model loading, waiting... (Attempt {attempt+1})")
                time.sleep(15)
                continue
            else:
                print(f"Image API error code: {response.status_code}, response: {response.text}")
                time.sleep(5)
        except Exception as e:
            print(f"Image exception: {e}")
            time.sleep(5)
    return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Bisroid Ai Bot!\n\n"
        "🌐 Aap mujhse **English, Assamese (অসমীয়া), aur Hindi** me baat kar sakte hain.\n"
        "❓ Aap koi bhi sawal pooch sakte hain.\n"
        "🖼️ Image generate karne ke liye: `/image [prompt]`\n"
        "🎬 Video generate karne ke liye: `/video [prompt]`\n"
        f"🎁 Free users ke liye rozane {DAILY_FREE_LIMIT} videos/images ki limit hai.\n\n"
        "✨ Unlimited access ke liye /premium type karein."
    )

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 **Bisroid Ai Pro / Premium**\n\n"
        "Unlimited AI Generation ke liye Pro banayein!\n"
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

async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = " ".join(context.args)

    if not user_prompt:
        await update.message.reply_text("Kripya image ka prompt dein, jaise: `/image a beautiful sunset over mountains`")
        return

    await update.message.reply_text("🎨 Image generate ho rahi hai, thoda intezaar karein...")
    
    image_bytes = generate_image(user_prompt)
    
    if image_bytes:
        with open("generated_image.jpg", "wb") as f:
            f.write(image_bytes)
        with open("generated_image.jpg", "rb") as image_file:
            await update.message.reply_photo(photo=image_file, caption=f"Prompt: {user_prompt}")
    else:
        await update.message.reply_text("⚠️ Image generate karne me samasya aayi. Model abhi busy hai, kripya 1 minute baad dubara try karein!")

async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    str_user_id = str(user_id)
    user_prompt = " ".join(context.args)

    if not user_prompt:
        await update.message.reply_text("Kripya video ka prompt dein, jaise: `/video a futuristic city`")
        return

    db = load_db()
    is_premium = user_id in ADMIN_IDS or user_id in db["lifetime"] or str_user_id in db["monthly"]

    if not is_premium:
        from datetime import date
        today = str(date.today())
        if user_id not in user_usage or user_usage[user_id]["date"] != today:
            user_usage[user_id] = {"date": today, "count": 0}
        if user_usage[user_id]["count"] >= DAILY_FREE_LIMIT:
            await update.message.reply_text("🚨 Aapki Aaj ki Free Limit Khatam Ho Chuki Hai!\n\n✨ Unlimited access ke liye /premium type karein.")
            return
        user_usage[user_id]["count"] += 1

    await update.message.reply_text("🎬 Video generate ho raha hai, model load hone me 2-3 minute lag sakte hain... Kripya intezaar karein!")
    
    video_bytes = generate_video(user_prompt)
    
    if video_bytes:
        with open("generated_video.mp4", "wb") as f:
            f.write(video_bytes)
        with open("generated_video.mp4", "rb") as video_file:
            await update.message.reply_video(video=video_file, caption=f"Prompt: {user_prompt}")
    else:
        await update.message.reply_text("⚠️ Model abhi bhi busy ya offline hai. Kripya 2 minute baad dubara try karein!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text or text.startswith('/'):
        return

    if not ai_client:
        return

    try:
        system_instruction = (
            "You are Bisroid AI, a helpful assistant. "
            "You can fluently converse in English, Assamese (অসমীয়া), and Hindi. "
            "Detect the user's language and reply in the exact same language. "
            "Answer any questions accurately and friendly."
        )

        response = ai_client.models.generate_content(
            model='gemini-3.6-flash',
            contents=f"{system_instruction}\n\nUser Question: {text}"
        )
        
        reply_text = response.text
        if reply_text:
            await update.message.reply_text(reply_text)
    except Exception as e:
        print(f"Chat AI Error: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("premium", premium_command))
    app.add_handler(CommandHandler("addpremium", add_premium))
    app.add_handler(CommandHandler("addlifetime", add_lifetime))
    app.add_handler(CommandHandler("removepremium", remove_premium))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(CommandHandler("video", video_command))
    
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot with Stable Image & Video Generation is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
                
