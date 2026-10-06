import os
import time
import requests
import logging
from dotenv import load_dotenv
from gptv5 import gpt4_reply

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def delete_active_webhook():
    """Telegram refuses getUpdates if a webhook is currently registered."""
    try:
        res = requests.get(f"{BASE_URL}/deleteWebhook", timeout=10)
        logger.info(f"[INIT] Webhook cleared: {res.json().get('description')}")
    except Exception as e:
        logger.warning(f"[INIT] Failed to clear webhook: {e}")

def send_message(chat_id: int, text: str):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code != 200:
            logger.error(f"[TELEGRAM API ERROR] Code {res.status_code}: {res.text}")
    except Exception as e:
        logger.error(f"[SEND ERROR] Could not reach Telegram: {e}")

def start_polling():
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN is missing from .env environment variables.")
        return

    delete_active_webhook()
    logger.info("🚀 Starting Long Polling bot engine...")

    offset = None

    while True:
        try:
            # timeout=30 keeps the connection open up to 30s waiting for updates (Long Polling)
            params = {"timeout": 30, "offset": offset}
            response = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=35)

            if response.status_code == 200:
                data = response.json()
                updates = data.get("result", [])

                for update in updates:
                    # Update offset to update_id + 1 so Telegram knows we processed it
                    offset = update["update_id"] + 1

                    message = update.get("message", {})
                    recipient_chat_id = message.get("chat", {}).get("id")

                    if not recipient_chat_id:
                        continue

                    user_msg = message.get("text", "")

                    if not user_msg or not user_msg.strip():
                        ai_reply = "عيني، أنا أكدر اجاوب بس الرسائل النصية حالياً. شلون أگدر أساعدك؟"
                    else:
                        ai_reply = gpt4_reply(recipient_chat_id, user_msg)

                    send_message(recipient_chat_id, ai_reply)
                    logger.info(f"[SUCCESS] Replied to update_id {update['update_id']} for chat {recipient_chat_id}")

            elif response.status_code == 409:
                logger.error("❌ Conflict: Another instance of this bot is already running!")
                time.sleep(5)

        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Network error during polling ({e}). Reconnecting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"❌ Unexpected polling error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    start_polling()