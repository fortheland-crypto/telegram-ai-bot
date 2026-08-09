import os
import requests
from fastapi import FastAPI, Request

app = FastAPI()

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Ты — вежливый, умный и полезный ассистент в Telegram. Ты отвечаешь четко, понятно и доброжелательно на любые вопросы."
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
                reply = "⚠️ Ошибка: GROQ_API_KEY не задан в настройках Vercel."
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

        # Post reply to Telegram API
        if bot_token and reply:
            telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            requests.post(
                telegram_url,
                json={
                    "chat_id": chat_id,
                    "text": reply,
                    "parse_mode": "Markdown"
                },
                timeout=10
            )

        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
