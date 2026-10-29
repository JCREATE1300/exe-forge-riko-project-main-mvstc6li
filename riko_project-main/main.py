"""Talk to Riko: press Enter, speak, and she answers out loud on the avatar page.

    your voice -> asr.py -> text -> llm.py -> her reply -> tts.py -> her voice -> viewer.py -> avatar

Run:  uv run main.py                 (uses asr / tts from character_config.yaml)
      uv run main.py --tts fish      (override the voice)
      uv run main.py --asr groq      (override the ears)
"""
import argparse

from riko import asr, llm, tts, viewer
from riko.config import load_config


def main():
    parser = argparse.ArgumentParser(description="Talk to Riko.")
    parser.add_argument("--asr", choices=["local", "groq"], help="speech to text (overrides the config)")
    parser.add_argument("--tts", choices=["sovits", "fish"], help="her voice (overrides the config)")
    args = parser.parse_args()

    cfg = load_config()
    cfg["asr"] = args.asr or cfg["asr"]
    cfg["tts"] = args.tts or cfg["tts"]

    print(f"\n=== Riko  |  model: {cfg['model']}  |  ears: {cfg['asr']}  |  voice: {cfg['tts']} ===")
    llm.check(cfg)
    asr.check(cfg)
    tts.check(cfg)
    viewer.start(cfg)

    while True:
        try:
            recording = asr.record()
            if recording is None:
                continue
            text = asr.transcribe(recording, cfg)
            if not text:
                print("(heard nothing, try again)")
                continue
            print(f"You:  {text}")
            answer = llm.reply(text, cfg)
            print(f"Riko: {answer}")
            viewer.play(tts.speak(answer, cfg))
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            return
        except Exception as e:  # one bad turn should not end the chat
            print(f"[error] {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
