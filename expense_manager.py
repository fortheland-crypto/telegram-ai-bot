import os
import json
import re
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

DB_FILE = os.path.join(os.path.dirname(__file__), "expenses.json")

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
        Parses text for expense intent.
        Returns (amount, category, note) if expense is detected, else None.
        Matches phrases like: "потратил 500 на продукты", "1200 такси", "купил за 350 рублей", "минус 400"
        """
        text_lower = text.lower().strip()

        # Check explicit keywords or patterns
        keywords = ["потратил", "потратила", "купил", "купила", "оплатил", "оплатила", "заплатил", "заплатила", "расход", "стоило", "минус"]
        is_expense_phrase = any(kw in text_lower for kw in keywords)

        # Regex patterns for numbers followed by currency or category
        # Match numbers like 500, 1200, 350.50
        pattern = r"(?:(?:потратил[а]?|купил[а]?|оплатил[а]?|заплатил[а]?|расход|минус)?\s*)(\d+(?:[\.,]\d{1,2})?)\s*(?:руб|рублей|рубля|р|руб\.)?\s*(?:на|за|в)?\s*(.*)"
        
        match = re.search(r"(\d+(?:[\.,]\d{1,2})?)\s*(?:руб|рублей|рубля|р|руб\.)?", text_lower)
        if not match:
            return None

        # Only trigger if expense keyword is present or text is short like "500 такси", "1200 еда"
        if not is_expense_phrase and len(text_lower.split()) > 4:
            return None

        try:
            amount_str = match.group(1).replace(",", ".")
            amount = float(amount_str)
            if amount <= 0:
                return None
        except ValueError:
            return None

        # Determine category / note
        note = text.strip()
        category = "Другое"
        if any(w in text_lower for w in ["такси", "метро", "автобус", "бензин", "проезд", "транспорт"]):
            category = "🚕 Транспорт"
        elif any(w in text_lower for w in ["еда", "продукты", "обед", "ужин", "завтрак", "кафе", "ресторан", "магазин", "хлеб"]):
            category = "🍔 Еда и Продукты"
        elif any(w in text_lower for w in ["коммуналка", "квартира", "свет", "газ", "вода", "интернет", "аренда"]):
            category = "🏠 Жилье и Услуги"
        elif any(w in text_lower for w in ["аптека", "врач", "лекарства", "здоровье"]):
            category = "💊 Здоровье"
        elif any(w in text_lower for w in ["одежда", "обувь", "покупки", "шопинг"]):
            category = "🛍️ Покупки"
        elif any(w in text_lower for w in ["кино", "игра", "развлечения", "отдых"]):
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
            return "📊 **Статистика расходов:**\n\nУ вас пока нет записанных расходов. Напишите или скажите голосом, например: *«Потратил 500 рублей на продукты»*."

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
        if str_id in self.data:
            self.data[str_id] = {
                "total": 0.0,
                "categories": {},
                "items": []
            }
            self._save_db()


# Global Expense Manager instance
expense_manager = ExpenseManager()
