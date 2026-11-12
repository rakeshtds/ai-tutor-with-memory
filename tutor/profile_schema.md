# Learner Profile Schema

The profile is the tutor's long-term memory about one learner. It is stored in
SQLite (`profile_fields` + `profile_history`) and rendered into the system
prompt at the start of every session.

## Fields

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `goals` | list[str] | What the learner is working toward | `["pass calculus final in June"]` |
| `learns_best_by` | str | Explanation style that works | `"worked examples before theory"` |
| `pace` | str | Preferred step size and check-in frequency | `"short steps, frequent checks"` |
| `mastered_topics` | list[str] | Topics the learner has demonstrated | `["product rule"]` |
| `active_topics` | list[str] | Topics currently being learned | `["chain rule"]` |
| `misconceptions` | list[obj] | Recurring errors: `{topic, note, seen_count}` | see below |
| `preferences` | dict | Small free-form facts | `{"session_length_min": 25}` |

Misconception object:

```json
{"topic": "chain rule", "note": "mixes it up with the product rule under time pressure", "seen_count": 2}
```

## Update rules

1. Only the post-session **reflection step** writes the profile — never mid-session.
2. Updates must pass `validate_updates()` in `memory.py`: unknown fields and
   wrong types are dropped silently.
3. The reflection model may only assert things evidenced in the transcript
   (no guessing at goals or style).
4. A topic moves to `mastered_topics` only after the learner demonstrates it
   unaided in the transcript.
5. `seen_count` on a misconception increments each session it recurs; at 2+ the
   tutor must change teaching strategy for that topic.
6. Every write is recorded in `profile_history` (old value, new value, time)
   so the memory is auditable and reversible.
