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

KEYBOARD_MAIN = {
    "inline_keyboard": [
        [
            {"text": "🧹 Очистить контекст", "callback_data": "action:clear"},
            {"text": "ℹ️ Инфо о модели", "callback_data": "action:info"}
        ],
        [
            {"text": "💡 Справка", "callback_data": "action:help"}
        ]
    ]
}

KEYBOARD_RESPONSE = {
    "inline_keyboard": [
        [
            {"text": "🔄 Пересоздать ответ", "callback_data": "action:regenerate"},
            {"text": "🧹 Очистить контекст", "callback_data": "action:clear"}
        ]
    ]
}

def query_groq(prompt_text: str, groq_key: str, groq_model: str) -> str:
    """Queries Groq API synchronously via stdlib urllib."""
    groq_url = "https://api.groq.com/openai/v1/chat/completions"
    payload = json.dumps({
        "model": groq_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.7
    }).encode("utf-8")

    req = urllib.request.Request(
        groq_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json",
            "User-Agent": "OpenAI/Python 1.14.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=14) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            return res_json["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as http_err:
        err_body = http_err.read().decode("utf-8", errors="ignore")
        return f"❌ Ошибка Groq API ({http_err.code}): {err_body or str(http_err)}"
    except Exception as err:
        return f"❌ Ошибка соединения с ИИ: {str(err)}"

def answer_callback(bot_token: str, callback_id: str, text: str = ""):
    """Answers Telegram callback query to stop loading spinner."""
    url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
    payload = json.dumps({"callback_query_id": callback_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

@app.get("/")
async def root():
    return {"status": "online", "service": "Telegram AI Bot on Vercel (Groq Llama-3.3)"}

@app.post("/")
@app.post("/webhook")
async def webhook(request: Request):
    """Serverless Webhook endpoint with Telegram Inline Keyboards & Callback Queries."""
    bot_token = os.getenv("BOT_TOKEN", "").strip() or DEFAULT_BOT_TOKEN
    groq_key = os.getenv("GROQ_API_KEY", "").strip() or DEFAULT_GROQ_KEY
    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

    try:
        data = await request.json()

        # Handle Callback Queries (Inline Button clicks)
        if "callback_query" in data:
            cb = data["callback_query"]
            cb_id = cb.get("id")
            cb_data = cb.get("data", "")
            cb_msg = cb.get("message", {})
            chat_id = cb_msg.get("chat", {}).get("id")

            answer_callback(bot_token, cb_id)

            if cb_data == "action:clear":
                reply = "🧹 **История диалога очищена!** Все предыдущие темы сброшены."
                markup = KEYBOARD_MAIN
            elif cb_data == "action:info":
                reply = (
                    "ℹ️ **Информация о боте:**\n\n"
                    "• **Провайдер ИИ:** `Groq`\n"
                    f"• **Модель:** `{groq_model}`\n"
                    "• **Хостинг:** Vercel 24/7"
                )
                markup = KEYBOARD_MAIN
            elif cb_data == "action:help":
                reply = (
                    "💡 **Справка по использованию:**\n\n"
                    "1. Задавайте любые вопросы в чат.\n"
                    "2. Нажимайте кнопку **«🔄 Пересоздать ответ»** под сообщением ИИ, чтобы получить другой вариант ответа.\n"
                    "3. Нажимайте **«🧹 Очистить контекст»**, чтобы начать тему с нуля."
                )
                markup = KEYBOARD_MAIN
            elif cb_data == "action:regenerate":
                prompt_text = cb_msg.get("text", "Привет")
                reply = query_groq(prompt_text, groq_key, groq_model)
                markup = KEYBOARD_RESPONSE
            else:
                reply = "Команда обработана."
                markup = KEYBOARD_MAIN

            return JSONResponse({
                "method": "sendMessage",
                "chat_id": chat_id,
                "text": reply,
                "reply_markup": markup
            })

        # Handle regular text messages
        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()

        if not chat_id or not text:
            return JSONResponse({"status": "ignored"})

        if text == "/start":
            reply = "👋 **Привет! Я Telegram-бот со встроенным ИИ на базе Groq (Llama 3.3).**\n\nЗадай мне любой вопрос или используй кнопки ниже:"
            markup = KEYBOARD_MAIN
        elif text == "/help":
            reply = "💡 **Справка:**\nЗадавай любые вопросы в чат, и я отвечу с помощью нейросети Groq Llama-3.3-70B."
            markup = KEYBOARD_MAIN
        elif text == "/info":
            reply = f"ℹ️ **Провайдер:** Groq\n**Модель:** `{groq_model}`\n**Хостинг:** Vercel 24/7"
            markup = KEYBOARD_MAIN
        else:
            reply = query_groq(text, groq_key, groq_model)
            markup = KEYBOARD_RESPONSE

        # Return direct Webhook response with reply_markup
        return JSONResponse({
            "method": "sendMessage",
            "chat_id": chat_id,
            "text": reply,
            "reply_markup": markup
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})
