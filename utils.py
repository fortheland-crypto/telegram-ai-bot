from typing import List

MAX_TELEGRAM_MSG_LEN = 4000

def split_message(text: str, max_length: int = MAX_TELEGRAM_MSG_LEN) -> List[str]:
    """
    Split a long message into multiple chunks that fit within Telegram's limit.
    Tries to split by paragraphs/newlines first to preserve readability.
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = []
    current_length = 0

    lines = text.split("\n")

    for line in lines:
        line_len = len(line) + 1  # count the newline
        if current_length + line_len > max_length:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            # If a single line is longer than max_length, split by characters
            if line_len > max_length:
                for i in range(0, len(line), max_length):
                    chunks.append(line[i:i + max_length])
            else:
                current_chunk.append(line)
                current_length = line_len
        else:
            current_chunk.append(line)
            current_length += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks
