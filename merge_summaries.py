"""
Merge per-chunk summary files into the single summary file used by chat.py.

Place summary files named like "history_chunk_12_summary.txt" in data/summaries/.
They are merged in chunk-number order into data/summary.txt.
"""

import os
import re

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.getenv("DATA_DIR", "data")
SUMMARIES_DIR = os.path.join(DATA_DIR, "summaries")
OUTPUT_FILE = os.path.join(DATA_DIR, "summary.txt")

def sort_key(file_name: str):
    """Sort by the first number in the file name; files without a number go last."""
    match = re.search(r"\d+", file_name)
    return (match is None, int(match.group()) if match else 0, file_name)

def merge_summaries() -> None:
    """Combine all summary files into one, keeping their chunk order."""
    if not os.path.isdir(SUMMARIES_DIR):
        print(f"No summaries folder found at '{SUMMARIES_DIR}'.")
        return

    files = sorted(
        (name for name in os.listdir(SUMMARIES_DIR) if name.endswith("_summary.txt")),
        key=sort_key,
    )

    sections = []
    for file_name in files:
        with open(os.path.join(SUMMARIES_DIR, file_name), "r", encoding="utf-8") as file:
            content = file.read().strip()
        if content:
            sections.append(f"===== {file_name} =====\n{content}")

    if not sections:
        print("No summary files with content were found.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_file:
        out_file.write("\n\n".join(sections) + "\n")

    print(f"Merged {len(sections)} summaries into '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    merge_summaries()