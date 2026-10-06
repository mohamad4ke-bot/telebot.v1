import os
import csv
import io
import requests
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def get_business_data() -> str:
    csv_url = os.getenv("SHEET_URL")
    
    if not csv_url:
        logger.error("❌ [sheets.py] Error: SHEET_URL environment variable is missing.")
        return "Business data temporarily unavailable."

    try:
        response = requests.get(csv_url, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"

        csv_file = io.StringIO(response.text)
        reader = csv.DictReader(csv_file)

        if not reader.fieldnames:
            return "No product data available inside the sheet right now."

        knowledge_lines = ["=== OFFICIAL BUSINESS & PRODUCT DATA ===\n"]

        for row in reader:
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
        logger.error(f"❌ Knowledge Base Processing Error: {e}")
        return "Business data temporarily unavailable."