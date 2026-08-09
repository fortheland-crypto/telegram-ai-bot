import os
import requests
from fastapi import FastAPI, Request

app = FastAPI()

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Ты — вежливый, умный и полезный ассистент в Telegram. Ты отвечаешь четко, понятно и доброжелательно на любые вопросы."
)

def send_telegram_message(bot_token: str, chat_id: int, text: str):
    """Sends a text message to Telegram with safe Markdown fallback."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # Split text if longer than Telegram limit
    max_len = 4000
    chunks = [text[i:i+max_len] for i in range(0, len(text), max_len)] if len(text) > max_len else [text]

    for chunk in chunks:
        # Try sending with Markdown formatting
        res = requests.post(
            url,
            json={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"},
            timeout=10
        )
        
        # If Markdown parsing fails (Telegram Bad Request 400), fallback to plain text
        if res.status_code != 200:
            requests.post(
                url,
                json={"chat_id": chat_id, "text": chunk},
                timeout=10
            )

@app.get("/")
async def root():
    return {"status": "online", "service": "Telegram AI Bot on Vercel (Groq Llama-3.3)"}

@app.post("/")
@app.post("/webhook")
async def webhook(request: Request):
    """Serverless Webhook endpoint for Telegram Updates."""
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

    try:
        data = await request.json()
        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()

        if not chat_id or not text:
            return {"status": "ignored"}

        # Handle commands
        if text == "/start":
            reply = "👋 **Привет! Я Telegram-бот со встроенным ИИ на базе Groq (Llama 3.3).**\n\nЗадай мне любой вопрос!"
        elif text == "/help":
            reply = "💡 **Справка:**\nЗадавай любые вопросы в чат, и я отвечу с помощью нейросети Groq Llama-3.3-70B."
        elif text == "/info":
            reply = f"ℹ️ **Провайдер:** Groq\n**Модель:** `{groq_model}`\n**Хостинг:** Vercel 24/7"
        else:
            if not groq_key:
                reply = "⚠️ Ошибка: GROQ_API_KEY не установлен."
            else:
                # Query Groq API directly
                groq_url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": groq_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0.7
                }
                res = requests.post(groq_url, json=payload, headers=headers, timeout=15)
                if res.status_code == 200:
                    res_json = res.json()
                    reply = res_json["choices"][0]["message"]["content"].strip()
                else:
                    reply = f"❌ Ошибка ИИ ({res.status_code}): {res.text}"

        # Send reply to Telegram with safe fallback
        if bot_token and reply:
            send_telegram_message(bot_token, chat_id, reply)

        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
