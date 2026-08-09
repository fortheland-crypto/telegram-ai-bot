import logging
import os
import tempfile
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder

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

def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🧹 Очистить контекст", callback_data="action:clear")
    builder.button(text="ℹ️ Инфо о модели", callback_data="action:info")
    builder.button(text="💡 Справка", callback_data="action:help")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_response_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Пересоздать ответ", callback_data="action:regenerate")
    builder.button(text="🧹 Очистить контекст", callback_data="action:clear")
    builder.adjust(2)
    return builder.as_markup()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handler for /start command."""
    welcome_text = (
        "👋 **Привет! Я Telegram-бот со встроенным ИИ.**\n\n"
        "Я могу отвечать на твои вопросы, помогать с текстами, и **распознавать голосовые сообщения**!\n\n"
        "Просто напиши мне вопрос или отправь голосовое сообщение 🎙️!"
    )
    await message.answer(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Handler for /help command."""
    model_name = get_current_model_name()
    help_text = (
        "💡 **Как со мной общаться:**\n\n"
        "1. **Задавай любые вопросы:** Напиши текстом или **отправь голосовое сообщение 🎙️**.\n"
        "2. **Кнопка «🔄 Пересоздать ответ»:** Перегенерирует ответ нейросети.\n"
        "3. **Сброс контекста:** Очищает историю диалога в один клик.\n\n"
        f"⚙️ **Текущий провайдер:** `{config.AI_PROVIDER}` ({model_name})"
    )
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())

@router.message(Command("clear"))
async def cmd_clear(message: types.Message):
    """Handler for /clear command to reset user chat memory."""
    user_id = message.from_user.id
    memory.clear_history(user_id)
    await message.answer("🧹 **История диалога очищена!** Мы начинаем с чистого листа.", parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())

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
        f"• **Распознавание речи:** `Groq Whisper` 🎙️\n"
        f"• **Сообщений в памяти для вас:** {history_len} / {config.MAX_HISTORY_MESSAGES}\n"
    )
    await message.answer(info_text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())

# Callback Query Handlers
@router.callback_query(F.data == "action:clear")
async def cb_clear(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    memory.clear_history(user_id)
    await callback.answer("История очищена!")
    await callback.message.answer("🧹 **История диалога очищена!**", parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())

@router.callback_query(F.data == "action:info")
async def cb_info(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    history_len = len(memory.get_history(user_id))
    model_name = get_current_model_name()
    await callback.answer()
    info_text = (
        "ℹ️ **Информация о боте:**\n\n"
        f"• **Провайдер ИИ:** `{config.AI_PROVIDER}`\n"
        f"• **Модель:** `{model_name}`\n"
        f"• **Распознавание речи:** `Groq Whisper` 🎙️\n"
        f"• **Сообщений в памяти:** {history_len} / {config.MAX_HISTORY_MESSAGES}\n"
    )
    await callback.message.answer(info_text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())

@router.callback_query(F.data == "action:help")
async def cb_help(callback: types.CallbackQuery):
    await callback.answer()
    help_text = (
        "💡 **Справка:**\n\n"
        "1. Пишите любые вопросы или **отправляйте голосовые сообщения 🎙️**.\n"
        "2. Кнопка **«🔄 Пересоздать ответ»** под ответом сгенерирует новый вариант ответа ИИ.\n"
        "3. Кнопка **«🧹 Очистить контекст»** сбросит историю."
    )
    await callback.message.answer(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())

@router.callback_query(F.data == "action:regenerate")
async def cb_regenerate(callback: types.CallbackQuery):
    await callback.answer("Перегенерируем ответ...")
    user_id = callback.from_user.id
    prompt_text = callback.message.text or "Привет"

    await callback.bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.TYPING)
    history = memory.get_history(user_id)
    response_text = await ai_service.generate_response(prompt_text, history)
    
    memory.add_user_message(user_id, prompt_text)
    memory.add_assistant_message(user_id, response_text)

    chunks = split_message(response_text)
    for i, chunk in enumerate(chunks):
        markup = get_response_keyboard() if i == len(chunks) - 1 else None
        try:
            await callback.message.answer(chunk, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        except TelegramBadRequest:
            await callback.message.answer(chunk, parse_mode=None, reply_markup=markup)

# Voice Message Handler
@router.message(F.voice)
async def handle_voice(message: types.Message):
    """Handler for voice messages (speech-to-text via Groq Whisper)."""
    user_id = message.from_user.id
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # Download Telegram voice file
    voice = message.voice
    file_info = await message.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
        temp_audio_path = temp_audio.name

    try:
        await message.bot.download_file(file_info.file_path, temp_audio_path)

        # Transcribe audio using Groq Whisper API
        transcribed_text = await ai_service.transcribe_audio(temp_audio_path)

        if not transcribed_text or transcribed_text.startswith("❌") or transcribed_text.startswith("⚠️"):
            await message.answer(transcribed_text or "⚠️ Не удалось распознать речь.")
            return

        # Send transcription note to user
        await message.answer(f"🎤 *Вы сказали:* «{transcribed_text}»", parse_mode=ParseMode.MARKDOWN)

        # Process with AI
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        history = memory.get_history(user_id)

        response_text = await ai_service.generate_response(transcribed_text, history)

        memory.add_user_message(user_id, transcribed_text)
        memory.add_assistant_message(user_id, response_text)

        chunks = split_message(response_text)
        for i, chunk in enumerate(chunks):
            markup = get_response_keyboard() if i == len(chunks) - 1 else None
            try:
                await message.answer(chunk, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
            except TelegramBadRequest:
                await message.answer(chunk, parse_mode=None, reply_markup=markup)
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

@router.message()
async def handle_message(message: types.Message):
    """General handler for user text messages."""
    if not message.text:
        await message.answer("⚠️ Я умею обрабатывать только текстовые и голосовые сообщения 🎙️.")
        return

    user_id = message.from_user.id
    user_text = message.text.strip()

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    history = memory.get_history(user_id)

    response_text = await ai_service.generate_response(user_text, history)

    memory.add_user_message(user_id, user_text)
    memory.add_assistant_message(user_id, response_text)

    chunks = split_message(response_text)
    for i, chunk in enumerate(chunks):
        markup = get_response_keyboard() if i == len(chunks) - 1 else None
        try:
            await message.answer(chunk, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        except TelegramBadRequest:
            await message.answer(chunk, parse_mode=None, reply_markup=markup)
