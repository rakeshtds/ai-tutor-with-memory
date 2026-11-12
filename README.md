# AI Tutor With Memory

An AI tutor that remembers how *you* learn. After every session it updates a persistent learner profile — preferred explanation style, pace, goals, and recurring misconceptions — and injects that profile into the next session's system prompt, so lesson two never starts from zero.

## Features

- Persistent learner profile in SQLite (no server needed): style preferences, pace, goals, mastered topics, active misconceptions
- Memory-aware system prompt assembled from the profile at session start
- Post-session reflection step: the model proposes profile updates (validated against the schema before saving)
- Misconception tracking: a concept the student gets wrong twice is flagged and re-taught with a different strategy next time
- Full profile history with timestamps, so you can see what the tutor has learned about the learner
- CLI session loop; works with any OpenAI-compatible endpoint

## Architecture

`tutor/memory.py` owns the SQLite profile store (get / update / render-as-prompt). `tutor/tutor.py` runs the session: load profile → build system prompt → chat loop → on exit, a reflection call extracts structured profile updates → schema validation → save. See `tutor/profile_schema.md` for the profile contract.

## Tech Stack

Python 3.11 · SQLite (stdlib) · OpenAI-compatible LLM API

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
```

## Usage

```bash
# Start (or resume) tutoring for a learner
python -m tutor.tutor --learner maya --subject "high-school calculus"

# Inspect what the tutor remembers
python -m tutor.memory --learner maya --show
```

During a session, type normally; type `quit` to end — the tutor reflects on the session and updates the profile before exiting.

## Example Output

Profile excerpt after two sessions:

```
Learner: maya
Goals: pass calculus final in June
Learns best by: worked examples before theory
Pace: short steps, frequent checks
Mastered: chain rule (basic), product rule
Watch out: mixes up chain rule and product rule under time pressure
```

## Project Structure

```
tutor/memory.py          SQLite learner-profile store + prompt rendering
tutor/tutor.py           Session loop + post-session reflection
tutor/profile_schema.md  Profile field contract and update rules
```

## Roadmap

- Spaced-repetition scheduling driven by misconception history
- Multiple subjects per learner with separate mastery maps
- Web UI with a profile dashboard

---

An original implementation built for portfolio purposes. Sample data is synthetic.
