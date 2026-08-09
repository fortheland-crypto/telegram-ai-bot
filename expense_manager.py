import os
import json
import re
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

DB_FILE = os.path.join(os.path.dirname(__file__), "expenses.json")

# Mapping for spoken Russian number words
NUMBER_WORDS = {
    "сто": 100, "двести": 200, "триста": 300, "четыреста": 400, "пятьсот": 500,
    "шестьсот": 600, "семьсот": 700, "восемьсот": 800, "девятьсот": 900,
    "тысяча": 1000, "тысячи": 1000, "тысяч": 1000,
    "десять": 10, "двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50,
    "шестьдесят": 60, "семьдесят": 70, "восемьдесят": 80, "девяносто": 90,
    "один": 1, "одна": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5,
    "шесть": 6, "семь": 7, "восемь": 8, "девять": 9
}

class ExpenseManager:
    """Manages persistent expense tracking and financial statistics per user."""

    def __init__(self, db_filepath: str = DB_FILE):
        self.db_filepath = db_filepath
        self._load_db()

    def _load_db(self):
        if os.path.exists(self.db_filepath):
            try:
                with open(self.db_filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading expenses DB: {e}")
                self.data = {}
        else:
            self.data = {}

    def _save_db(self):
        try:
            with open(self.db_filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving expenses DB: {e}")

    def _get_user_record(self, user_id: int) -> Dict[str, Any]:
        str_id = str(user_id)
        if str_id not in self.data:
            self.data[str_id] = {
                "total": 0.0,
                "categories": {},
                "items": []
            }
        return self.data[str_id]

    def parse_expense_text(self, text: str) -> Optional[Tuple[float, str, str]]:
        """
        Parses text or transcribed voice for expense intent.
        Supports digits ("500") and word numbers ("пятьсот рублей").
        Returns (amount, category, note) if expense is detected, else None.
        """
        text_lower = text.lower().strip()

        amount = 0.0

        # 1. Try digit extraction first
        digit_match = re.search(r"(\d+(?:[\.,]\d{1,2})?)", text_lower)
        if digit_match:
            try:
                amount = float(digit_match.group(1).replace(",", "."))
            except ValueError:
                amount = 0.0

        # 2. If no digits found, check for spoken number words
        if amount <= 0:
            words = text_lower.split()
            current_sum = 0
            temp_val = 0
            for w in words:
                clean_w = re.sub(r"[^\w]", "", w)
                if clean_w in NUMBER_WORDS:
                    val = NUMBER_WORDS[clean_w]
                    if val == 1000:
                        temp_val = (temp_val if temp_val > 0 else 1) * 1000
                        current_sum += temp_val
                        temp_val = 0
                    else:
                        temp_val += val
            current_sum += temp_val
            if current_sum > 0:
                amount = float(current_sum)

        if amount <= 0:
            return None

        # Determine category / note
        note = text.strip()
        category = "Другое"
        if any(w in text_lower for w in ["такси", "метро", "автобус", "бензин", "проезд", "транспорт", "машину", "авто"]):
            category = "🚕 Транспорт"
        elif any(w in text_lower for w in ["еда", "продукты", "обед", "ужин", "завтрак", "кафе", "ресторан", "магазин", "хлеб", "кофе", "пицца", "еду"]):
            category = "🍔 Еда и Продукты"
        elif any(w in text_lower for w in ["коммуналка", "квартира", "свет", "газ", "вода", "интернет", "аренда", "связь"]):
            category = "🏠 Жилье и Услуги"
        elif any(w in text_lower for w in ["аптека", "врач", "лекарства", "здоровье", "больница"]):
            category = "💊 Здоровье"
        elif any(w in text_lower for w in ["одежда", "обувь", "покупки", "шопинг", "купил", "купила"]):
            category = "🛍️ Покупки"
        elif any(w in text_lower for w in ["кино", "игра", "развлечения", "отдых", "театр"]):
            category = "🎬 Развлечения"

        return (amount, category, note)

    def add_expense(self, user_id: int, amount: float, category: str, note: str) -> Dict[str, Any]:
        """Adds an expense transaction to user ledger."""
        rec = self._get_user_record(user_id)
        rec["total"] = round(rec["total"] + amount, 2)
        rec["categories"][category] = round(rec["categories"].get(category, 0.0) + amount, 2)
        rec["items"].append({
            "amount": amount,
            "category": category,
            "note": note
        })
        self._save_db()
        return rec

    def get_stats(self, user_id: int) -> str:
        """Formats current user expense statistics into readable message."""
        rec = self._get_user_record(user_id)
        total = rec["total"]
        categories = rec["categories"]
        items_count = len(rec["items"])

        if total == 0 and items_count == 0:
            return "📊 **Статистика расходов:**\n\nУ вас пока нет записанных расходов. Напишите или скажите голосом 🎙️, например:\n• *«Потратил 500 рублей на продукты»*\n• *«1200 такси»*\n• *«Пятьсот рублей на еду»*"

        lines = [
            "📊 **Статистика ваших расходов:**\n",
            f"💰 **Всего потрачено:** `{total:,.2f} руб.`".replace(",", " "),
            f"📝 **Всего записей:** `{items_count}`\n",
            "**По категориям:**"
        ]

        for cat, cat_total in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"• {cat}: `{cat_total:,.2f} руб.`".replace(",", " "))

        return "\n".join(lines)

    def reset_expenses(self, user_id: int):
        """Resets all expense records for user."""
        str_id = str(user_id)
        self.data[str_id] = {
            "total": 0.0,
            "categories": {},
            "items": []
        }
        self._save_db()


# Global Expense Manager instance
expense_manager = ExpenseManager()
