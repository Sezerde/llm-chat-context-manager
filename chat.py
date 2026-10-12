"""
Command-line chat client for the Claude API with locally stored history.

The full conversation history is kept on disk. Each request sends only the
most recent messages, plus a merged summary of earlier conversations (if one
exists), so long-running conversations stay within the model's context window.
"""

import json
import os
from typing import Dict, List

import anthropic
from dotenv import load_dotenv

load_dotenv()

# Configuration (any of these can be overridden in .env)
API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))
MAX_CONTEXT_MESSAGES = int(os.getenv("MAX_CONTEXT_MESSAGES", "20"))

DATA_DIR = os.getenv("DATA_DIR", "data")
HISTORY_FILE = os.path.join(DATA_DIR, "conversation_history.json")
CORE_PROMPT_FILE = os.path.join(DATA_DIR, "core_prompt.txt")
SUMMARY_FILE = os.path.join(DATA_DIR, "summary.txt")

DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant."
EXIT_COMMANDS = {"exit", "quit", "q"}

Message = Dict[str, str]


def load_conversation_history() -> List[Message]:
    """
    Load the full conversation history from local storage.

    Older versions stored the system prompt inside the history (OpenAI format).
    The Anthropic Messages API only accepts "user" and "assistant" roles,
    so any other entries are filtered out.
    """
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            history = json.load(file)
    except json.JSONDecodeError:
        # Keep the unreadable file instead of overwriting it on the next save
        backup = HISTORY_FILE + ".corrupt"
        os.replace(HISTORY_FILE, backup)
        print(f"Warning: could not parse the history file. Moved it to '{backup}' and started a new history.")
        return []

    if not isinstance(history, list):
        print("Warning: unexpected history format. Starting a new history.")
        return []

    return [
        message for message in history
        if isinstance(message, dict)
        and message.get("role") in ("user", "assistant")
        and isinstance(message.get("content"), str)
        and message["content"].strip()
    ]


def save_conversation_history(history: List[Message]) -> None:
    """
    Write the full conversation history to local storage.

    Writes to a temporary file first, then replaces the original,
    so a crash mid-write cannot corrupt the existing history.
    """
    temp_file = HISTORY_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=4)
    os.replace(temp_file, HISTORY_FILE)


def read_text_file(path: str) -> str:
    """Return the stripped contents of a text file, or an empty string if it does not exist."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            return file.read().strip()
    return ""


def build_system_prompt() -> str:
    """Combine the core prompt with the merged summary of earlier conversations, if available."""
    core_prompt = read_text_file(CORE_PROMPT_FILE) or DEFAULT_SYSTEM_PROMPT
    summary = read_text_file(SUMMARY_FILE)
    if summary:
        return f"{core_prompt}\n\nSummary of earlier conversations:\n{summary}"
    return core_prompt


def build_message_window(history: List[Message], max_messages: int) -> List[Message]:
    """
    Select the most recent messages to send to the API.

    The API requires the first message to come from the user and roles to
    alternate, so leading assistant messages are dropped and consecutive
    messages from the same role are merged.
    """
    window = history[-max(1, max_messages):]

    while window and window[0]["role"] != "user":
        window = window[1:]

    merged: List[Message] = []
    for message in window:
        if merged and merged[-1]["role"] == message["role"]:
            merged[-1] = {
                "role": message["role"],
                "content": merged[-1]["content"] + "\n\n" + message["content"],
            }
        else:
            merged.append({"role": message["role"], "content": message["content"]})
    return merged


def extract_text(response) -> str:
    """Join all text blocks in an API response."""
    return "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()


def main() -> None:
    """Run the interactive chat loop."""
    if not API_KEY:
        print("Error: ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")
        return

    os.makedirs(DATA_DIR, exist_ok=True)

    client = anthropic.Anthropic(api_key=API_KEY)
    history = load_conversation_history()
    system_prompt = build_system_prompt()

    print(f"Chat started with {MODEL}. History is stored locally in '{DATA_DIR}/'.")
    print("Type 'exit' to quit.")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break

        if not user_input:
            continue
        if user_input.lower() in EXIT_COMMANDS:
            print("Session ended.")
            break

        history.append({"role": "user", "content": user_input})

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=build_message_window(history, MAX_CONTEXT_MESSAGES),
            )
        except anthropic.APIError as error:
            history.pop()  # Drop the unanswered message so the history stays consistent
            print(f"\n[API error] {error}")
            continue

        reply = extract_text(response)
        if not reply:
            history.pop()
            print("\n[Warning] The model returned an empty reply. Please try again.")
            continue

        print(f"\nAssistant: {reply}")
        history.append({"role": "assistant", "content": reply})
        save_conversation_history(history)


if __name__ == "__main__":
    main()