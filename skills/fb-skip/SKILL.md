---
name: fb-skip
description: This skill should be used when the user says "skip candidate N", "skip N", "pass on N", or wants to dismiss one or more open candidates from the fb-research list without researching them. Can be invoked directly as /fb-skip or called by fb-research mid-flow.
version: 1.0.0
---

# fb-skip

Mark one or more open candidates as skipped so they no longer appear in the open candidate list. Does not post any reply — just records the skip and shows the updated list.

---

## Usage

- `/fb-skip 3` — skip candidate number 3
- `/fb-skip 2 5` — skip candidates 2 and 5
- `/fb-skip 3 --reason "off-topic"` — skip with a recorded reason

If called by `fb-research` mid-flow, the arguments are passed directly.

---

## Step 1 — Parse Arguments

Extract candidate numbers and optional reason from the arguments.

- Numbers: one or more integers (e.g. `3`, `2 5`)
- Reason: optional free text after `--reason` (default: empty)

If no numbers provided → list the current open candidates and ask which to skip.

---

## Step 2 — Skip Each Candidate

For each candidate number, run:

```bash
cd "/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent"
python3 scripts/list_open_candidates.py --skip {number} --reason "{reason}"
```

Run sequentially if skipping multiple candidates — each skip rebuilds the list, so numbers shift after each operation. Process in **descending order** (highest number first) to avoid number-shift errors mid-sequence.

Capture stderr for confirmation messages.

---

## Step 3 — Show Updated List

After all skips are recorded, run the script one final time to get the current open list:

```bash
cd "/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent"
python3 scripts/list_open_candidates.py
```

Display the result in the same format as `fb-research` Step 1:

```
Open candidates ({n} remaining):

{number}. [{topic}] {author} — {text snippet} (scan: {scan_date})
...

Pick a number to research, or skip more candidates.
```

If the list is empty → "No open candidates. Run /fb-scan for fresh posts."

---

## File Paths

| File | Path |
|------|------|
| Script | `scripts/list_open_candidates.py` |
| Skip records | `tracking/skipped/{post_id}.md` |
