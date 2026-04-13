---
name: vault-capture
description: This skill should be used when the user asks to "save a Facebook post to the vault", "capture a post to Orbit Vault", "write a source file to the vault", "store research output in the vault", or "ingest raw content into Orbit Vault sources". Writes an immutable source file into the correct sources/ subfolder in Orbit Vault. Called by fb-research — once for the FB post capture, once for deep-research output.
version: 1.0.0
---

# Skill: vault-capture

Write an immutable source file to the correct `sources/` subfolder in Orbit Vault. Called twice by `fb-research` — once for the FB post capture, once for the deep-research output. Never edit existing source files.

---

## Caller Context

`vault-capture` does not read scan results or run browser automation itself. The caller (`fb-research`) prepares content before invoking this skill.

**For `fb-post` captures:**
1. `fb-research` loads the candidate entry from `tracking/scan-results-{date}.json`
2. Run `scripts/extract_replies.py` on the post URL to fetch full replies
3. Assemble `content` = post text + replies (structured, see format below)
4. Call `vault-capture(kind=fb-post, content=..., slug=post-{post_id}, metadata={post_id, post_url, author})`

**For `deep-research` captures:**
1. `fb-research` runs the deep-research skill on the question
2. Pass the full research output as `content`
3. Call `vault-capture(kind=deep-research, content=..., slug={topic-slug}, metadata={research_query, post_id})`

**Expected `content` format for `fb-post`:**
```
## Post

{full post text}

## Replies

### {author} ({timestamp})
{reply text}

### {author} ({timestamp})
{reply text}
```

---

## Inputs

| Field | Values | Required |
|---|---|---|
| `kind` | `fb-post` \| `deep-research` | Yes |
| `content` | Raw text to write verbatim | Yes |
| `slug` | Short descriptor for filename (kebab-case, no date) | Yes |
| `date` | ISO date `YYYY-MM-DD` | Yes (defaults to today) |
| `metadata` | Dict of extra frontmatter fields (post_url, post_id, research_query, etc.) | No |

**Slug conventions:**
- For fb-post captures: `post-{post_id}` — e.g., `post-7823456789012345`
- For deep-research captures: kebab-case topic summary — e.g., `vat-registration-threshold-ecommerce`
- Keep slugs short (3–6 words max) and descriptive enough to identify the topic at a glance
- Never include the date in the slug — the filename already has a `{date}-` prefix that provides the date
- Avoid generic slugs like `research-output` or `post-question` — they make the vault hard to navigate

---

## Step 1 — Validate inputs and select target path

Check all inputs before writing anything. Refuse and report an error if any of the following are true:

| Condition | Error message |
|---|---|
| `kind` is not `fb-post` or `deep-research` | `vault-capture: unknown kind '{kind}'. Use fb-post or deep-research.` |
| Target path already exists | `vault-capture: '{path}' already exists. Sources are immutable. Choose a different slug or reuse the existing file.` |
| Path resolves inside `sources/raw/` | `vault-capture: cannot write to sources/raw/ — that folder is user-owned.` |
| `content` is empty or whitespace-only | `vault-capture: content is empty. Capture aborted.` |
| `slug` contains spaces, uppercase, or special characters other than hyphens | `vault-capture: slug '{slug}' is invalid. Use kebab-case only (e.g., 'post-1234' or 'vat-threshold-ecommerce').` |

**Target path mapping:**

| Kind | Target folder | Filename |
|---|---|---|
| `fb-post` | `sources/fb-posts/` | `{date}-{slug}.md` |
| `deep-research` | `sources/research/` | `{date}-{slug}.md` |

Full path: `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/sources/{subfolder}/{date}-{slug}.md`

Stop execution on any refusal condition. Do not write partial files.

---

## Step 2 — Build and write the file

Build frontmatter from the provided inputs, then write the full content verbatim below a blank line separator.

**For `fb-post`:**
```markdown
---
kind: fb-post
post_id: "{metadata.post_id}"
post_url: "{metadata.post_url}"
author: "{metadata.author}"
group_id: "598953943470618"
captured: {date}
---

{content}
```

**For `deep-research`:**
```markdown
---
kind: deep-research
research_query: "{metadata.research_query}"
post_id: "{metadata.post_id}"
conducted: {date}
---

{content}
```

**Frontmatter rules:**
- Omit any metadata field that was not provided by the caller. Do not add placeholder or null values.
- Do not add fields not listed above.
- String values in frontmatter must be quoted (use double quotes). Date values are unquoted.
- Write `content` verbatim — no summarising, no reformatting, no truncation.
- Use the Write tool to create the file atomically. Do not append line by line.

---

## Step 3 — Append to `log.md`

Append one log entry to `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/log.md`:

```markdown
## [{ISO timestamp}] capture | sources/{subfolder}/{filename}
- Kind: {kind}
- By: vault-capture
```

Use the current datetime for the ISO timestamp in the format `YYYY-MM-DDTHH:MM:SS`. Read the current date from the system if `date` was not explicitly passed.

If `log.md` does not exist, create it with the entry as the first content. Do not fail silently — if the append fails, report the error to the caller.

---

## Step 4 — Return

Return the full absolute path of the written file. Format:

