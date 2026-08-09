import os
import json
import re
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

DB_FILE = os.path.join(os.path.dirname(__file__), "expenses.json")

# Spoken Russian number words
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
    """Manages persistent multi-currency expense tracking (KZT, RUB, USD) and financial statistics per user."""

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
        if str_id not in self.data or not isinstance(self.data[str_id], dict) or "totals" not in self.data[str_id]:
            self.data[str_id] = {
                "totals": {
                    "₸ (KZT)": 0.0,
                    "₽ (RUB)": 0.0,
                    "$ (USD)": 0.0
                },
                "categories": {},
                "items": []
            }
        return self.data[str_id]

    def parse_expense_text(self, text: str) -> Optional[Tuple[float, str, str, str]]:
        """
        Parses text or voice transcription for multi-currency expense intent.
        Returns (amount, currency, category, note) if expense detected, else None.
        Supported currencies: KZT (тенге, тг), RUB (рубли, руб), USD (доллары, $).
        """
        text_lower = text.lower().strip()

        # 1. Detect Currency with strict word boundaries
        currency = None
        if re.search(r"\b(?:тенге|тг|kzt|₸)\b", text_lower):
            currency = "₸ (KZT)"
        elif re.search(r"\b(?:доллар|долларов|доллара|баксов|бакс|\$|usd)\b", text_lower):
            currency = "$ (USD)"
        elif re.search(r"\b(?:рубль|рублей|рубля|руб|р\.|₽|rub)\b", text_lower):
            currency = "₽ (RUB)"

        # Default fallback currency if not explicitly mentioned
        if not currency:
            currency = "₸ (KZT)"

        amount = 0.0

        # 2. Extract digits
        digit_match = re.search(r"(\d+(?:[\.,]\d{1,2})?)", text_lower)
        if digit_match:
            try:
                amount = float(digit_match.group(1).replace(",", "."))
            except ValueError:
                amount = 0.0

        # 3. Extract spoken number words if no digits
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

        return (amount, currency, category, note)

    def add_expense(self, user_id: int, amount: float, currency: str, category: str, note: str) -> Dict[str, Any]:
        """Adds a multi-currency expense transaction to user ledger."""
        rec = self._get_user_record(user_id)

        # Update total for currency
        current_curr_total = rec["totals"].get(currency, 0.0)
        rec["totals"][currency] = round(current_curr_total + amount, 2)

        # Update category totals per currency
        if category not in rec["categories"]:
            rec["categories"][category] = {}
        rec["categories"][category][currency] = round(rec["categories"][category].get(currency, 0.0) + amount, 2)

        rec["items"].append({
            "amount": amount,
            "currency": currency,
            "category": category,
            "note": note
        })
        self._save_db()
        return rec

    def get_stats(self, user_id: int) -> str:
        """Formats current user multi-currency expense statistics into readable message."""
        rec = self._get_user_record(user_id)
        totals = rec["totals"]
        categories = rec["categories"]
        items_count = len(rec["items"])

        active_totals = {curr: amt for curr, amt in totals.items() if amt > 0}

        if not active_totals and items_count == 0:
            return (
                "📊 **Статистика расходов:**\n\n"
                "У вас пока нет записанных расходов. Напишите или скажите голосом 🎙️:\n"
                "• 🇰🇿 *«1000 тенге продукты»*\n"
                "• 🇺🇸 *«50 долларов такси»*\n"
                "• 🇷🇺 *«1500 рублей еда»*"
            )

        lines = [
            "📊 **Статистика ваших расходов:**\n",
            "💰 **Всего потрачено по валютам:**"
        ]

        for curr, curr_amt in totals.items():
            if curr_amt > 0:
                lines.append(f"• {curr}: `{curr_amt:,.2f}`".replace(",", " "))

        lines.append(f"\n📝 **Всего записей:** `{items_count}`\n")
        lines.append("**По категориям:**")

        for cat, cat_dict in categories.items():
            cat_lines = []
            for curr, cat_amt in cat_dict.items():
                if cat_amt > 0:
                    cat_lines.append(f"{cat_amt:,.2f} {curr}".replace(",", " "))
            if cat_lines:
                lines.append(f"• {cat}: " + ", ".join(cat_lines))

        return "\n".join(lines)

    def reset_expenses(self, user_id: int):
        """Resets all expense records for user."""
        str_id = str(user_id)
        self.data[str_id] = {
            "totals": {
                "₸ (KZT)": 0.0,
                "₽ (RUB)": 0.0,
                "$ (USD)": 0.0
            },
            "categories": {},
            "items": []
        }
        self._save_db()


# Global Expense Manager instance
expense_manager = ExpenseManager()
