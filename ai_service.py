import logging
from typing import List, Dict
import config

logger = logging.getLogger(__name__)

class AIService:
    """Unified service for interacting with LLM providers (Groq, OpenAI, Gemini)."""

    def __init__(self):
        self.provider = config.AI_PROVIDER.lower()
        self._openai_client = None
        self._groq_client = None
        self._gemini_client = None

        if self.provider == "groq":
            if not config.GROQ_API_KEY:
                logger.warning("GROQ_API_KEY is not configured in environment variables.")
            else:
                try:
                    from openai import AsyncOpenAI
                    self._groq_client = AsyncOpenAI(
                        api_key=config.GROQ_API_KEY,
                        base_url="https://api.groq.com/openai/v1"
                    )
                except ImportError:
                    logger.error("openai package is not installed.")

        elif self.provider == "openai":
            if not config.OPENAI_API_KEY:
                logger.warning("OPENAI_API_KEY is not configured in environment variables.")
            else:
                try:
                    from openai import AsyncOpenAI
                    self._openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
                except ImportError:
                    logger.error("openai package is not installed.")

        elif self.provider == "gemini":
            if not config.GEMINI_API_KEY:
                logger.warning("GEMINI_API_KEY is not configured in environment variables.")
            else:
                try:
                    from google import genai
                    self._gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
                except ImportError:
                    logger.error("google-genai package is not installed.")

    async def generate_response(
        self,
        prompt: str,
        history: List[Dict[str, str]]
    ) -> str:
        """Generate response from AI provider given prompt and past conversation history."""

        if self.provider == "groq":
            return await self._generate_groq(prompt, history)
        elif self.provider == "openai":
            return await self._generate_openai(prompt, history)
        elif self.provider == "gemini":
            return await self._generate_gemini(prompt, history)
        else:
            return f"❌ Ошибка конфигурации: неизвестный ИИ провайдер '{self.provider}'. Укажите 'groq', 'openai' или 'gemini'."

    async def _generate_groq(
        self,
        prompt: str,
        history: List[Dict[str, str]]
    ) -> str:
        if not config.GROQ_API_KEY:
            return "⚠️ Не задан GROQ_API_KEY. Пожалуйста, добавьте ключ в файл `.env`."

        if not self._groq_client:
            from openai import AsyncOpenAI
            self._groq_client = AsyncOpenAI(
                api_key=config.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )

        messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
        for item in history:
            messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self._groq_client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=messages,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.exception("Error calling Groq API")
            return f"❌ Ошибка при обращении к Groq API: {str(e)}"

    async def _generate_openai(
        self,
        prompt: str,
        history: List[Dict[str, str]]
    ) -> str:
        if not config.OPENAI_API_KEY:
            return "⚠️ Не задан OPENAI_API_KEY. Пожалуйста, добавьте ключ в файл `.env`."

        if not self._openai_client:
            from openai import AsyncOpenAI
            self._openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

        messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
        for item in history:
            messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self._openai_client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.exception("Error calling OpenAI API")
            return f"❌ Ошибка при обращении к OpenAI API: {str(e)}"

    async def _generate_gemini(
        self,
        prompt: str,
        history: List[Dict[str, str]]
    ) -> str:
        if not config.GEMINI_API_KEY:
            return "⚠️ Не задан GEMINI_API_KEY. Пожалуйста, добавьте ключ в файл `.env`."

        try:
            from google import genai
            from google.genai import types

            if not self._gemini_client:
                self._gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)

            contents = []
            for item in history:
                role = "user" if item["role"] == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=item["content"])]
                    )
                )

            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)]
                )
            )

            config_params = types.GenerateContentConfig(
                system_instruction=config.SYSTEM_PROMPT,
                temperature=0.7,
            )

            import asyncio
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._gemini_client.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=contents,
                    config=config_params,
                )
            )

            return response.text.strip()
        except Exception as e:
            logger.exception("Error calling Gemini API")
            return f"❌ Ошибка при обращении к Gemini API: {str(e)}"


# Global AI Service instance
ai_service = AIService()
