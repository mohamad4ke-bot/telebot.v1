import os
import requests
from flask import Flask, request, jsonify
from gptv4 import gpt4_reply
from dotenv import load_dotenv

# 1. Load hidden keys from environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# 2. Initialize Flask application
app = Flask(__name__)


# 3. Webhook endpoint
@app.route("/telegram_webhook", methods=["POST"])
def telegram_webhook():
    try:
        incoming_data = request.get_json(silent=True)
        if not incoming_data:
            return jsonify({"status": "ignored", "reason": "empty payload"}), 200

        print(f"\n[INCOMING DATA]: {incoming_data}")

        # Safely extract message details without nested crash-prone blocks
        message = incoming_data.get("message", {})
        recipient_chat_id = message.get("chat", {}).get("id")

        if not recipient_chat_id:
            print("[Debug] No valid recipient chat found; dropped packet safely.")
            return jsonify({"status": "ignored", "reason": "no recipient chat found"}), 200

        user_msg = message.get("text", "")

        # Guard clause: Handle non-text messages (photos, voice notes, stickers)
        if not user_msg or not user_msg.strip():
            ai_reply = "عيني، أنا أكدر اجاوب بس الرسائل النصية حالياً. شلون أگدر أساعدك؟"
        else:
            ai_reply = gpt4_reply(recipient_chat_id, user_msg)

        print(f"\n[SUCCESS] AI Replied: {ai_reply}")

        # Send response payload back to Telegram API
        if TELEGRAM_TOKEN:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {
                "chat_id": recipient_chat_id,
                "text": ai_reply
            }
            requests.post(url, json=payload, timeout=10)
        else:
            print("[ERROR] TELEGRAM_BOT_TOKEN is missing from environment variables.")

        return jsonify({"status": "success", "reply": ai_reply}), 200

    except Exception as e:
        print(f"\n[ERROR] Server loop exception: {e}")
        # Always return 200 to Telegram to prevent infinite retry loop storms on server errors
        return jsonify({"status": "error", "details": str(e)}), 200


if __name__ == "__main__":
    app.run(port=5000, threaded=True, debug=True)