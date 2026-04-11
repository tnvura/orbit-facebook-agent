# Orbit Facebook Agent

## Business Context

AI agent for building Orbit Advisory's social presence in Thai Facebook accounting/tax communities. The agent monitors target groups, identifies tax/accounting questions, researches correct answers, and drafts replies as the Orbit Advisory page — all with human approval before posting.

**Target group**: อยากรู้เรื่องบัญชี เรื่องภาษี เชิญที่นี่คะ  
**Group ID**: `598953943470618`  
**Group URL**: https://www.facebook.com/groups/598953943470618  
**Group size**: 184.9K members (as of 2026-04-11)

---

## Architecture

```
/fb-scan    → Playwright extract → JS keyword filter → Haiku classify → candidate list
/fb-research → Vault search → deep-research verify → validate replies → vault-ingest → draft
/fb-reply   → Load draft → Playwright fill comment → user confirms → post
```

**Human-in-the-loop**: agent drafts everything, user approves before any comment is posted.

### Component Files

| Component | File(s) |
|-----------|---------|
| Scan command | `commands/fb-scan.md` + `skills/fb-scan/SKILL.md` |
| Research command | `commands/fb-research.md` + `skills/fb-research/SKILL.md` |
| Reply command | `commands/fb-reply.md` |
| Vault ingest skill | `skills/vault-ingest/SKILL.md` |
| FB engagement agent | `agents/fb-engagement-agent.md` |
| Post extraction script | `scripts/extract_posts.py` |
| Classification script | `scripts/classify_posts.py` |
| Reply extraction script | `scripts/extract_replies.py` |
| Reply posting script | `scripts/post_reply.py` |

---

## Playwright Conventions

**ALWAYS** use these flags when opening the browser:
```bash
playwright-cli open "URL" --headed --profile "/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent/.browser-profile"
```

- `--headed`: user must see the browser (required)
- `--profile`: persistent session keeps Orbit Advisory logged in

The profile stores the Orbit Advisory page as the active profile. Comment boxes will show "Comment as Orbit Advisory". Do NOT switch to personal profile.

**Reference**: `reference/playwright-facebook-controls.md` — validated controls for post extraction, scrolling, "See more" expansion, commenting.

### Snapshot vs JS eval

- **Snapshots** (`playwright-cli snapshot`): use ONLY for finding clickable element refs (e.g., "See more" button ref). Output is a large YAML file — never read it for content.
- **JS eval** (`playwright-cli eval "() => ...")`): use for ALL content extraction (post text, replies, URLs). Returns clean strings/JSON.

---

## Token Optimization Rules

1. **JS pre-filter** (zero LLM tokens): extract only posts matching Thai question + accounting/tax keywords before any LLM sees the text
2. **Bash dedup** (zero LLM tokens): check `tracking/processed-post-ids.txt` with grep before extraction
3. **Haiku classification**: use Python script calling Anthropic API — runs outside the Opus context window
4. **Vault-first**: always search Orbit Vault before invoking deep-research; skip deep-research if vault has strong coverage
5. **Text-only extraction**: JS eval returns strings, not DOM structures

---

## Orbit Vault Integration

Orbit Vault is the knowledge base at `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/`.

When researching a question:
1. `Grep` the vault first with Thai and English keywords
2. If strong match → read the matched pages, draft from them
3. If weak/no match → invoke deep-research skill
4. After research → update vault via vault-ingest skill

The vault compounds: each question answered makes future answers faster.

---

## Reply Voice Guide

All Facebook replies drafted as Orbit Advisory must be:
- **Thai language** — always (group is Thai)
- **Professional but approachable** — like a friendly expert, not a cold corporate account
- **Specific** — cite the actual law, form name, or rate (e.g., "ตาม ม.65 ทวิ แห่งประมวลรัษฎากร")
- **Practical** — give actionable steps, not just "you should consult an accountant"
- **Not a hard sell** — Orbit Advisory's name will appear naturally from the page; no need to promote services explicitly

---

## Tracking Files

| File | Purpose |
|------|---------|
| `tracking/processed-post-ids.txt` | Newline-separated post IDs that have been scanned/replied to |
| `tracking/scan-results-{date}.json` | Candidates from each scan session |
| `tracking/drafts/{post-id}.md` | Draft replies awaiting approval |
| `tracking/posted/{post-id}.md` | Archive of posted replies |

`processed-post-ids.txt` is gitignored (local state). `scan-results-*.json` and the directory structure are gitignored too.

---

## Session Start Checklist

1. Read this CLAUDE.md
2. Check `SPRINT.md` for current status
3. If working on browser automation — verify session still works:
   `playwright-cli open "https://www.facebook.com/groups/598953943470618" --headed --profile ".../.browser-profile"`

---

## Rules

- Thai-first: all reply drafts in Thai
- Human approves before posting — no auto-submit ever
- Never read snapshot YAML for content — use JS eval
- Always use `--profile` flag with playwright-cli
- Follow flowaccount plugin conventions for all plugin files
- Do not create files outside this directory without explicit instruction
