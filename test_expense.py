from expense_manager import expense_manager

def test_thousand_abbreviations():
    user_id = 99999
    expense_manager.reset_expenses(user_id)

    # Test spoken abbreviations transcribed by Whisper: "5 тыс", "5 тысяч", "8 тыс"
    text = "Я потратил 5 тыс тенге такси, 5 тысяч на продукты и 8 тыс на заправку авто"
    parsed_list = expense_manager.parse_all_expenses(text)

    print("Parsed thousand abbreviation items:", parsed_list)
    assert len(parsed_list) == 3

    amounts = [p[0] for p in parsed_list]
    assert amounts == [5000.0, 5000.0, 8000.0], f"Expected [5000.0, 5000.0, 8000.0], got {amounts}"

    for amount, currency, category, note in parsed_list:
        expense_manager.add_expense(user_id, amount, currency, category, note)

    stats = expense_manager.get_stats(user_id)
    print("\nSpoken Thousand Stats output:\n", stats)

    assert "18 000" in stats
    assert "Всего проведенных операций: 3" in stats

    expense_manager.reset_expenses(user_id)
    print("Spoken thousand abbreviation test passed successfully!")

if __name__ == "__main__":
    test_thousand_abbreviations()
