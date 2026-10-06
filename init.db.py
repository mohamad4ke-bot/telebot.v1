import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DB_NAME = "chatbot.db"

def setup_database():
    logger.info("Initializing database setup...")
    try:
        with sqlite3.connect(DB_NAME, timeout=10.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            cursor = conn.cursor()
            
            # Conversation memory
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    chat_id TEXT PRIMARY KEY,
                    history_json TEXT NOT NULL
                )
            """)
            
            # Outbound message queue (Linear Throttler)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS outbound_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            
        logger.info(f"✅ Success! Database '{DB_NAME}' initialized with queue table.")
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")

if __name__ == "__main__":
    setup_database()