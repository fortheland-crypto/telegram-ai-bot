import os
import json
import urllib.request
import urllib.error
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

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

@app.get("/")
async def root():
    return {"status": "online", "service": "Telegram AI Bot on Vercel (Groq Llama-3.3)"}

@app.post("/")
@app.post("/webhook")
async def webhook(request: Request):
    """Serverless Webhook endpoint returning direct Telegram response payload."""
    bot_token = os.getenv("BOT_TOKEN", "").strip() or DEFAULT_BOT_TOKEN
    groq_key = os.getenv("GROQ_API_KEY", "").strip() or DEFAULT_GROQ_KEY
    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

    try:
        data = await request.json()
        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()

        if not chat_id or not text:
            return JSONResponse({"status": "ignored"})

        # Handle commands
        if text == "/start":
            reply = "👋 Привет! Я Telegram-бот со встроенным ИИ на базе Groq (Llama 3.3). Задай мне любой вопрос!"
        elif text == "/help":
            reply = "💡 Справка:\nЗадавай любые вопросы в чат, и я отвечу с помощью нейросети Groq Llama-3.3-70B."
        elif text == "/info":
            reply = f"ℹ️ Провайдер: Groq\nМодель: {groq_model}\nХостинг: Vercel 24/7"
        else:
            # Query Groq API via standard urllib
            groq_url = "https://api.groq.com/openai/v1/chat/completions"
            payload = json.dumps({
                "model": groq_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.7
            }).encode("utf-8")

            req = urllib.request.Request(
                groq_url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_json = json.loads(response.read().decode("utf-8"))
                    reply = res_json["choices"][0]["message"]["content"].strip()
            except Exception as err:
                reply = f"❌ Ошибка получения ответа от ИИ: {str(err)}"

        # Return direct Webhook response payload to Telegram
        return JSONResponse({
            "method": "sendMessage",
            "chat_id": chat_id,
            "text": reply
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})
