from expense_manager import expense_manager

def test_multi_currency_expenses():
    user_id = 88888
    expense_manager.reset_expenses(user_id)

    # Test KZT (Тенге)
    res_kzt = expense_manager.parse_expense_text("Потратил 5000 тенге на продукты")
    assert res_kzt is not None
    assert res_kzt[0] == 5000.0
    assert res_kzt[1] == "₸ (KZT)"
    assert res_kzt[2] == "🍔 Еда и Продукты"

    # Test USD (Доллары)
    res_usd = expense_manager.parse_expense_text("50 долларов такси")
    assert res_usd is not None
    assert res_usd[0] == 50.0
    assert res_usd[1] == "$ (USD)"
    assert res_usd[2] == "🚕 Транспорт"

    # Test RUB (Рубли)
    res_rub = expense_manager.parse_expense_text("1500 рублей еда")
    assert res_rub is not None
    assert res_rub[0] == 1500.0
    assert res_rub[1] == "₽ (RUB)"

    # Add expenses to manager
    expense_manager.add_expense(user_id, res_kzt[0], res_kzt[1], res_kzt[2], res_kzt[3])
    expense_manager.add_expense(user_id, res_usd[0], res_usd[1], res_usd[2], res_usd[3])
    expense_manager.add_expense(user_id, res_rub[0], res_rub[1], res_rub[2], res_rub[3])

    stats = expense_manager.get_stats(user_id)
    print("Multi-currency Stats output:\n", stats)

    assert "5 000.00" in stats or "5000.00" in stats
    assert "50.00" in stats
    assert "1 500.00" in stats or "1500.00" in stats

    expense_manager.reset_expenses(user_id)
    print("Multi-currency tests passed successfully!")

if __name__ == "__main__":
    test_multi_currency_expenses()
