---
name: vault-research
description: This skill should be used when the user asks to "research a topic", "add to the vault", "look up [tax/accounting topic]", "what does the vault know about", "research [Thai tax term]", or any time a tax or accounting question should be researched and stored as knowledge. Also invoked internally by fb-research when vault coverage is insufficient. Researches a question, updates Orbit Vault, and returns compiled findings.
version: 1.0.0
---

# vault-research

Research a Thai tax or accounting topic, compile findings into Orbit Vault, and return a structured result. Called directly by the user or internally by `fb-research`.

---

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | Yes | Thai or English question or topic to research |
| `post_id` | string | No | If provided (by fb-research), passed to vault-compile to create a `posts/` page stub |
| `existing_matches` | list | No | Partial vault matches already found by the caller — passed to vault-deep-research to avoid re-fetching known sources |

---

## Step 1 — Search Orbit Vault

Invoke **vault-search** with the question.

Search using:
- Thai keywords extracted from the question (e.g. `ภ.พ.36`, `VAT`, `ค่าเบี้ยเลี้ยง`)
- English equivalents for cross-listed topics

Returns: `strong` / `weak` / `none`

Read any matched pages fully before proceeding.

---

## Step 2 — Coverage Gate

**If STRONG** (≥1 directly relevant compiled page exists):
- Read the matched `topics/` and `entities/` pages in full
- Skip Steps 3–5
- Set `research_path = vault_only`
- Proceed to Step 6 (return)

**If WEAK or NONE:**
- Proceed to Step 3

---

## Step 3 — Run vault-deep-research

Invoke the **vault-deep-research** skill on the question.

Pass:
- The verbatim question text
- `post_id` if provided (for stub mapping in the research output)
- `existing_matches` if provided (to skip re-fetching known sources)

vault-deep-research writes its output to `Orbit Vault/sources/research/{date}-{slug}.md`.

Note from the result:
- `source_path` — path to the written research file
- `confidence` — HIGH / MEDIUM / LOW
- `stubs_filled` — list of topics/entities/posts pages to create or update
- `c4_gaps` — any unresolved claims with no authoritative source

---

## Step 4 — Capture Research Output

Invoke **vault-capture** with:
- `kind = deep-research`
- `content` = full vault-deep-research output
- `slug` = topic slug from vault-deep-research
- `date` = today
- `metadata.post_id` = post_id (if provided)

vault-capture writes to `Orbit Vault/sources/research/{date}-{slug}.md` and appends to `log.md`.

If vault-capture reports the file already exists (re-run scenario), skip and use the existing path.

---

## Step 5 — Compile Vault Pages

Invoke **vault-compile** with:
- `source_paths` = [captured research file path]
- Include `post_id` context if provided (vault-compile uses it to create/update the `posts/` stub)

vault-compile creates or updates:
- `topics/` pages for broad subjects covered
- `entities/` pages for specific forms, laws, organisations
- `posts/` stub (only if `post_id` was provided)

Collect the compile result: pages created, pages updated, any contradictions.

Set `research_path = deep_research`.

---

## Step 6 — Return

Return a structured result to the caller:

```
VAULT-RESEARCH RESULT
=====================
Research path:   vault_only | deep_research
Coverage:        strong | weak | none (pre-research state)
Confidence:      HIGH | MEDIUM | LOW
Pages created:   [list]
Pages updated:   [list]
C4 gaps:         [list of unresolved claims, or "none"]
Source file:     [path to research file, or "vault only — no new source"]
Vault pages:     [list of all relevant compiled pages for caller to read]
```

When called by **fb-research**: return this object so fb-research can read the vault pages and draft the Thai reply.

When called **directly by user**: also print the result summary and list page titles with one-line descriptions so the user knows what was added to the vault.

---

## Error Handling

| Situation | Action |
|-----------|--------|
| vault-deep-research returns LOW confidence | Set confidence = LOW; include C4 gaps in result; do not suppress — let the caller decide whether to proceed |
| vault-capture reports duplicate file | Use the existing file path; do not re-write |
| vault-compile fails on one page | Report the failed page; return partial result with remaining pages |
| vault-search errors | Treat as `none` coverage; proceed to deep-research; log the error |

---

## Skills Invoked

| Skill | Step | When |
|-------|------|------|
| vault-search | 1 | Always |
| vault-deep-research | 3 | If coverage is weak or none |
| vault-capture | 4 | If deep-research ran |
| vault-compile | 5 | If deep-research ran |
