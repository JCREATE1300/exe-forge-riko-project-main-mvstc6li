"""Her brain: send the chat so far to OpenAI and get her reply.

The chat is saved to history_file after every turn, so she remembers it
next time. Delete that file to start fresh.
"""
import json

from openai import OpenAI

from riko.config import ROOT, need_key


def check(cfg):
    need_key("OPENAI_API_KEY", f"the LLM, model {cfg['model']}")


def reply(user_text, cfg):
    history_path = ROOT / cfg["history_file"]
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else []
    history.append({"role": "user", "content": user_text})

    # ponytail: sends the whole chat every turn; trim to history[-N:] if it gets long or pricey.
    response = OpenAI().responses.create(
        model=cfg["model"],
        instructions=cfg["system_prompt"],
        input=history,
    )

    history.append({"role": "assistant", "content": response.output_text})
    history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    return response.output_text


if __name__ == "__main__":
    # One test message: uv run python -m riko.llm
    from riko.config import load_config
    cfg = load_config()
    check(cfg)
    print("Riko:", reply("Hi! Say something short.", cfg))
