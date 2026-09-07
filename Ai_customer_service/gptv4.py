import os
import json
import sqlite3
import time
import requests
from threading import Thread, Lock
from flask import Flask, request, jsonify
from openai import OpenAI

# External sheet module compatibility fallback
try:
    from sheetsv2 import get_business_data
except ImportError:
    def get_business_data():
        sheet_url = os.getenv("GOOGLE_SHEET_URL", "")
        if not sheet_url:
            return "Business data temporarily unavailable."
        try:
            res = requests.get(sheet_url, timeout=10)
            res.raise_for_status()
            return res.text
        except Exception as e:
            return f"Business data temporarily unavailable: {e}"

API_KEY = os.getenv("your_ai_api_key")
TELEGRAM_BOT_TOKEN = os.getenv("your_bot_token")

client = OpenAI(api_key=API_KEY)
app = Flask(__name__)

# ==========================================
# 🛠️ GLOBAL MEMORY & THREAD-SAFETY CONTROLS
# ==========================================
db_lock = Lock()
knowledge_lock = Lock()
cached_knowledge = "بيانات العمل غير متوفرة حالياً."
DB_NAME = "chatbot.db"


def background_sheets_worker():
    """Updates memory cache in RAM every 10 minutes without blocking web threads."""
    global cached_knowledge
    while True:
        try:
            fresh_data = get_business_data()
            if fresh_data and "Business data temporarily unavailable" not in fresh_data:
                with knowledge_lock:
                    cached_knowledge = fresh_data
                print("✅ [Background Worker] Business knowledge successfully synchronized.")
        except Exception as e:
            print(f"⚠️ [Background Worker] Sheet Sync Failed: {e}")
        
        time.sleep(600)


# Start background worker daemon on import
worker_thread = Thread(target=background_sheets_worker, daemon=True)
worker_thread.start()


# ==========================================
# 💾 SAFE DATABASE INTERFACES (WITH LOCKS)
# ==========================================

def init_db():
    """Creates local database file and sets up schema safely under thread lock."""
    with db_lock:
        with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    chat_id TEXT PRIMARY KEY,
                    history_json TEXT NOT NULL
                )
            """)
            conn.commit()


def load_history(chat_id: str) -> list:
    """Retrieves past user-assistant message log with strict lock isolation."""
    with db_lock:
        with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT history_json FROM memory WHERE chat_id = ?", (str(chat_id),))
            row = cursor.fetchone()

    if row and row[0]:
        try:
            history = json.loads(row[0])
            # Guarantee system prompts never bleed into loaded chat logs
            return [msg for msg in history if isinstance(msg, dict) and msg.get("role") != "system"]
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def save_history(chat_id: str, history_list: list):
    """Persists chat dialogue without saving injected system prompts to SQLite."""
    # Filter out system instruction payloads to prevent DB bloat
    clean_history = [msg for msg in history_list if msg.get("role") != "system"]
    
    with db_lock:
        with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO memory (chat_id, history_json) VALUES (?, ?)",
                (str(chat_id), json.dumps(clean_history))
            )
            conn.commit()


# Initialize database table safely upon script startup
init_db()


# ==========================================
# 🚀 OPTIMIZED PRODUCTION GPT ENGINE
# ==========================================

def gpt4_reply(chat_id: str, msg_txt: str) -> str:
    # 1. Fetch clean historical messages
    raw_history = load_history(chat_id)
    
    # 2. Sliding window memory constraint: Keep only last 10 messages
    conversation_only = raw_history[-10:]
    
    # 3. Pull live context from global memory cache
    with knowledge_lock:
        current_knowledge = cached_knowledge
    
        fresh_system_prompt = {
        "role": "system",
        "content": (
            "You are a professional customer support assistant for an Iraqi business. "
            "Use this exact live data to check product availability, descriptions, and prices:\n\n"
            f"{current_knowledge}\n\n"
            "WHEN TO GIVE THE SUPPORT USERNAME (@YOUR_TELEGRAM_USERNAME):\n"
            "1. If the user asks for a product, price, or service NOT listed in the live data.\n"
            "2. If you cannot understand the user's request or don't know the answer.\n"
            "3. If the user asks to speak to a real human or customer support.\n"
            "4. If you notice you are repeating yourself or hitting a wall.\n\n"
            "In any of these cases, apologize politely in Iraqi Arabic and instruct them to contact @YOUR_TELEGRAM_USERNAME directly.\n\n"
            "Reply natively in Iraqi Arabic."
        )
    }
    # 5. Assemble runtime payload
    messages_payload = [fresh_system_prompt] + conversation_only + [{"role": "user", "content": msg_txt}]
    
    try:
        # 6. Call OpenAI chat completion
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_payload,
            temperature=0.7
        )
        
        ai_reply = response.choices[0].message.content
        
        # 7. Construct clean history log (excluding system prompt)
        updated_history = conversation_only + [
            {"role": "user", "content": msg_txt},
            {"role": "assistant", "content": ai_reply}
        ]
        
        # 8. Save clean log back to database
        save_history(chat_id, updated_history)
        
        return ai_reply

    except Exception as e:
        print(f"❌ OpenAI Execution Error: {e}")
        return "عذراً، صارت مشكلة بالسيرفر. يرجى المحاولة بعد قليل."