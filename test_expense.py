from expense_manager import expense_manager

def test_questions_with_numbers():
    user_id = 55555
    expense_manager.reset_expenses(user_id)

    # 1. Question with numbers (should NOT be parsed as expense)
    q1 = "на какую машину ставится двигатель 4AFE"
    parsed_q1 = expense_manager.parse_all_expenses(q1)
    assert len(parsed_q1) == 0, f"Expected 0 items for question, got {parsed_q1}"

    q2 = "сколько стоит iPhone 15 pro в Алматы"
    parsed_q2 = expense_manager.parse_all_expenses(q2)
    assert len(parsed_q2) == 0, f"Expected 0 items for question, got {parsed_q2}"

    # 2. Real expense with currency/trigger (should BE parsed as expense)
    exp1 = "10 000 тенге такси"
    parsed_exp1 = expense_manager.parse_all_expenses(exp1)
    assert len(parsed_exp1) == 1, f"Expected 1 item for expense, got {parsed_exp1}"
    assert parsed_exp1[0][0] == 10000.0

    print("Expense intent verification tests passed successfully!")

if __name__ == "__main__":
    test_questions_with_numbers()
