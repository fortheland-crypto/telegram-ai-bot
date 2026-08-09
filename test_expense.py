from expense_manager import expense_manager

def test_expenses():
    user_id = 99999
    expense_manager.reset_expenses(user_id)

    # Test parsing
    res1 = expense_manager.parse_expense_text("Потратил 500 рублей на продукты")
    assert res1 is not None, "Failed to parse 500 rubles"
    assert res1[0] == 500.0
    assert res1[1] == "🍔 Еда и Продукты"

    res2 = expense_manager.parse_expense_text("1200 такси")
    assert res2 is not None, "Failed to parse 1200 taxi"
    assert res2[0] == 1200.0
    assert res2[1] == "🚕 Транспорт"

    # Add expenses
    expense_manager.add_expense(user_id, res1[0], res1[1], res1[2])
    expense_manager.add_expense(user_id, res2[0], res2[1], res2[2])

    stats = expense_manager.get_stats(user_id)
    print("Stats output:\n", stats)

    assert "1 700.00 руб" in stats or "1700.00 руб" in stats or "1700" in stats
    expense_manager.reset_expenses(user_id)
    print("Expense Manager tests passed successfully!")

if __name__ == "__main__":
    test_expenses()
