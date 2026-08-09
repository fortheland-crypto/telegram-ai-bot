import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramBadRequest

import config
from memory import memory
from ai_service import ai_service
from utils import split_message

logger = logging.getLogger(__name__)

router = Router()

def get_current_model_name() -> str:
    if config.AI_PROVIDER == "groq":
        return config.GROQ_MODEL
    elif config.AI_PROVIDER == "openai":
        return config.OPENAI_MODEL
    elif config.AI_PROVIDER == "gemini":
        return config.GEMINI_MODEL
    return "unknown"

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handler for /start command."""
    welcome_text = (
        "👋 **Привет! Я Telegram-бот со встроенным ИИ.**\n\n"
        "Я могу отвечать на любые твои вопросы, помогать с текстами, идеями, программированием и многим другим!\n\n"
        "**Доступные команды:**\n"
        "• /start — Перезапустить бота\n"
        "• /help — Справка и возможности\n"
        "• /clear — Очистить историю нашего диалога\n"
        "• /info — Информация об используемой нейросети\n\n"
        "Просто напиши мне любой вопрос в чат! 👇"
    )
    await message.answer(welcome_text, parse_mode=ParseMode.MARKDOWN)

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Handler for /help command."""
    model_name = get_current_model_name()
    help_text = (
        "💡 **Как со мной общаться:**\n\n"
        "1. **Задавай любые вопросы:** Напиши свой вопрос простыми словами.\n"
        "2. **Контекст общения:** Я помню предыдущие сообщения в диалоге, поэтому ты можешь задавать уточняющие вопросы (например, *«Расскажи подробнее про пункт 2»*).\n"
        "3. **Сброс контекста:** Если хочешь начать тему с чистого листа, введи команду `/clear`.\n\n"
        f"⚙️ **Текущий провайдер:** `{config.AI_PROVIDER}` ({model_name})"
    )
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

@router.message(Command("clear"))
async def cmd_clear(message: types.Message):
    """Handler for /clear command to reset user chat memory."""
    user_id = message.from_user.id
    memory.clear_history(user_id)
    await message.answer("🧹 **История диалога очищена!** Мы начинаем с чистого листа.", parse_mode=ParseMode.MARKDOWN)

@router.message(Command("info"))
async def cmd_info(message: types.Message):
    """Handler for /info command."""
    user_id = message.from_user.id
    history_len = len(memory.get_history(user_id))
    model_name = get_current_model_name()

    info_text = (
        "ℹ️ **Информация о боте:**\n\n"
        f"• **Провайдер ИИ:** `{config.AI_PROVIDER}`\n"
        f"• **Модель:** `{model_name}`\n"
        f"• **Сообщений в памяти для вас:** {history_len} / {config.MAX_HISTORY_MESSAGES}\n"
    )
    await message.answer(info_text, parse_mode=ParseMode.MARKDOWN)

@router.message()
async def handle_message(message: types.Message):
    """General handler for user text messages."""
    if not message.text:
        await message.answer("⚠️ Я умею обрабатывать только текстовые сообщения.")
        return

    user_id = message.from_user.id
    user_text = message.text.strip()

    # Show typing action in Telegram UI
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # Get conversation history before adding current message
    history = memory.get_history(user_id)

    # Generate response from AI service
    response_text = await ai_service.generate_response(user_text, history)

    # Add query and answer to user's conversation history
    memory.add_user_message(user_id, user_text)
    memory.add_assistant_message(user_id, response_text)

    # Split response if it exceeds Telegram's limit
    chunks = split_message(response_text)

    for chunk in chunks:
        try:
            # Try sending with Markdown formatting
            await message.answer(chunk, parse_mode=ParseMode.MARKDOWN)
        except TelegramBadRequest:
            # Fallback to plain text if Markdown parsing fails
            await message.answer(chunk, parse_mode=None)
