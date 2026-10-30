"""Her brain: send the chat so far to OpenAI and get her reply.

The chat is saved to history_file after every turn, so she remembers it
next time. Delete that file to start fresh.
"""
import json

from openai import OpenAI

from riko.config import ROOT, need_key


def check(cfg):
    need_key("OPENAI_API_KEY", f"the LLM, model {cfg['model']}")


def _load_history(history_path):
    if not history_path.exists():
        return []
    try:
        parsed = json.loads(history_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print(f"[llm] history reset because {history_path.name} was unreadable")
        return []
    if not isinstance(parsed, list):
        print(f"[llm] history reset because {history_path.name} did not contain a list")
        return []
    return parsed


def reply(user_text, cfg):
    history_path = ROOT / cfg["history_file"]
    history = _load_history(history_path)
    history.append({"role": "user", "content": user_text})

    # Keep the conversation bounded; a long history gets expensive and noisy.
    if len(history) > 50:
        history = history[-50:]

    response = OpenAI().responses.create(
        model=cfg["model"],
        instructions=cfg["system_prompt"],
        input=history,
    )
    reply_text = getattr(response, "output_text", None)
    if not reply_text:
        raise RuntimeError("OpenAI returned an empty response.")

    history.append({"role": "assistant", "content": reply_text})
    history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    return reply_text


if __name__ == "__main__":
    # One test message: uv run python -m riko.llm
    from riko.config import load_config
    cfg = load_config()
    check(cfg)
    print("Riko:", reply("Hi! Say something short.", cfg))
