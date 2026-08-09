import os
import json
import re
import logging
from typing import Dict, Any, Tuple, Optional, List

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

def format_money(val: float) -> str:
    """Formats money numbers cleanly without trailing .00 if whole number."""
    if val.is_integer():
        return f"{int(val):,}".replace(",", " ")
    return f"{val:,.2f}".replace(",", " ")

def normalize_spoken_numbers(text: str) -> str:
    """
    Normalizes speech-to-text thousand abbreviations and space-separated numbers:
    - "5 тыс" / "5 тысяч" -> "5000"
    - "8 тыс" / "8 тысяч" -> "8000"
    - "10 000" -> "10000"
    - "2.5 тыс" -> "2500"
    """
    t = text.lower().strip()
    # Remove spaces in numbers e.g. "10 000" -> "10000"
    t = re.sub(r"(\d{1,3})\s+(\d{3})\b", r"\1\2", t)
    t = re.sub(r"(\d{1,3})\s+(\d{3})\b", r"\1\2", t)

    # Replace "тыс", "тысяч", "тысячи", "тысяча" multiplier (e.g. 5 тыс -> 5000, 8 тысяч -> 8000)
    t = re.sub(
        r"(\d+(?:[\.,]\d+)?)\s*(?:тыс\.|тыс|тысяч|тысячи|тысяча)\b",
        lambda m: str(int(float(m.group(1).replace(",", ".")) * 1000)),
        t
    )
    return t

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

    def _parse_single_segment(self, text_segment: str, default_currency: str) -> Optional[Tuple[float, str, str, str]]:
        text_lower = text_segment.lower().strip()

        # 1. Detect Currency in segment
        currency = default_currency
        if re.search(r"\b(?:тенге|тг|kzt|₸)\b", text_lower):
            currency = "₸ (KZT)"
        elif re.search(r"\b(?:доллар|долларов|доллара|баксов|бакс|\$|usd)\b", text_lower):
            currency = "$ (USD)"
        elif re.search(r"\b(?:рубль|рублей|рубля|руб|р\.|₽|rub)\b", text_lower):
            currency = "₽ (RUB)"

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
        note = text_segment.strip()
        category = "Другое"
        if any(w in text_lower for w in ["заправка", "бензин", "авто", "машину", "заправил", "заправила", "газ", "такси", "метро", "автобус", "проезд", "транспорт"]):
            category = "⛽ Заправка авто и Транспорт"
        elif any(w in text_lower for w in ["еда", "продукты", "обед", "ужин", "завтрак", "кафе", "ресторан", "магазин", "хлеб", "кофе", "пицца", "еду"]):
            category = "🍔 Еда и Продукты"
        elif any(w in text_lower for w in ["коммуналка", "коммунальные", "квартира", "свет", "вода", "интернет", "аренда", "связь", "услуги"]):
            category = "🏠 Жилье и Услуги"
        elif any(w in text_lower for w in ["аптека", "врач", "лекарства", "здоровье", "больница"]):
            category = "💊 Здоровье"
        elif any(w in text_lower for w in ["одежда", "обувь", "покупки", "шопинг", "купил", "купила"]):
            category = "🛍️ Покупки"
        elif any(w in text_lower for w in ["кино", "игра", "развлечения", "отдых", "театр"]):
            category = "🎬 Развлечения"

        return (amount, currency, category, note)

    def parse_all_expenses(self, text: str) -> List[Tuple[float, str, str, str]]:
        """
        Parses text or transcribed voice for ALL expenses present in a single message.
        Normalizes spoken thousand abbreviations ("5 тыс" -> 5000, "8 тысяч" -> 8000).
        """
        text_normalized = normalize_spoken_numbers(text)
        text_lower = text_normalized.lower().strip()

        # Determine global default currency from text
        global_currency = "₸ (KZT)"
        if re.search(r"\b(?:доллар|долларов|доллара|баксов|бакс|\$|usd)\b", text_lower):
            global_currency = "$ (USD)"
        elif re.search(r"\b(?:рубль|рублей|рубля|руб|р\.|₽|rub)\b", text_lower):
            global_currency = "₽ (RUB)"
        elif re.search(r"\b(?:тенге|тг|kzt|₸)\b", text_lower):
            global_currency = "₸ (KZT)"

        # Split into segments by punctuation, newlines, and conjunction 'и'
        segments = re.split(r"[,;\n\.]|\bи\b", text_normalized)
        results = []

        for seg in segments:
            seg_str = seg.strip()
            if not seg_str:
                continue
            parsed = self._parse_single_segment(seg_str, global_currency)
            if parsed:
                results.append(parsed)

        # Fallback to single segment parse if regex split produced nothing
        if not results:
            parsed = self._parse_single_segment(text_normalized, global_currency)
            if parsed:
                results.append(parsed)

        return results

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
        """Formats clean, asterisk-free multi-currency expense statistics with totals and category subdivisions."""
        rec = self._get_user_record(user_id)
        totals = rec["totals"]
        categories = rec["categories"]
        items = rec["items"]
        items_count = len(items)

        active_totals = {curr: amt for curr, amt in totals.items() if amt > 0}

        if not active_totals and items_count == 0:
            return (
                "📊 СТАТИСТИКА РАСХОДОВ\n\n"
                "Ваша база расходов пуста.\n\n"
                "Отправьте текстовое или голосовое сообщение 🎙️ с суммой и назначением, чтобы добавить первый расход."
            )

        lines = [
            "📊 ОБЩАЯ СТАТИСТИКА РАСХОДОВ\n",
            "💵 ОБЩАЯ СУММА НАКОПЛЕННЫХ РАСХОДОВ:"
        ]

        for curr, curr_amt in totals.items():
            if curr_amt > 0:
                formatted_num = format_money(curr_amt)
                lines.append(f"  • {curr}: {formatted_num}")

        lines.append(f"\n📝 Всего проведенных операций: {items_count}")
        lines.append("\n📁 ПОДРАЗДЕЛЕНИЯ И КАТЕГОРИИ:")

        for cat, cat_dict in categories.items():
            cat_lines = []
            for curr, cat_amt in cat_dict.items():
                if cat_amt > 0:
                    formatted_amt = format_money(cat_amt)
                    cat_lines.append(f"{formatted_amt} {curr}")
            if cat_lines:
                lines.append(f"  • {cat}: " + ", ".join(cat_lines))

        if items:
            lines.append("\n📜 ПОСЛЕДНИЕ ЗАПИСИ:")
            for item in items[-5:]:
                amt_str = format_money(item['amount'])
                lines.append(f"  - {amt_str} {item['currency']} ({item['category']}): {item['note']}")

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
