---
name: fb-reply
description: This skill should be used when the user runs "/fb-reply <post_id>", "post reply", "post the draft", or wants to submit an approved draft reply to a Facebook group post as Orbit Advisory. Requires an existing draft in tracking/drafts/{post_id}.md. Always shows the full draft and requires explicit confirmation before posting.
version: 1.0.0
---

# fb-reply

Post a pre-approved draft reply to a Facebook group post as Orbit Advisory.
Hard-stop confirmation required — nothing is posted without explicit user approval.

---

## Overview

1. Load and display the draft
2. Hard-stop confirmation
3. Post via browser automation (profile safety check included)
4. Archive draft to `tracking/posted/`
5. Update Orbit Vault post page outcome to `posted`
6. Remove draft file

---

## Step 1 — Load Draft

Parse `$ARGUMENTS` for a `post_id`.

If no argument → list all files in `tracking/drafts/`:

```bash
ls "/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent/tracking/drafts/"
```

Display each as a numbered list with the frontmatter `author` field. Ask which to post.

If post_id provided → read `tracking/drafts/{post_id}.md`.

If file does not exist → "No draft found for {post_id}. Run `/fb-research` first." — stop.

---

## Step 2 — Display Draft and Hard-Stop Confirmation

Show the full draft to the user:

```
## Draft ready to post

Post:   {post_url}
Author: {author}

--- Reply ---
{full draft body text}
-------------

Type "post" to submit this comment as Orbit Advisory, or anything else to cancel.
```

Wait for user input.

- If input is exactly `post` (case-insensitive) → proceed to Step 3
- Any other input → "Cancelled. Draft preserved at tracking/drafts/{post_id}.md." — stop

---

## Step 3 — Post via Script

```bash
cd "/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent"
python3 scripts/post_reply.py \
  "{post_url}" \
  "tracking/drafts/{post_id}.md" \
  ".browser-profile"
```

**Exit code handling:**

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Posted successfully | Proceed to Step 4 |
| 1 | Error (browser/network/comment box) | Report error, preserve draft, stop |
| 2 | Wrong profile (not Orbit Advisory) | "Switch to Orbit Advisory in Chrome and retry." — stop |

---

## Step 4 — Archive Draft to `tracking/posted/`

Read `tracking/drafts/{post_id}.md`. Write to `tracking/posted/{post_id}.md` adding a `posted` date field to the frontmatter:

```markdown
---
post_id: "{post_id}"
post_url: "{post_url}"
author: "{author}"
drafted: {drafted_date}
posted: {today YYYY-MM-DD}
status: posted
---

{reply body text}
```

---

## Step 5 — Update Orbit Vault Post Page

Find the vault post page:

```bash
ls "/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/posts/" | grep "{post_id}"
```

If found → read the file and update the `outcome` frontmatter field from `reply-drafted` to `posted`.

If not found → warn "Vault post page not found for {post_id} — skipping vault update." and continue.

---

## Step 6 — Remove Draft File

Delete `tracking/drafts/{post_id}.md`.

---

## Step 7 — Confirm to User

```
Posted successfully.

  Post:   {post_url}
  Author: {author}
  Archived: tracking/posted/{post_id}.md
  Vault:  outcome updated to "posted"
```

---

## File Paths

| File | Path |
|------|------|
| Draft input | `tracking/drafts/{post_id}.md` |
| Posted archive | `tracking/posted/{post_id}.md` |
| Post script | `scripts/post_reply.py` |
| Browser profile | `.browser-profile` |
| Vault posts | `Orbit Vault/posts/` |

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Draft file missing | Report and stop |
| User does not type "post" | Cancel and preserve draft |
| Script exits 1 (browser error) | Report stderr, preserve draft, stop |
| Script exits 2 (wrong profile) | Instruct user to switch profile in Chrome, stop |
| Vault page not found | Warn and continue — non-blocking |
