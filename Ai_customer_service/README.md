# Local AI Customer Support Telegram Bot Engine

A high-performance, thread-safe Python Flask backend that connects a Telegram bot to OpenAI's GPT-4o-mini, using a background daemon worker to dynamically cache business inventory and data straight from a standard Google Sheet.

## 🛠️ Key Architectural Wins

- **Instant Momentum (Zero-to-Live in 5 Mins):** Completely plug-and-play codebase. Just drop your private API tokens into a `.env` file and execute.
- **Relief from Boring Grunt Work:** All complex data type sanitization, custom Iraqi Arabic fallback prompts, and API integration connections are pre-coded and fully operational.
- **Production-Ready Stability:**
  - **Background Caching Daemon:** Instead of spimming the Google Sheets API on every user message (which triggers immediate rate-limit blocks), a background thread safely caches your sheet data into RAM every 10 minutes.
  - **Thread-Safe Memory Locks:** Implements strict `threading.Lock` protocols to prevent database race conditions or crashes when multiple customers text the bot at the exact same millisecond.
  - **Token-Saving Context Window:** Features an automated sliding context window that retains only the last 10 chat messages, keeping your OpenAI API wallet safe from token bloat.

## 🚀 Prerequisites & Installation

1. **Clone/Extract the project files** into a clean directory on your environment.
2. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Your Environment Variables:**
   - Locate the `.env.example` file in the root directory.
   - Rename the file to exactly `.env`.
   - Open it and populate your credentials:
     ```env
     TELEGRAM_BOT_TOKEN=your_token_from_botfather
     OPENAI_API_KEY=your_openai_api_key
     SHEET_URL=your_published_google_sheet_csv_url
     ```

## 📊 Google Sheets Configuration
To use a Google Sheet as your free, lightweight Content Management System (CMS):
1. Open your target inventory or business knowledge Google Sheet.
2. Navigate to **File** ➡️ **Share** ➡️ **Publish to web**.
3. In the link settings dropdown, change "Web page" to **Comma-separated values (.csv)**.
4. Click **Publish**, copy the generated URL link, and paste it directly as your `SHEET_URL` variable inside your `.env` file.

## ⚡ Running the Bot
Execute the main application file via your terminal:
```bash
python mainv3.py
```
The Flask backend will spin up locally on port `5000`. Expose this port to the web using a tool like `ngrok` or deploy the codebase natively onto an app hosting tier (Render, Vercel, Railway), then set your destination URL string as your Telegram bot's active webhook endpoint.
