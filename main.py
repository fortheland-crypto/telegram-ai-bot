import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

import config
from handlers import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Telegram AI Bot...")

    # Validate Telegram Bot Token
    if not config.BOT_TOKEN or config.BOT_TOKEN == "your_telegram_bot_token_here":
        logger.error("❌ BOT_TOKEN не задан в файле .env! Пожалуйста, укажите токен вашего бота от @BotFather.")
        print("\n" + "="*60)
        print(" ОШИБКА: Запуск невозможно выполнить без BOT_TOKEN!")
        print(" 1. Создайте бот у @BotFather в Telegram.")
        print(" 2. Переименуйте файл .env.example в .env")
        print(" 3. Укажите ваш BOT_TOKEN и API-ключ ИИ (OPENAI_API_KEY или GEMINI_API_KEY).")
        print("="*60 + "\n")
        return

    # Check AI configuration warning
    if config.AI_PROVIDER == "openai" and not config.OPENAI_API_KEY:
        logger.warning("⚠️ Внимание: Выбран провайдер OpenAI, но OPENAI_API_KEY не установлен.")
    elif config.AI_PROVIDER == "gemini" and not config.GEMINI_API_KEY:
        logger.warning("⚠️ Внимание: Выбран провайдер Gemini, но GEMINI_API_KEY не установлен.")

    # Initialize Bot and Dispatcher
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    # Include command router
    dp.include_router(router)

    # Delete existing webhooks and start polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info(f"Bot successfully started! AI Provider: {config.AI_PROVIDER}")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
