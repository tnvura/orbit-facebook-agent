---
name: vault-compile
description: This skill should be used when the user asks to "compile vault pages", "synthesize research into the vault", "fill vault stubs", "update the knowledge base from a source", or "run vault-compile". Reads source files from Orbit Vault and writes compiled knowledge into topics/, entities/, connections/, and posts/ pages.
version: 1.0.0
---

# Skill: vault-compile

Synthesize one or more source files into compiled knowledge pages in Orbit Vault. The "ripple" skill — one source typically touches 3–10 pages. Called by `/fb-research` and `/vault-ingest`.

---

## When to Use

| Trigger | Caller |
|---|---|
| FB post captured → stubs needed immediately | `/fb-research` (after `vault-capture` fb-post) |
| Deep-research output ready → fill stubs with verified facts | `/fb-research` (after `vault-capture` research) |
| User drops a clipping in `sources/raw/` → compile into vault | `/vault-ingest` |
| Housekeeping run detects uncompiled sources | `/vault-ingest --pending` |

Do not call this skill directly on `sources/` files that have not yet been captured via `vault-capture`. Compilation always follows capture.

---

## Skills Required

This skill depends on two obsidian skills that must be applied throughout:

| Skill | When to use |
|---|---|
| `obsidian:obsidian-markdown` | **Every page write** — all compiled pages must use valid Obsidian-flavored markdown: YAML frontmatter, `[[wikilinks]]` (not `[text](path)`), callouts (`> [!warning]`), and `aliases` property. Read the skill for full syntax reference. |
| `obsidian:obsidian-cli` | **Backlink sweep (Step 5)** — use `obsidian backlinks file="{name}"` and `obsidian links file="{name}"` to traverse the graph. Requires Obsidian to be open. If Obsidian is closed, fall back to `Grep pattern="\[\[{pagename}\]\]"`. |

---

## Inputs

| Field | Description | Required |
|---|---|---|
| `source_paths` | One or more paths inside `Orbit Vault/sources/` | Yes |
| `focus_topic` | Optional hint to narrow compile scope | No |

---

## Critical Rule — Replies Are Not Truth

When compiling a `sources/fb-posts/` file, the `## Replies` section contains **unverified claims from Facebook commenters**. These must never be compiled into `topics/` or `entities/` pages as facts.

| Source | Treatment |
|---|---|
| Post replies | Record in `posts/` page "Existing Replies Validation" table as **claims only** — mark each as 🔍 Unvalidated |
| `sources/research/` files | The only authorised input for compiling knowledge into `topics/` and `entities/` pages |

Compiling from an `fb-post` source alone produces **stubs only** — structure in place, all Details/Common Mistakes sections marked `*Pending deep-research*`. The stubs are filled when a matching `sources/research/` file is compiled.

---

## Step 1 — Detect source kind

For each source path, determine strategy:

| Kind | Detected by | Strategy |
|---|---|---|
| `fb-post` | Path in `sources/fb-posts/` | Create post page; create topic/entity stubs; record replies as unvalidated claims only |
| `deep-research` | Path in `sources/research/` | Fill topic/entity stubs with verified knowledge; update post page Answer + Draft Reply |
| `legal-text` | Path in `sources/raw/` AND content contains `**มาตรา NN**` or `**ข้อ NN**` markers | Chunked compile (see §Chunked Compile Protocol) |
| `article` | Path in `sources/raw/`, no legal markers | Extract topics/entities; size-chunk if >10k tokens |

Read each source file's frontmatter and first 50 lines to determine kind before proceeding.

---

## Step 2 — Read `index.md`

Read `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/index.md` to understand current vault state. This determines which pages already exist and need updating vs. which need creating.

---

## Step 3 — Identify pages to touch

Based on the source content, list all candidate compiled pages:

- **Entities** mentioned (forms, laws, organisations) → `entities/` pages
- **Topics** covered (concepts, rules, thresholds) → `topics/` pages
- **Cross-cutting insights** linking 2+ existing pages → `connections/` page
- **FB post research record** (kind=`fb-research`) → `posts/` page
- **Wikilinks in source frontmatter** whose target doesn't exist → stub entity pages

---

## Step 4 — Create or update each page

For each candidate page, apply this decision tree:

```
Does a page with matching title or alias exist?
│
├── NO → CREATE from template
│        - Copy from templates/{type}.md
│        - Fill all required sections
│        - Add ≥2 [[wikilinks]] to nearest existing pages
│        - Append row to index.md
│
└── YES → READ existing page in full
           Does the new info ADD, CLARIFY, or CONTRADICT?
           │
           ├── ADDS      → Append to relevant section; add source to frontmatter; bump `updated`
           ├── CLARIFIES → Refine wording; preserve original phrasing alongside new
           └── CONTRADICTS → Apply contradiction protocol (see below)
```

### Contradiction Protocol

When new info conflicts with an existing claim:

1. Wrap the conflicting section with a dated-claims block:

```markdown
> ⚠️ **Dated claim — conflict unresolved.** Review needed.

- **As of {existing date}** ([[sources/...]]): {existing claim}
- **As of {today}** ([[sources/...]]): {new claim}
```

