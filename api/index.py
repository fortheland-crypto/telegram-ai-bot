import os
import sys
import logging
from fastapi import FastAPI, Request

# Ensure parent directory is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

app = FastAPI()

_bot = None
_dp = None

def get_bot_and_dp():
    global _bot, _dp
    if _bot is None:
        from aiogram import Bot, Dispatcher
        import config
        from handlers import router

        token = os.getenv("BOT_TOKEN", "").strip() or config.BOT_TOKEN
        if not token or token == "your_telegram_bot_token_here":
            raise ValueError("BOT_TOKEN is not configured in Vercel environment variables!")

        _bot = Bot(token=token)
        _dp = Dispatcher()
        _dp.include_router(router)
    return _bot, _dp

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Telegram AI Bot on Vercel"
    }

@app.post("/")
@app.post("/webhook")
async def webhook(request: Request):
    """Vercel Webhook endpoint for Telegram Updates."""
    try:
        from aiogram import types
        bot, dp = get_bot_and_dp()
        json_str = await request.json()
        update = types.Update.model_validate(json_str, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        logger.exception("Error processing webhook update")
        return {"status": "error", "detail": str(e)}
