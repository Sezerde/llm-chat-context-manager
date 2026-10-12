# LLM Chat Client with Context Management

A command-line chat client for the Claude API that keeps the full conversation
history on your own machine and manages the model's context window automatically.

## Why I Built This

I started this project because the chat tools I was using couldn't carry
anything over between conversations. Once a chat hit the model's context
limit, I had to open a new one and start from scratch.

It felt like having an English tutor who loses their memory every morning:
before every lesson, you have to reintroduce yourself and explain how far
you've gotten.

So I built my own client, first on the OpenAI API and later on the Claude API,
that saves the full conversation history to my own drive and decides what to
send to the model each time.

Building it taught me that the API itself doesn't remember anything between
requests: the client has to decide what history to send every time. That's
the part this project handles.

Note: conversation history is stored locally, but messages are still sent to
the Claude API to generate replies.

## How It Works

```
data/core_prompt.txt ──┐
                       ├──> system prompt ──┐
data/summary.txt ──────┘                    ├──> Claude API
                                            │
last N messages of history ─────────────────┘
```

- The full history is saved to `data/conversation_history.json` after every reply.
- Each request sends only the most recent messages (`MAX_CONTEXT_MESSAGES`),
  so long conversations stay within the context window and cost stays bounded.
- If you provide summaries of earlier conversations (see Using Summaries),
  they are merged and added to the system prompt, so older context can
  carry forward.

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add your Anthropic API key.
3. (Optional) Copy `core_prompt.example.txt` to `data/core_prompt.txt` and edit it.
4. Run: `python chat.py`

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | Your Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-haiku-5-5` | Model used for replies |
| `MAX_CONTEXT_MESSAGES` | `20` | Number of recent messages sent with each request |
| `MAX_TOKENS` | `1024` | Maximum length of each reply |

## Using Summaries (Optional)

Place summary files named like `history_chunk_12_summary.txt` in
`data/summaries/`, then run `python merge_summaries.py`. The merged result is
written to `data/summary.txt` and loaded the next time you start a chat.

## Design Decisions

- **Full history on disk, partial history in each request.** Nothing is lost
  locally, while each request stays within a predictable size.
- **Safe writes.** History is written to a temporary file and then swapped in,
  so a crash mid-write cannot corrupt it. An unreadable history file is backed
  up instead of being overwritten.
- **Consistent state on failure.** If an API call fails, the unanswered message
  is removed so the stored history always contains complete exchanges.
- **Backward compatibility.** Histories from the original OpenAI-based version
  are filtered to the roles the Anthropic API accepts.

## Known Limitations

- Summaries are created outside this tool; they are not generated automatically yet.
- The context window is measured in messages, not tokens, so very long
  messages could still approach the model's limit.
- Only storage is local; replies require sending messages to a cloud API.

## Future Work

- Generate summaries automatically when the history grows past a threshold
- Use a token-based budget instead of a message count
- Support local models (e.g., Ollama) for fully offline use
- Encrypt the stored history at rest