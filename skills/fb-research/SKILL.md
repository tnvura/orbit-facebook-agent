---
name: fb-research
description: This skill should be used when the user runs "/fb-research [number]", "research candidate", "research post number", "look up this post", or wants to research a Facebook accounting/tax question from the scan results. Takes a candidate from tracking/scan-results and produces a compiled vault entry plus a draft Thai reply.
version: 1.0.0
---

# fb-research

Research a candidate Facebook post, update Orbit Vault, and draft a Thai reply for human review.

## Overview

This skill orchestrates the full research pipeline for one candidate from `/fb-scan` results:

1. Load the candidate post
2. Extract existing community replies
3. Check Orbit Vault for existing coverage
4. Research via `vault-deep-research` if needed
5. Compile findings into the vault
6. Draft the Thai reply
7. Save and present to the user

The pipeline is **vault-first**: always check existing knowledge before doing external research. Each run compounds the vault, making future answers faster.

---

## Step 1 — Load Candidate

Parse `$ARGUMENTS` (the candidate number passed by the user):

- If a number (e.g. `3`) → load `tracking/scan-results-{today}.json`, pick entry at index `[number - 1]`
- If no argument → read `tracking/scan-results-{today}.json` and list all candidates by number, then stop and ask user which to research
- If no scan-results file for today → check yesterday's date, then report: "No scan results found. Run `/fb-scan` first."

Extract from the candidate entry: `post_id`, `post_url`, `author`, `text` (first 500 chars), `topic_tag`.

If `post_id` already exists in `tracking/processed-post-ids.txt` → warn user: "Post {post_id} was already processed. Research again? [y/N]" — stop unless confirmed.

---

## Step 2 — Extract Existing Replies

Run the reply extraction script:

```bash
cd "/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent"
python scripts/extract_replies.py "{post_url}"
```

The script outputs JSON: `[{"author": "...", "text": "...", "timestamp": "..."}, ...]`

If the script fails or returns an empty array, continue — zero replies is valid (common for fresh posts).

Store the replies list for Step 7 (reply validation).

---

## Step 3 — Search Orbit Vault

Invoke the **vault-search** skill to check existing coverage.

Search using:
- Thai keywords extracted from the post text (e.g. `ใบกำกับภาษี`, `VAT`, `ภ.พ.36`)
- The `topic_tag` from the scan result
- English equivalents if topic is cross-listed in vault

Return from vault-search: `strong` (≥1 directly relevant compiled page) / `weak` (partial match only) / `none`.

Read any matched pages fully before deciding.

---

## Step 4 — Research Decision Gate

**If vault coverage is STRONG:**
- Read the matched `topics/` and `entities/` pages
- Proceed directly to Step 6 (draft reply from vault)
- Skip Steps 5a–5b
- Note in the output: "Drafted from vault — no deep-research needed"

**If vault coverage is WEAK or NONE:**
- Proceed to Step 5a (vault-capture) then Step 5b (vault-deep-research)

---

## Step 5a — Capture the FB Post (if not already captured)

Check `sources/fb-posts/` for an existing file matching the post_id:

```bash
ls "/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/sources/fb-posts/" | grep "{post_id}"
```

If not found → invoke the **vault-capture** skill with `kind: fb-post` to create the source file at `Orbit Vault/sources/fb-posts/{YYYY-MM-DD}-post-{post_id}.md`.

If already exists → skip.

---

## Step 5b — Run vault-deep-research

Invoke the **vault-deep-research** skill on the question.

Pass:
- The verbatim Thai question text
- The post_id (for stub mapping)
- Any partial vault matches from Step 3 (to skip re-fetching known sources)

vault-deep-research writes its output directly to `Orbit Vault/sources/research/{date}-{slug}.md`.

After it completes, note:
- The confidence level (HIGH / MEDIUM / LOW)
- The stubs it filled (list of `topics/` + `entities/` + `posts/` page paths to create/update)
- Any C4 claims (questions with no authoritative source)

---

## Step 6 — Compile Vault Pages

Invoke the **vault-compile** skill to create or update vault pages from the research output.

Compile runs in this order:
1. `topics/` pages (broad subject pages)
2. `entities/` pages (specific forms/laws/orgs)
3. `posts/` page for this post_id (includes the draft Thai reply)
4. Backlink sweep (reciprocal links)
5. `index.md` update
6. `log.md` append

vault-compile writes the draft Thai reply into the `posts/` page under `## Draft Reply`.

---

## Step 7 — Validate Existing Replies

Using the replies from Step 2 and the research findings from Steps 3–5b, assess each community reply:

| Commenter | Reply (gist) | Assessment |
|-----------|-------------|------------|
| {author}  | {first 80 chars} | ✅ Correct / ⚠️ Partial / ❌ Wrong |

For each flagged reply, note specifically what is wrong and which law/standard contradicts it.

If no replies exist, skip this table.

---

## Step 8 — Present Results to User

Present a structured summary:

```
## /fb-research Results: {author} — {question snippet}

### Research Path
- Vault coverage: [strong / weak / none]
- Deep-research: [run / skipped]
- Confidence: [HIGH / MEDIUM / LOW]
- Sources used: [list]

### Vault Updates
- Created: [list of new pages]
- Updated: [list of updated pages]

### Reply Validation
[table from Step 7, or "No existing replies"]

### Draft Thai Reply
[draft from the posts/ page]

---
To post: /fb-reply {post_id}
To discard: delete tracking/drafts/{post_id}.md
```

Also save the draft to `tracking/drafts/{post_id}.md`:

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

## Error Handling

| Situation | Action |
|-----------|--------|
| No scan results for today | Report and stop; prompt user to run `/fb-scan` |
| `extract_replies.py` fails | Warn, continue with empty replies list |
| vault-deep-research returns LOW confidence | Include confidence warning in the summary; flag specific C4 claims |
| vault-compile fails on one page | Report the failed page, continue with others |
| Post already in `processed-post-ids.txt` | Warn and ask for confirmation before re-researching |

---

## Reply Voice Rules

Draft replies following the **Reply Voice Guide** in `CLAUDE.md` (section "Reply Voice Guide"):

- Thai language always
- Professional but approachable — friendly expert, not corporate
- Specific — cite the actual law, form name, or rate (e.g., "ตาม ม.80/1 แห่งประมวลรัษฎากร")
- Practical — give actionable steps, not "consult an accountant"
- Not a hard sell — Orbit Advisory's name appears from the page; no service promotion needed

---

## File Paths

| File | Path |
|------|------|
| Scan results | `tracking/scan-results-{YYYY-MM-DD}.json` |
| Processed IDs | `tracking/processed-post-ids.txt` |
| Draft output | `tracking/drafts/{post_id}.md` |
| FB post source | `Orbit Vault/sources/fb-posts/{date}-post-{post_id}.md` |
| Research source | `Orbit Vault/sources/research/{date}-{slug}.md` |
| Vault base | `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/` |
| Plugin base | `/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent/` |

---

## Skills Invoked

| Skill | When |
|-------|------|
| vault-search | Step 3 — always |
| vault-capture | Step 5a — if fb-post not already captured |
| vault-deep-research | Step 5b — if vault coverage is weak or none |
| vault-compile | Step 6 — always |
