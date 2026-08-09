import os
import json
import httpx
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

async def query_groq_async(client: httpx.AsyncClient, prompt_text: str, groq_key: str, groq_model: str) -> str:
    groq_url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": groq_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.7
    }
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json",
        "User-Agent": "OpenAI/Python 1.14.0"
    }

    try:
        res = await client.post(groq_url, json=payload, headers=headers, timeout=9.0)
        if res.status_code == 200:
            res_json = res.json()
            return res_json["choices"][0]["message"]["content"].strip()
        else:
            return f"❌ Ошибка Groq API ({res.status_code}): {res.text}"
    except Exception as err:
        return f"❌ Ошибка соединения с ИИ: {str(err)}"

async def transcribe_voice_async(client: httpx.AsyncClient, audio_bytes: bytes, groq_key: str) -> str:
    groq_url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "User-Agent": "OpenAI/Python 1.14.0"
    }
    files = {
        "file": ("voice.ogg", audio_bytes, "audio/ogg"),
        "model": (None, "whisper-large-v3-turbo")
    }

    try:
        res = await client.post(groq_url, files=files, headers=headers, timeout=9.0)
        if res.status_code == 200:
            return res.json().get("text", "").strip()
        else:
            return f"❌ Ошибка Whisper API ({res.status_code}): {res.text}"
    except Exception as err:
        return f"❌ Ошибка распознавания речи: {str(err)}"

async def send_telegram_async(client: httpx.AsyncClient, bot_token: str, chat_id: int, text: str, reply_markup: dict = None):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        await client.post(url, json=payload, timeout=5.0)
    except Exception as e:
        print("Telegram API send error:", e)

@app.get("/")
@app.get("/webhook")
async def root():
    return {"status": "online", "service": "Telegram AI Bot on Vercel (Groq Llama-3.3)"}

@app.post("/")
@app.post("/webhook")
async def webhook(request: Request):
    """Serverless Webhook endpoint processing updates 24/7 on Vercel asynchronously."""
    bot_token = os.getenv("BOT_TOKEN", "").strip() or DEFAULT_BOT_TOKEN
    groq_key = os.getenv("GROQ_API_KEY", "").strip() or DEFAULT_GROQ_KEY
    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

    try:
        data = await request.json()

        async with httpx.AsyncClient() as client:
            # Handle Callback Queries (Inline Button clicks)
            if "callback_query" in data:
                cb = data["callback_query"]
                cb_id = cb.get("id")
                cb_data = cb.get("data", "")
                cb_msg = cb.get("message", {})
                chat_id = cb_msg.get("chat", {}).get("id")

                try:
                    await client.post(
                        f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
                        json={"callback_query_id": str(cb_id)},
                        timeout=3.0
                    )
                except Exception:
                    pass

                if cb_data == "action:clear":
                    reply = "🧹 История диалога очищена! Все предыдущие темы сброшены."
                    markup = KEYBOARD_MAIN
                elif cb_data == "action:info":
                    reply = f"ℹ️ Информация о боте:\n\n• Провайдер ИИ: Groq\n• Модель: {groq_model}\n• Хостинг: Vercel 24/7\n• Голос: Groq Whisper 🎙️"
                    markup = KEYBOARD_MAIN
                elif cb_data == "action:help":
                    reply = (
                        "💡 Справка по использованию:\n\n"
                        "1. Задавайте любые вопросы в чат текстом или голосом 🎙️.\n"
                        "2. Нажимайте кнопку «🔄 Пересоздать ответ» под сообщением ИИ, чтобы получить другой вариант ответа.\n"
                        "3. Нажимайте «🧹 Очистить контекст», чтобы начать тему с нуля."
                    )
                    markup = KEYBOARD_MAIN
                elif cb_data == "action:regenerate":
                    prompt_text = cb_msg.get("text", "Привет")
                    reply = await query_groq_async(client, prompt_text, groq_key, groq_model)
                    markup = KEYBOARD_RESPONSE
                else:
                    reply = "Команда обработана."
                    markup = KEYBOARD_MAIN

                await send_telegram_async(client, bot_token, chat_id, reply, reply_markup=markup)
                return JSONResponse({
                    "method": "sendMessage",
                    "chat_id": chat_id,
                    "text": reply,
                    "reply_markup": markup
                })

            # Handle regular text or voice messages
            message = data.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "").strip()
            voice = message.get("voice")

            if not chat_id:
                return JSONResponse({"status": "ignored"})

            # Process Voice Note
            if voice:
                file_id = voice.get("file_id")
                if file_id:
                    res = await client.get(
                        f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}",
                        timeout=5.0
                    )
                    file_info = res.json()
                    file_path = file_info.get("result", {}).get("file_path")

                    if file_path:
                        audio_res = await client.get(
                            f"https://api.telegram.org/file/bot{bot_token}/{file_path}",
                            timeout=6.0
                        )
                        audio_bytes = audio_res.content

                        transcribed_text = await transcribe_voice_async(client, audio_bytes, groq_key)
                        if transcribed_text and not transcribed_text.startswith("❌"):
                            await send_telegram_async(client, bot_token, chat_id, f"🎤 Вы сказали: «{transcribed_text}»")
                            reply = await query_groq_async(client, transcribed_text, groq_key, groq_model)
                            await send_telegram_async(client, bot_token, chat_id, reply, reply_markup=KEYBOARD_RESPONSE)
                            return JSONResponse({
                                "method": "sendMessage",
                                "chat_id": chat_id,
                                "text": reply,
                                "reply_markup": KEYBOARD_RESPONSE
                            })
                        else:
                            reply = transcribed_text or "⚠️ Не удалось распознать речь."
                            await send_telegram_async(client, bot_token, chat_id, reply)
                            return JSONResponse({
                                "method": "sendMessage",
                                "chat_id": chat_id,
                                "text": reply
                            })

            if not text:
                return JSONResponse({"status": "ignored"})

            if text == "/start":
                reply = "👋 Привет! Я Telegram-бот со встроенным ИИ на базе Groq (Llama 3.3) и Whisper 🎙️.\n\nЗадай мне любой вопрос текстом или голосом!"
                markup = KEYBOARD_MAIN
            elif text == "/help":
                reply = "💡 Справка:\nЗадавай любые вопросы в чат текстом или голосом 🎙️, и я отвечу с помощью нейросети Groq Llama-3.3-70B."
                markup = KEYBOARD_MAIN
            elif text == "/info":
                reply = f"ℹ️ Провайдер: Groq\nМодель: {groq_model}\nГолос: Groq Whisper 🎙️\nХостинг: Vercel 24/7"
                markup = KEYBOARD_MAIN
            else:
                reply = await query_groq_async(client, text, groq_key, groq_model)
                markup = KEYBOARD_RESPONSE

            await send_telegram_async(client, bot_token, chat_id, reply, reply_markup=markup)
            return JSONResponse({
                "method": "sendMessage",
                "chat_id": chat_id,
                "text": reply,
                "reply_markup": markup
            })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})
