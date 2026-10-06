import os
import requests
import logging
from flask import Flask, request, jsonify
from gptv5 import gpt4_reply
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

app = Flask(__name__)

@app.route("/telegram_webhook", methods=["POST"])
def telegram_webhook():
    try:
        incoming_data = request.get_json(silent=True)
        if not incoming_data:
            return jsonify({"status": "ignored", "reason": "empty payload"}), 200

        logger.info(f"[INCOMING DATA]: {incoming_data}")

        message = incoming_data.get("message", {})
        recipient_chat_id = message.get("chat", {}).get("id")

        if not recipient_chat_id:
            logger.warning("[Debug] No valid recipient chat found; dropped packet safely.")
            return jsonify({"status": "ignored", "reason": "no recipient chat found"}), 200

        user_msg = message.get("text", "")

        if not user_msg or not user_msg.strip():
            ai_reply = "عيني، أنا أكدر اجاوب بس الرسائل النصية حالياً. شلون أگدر أساعدك؟"
        else:
            ai_reply = gpt4_reply(recipient_chat_id, user_msg)

        logger.info(f"[SUCCESS] AI Replied: {ai_reply}")

        if TELEGRAM_TOKEN:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {
                "chat_id": recipient_chat_id,
                "text": ai_reply
            }
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code != 200:
                logger.error(f"[TELEGRAM API ERROR] Code {res.status_code}: {res.text}")
            else:
                logger.info(f"[SUCCESS] Message delivered to chat {recipient_chat_id}")
        else:
            logger.error("[ERROR] TELEGRAM_BOT_TOKEN is missing from environment variables.")

        return jsonify({"status": "success", "reply": ai_reply}), 200

    except Exception as e:
        logger.error(f"[ERROR] Server loop exception: {e}")
        return jsonify({"status": "error", "details": str(e)}), 200

if __name__ == "__main__":
    app.run(port=5000, threaded=True, debug=True)