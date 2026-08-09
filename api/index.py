import os
import sys
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types

# Ensure parent directory is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from handlers import router

app = FastAPI()

# Initialize Bot and Dispatcher
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Telegram AI Bot on Vercel",
        "provider": config.AI_PROVIDER
    }

@app.post("/")
@app.post("/webhook")
async def webhook(request: Request):
    """Vercel Webhook endpoint for Telegram Updates."""
    try:
        json_str = await request.json()
        update = types.Update.model_validate(json_str, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