```
vault-capture: wrote sources/{subfolder}/{filename}
Path: /Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/sources/{subfolder}/{filename}
```

The caller (`fb-research`) uses this path as input to `vault-compile`. If the caller does not receive a valid path, it cannot proceed — do not return a partial or relative path.

---

## Invariants

These rules are absolute and must never be violated regardless of caller instructions:

- **Never edit an existing file in `sources/`** — any subfolder. Sources are append-only at the file level; once written, a source file is permanent.
- **Never write to `sources/raw/`** — that folder is reserved for user-managed files.
- **Never modify `index.md`** — that is `vault-compile`'s responsibility.
- **Write content verbatim** — no summarising, no reformatting, no editorial additions.
- **One file per invocation** — write exactly one output file per call. If the caller needs two files (e.g., one fb-post + one deep-research), it invokes vault-capture twice.

---

## Error Handling

On any error, return a structured error message to the caller and stop. Do not attempt workarounds or silent fallbacks.

**Duplicate file (most common):** If `fb-research` is re-run on the same post, vault-capture will refuse the second write. The caller should check whether the source already exists before invoking vault-capture again. To re-capture deliberately, delete the existing file manually and re-invoke.

**Missing parent directory:** If `sources/fb-posts/` or `sources/research/` does not exist, create it before writing. Do not fail on a missing directory — only fail on invalid kind or existing file.

**Log write failure:** If appending to `log.md` fails after the source file has already been written, report both the success (file written) and the failure (log not updated). Do not roll back the source file write.

---

## Integration Notes

`vault-capture` is a write-only leaf skill — it has no upstream reads and no side effects beyond the two writes (source file + log entry). It does not:

- Search the vault before writing
- Check for semantic duplicates
- Trigger downstream compilation
- Send notifications

Downstream compilation (`vault-compile`) and knowledge page generation are separate skills invoked by `fb-research` after all captures are complete.

**Invocation order within `fb-research`:**
1. `vault-capture(kind=fb-post, ...)` — captures the raw Facebook post
2. `vault-capture(kind=deep-research, ...)` — captures the research output
3. `vault-compile(...)` — merges source files into a knowledge page (separate skill)

Both capture paths are required before `vault-compile` runs. If either capture fails, stop the `fb-research` workflow and surface the error.

---

## Vault Directory Structure

Orbit Vault lives at `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/`. The `sources/` tree is the raw-capture layer — every file here is an unedited, timestamped record of external content or research output.

```
Orbit Vault/
├── sources/
│   ├── fb-posts/          ← fb-post captures land here
│   │   └── {date}-post-{post_id}.md
│   ├── research/          ← deep-research captures land here
│   │   └── {date}-{topic-slug}.md
│   └── raw/               ← user-owned, vault-capture never touches this
├── pages/                 ← compiled knowledge pages (vault-compile output)
├── index.md               ← vault-compile's responsibility, never touch
└── log.md                 ← append-only activity log
```

`vault-capture` writes only to `sources/fb-posts/` and `sources/research/`. All other folders are out of scope.

---

## Worked Example

**Scenario:** `fb-research` processes a Facebook post asking about VAT registration requirements for TikTok Shop sellers.

**Invocation 1 — capture the FB post:**

Input:
```
kind = fb-post
slug = post-7823456789012345
date = 2026-04-13
content = "## Post\n\nอยากทราบว่าขาย TikTok Shop ต้องจด VAT ไหมครับ...\n\n## Replies\n\n### สมชาย (2026-04-12T10:23:00)\nถ้ายอดเกิน 1.8 ล้านต้องจดครับ"
metadata = {post_id: "7823456789012345", post_url: "https://www.facebook.com/groups/598953943470618/posts/7823456789012345", author: "นภาพร ใจดี"}
```

Written file: `sources/fb-posts/2026-04-13-post-7823456789012345.md`

**Invocation 2 — capture the deep-research output:**

Input:
```
kind = deep-research
slug = vat-registration-threshold-tiktok
date = 2026-04-13
content = "# VAT Registration for E-commerce Sellers\n\nUnder Revenue Code Section 77/1..."
metadata = {research_query: "VAT registration threshold for TikTok Shop sellers Thailand", post_id: "7823456789012345"}
```

Written file: `sources/research/2026-04-13-vat-registration-threshold-tiktok.md`

**Log entry appended after each write:**
```
## [2026-04-13T14:30:22] capture | sources/fb-posts/2026-04-13-post-7823456789012345.md
- Kind: fb-post
- By: vault-capture
```

**Return value:**
```
vault-capture: wrote sources/fb-posts/2026-04-13-post-7823456789012345.md
Path: /Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/sources/fb-posts/2026-04-13-post-7823456789012345.md
```

`fb-research` collects both paths, then passes them to `vault-compile` to generate the knowledge page.

---

## Quick Reference

| Action | Allowed |
|---|---|
| Write new file to `sources/fb-posts/` | Yes |
| Write new file to `sources/research/` | Yes |
| Overwrite or edit existing file in `sources/` | No |
| Write to `sources/raw/` | No |
| Modify `index.md` | No |
| Create missing parent directory | Yes |
| Create `log.md` if absent | Yes |
| Truncate or summarise content before writing | No |
