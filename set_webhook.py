import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot

async def main():
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python3 set_webhook.py https://your-project.vercel.app")
        print("  python3 set_webhook.py delete")
        return

    url_arg = sys.argv[1].strip()
    token = os.getenv("BOT_TOKEN")

    if not token:
        print("❌ BOT_TOKEN не найден в .env!")
        return

    bot = Bot(token=token)

    try:
        if url_arg.lower() == "delete":
            await bot.delete_webhook(drop_pending_updates=True)
            print("✅ Webhook успешно удален! Теперь можно использовать локальный запуск через main.py.")
        else:
            # Ensure URL has https://
            if not url_arg.startswith("http"):
                url_arg = f"https://{url_arg}"
            
            # Ensure trailing webhook route
            if not url_arg.endswith("/webhook"):
                url_arg = url_arg.rstrip("/") + "/webhook"

            print(f"Устанавливаем Webhook URL: {url_arg}")
            await bot.set_webhook(url=url_arg, drop_pending_updates=True)
            info = await bot.get_webhook_info()
            print(f"✅ Webhook успешно установлен на: {info.url}")
    except Exception as e:
        print("❌ Ошибка при установке Webhook:", e)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