2. Append a `contradiction |` entry to `log.md`
3. Add the conflict to the return value — caller must surface it to the human

---

## Step 5 — Backlink sweep

After all page writes, for each new or updated page:

1. Get the page's outbound links — prefer `obsidian:obsidian-cli`:
   ```bash
   obsidian links file="{page-name}"
   ```
   Fallback if Obsidian is closed: `Grep pattern="\[\[" path="{compiled-page-path}"` to extract wikilinks manually.

2. For each linked target, check whether it already links back — prefer:
   ```bash
   obsidian backlinks file="{target-name}"
   ```
   Fallback: `Grep pattern="\[\[{page-name}\]\]" path="Orbit Vault/"`.

3. If the target page does **not** link back, append a wikilink entry to its Related Topics section.

---

## Step 6 — Update `index.md`

For each new or updated compiled page, update its row in the relevant pipe-table:

| New page | Add row under correct section |
| Updated page | Update Summary and Updated date in existing row |

---

## Step 7 — Append to `log.md`

```
## [{ISO timestamp}] compile | {list of pages touched}
- Source: {source_path(s)}
- Ripple: {n} pages touched ({x} created, {y} updated, {z} cross-refs added)
- By: vault-compile
```

If any contradictions were found, add one entry per conflict:

```
## [{ISO timestamp}] contradiction | {page path}
- Old ({date}): {claim}
- New ({today}): {claim}
- Resolution: both retained, dated; human review pending
```

---

## Step 8 — Return

Return a summary to the caller:

```
COMPILE RESULT
==============
Pages created:  {n} — {list}
Pages updated:  {n} — {list}
Stubs created:  {n} — {list}
Contradictions: {n} — {list with page paths}
```

If contradictions > 0, the caller must present them to the human before drafting any reply that depends on the contested claims.

---

## Chunked Compile Protocol

Triggered automatically when source kind is `legal-text` or source file exceeds ~10k tokens.

### Layer 1 — Pre-pass (skeleton TOC)

Before processing any chunk:
1. Grep source for section markers (`**มาตรา NN**`, `**ข้อ NN**`, `#`/`##` headings)
2. Grep source for bolded defined terms (`**"..."**` pattern)
3. Grep source for cross-references (มาตรา mentions, wikilinks)
4. Write skeleton to `Orbit Vault/logs/compile-working-{ISO}.md`:

```markdown
## Compile in progress: {source path}
Started: {ISO timestamp}

### Skeleton TOC
- §NN: {section title} — defines: {term list}
- §NN: {section title} — cross-refs: §MM, §PP

### Stub entities to create
- [[entities/{name}]] — defined §NN, referenced §MM

### Cross-references pending
- §NN → §MM (not yet processed)

### Ripple count
Created: 0 | Updated: 0
```

### Layer 2 — Per-chunk loop

For each chunk (section-aligned, ~2–4k tokens):
1. Read `logs/compile-working-{ISO}.md`
2. Read chunk via `Read` with `offset`/`limit`
3. Apply Steps 3–5 for this chunk's content
4. Append findings to working memory (new stubs, resolved/pending cross-refs, updated ripple count)

### Layer 3 — Post-pass (coherence sweep)

After all chunks:
1. Read all newly-created pages
2. Verify all `[[wikilinks]]` resolve — fix broken ones
3. Detect thematic groupings → create `connections/` pages
4. Create any deferred stub pages from working memory
5. Finalize `index.md` and `log.md` (single `compile |` entry with total ripple count)
6. Rename working memory to `logs/compile-completed-{ISO}.md`

---

## Invariants

- Never edit any file in `sources/` — any subfolder.
- Never delete content from an existing compiled page — append, refine, or dated-overwrite only.
- Always read `index.md` before writing any compiled page.
- Every new page must have frontmatter + at least one source citation + ≥2 `[[wikilinks]]` (stubs exempt until backfilled).
- Use official Thai script for form names: `ภ.ง.ด.53` not `PND53`.
- **Never compile reply content into `topics/` or `entities/` pages.** Replies are reference only. Truth comes from `sources/research/` files produced by deep-research.
- **All page writes must follow `obsidian:obsidian-markdown` syntax** — YAML frontmatter, `[[wikilinks]]` for internal links, callouts for warnings/notes. Never use `[text](relative/path.md)` for internal vault links.

---

## References

| File | Purpose |
|---|---|
| `Orbit Vault/CLAUDE.md` | Vault schema — directory layout, page types, naming conventions, cross-linking rules, index.md and log.md format |
| `Orbit Vault/templates/topic.md` | Template for `topics/` pages — required frontmatter fields and section layout |
| `Orbit Vault/templates/entity.md` | Template for `entities/` pages — required frontmatter fields and section layout |
| `Orbit Vault/templates/connection.md` | Template for `connections/` pages — required frontmatter fields and section layout |
| `Orbit Vault/templates/post.md` | Template for `posts/` pages — required frontmatter fields and section layout |
| `obsidian:obsidian-markdown` skill | Obsidian-flavored markdown syntax reference — YAML frontmatter, wikilinks, callouts, aliases |
| `obsidian:obsidian-cli` skill | Obsidian CLI commands for backlink traversal (`obsidian links`, `obsidian backlinks`) |
