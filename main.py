import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
# Agar aapke code me Gemini/Google AI ki library hai toh woh yahan import hogi
# import google.generativeai as genai

# ================= CONFIGURATION =================
# Apne Telegram Bot ka token yahan dalein (ya environment variable se lein)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "Aapka_Telegram_Bot_Token")

# Hugging Face Access Token jo abhi aapne banaya hai
HF_TOKEN = "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"
VIDEO_API_URL = "https://api-inference.huggingface.co/models/cerspense/zeroscope_v2_500w"

headers = {"Authorization": f"Bearer {HF_TOKEN}"}

# ================= VIDEO GENERATION FUNCTION =================
def generate_video(prompt_text):
    payload = {"inputs": prompt_text}
    response = requests.post(VIDEO_API_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.content
    else:
        print("Video Error:", response.text)
        return None

# ================= TELEGRAM COMMANDS =================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! Main hoon **Bisroid Ai Bot**.\n\n"
        "Aap mujhse chat kar sakte hain aur ab free video bhi generate kar sakte hain!\n"
        "Commands:\n"
        "• /video [text prompt] - Video banane ke liye"
    )

async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = " ".join(context.args)
    if not user_prompt:
        await update.message.reply_text("Kripya video ka prompt dein, jaise: /video a cat playing guitar")
        return

    await update.message.reply_text("🎬 Video generate ho raha hai, isme 1-2 minute ka samay lag sakta hai...")
    
    video_bytes = generate_video(user_prompt)
    
    if video_bytes:
        with open("generated_video.mp4", "wb") as f:
            f.write(video_bytes)
        
        with open("generated_video.mp4", "rb") as video_file:
            await update.message.reply_video(video=video_file, caption=f"Prompt: {user_prompt}")
    else:
        await update.message.reply_text("Maaf kijiye, free video model abhi busy hai ya load ho raha hai. Thodi der baad try karein.")

# (Agar aapka purana chat handler ya doosri functions hain, unhe aap yahan niche rakh sakte hain)

# ================= MAIN FUNCTION =================
def main():
    # Application builder setup
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers add karna
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("video", video_command))
    
    # Bot ko start karna (Polling)
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
