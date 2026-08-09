from collections import defaultdict
from typing import List, Dict, Any
import config

class MemoryManager:
    """Manages in-memory chat history for each Telegram user."""
    
    def __init__(self, max_history: int = config.MAX_HISTORY_MESSAGES):
        self.max_history = max_history
        # Structure: {user_id: [{"role": "user"|"assistant", "content": "text"}]}
        self._store: Dict[int, List[Dict[str, str]]] = defaultdict(list)

    def get_history(self, user_id: int) -> List[Dict[str, str]]:
        """Retrieve recent conversation history for a given user."""
        return self._store[user_id]

    def add_user_message(self, user_id: int, content: str):
        """Append user message to history, maintaining max_history limit."""
        self._store[user_id].append({"role": "user", "content": content})
        self._trim_history(user_id)

    def add_assistant_message(self, user_id: int, content: str):
        """Append assistant response to history, maintaining max_history limit."""
        self._store[user_id].append({"role": "assistant", "content": content})
        self._trim_history(user_id)

    def clear_history(self, user_id: int):
        """Clear conversation history for a user."""
        if user_id in self._store:
            self._store[user_id].clear()

    def _trim_history(self, user_id: int):
        """Keep history within max allowed count."""
        if len(self._store[user_id]) > self.max_history:
            # Keep only the latest `max_history` items
            self._store[user_id] = self._store[user_id][-self.max_history:]

# Global memory instance
memory = MemoryManager()
