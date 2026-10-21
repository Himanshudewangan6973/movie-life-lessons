import os
import csv
import time
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from google import genai
from google.genai import types

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load API Keys from environment
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not GEMINI_API_KEY or not TELEGRAM_BOT_TOKEN:
    print("[Error] Missing GEMINI_API_KEY or TELEGRAM_BOT_TOKEN environment variables.")
    exit(1)

# Initialize GenAI Client
genai_client = genai.Client(api_key=GEMINI_API_KEY)
CSV_FILENAME = "movie_life_lessons.csv"

def verify_csv_exists():
    """Ensures the CSV file exists with the 9 core headers. Never overwrites existing data."""
    headers = [
        "official_title", "release_year", "imdb_rating", 
        "micro_summary", "target_age_group", "socioeconomic_context", 
        "life_condition_trigger", "slang_and_cultural_anchors", "core_psychological_lesson"
    ]
    if not os.path.exists(CSV_FILENAME):
        with open(CSV_FILENAME, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        print(f"[Info] Created new '{CSV_FILENAME}' with standard 9-column headers.")
    else:
        print(f"[Info] Connected to existing '{CSV_FILENAME}'. Append-only mode active.")

def auto_generate_movie_entry(user_input: str) -> list:
    """Uses gemini-3.8-flash to generate strictly 9 pipe-separated fields."""
    prompt = f"""
    Analyze the movie input query: '{user_input}'.
    Identify the exact, official full movie title and release year, even if the user provided an incomplete or fuzzy name.
    
    Return ONLY a valid pipe-separated string (|) containing these exact 9 fields in order (no markdown, no extra text, no intro):
    1. Official Full Movie Title (Cleaned & corrected, e.g., 'Golmaal: Fun Unlimited')
    2. Release Year (e.g., 2006)
    3. IMDb Rating (e.g., 7.4/10)
    4. Micro-summary (Strictly 5 words or less using Gen-Z/Millennial tone)
    5. Target Age Group (e.g., Early Adulthood (18–24))
    6. Socioeconomic Context (e.g., Unemployed urban youth)
    7. Life Condition / Trigger (The specific real-life crisis)
    8. Slang & Cultural Anchors (Comma-separated hashtags like #JugaadLife, #SlackerCore)
    9. Core Psychological Lesson (Actionable 1-sentence takeaway)
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = genai_client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                )
            )
            fields = [f.strip() for f in response.text.split("|")]
            # Strict validation: must be exactly 9 fields to protect database structure
            if len(fields) == 9:
                return fields
        except Exception as e:
            print(f"[Warning] Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                raise e
    raise Exception("Failed to generate valid 9-field entry after multiple retries.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responds to the /start command."""
    await update.message.reply_text(
        "👋 Welcome to Movie Life Lessons Logger!\n\n"
        "Send me any movie name, and I will auto-correct the title, fetch the year/IMDb rating, and cleanly append it to your 9-column database!"
    )

async def handle_movie_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes incoming text messages as movie titles."""
    user_input = update.message.text.strip()
    if not user_input:
        return

    status_msg = await update.message.reply_text(f"⚡ Processing '{user_input}'...")

    try:
        data = auto_generate_movie_entry(user_input)
        
        # Safely append the strictly formatted 9-column row without touching existing data
        with open(CSV_FILENAME, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(data)
        
        response_text = (
            f"🎬 *Official Title:* {data[0]} ({data[1]})\n"
            f"⭐ *IMDb Rating:* {data[2]}\n\n"
            f"📌 *Micro-summary:* {data[3]}\n"
            f"🎯 *Target Age:* {data[4]}\n"
            f"💵 *Socioeconomic Context:* {data[5]}\n"
            f"⚡ *Trigger/Crisis:* {data[6]}\n"
            f"🏷️ *Anchors:* {data[7]}\n"
            f"💡 *Lesson:* {data[8]}"
        )
        await status_msg.edit_text(response_text, parse_mode='Markdown')

    except Exception as e:
        await status_msg.edit_text(f"❌ Error processing '{user_input}': {str(e)}")

def main():
    verify_csv_exists()
    print("🚀 Starting Telegram Bot Listener (9-Column Safe Append Mode)...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_input))

    print("🤖 Bot is active and listening on Telegram! Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
