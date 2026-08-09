from expense_manager import expense_manager

def test_batch_expenses():
    user_id = 77777
    expense_manager.reset_expenses(user_id)

    text = "Я потратил 1500 тенге такси, 2500 на продукты и на коммунальные услуги 6000 тенге"
    parsed_list = expense_manager.parse_all_expenses(text)

    print("Parsed batch items count:", len(parsed_list))
    for p in parsed_list:
        print("Item:", p)

    assert len(parsed_list) == 3, f"Expected 3 items, got {len(parsed_list)}"

    for amount, currency, category, note in parsed_list:
        expense_manager.add_expense(user_id, amount, currency, category, note)

    stats = expense_manager.get_stats(user_id)
    print("\nBatch Stats output:\n", stats)

    assert "10 000.00" in stats or "10000.00" in stats
    assert "Всего проведенных операций: 3" in stats

    expense_manager.reset_expenses(user_id)
    print("Batch expenses tests passed successfully!")

if __name__ == "__main__":
    test_batch_expenses()
