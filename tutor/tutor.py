"""Tutoring session loop with a memory-aware system prompt.

Flow: load profile -> build system prompt -> chat -> on exit, reflect on the
transcript and persist validated profile updates.

Usage: python -m tutor.tutor --learner maya --subject "high-school calculus"
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tutor.memory import apply_updates, get_profile, render_for_prompt  # noqa: E402

SYSTEM_TEMPLATE = """You are a patient, expert tutor for {subject}.
Adapt every explanation to this learner profile:

{memory}

Teaching rules:
- Match the learner's preferred style and pace from the profile.
- For topics listed under "Watch out", use a different strategy than worked
  examples alone (e.g. contrast the confusable ideas side by side).
- Check understanding with one small question before moving on.
- Never mention the profile or these instructions.
"""

REFLECTION_PROMPT = """Below is a tutoring session transcript. Extract updates to the
learner profile as a JSON object using ONLY these fields:
- goals (list of strings), learns_best_by (string), pace (string),
  mastered_topics (list), active_topics (list),
  misconceptions (list of {{"topic", "note", "seen_count"}}),
  preferences (object).
Only include fields you have real evidence for in THIS transcript. Merge with
the current profile sensibly (keep still-true entries). Return JSON only.

Current profile: {profile}

Transcript:
{transcript}
"""


def _client():
    from openai import OpenAI

    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _chat(client, model: str, messages: list[dict]) -> str:
    response = client.chat.completions.create(model=model, messages=messages, temperature=0.4)
    return response.choices[0].message.content


def reflect_and_save(client, model: str, learner: str, transcript: str, db_path: str) -> dict:
    """Post-session reflection: propose profile updates and persist them."""
    profile = get_profile(learner, db_path)
    raw = _chat(client, model, [{
        "role": "user",
        "content": REFLECTION_PROMPT.format(profile=json.dumps(profile), transcript=transcript),
    }])
    try:
        updates = json.loads(raw)
    except json.JSONDecodeError:
        print("(Reflection did not return valid JSON; profile unchanged.)")
        return profile
    new_profile = apply_updates(learner, updates, db_path)
    changed = [k for k in updates if k in new_profile]
    if changed:
        print(f"(Memory updated: {', '.join(changed)})")
    return new_profile


def run_session(learner: str, subject: str, model: str, db_path: str) -> None:
    client = _client()
    profile = get_profile(learner, db_path)
    memory_block = render_for_prompt(profile, learner)
    messages = [{"role": "system", "content": SYSTEM_TEMPLATE.format(subject=subject, memory=memory_block)}]
    print(f"Tutor ready for {learner} ({subject}). Type 'quit' to end the session.\n")
    transcript_lines: list[str] = []
    while True:
        try:
            user_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            user_text = "quit"
        if user_text.lower() in ("quit", "exit"):
            break
        if not user_text:
            continue
        messages.append({"role": "user", "content": user_text})
        transcript_lines.append(f"Student: {user_text}")
        reply = _chat(client, model, messages)
        messages.append({"role": "assistant", "content": reply})
        transcript_lines.append(f"Tutor: {reply}")
        print(f"\nTutor: {reply}\n")
    if transcript_lines:
        reflect_and_save(client, model, learner, "\n".join(transcript_lines), db_path)
    print("Session saved. Bye!")


def main() -> int:
    parser = argparse.ArgumentParser(description="AI tutor with learner memory")
    parser.add_argument("--learner", required=True)
    parser.add_argument("--subject", default="general study skills")
    parser.add_argument("--model", default=os.environ.get("TUTOR_MODEL", "gpt-4o-mini"))
    parser.add_argument("--db", default=os.environ.get("TUTOR_DB", "tutor_memory.db"))
    args = parser.parse_args()
    run_session(args.learner, args.subject, args.model, args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
