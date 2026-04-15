---
name: fb-research
description: This skill should be used when the user runs "/fb-research [number]", "research candidate", "research post number", "look up this post", or wants to research a Facebook accounting/tax question from the scan results. Takes a candidate from tracking/scan-results, delegates knowledge research to vault-research, and produces a draft Thai reply.
version: 1.1.0
---

# fb-research

Research a candidate Facebook post and draft a Thai reply for human review. Delegates all knowledge work to `vault-research` — this skill handles only the Facebook-specific workflow.

---

## Overview

1. Load the candidate post from scan results
2. Extract existing community replies
3. Capture the FB post to the vault
4. Invoke `vault-research` → research the question + update Orbit Vault
5. Validate community replies against research findings
6. Draft the Thai reply and save for approval
7. Present results to user

---

## Step 1 — Load Candidate

Run the open candidates script:

```bash
cd "/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent"
python3 scripts/list_open_candidates.py
```

**If no argument provided** → display the open list and wait for user input:

```
Open candidates ({n} total):

{number}. [{topic}] {author} — {text snippet} (scan: {scan_date})
...

Pick a number to research, or say "skip N" to dismiss a candidate.
```

- If user says "research N" or just types a number → proceed with that candidate
- If user says "skip N" (or "skip 2, 5") → invoke **fb-skip** with those numbers → re-run script → re-display updated list → wait again
- If list is empty → "No open candidates. Run `/fb-scan` for fresh posts." — stop

**If a number is provided as argument** → pick the matching entry from the script output by `number` field. If not found → "No open candidate with that number. Run `/fb-research` without arguments to see the current list." — stop.

**If script exits with code 2** → "No scan-results files found. Run `/fb-scan` first." — stop.

Extract from the selected candidate: `post_id`, `post_url`, `author`, `text`, `topic`.

---

## Step 2 — Extract Existing Replies

```bash
cd "/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent"
python3 scripts/extract_replies.py "{post_url}"
```

Output: `[{"author": "...", "text": "...", "timestamp": "..."}, ...]`

If the script fails or returns empty, continue — zero replies is valid.

Store the replies list for Step 5.

---

## Step 3 — Capture FB Post

Check `Orbit Vault/sources/fb-posts/` for an existing file matching the post_id:

```bash
ls "/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/sources/fb-posts/" | grep "{post_id}"
```

If not found → invoke **vault-capture** with:
- `kind = fb-post`
- `content` = post text + replies (structured as `## Post` / `## Replies` sections)
- `slug = post-{post_id}`
- `metadata` = `{post_id, post_url, author}`

If already exists → skip.

---

## Step 4 — Invoke vault-research

Invoke the **vault-research** skill:

```
vault-research(
  question    = post text (verbatim Thai question),
  post_id     = post_id,
)
```

vault-research handles everything: vault-search → coverage gate → vault-deep-research (if needed) → vault-capture → vault-compile.

Receive the result object:
- `research_path` (vault_only | deep_research)
- `confidence` (HIGH / MEDIUM / LOW)
- `pages_created`, `pages_updated`
- `c4_gaps`
- `vault_pages` (list of compiled pages to read for drafting the reply)

Read the compiled vault pages listed in `vault_pages` before proceeding to Step 5.

---

## Step 5 — Validate Existing Replies

Using the replies from Step 2 and the vault_pages from Step 4, assess each community reply:

| Commenter | Reply (gist) | Assessment |
|-----------|-------------|------------|
| {author}  | {first 80 chars} | ✅ Correct / ⚠️ Partial / ❌ Wrong |

Note specifically what is wrong and which law/standard contradicts it.

If no replies exist, skip this table.

---

## Step 6 — Draft Thai Reply and Save

Draft the Thai reply following the **Reply Voice Rules** below.

Save to `tracking/drafts/{post_id}.md`:

```markdown
---
post_id: "{post_id}"
post_url: "{post_url}"
author: "{author}"
drafted: {YYYY-MM-DD}
status: pending-approval
---

{draft reply text}
```

---

## Step 7 — Present Results

```
## /fb-research Results: {author} — {question snippet}

### Research Path
- Vault coverage: [strong / weak / none]
- Deep-research: [run / skipped]
- Confidence: [HIGH / MEDIUM / LOW]
- Sources: [list]

### Vault Updates
- Created: [list]
- Updated: [list]

### Reply Validation
[table from Step 5, or "No existing replies"]

### Draft Thai Reply
[draft text]

---
To post: /fb-reply {post_id}
To discard: delete tracking/drafts/{post_id}.md
```

---

## Reply Voice Rules

- Thai language always
- Use **ครับ** throughout — reply as a male speaker
- Professional but approachable — friendly expert, not corporate
- Specific — cite the actual law, form name, or rate (e.g. "ตาม ม.80/1 แห่งประมวลรัษฎากร")
- Practical — give actionable steps, not "consult an accountant"
- Not a hard sell — Orbit Advisory's name appears from the page; no explicit promotion
- **No emoji or icons** — reply must read as human-written, not bot-generated

---

## Error Handling

| Situation | Action |
|-----------|--------|
| No scan results for today | Report and stop; prompt to run `/fb-scan` |
| `extract_replies.py` fails | Warn, continue with empty replies list |
| vault-research returns LOW confidence | Include warning in summary; flag C4 claims |
| vault-research returns STRONG coverage | Note "Drafted from vault — no deep-research needed" |
| Post already in `processed-post-ids.txt` | Warn and ask confirmation before re-researching |

---

## File Paths

| File | Path |
|------|------|
| Scan results | `tracking/scan-results-{YYYY-MM-DD}.json` |
| Processed IDs | `tracking/processed-post-ids.txt` |
| Draft output | `tracking/drafts/{post_id}.md` |
| FB post source | `Orbit Vault/sources/fb-posts/{date}-post-{post_id}.md` |
| Vault base | `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/` |

---

## Skills Invoked

| Skill | Step | When |
|-------|------|------|
| vault-capture | 3 | If fb-post not already captured |
| vault-research | 4 | Always — handles all knowledge work |
