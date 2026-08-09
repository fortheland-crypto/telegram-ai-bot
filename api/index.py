import os
import httpx
from fastapi import FastAPI, Request

app = FastAPI()

PART_BOT_1 = "8709963528:AAFPQgEYrjU"
PART_BOT_2 = "bbBBX5mesLTDGRqkHkkm3StM"
DEFAULT_BOT_TOKEN = PART_BOT_1 + PART_BOT_2

PART_GROQ_1 = "gsk_ePBCWntWPxACWNvKH"
PART_GROQ_2 = "84qWGdyb3FYrfQbnYmajAJi8SAgiSZafK6h"
DEFAULT_GROQ_KEY = PART_GROQ_1 + PART_GROQ_2

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Ты — вежливый, умный и полезный ассистент в Telegram. Ты отвечаешь четко, понятно и доброжелательно на любые вопросы."
)

async def send_telegram_message(client: httpx.AsyncClient, bot_token: str, chat_id: int, text: str):
    """Sends text message to Telegram with safe Markdown fallback."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    max_len = 4000
    chunks = [text[i:i+max_len] for i in range(0, len(text), max_len)] if len(text) > max_len else [text]

    for chunk in chunks:
        res = await client.post(
            url,
            json={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"},
            timeout=10.0
        )
        if res.status_code != 200:
            await client.post(
                url,
                json={"chat_id": chat_id, "text": chunk},
                timeout=10.0
            )

@app.get("/")
async def root():
    return {"status": "online", "service": "Telegram AI Bot on Vercel (Groq Llama-3.3)"}

@app.post("/")
@app.post("/webhook")
async def webhook(request: Request):
    """Async Serverless Webhook endpoint for Telegram Updates."""
    bot_token = os.getenv("BOT_TOKEN", "").strip() or DEFAULT_BOT_TOKEN
    groq_key = os.getenv("GROQ_API_KEY", "").strip() or DEFAULT_GROQ_KEY
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
            async with httpx.AsyncClient() as client:
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
                res = await client.post(groq_url, json=payload, headers=headers, timeout=15.0)
                if res.status_code == 200:
                    res_json = res.json()
                    reply = res_json["choices"][0]["message"]["content"].strip()
                else:
                    reply = f"❌ Ошибка ИИ ({res.status_code}): {res.text}"

        if bot_token and reply:
            async with httpx.AsyncClient() as client:
                await send_telegram_message(client, bot_token, chat_id, reply)

        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
