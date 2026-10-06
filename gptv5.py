import os
import json
import sqlite3
import time
import logging
from threading import Thread, Lock
from openai import OpenAI

logger = logging.getLogger(__name__)

API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@YOUR_TELEGRAM_USERNAME")
BOT_LANGUAGE = os.getenv("BOT_LANGUAGE", "iraqi_arabic")

client = OpenAI(api_key=API_KEY)

FALLBACK_PROMPT = (
    "You are a support assistant. Live data:\n\n{current_knowledge}\n\n"
    "If unavailable or uncertain, ask to contact {telegram_username}."
)

ERROR_MESSAGES = {
    "english": "Sorry, a server error occurred. Please try again shortly.",
    "spanish": "Lo sentimos, ocurrió un error en el servidor. Por favor, intente de nuevo en un momento.",
    "iraqi_arabic": "عذراً، صارت مشكلة بالسيرفر. يرجى المحاولة بعد قليل."
}

try:
    with open("prompts.json", "r", encoding="utf-8") as f:
        PROMPTS = json.load(f)
except Exception as e:
    logger.error(f"Failed to load prompts.json: {e}")
    PROMPTS = {"iraqi_arabic": {"system_prompt": FALLBACK_PROMPT}}

db_lock = Lock()
knowledge_lock = Lock()
cached_knowledge = "بيانات العمل غير متوفرة حالياً."
DB_NAME = "chatbot.db"

def background_sheets_worker():
    """Syncs Google Sheets with Exponential Backoff on error."""
    global cached_knowledge
    try:
        from sheetsv2 import get_business_data
    except ImportError:
        logger.error("Failed to import sheetsv2. Using fallback data handler.")
        def get_business_data():
            return "Business data temporarily unavailable."

    retry_delay = 5       # Start retrying after 5 seconds
    max_delay = 600       # Cap delay at 10 minutes (600 seconds)

    while True:
        try:
            fresh_data = get_business_data()
            if fresh_data and "Business data temporarily unavailable" not in fresh_data:
                with knowledge_lock:
                    cached_knowledge = fresh_data
                logger.info("✅ [Background Worker] Business knowledge synchronized.")
                retry_delay = 5  # Reset retry timer on success
                time.sleep(max_delay)  # Wait 10 minutes before next routine check
            else:
                raise ValueError("Received invalid or empty sheet payload")

        except Exception as e:
            logger.warning(f"⚠️ [Background Worker] Sync failed ({e}). Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 3, max_delay)  # Exponential backoff (5s -> 15s -> 45s -> 135s...)

worker_thread = Thread(target=background_sheets_worker, daemon=True)
worker_thread.start()

def init_db():
    """Safety guard: Guarantees table exists and sets WAL mode on database creation."""
    with db_lock:
        conn = sqlite3.connect(DB_NAME, timeout=10.0, check_same_thread=False)
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    chat_id TEXT PRIMARY KEY,
                    history_json TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

init_db()

def load_history(chat_id: str) -> list:
    with db_lock:
        conn = sqlite3.connect(DB_NAME, timeout=10.0, check_same_thread=False)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT history_json FROM memory WHERE chat_id = ?", (str(chat_id),))
            row = cursor.fetchone()
            if row and row[0]:
                history = json.loads(row[0])
                return [msg for msg in history if isinstance(msg, dict) and msg.get("role") != "system"]
            return []
        except (json.JSONDecodeError, TypeError, sqlite3.Error) as e:
            logger.error(f"Error loading history for {chat_id}: {e}")
            return []
        finally:
            conn.close()

def save_history(chat_id: str, history_list: list):
    clean_history = [msg for msg in history_list if msg.get("role") != "system"]
    with db_lock:
        conn = sqlite3.connect(DB_NAME, timeout=10.0, check_same_thread=False)
        try:
            conn.execute("PRAGMA synchronous=NORMAL;")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO memory (chat_id, history_json) VALUES (?, ?)",
                (str(chat_id), json.dumps(clean_history))
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error saving history for {chat_id}: {e}")
        finally:
            conn.close()

def gpt4_reply(chat_id: str, msg_txt: str) -> str:
    raw_history = load_history(chat_id)
    conversation_only = raw_history[-10:]
    
    with knowledge_lock:
        current_knowledge = cached_knowledge

    lang_data = PROMPTS.get(BOT_LANGUAGE, PROMPTS.get("iraqi_arabic", {}))
    selected_prompt = lang_data.get("system_prompt", FALLBACK_PROMPT)
    
    formatted_prompt = selected_prompt.format(
        current_knowledge=current_knowledge,
        telegram_username=SUPPORT_USERNAME
    )

    fresh_system_prompt = {"role": "system", "content": formatted_prompt}
    messages_payload = [fresh_system_prompt] + conversation_only + [{"role": "user", "content": msg_txt}]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_payload,
            temperature=0.7
        )
        
        ai_reply = response.choices[0].message.content
        
        updated_history = conversation_only + [
            {"role": "user", "content": msg_txt},
            {"role": "assistant", "content": ai_reply}
        ]
        
        save_history(chat_id, updated_history)
        return ai_reply

    except Exception as e:
        logger.error(f"❌ OpenAI Execution Error: {e}")
        return ERROR_MESSAGES.get(BOT_LANGUAGE, ERROR_MESSAGES["iraqi_arabic"])