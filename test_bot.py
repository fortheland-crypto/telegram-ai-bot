import unittest
from memory import MemoryManager
from utils import split_message

class TestBotCore(unittest.TestCase):
    def test_memory_manager(self):
        mem = MemoryManager(max_history=4)
        user_id = 100
        mem.add_user_message(user_id, "Привет")
        mem.add_assistant_message(user_id, "Здравствуйте!")
        mem.add_user_message(user_id, "Как дела?")
        mem.add_assistant_message(user_id, "Отлично!")
        
        history = mem.get_history(user_id)
        self.assertEqual(len(history), 4)
        
        # Test overflow
        mem.add_user_message(user_id, "Пятый вопрос")
        history = mem.get_history(user_id)
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0]["content"], "Здравствуйте!")
        self.assertEqual(history[-1]["content"], "Пятый вопрос")
        
        # Test clear
        mem.clear_history(user_id)
        self.assertEqual(len(mem.get_history(user_id)), 0)

    def test_split_message(self):
        short_text = "Короткий текст"
        self.assertEqual(split_message(short_text), [short_text])
        
        long_text = "А" * 5000
        chunks = split_message(long_text, max_length=2000)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= 2000 for c in chunks))

if __name__ == "__main__":
    unittest.main()
