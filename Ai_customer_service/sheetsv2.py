import os
import csv
import io
import requests
from dotenv import load_dotenv

# Ensure environment variables from .env are loaded
load_dotenv()


def get_business_data() -> str:
    csv_url = os.getenv("SHEET_URL")
    
    # Guard clause: Exit early if URL is missing
    if not csv_url:
        print("❌ [sheets.py] Error: SHEET_URL environment variable is missing.")
        return "Business data temporarily unavailable."

    try:
        # 1. Added explicit timeout to prevent hanging the background thread indefinitely
        response = requests.get(csv_url, timeout=10)
        response.raise_for_status()

        # 2. Force UTF-8 decoding to guarantee Iraqi Arabic text doesn't turn into gibberish
        response.encoding = "utf-8"

        # 3. Use DictReader with StringIO for cleaner, crash-proof CSV parsing
        csv_file = io.StringIO(response.text)
        reader = csv.DictReader(csv_file)

        if not reader.fieldnames:
            return "No product data available inside the sheet right now."

        knowledge_lines = ["=== OFFICIAL BUSINESS & PRODUCT DATA ===\n"]

        for row in reader:
            # Pair non-empty headers with non-empty values cleanly
            items = [
                f"{k.strip()}: {v.strip()}"
                for k, v in row.items()
                if k and v and v.strip()
            ]
            if items:
                knowledge_lines.append(f"- {' | '.join(items)}")

        if len(knowledge_lines) == 1:
            return "No product data available inside the sheet right now."

        return "\n".join(knowledge_lines)

    except Exception as e:
        print(f"❌ Knowledge Base Processing Error: {e}")
        return "Business data temporarily unavailable."