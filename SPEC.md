# SPEC: Vault Skills (Phase 2 Foundation)

Spec for the four vault-interacting skills used by `/fb-research` and related workflows. Based on Karpathy's LLM Wiki pattern and Coleam's claude-memory-compiler adaptation, instantiated for Orbit Advisory's Thai tax/accounting domain.

## 1. Objective

Build a compounding Thai tax/accounting knowledge base in `Orbit Vault/` that:
- Grows with each Facebook question researched (source-driven ingest)
- Is queryable by Claude via a routing index, without RAG or embeddings
- Self-maintains via explicit lint operations (no silent drift)
- Preserves regulatory history (dated contradictions, never silent overwrites)

**Users:**
- Primary: `/fb-research` (programmatic caller)
- Secondary: Orbit Advisory (human reader via Obsidian)

**Non-goals:**
- Real-time sync, multi-user write, vector search, automatic scheduling.
- Replacing the reference docs in `Orbit Advisory/.claude/rules/` — those are authored, not compiled.

---

## 2. Architecture — Three Layers

```
Orbit Vault/
├── CLAUDE.md             ← schema (co-evolves; authored by human + Claude)
├── index.md              ← routing table (compiled; pipe-format)
├── log.md                ← append-only operation log (compiled)
├── templates/
│   └── knowledge-page.md ← page template with YAML frontmatter
├── sources/              ← IMMUTABLE raw material (three buckets by provenance)
│   ├── raw/              ←   user-dropped clippings (Obsidian Web Clipper output, manual saves)
│   ├── fb-posts/         ←   captured FB post + replies (written by vault-capture)
│   └── research/         ←   deep-research outputs (written by vault-capture)
├── topics/               ← compiled atomic knowledge — broad subjects (VAT, WHT)
├── entities/             ← compiled atomic knowledge — specific forms/orgs (ภ.ง.ด.53)
├── connections/          ← compiled cross-cutting synthesis (2+ topics/entities)
└── posts/                ← compiled Facebook-post records (filed Q&A)
```

**Layer rules:**
- `sources/` (all three subfolders) is **write-once**. Any skill that edits a file here must refuse.
- `sources/raw/` files are user-provided (typically via Obsidian Web Clipper). Skills read them but never edit them, never write new files into this folder.
- `sources/fb-posts/` and `sources/research/` are written by `vault-capture` during `/fb-research`.
- `topics/`, `entities/`, `connections/`, `posts/` are LLM-owned and freely editable.
- `CLAUDE.md` is the schema; changes require explicit human approval.
- `index.md` and `log.md` are compiled artifacts — regenerated/appended by skills, never hand-edited except for emergencies.

---

## 3. Page Schema

### User-dropped clipping frontmatter (in `sources/raw/`)

User-dropped clippings — typically from Obsidian Web Clipper — carry their own native frontmatter (`title`, `source`, `author`, `published`, `created`, `description`, `tags: [clippings]`). **Skills never rewrite or modify this frontmatter.** Compile reads it, preserves any `[[wikilinks]]` it contains (creating stub entity pages if the targets don't yet exist), and uses `source` as the canonical citation URL on compiled pages derived from the clipping.

### Standard YAML frontmatter (all compiled pages)

```yaml
---
title: "Page Title"
aliases: [alternate-name, thai-alias]
tags: [domain, topic]
sources:
  - "sources/2026-04-13-post-27137219875883997.md"
  - "sources/2026-04-13-deep-research-expense-without-invoice.md"
created: 2026-04-13
updated: 2026-04-13
---
```

### Section structure by page type

**`topics/`** (broad subjects):
1. Summary (2–4 sentences, Thai+English if mixed)
2. Key Points (bullets, each self-contained)
3. Details (encyclopedia prose)
4. Common Mistakes (Facebook-question-pattern-driven — highest value section)
5. Related Topics (wikilinks)
6. Sources (wikilinks to `sources/`)

**`entities/`** (forms, laws, orgs):
1. Summary
2. Key Facts (rate, deadline, form code, authority — tabular where possible)
3. When It Applies
4. Filing / Compliance Steps
5. Common Mistakes
6. Related Topics
7. Sources

**`connections/`** (synthesis):
```yaml
connects:
  - "topics/foreign-service-vat"
  - "entities/ภ.พ.36"
```
1. The Connection (what links these)
2. Key Insight (non-obvious relationship)
3. Evidence (specific examples / regulatory citations)
4. Related Concepts
5. Sources

**`posts/`** (filed Q&A from `/fb-research`):
```yaml
post_id: "27137219875883997"
post_url: "https://www.facebook.com/groups/598953943470618/posts/27137219875883997/"
author: "WhiteRabbit8044"
consulted:
  - "topics/deductible-expenses"
  - "entities/ใบกำกับภาษี"
outcome: "reply-drafted"  # or "no-reply-needed", "insufficient-knowledge"
filed: 2026-04-13
```
1. Question (verbatim Thai)
2. Answer (synthesized, with wikilinks)
3. Existing Replies Validation (correct/partial/wrong per other commenter)
4. Draft Reply (final Thai reply text)
5. Sources Consulted
6. Follow-Up Questions

### Filename rules
- `topics/`: kebab-case English, e.g. `foreign-service-vat.md`
- `entities/`: official Thai with dots, e.g. `ภ.พ.36.md`, `ภ.ง.ด.53.md`
- `connections/`: kebab-case description, e.g. `platform-wht-and-seller-accounting.md`
- `posts/`: `{YYYY-MM-DD}-{post-id}.md`
- `sources/`: `{YYYY-MM-DD}-{slug}.md`

---

## 4. `index.md` Format (Routing Table)

Pipe-table, grouped by folder. One-line summary must be specific enough for Claude to decide whether to open the page.

```markdown
# Orbit Vault Index

## Topics

| Article | Summary | Compiled From | Updated |
|---|---|---|---|
| [[topics/foreign-service-vat]] | VAT on payments to foreign service providers (Google/Meta) — self-assessed 7%, filed via ภ.พ.36 | sources/2026-04-13-... | 2026-04-13 |

## Entities

| Article | Summary | Compiled From | Updated |
|---|---|---|---|
| [[entities/ภ.พ.36]] | Monthly form for VAT on foreign service payments; due by 7th of following month | sources/2026-04-13-... | 2026-04-13 |

## Connections

| Article | Summary | Connects | Updated |
|---|---|---|---|
| [[connections/platform-wht-and-seller-accounting]] | Why sellers record platform fees net of WHT — platform self-withholds | topics/e-commerce-platforms, entities/ภ.ง.ด.53 | 2026-04-13 |

## Posts

| Article | Question Snippet | Outcome | Filed |
|---|---|---|---|
| [[posts/2026-04-13-27137219875883997]] | Can expenses without ใบกำกับภาษี be deducted? | reply-drafted | 2026-04-13 |
```

---

## 5. `log.md` Format

Grep-parseable, one entry per operation, ISO timestamp:

```markdown
## [2026-04-13T14:32:05] capture | sources/2026-04-13-post-27137219875883997.md
- Kind: fb-post
- By: vault-capture

## [2026-04-13T14:35:10] compile | topics/deductible-expenses.md (updated), entities/ใบกำกับภาษี.md (created)
- Source: sources/2026-04-13-deep-research-expense-without-invoice.md
- Ripple: touched 4 pages (2 updated, 1 created, 1 cross-ref added)
- By: vault-compile

## [2026-04-13T14:40:00] lint | 3 issues found
- Errors: 0, Warnings: 2, Suggestions: 1
- Report: logs/lint-2026-04-13T14-40.md
- By: vault-lint

## [2026-04-13T14:42:15] contradiction | entities/ภ.ง.ด.53.md
- Old claim (2026-01-10): Rate 5%
- New claim (2026-04-13): Rate 3%
- Resolution: both retained, dated; human review pending
- By: vault-compile
```

Retrieval: `grep "^## \[" log.md | tail -20`

---

## 6. The Four Skills

All four are standalone skills under `skills/`. Each has its own `SKILL.md`.

### 6.1 `vault-search` (read-only)

**Purpose:** Find relevant existing knowledge for a question. Called by `/fb-research` Step A before any deep research.

**Inputs:** Topic / question text (Thai or English), optional folder hint.

**Workflow:**
1. Read `index.md` (the routing table) first.
2. Select 3–10 candidate pages based on the question — rows whose summaries match.
3. `Grep` the vault for Thai terms and form codes from the question (e.g. `ภ.พ.36`, `ใบกำกับ`, `VAT`), layered on top of index-driven selection.
4. For each page hit, run Obsidian CLI `backlinks` and `links` to discover graph-adjacent pages.
5. Read each candidate page in full.
6. Return structured result: `{ strong_matches: [], weak_matches: [], no_match: bool, wikilinks_to_traverse: [] }`.

**Stop conditions:** Stops at 10 pages read. Never edits anything.

**Decision rule for caller:**
- `strong_matches` non-empty → `/fb-research` drafts from vault, skips deep-research.
- `weak_matches` only → `/fb-research` invokes deep-research, supplements vault.
- `no_match` → `/fb-research` must invoke deep-research.

### 6.2 `vault-capture` (write to `sources/fb-posts/` and `sources/research/` only)

**Purpose:** Immutably record system-generated raw material — deep-research output and Facebook post + replies. **Does not write to `sources/raw/`** (that folder is user-owned; clippings land there directly via Obsidian Web Clipper or manual save).

**Inputs:** Source kind (`fb-post` | `deep-research`), raw content, metadata (post URL, date, research query, etc.).

**Workflow:**
1. Select target subfolder by kind:
   - `fb-post` → `sources/fb-posts/`
   - `deep-research` → `sources/research/`
2. Generate slug and filename: `sources/{subfolder}/{YYYY-MM-DD}-{slug}.md`.
3. If file exists → ERROR. Sources are immutable. Caller must choose a new slug or reuse existing.
4. Write frontmatter + raw content verbatim.
5. Append to `log.md`: `## [ISO] capture | sources/{subfolder}/{path}`.
6. Return path.

**Explicit refusals:**
- Cannot edit existing files in `sources/` (any subfolder).
- Cannot write to `sources/raw/` — user-dropped clippings only.

### 6.3 `vault-compile` (write to `topics/`, `entities/`, `connections/`, `posts/`)

**Purpose:** Synthesize raw sources into compiled knowledge. The "10–15 page ripple" skill.

**Inputs:** Path(s) to one or more `sources/` files; optional focus topic.

**Source-kind router.** Compile detects the source kind from the file's path and frontmatter, then picks a strategy:

| Kind | Detected by | Strategy |
|---|---|---|
| `fb-research` | path is `sources/fb-posts/` or `sources/research/` | Synthesize answer-shaped knowledge — update topic pages, add common-mistakes entries, file a `posts/` page for the filed Q&A |
| `legal-text` | path is `sources/raw/` **and** content contains `**มาตรา NN**` or `**ข้อ NN**` markers | Section-aligned chunking (see §6.3.1). One entity per section. Create stubs for defined terms. |
| `article` | path is `sources/raw/` and no legal-section markers | Read whole clipping (chunk by size if >10k tokens), extract topics and entities, update/create pages, cite `source` URL from clipping frontmatter |

**Workflow:**
1. Determine source kind and select strategy.
2. Read the source file(s). If the source is a user-dropped clipping in `sources/raw/`, also read its native frontmatter for citation metadata and any `[[wikilinks]]` to auto-stub.
3. Read `index.md` to understand current state.
4. Identify candidate compiled pages to touch:
   - Entities mentioned (forms, laws, orgs) → `entities/` pages
   - Topics mentioned (concepts, rules) → `topics/` pages
   - Cross-cutting insights linking 2+ existing pages → new `connections/` page
   - If source is a FB post research record → file a `posts/` page
   - Any `[[wikilink]]` in source frontmatter whose target doesn't exist → create stub entity page (title + authority + source citation; flesh out later)
5. For each candidate page, decide create vs. update using this tree:

```
Does a page with matching title/alias exist?
├── NO  → CREATE new page from template
│         Add ≥2 [[wikilinks]] to nearest existing pages (found via index + grep + backlinks)
│         Append to index.md under correct section
└── YES → READ existing page
          Does the new info add/clarify/correct existing claims?
          ├── ADDS     → UPDATE: append to relevant section, add source, bump `updated`
          ├── CLARIFIES → UPDATE: refine wording, preserve original + new phrasing
          └── CONTRADICTS → WRITE-BOTH-WITH-DATES (see Contradiction Protocol)
```

6. After all page writes, sweep backlinks: for each new/updated page, ensure referenced pages link back (add to their Related Topics section if missing).
7. Update `index.md` rows for all touched pages (summary + Updated date).
8. Append to `log.md`: one `compile |` entry summarizing ripple count.
9. If contradictions were written, append one `contradiction |` entry per occurrence and return them to the caller for human review.

**Scope discipline:**
- A single compile call should touch 3–10 pages typically, up to ~15 for normal sources. Legal clippings (e.g. Revenue Code section ranges) may exceed this by design — one entity per section is correct, even at 25+ pages.
- Never delete content. Append, refine, or dated-overwrite only.

#### 6.3.1 Chunked Compile Protocol (large or section-structured sources)

Triggered when a source exceeds ~10k tokens OR when the source-kind router selects `legal-text`. Three-layer scaffold preserves whole-document understanding while processing atomic units:

**Layer 1 — Pre-pass: skeleton TOC**

Before any chunk is compiled, compile does one low-cost scan over the entire source:
1. `Grep` for section markers (`**มาตรา NN**`, `**ข้อ NN**`, `# `/`## ` headings).
2. `Grep` for bolded defined terms (`**"..."**` patterns).
3. `Grep` for wikilinks and cross-references.
4. Build a skeleton TOC (~1–2k tokens) listing every section header, every defined term with the section where defined, and every cross-reference.
5. Write skeleton to `logs/compile-working-{ISO}.md`.

**Layer 2 — Per-chunk compile loop**

For each chunk (section-aligned where possible, size-aligned otherwise, target ~2–4k tokens per chunk):
1. Read `logs/compile-working-{ISO}.md` (skeleton + running state) at chunk start.
2. Read the chunk's text via `Read` with `offset`/`limit`.
3. Process per the selected strategy (create/update entities, link cross-references).
4. Append findings to working memory:
   - New stubs to create (deferred)
   - Cross-references pending (target not yet processed)
   - Ripple count so far
5. Move to next chunk.

Working-memory file format:
```markdown
## Compile in progress: sources/raw/มาตรา 38_64.md
Started: 2026-04-13T15:00:00

### Skeleton TOC
- §38: ประเภทภาษีเงินได้
- §39: นิยาม (defines: เงินได้พึงประเมิน, ปีภาษี, บริษัทหรือห้างหุ้นส่วนนิติบุคคล, ขาย)
- §40: ประเภทของเงินได้พึงประเมิน (cross-ref: §47 ทวิ)
- ...

### Stub entities to create
- [[entities/เงินได้พึงประเมิน]] — defined §39, referenced §40, §41
- [[entities/บริษัทหรือห้างหุ้นส่วนนิติบุคคล]] — defined §39

### Cross-references pending
- §40 → §47 ทวิ (not yet processed)
- §42 → §39 (resolved)

### Ripple count
Created: 3 | Updated: 1
```

**Layer 3 — Post-pass: coherence sweep**

After all chunks are compiled:
1. Read all newly-created compiled pages in sequence.
2. Verify cross-references resolve (no broken `[[wikilinks]]`).
3. Detect thematic groupings → create `connections/` pages where warranted (e.g. `connections/assessable-income-types.md` linking §40(1)–(8)).
4. Create any deferred stub pages from working memory.
5. Finalize `index.md` rows for every touched page.
6. Append one `compile |` summary entry to `log.md` with total ripple count.
7. Archive working-memory file to `logs/compile-completed-{ISO}.md` (don't delete — useful audit trail).

**Quality note.** Chunking preserves understanding through the three-layer scaffold. Token cost is comparable to one-pass compile (sometimes slightly higher due to skeleton reads per chunk) but per-page extraction quality is significantly better, especially for dense legal text where precision matters.

**Contradiction Protocol (write-both-with-dates):**

When new info conflicts with existing content on a page:

```markdown
## Key Facts

> ⚠️ **Dated claim — conflict unresolved.** Review needed.

- **As of 2026-01-10** ([[sources/2026-01-10-old-source]]): Rate is 5%
- **As of 2026-04-13** ([[sources/2026-04-13-new-source]]): Rate is 3%
```

- Both claims retained with dates and source wikilinks
- A visible warning marker is added to the page
- `log.md` gets a `contradiction |` entry
- `vault-compile` returns a list of unresolved contradictions to its caller
- `/fb-research` must surface these to the human before drafting a reply that relies on the contested claim

### 6.4 `vault-lint` (read-only, writes report to `logs/`)

**Purpose:** Detect drift before it compounds. Runs on demand.

**Seven checks (all adopted):**

1. **Broken wikilinks** — `[[path]]` targets that don't exist → ERROR
2. **Orphan pages** — compiled pages with zero inbound links → WARNING
3. **Orphan sources** — files in any `sources/` subfolder (`raw/`, `fb-posts/`, `research/`) never referenced by a compiled page → WARNING. Report groups orphans by subfolder; user-dropped clippings in `sources/raw/` are the most common source and lint offers to compile them.
4. **Stale compiled pages** — source in frontmatter has `mtime` newer than the compiled page's `updated` date → WARNING
5. **Contradictions** — pages containing the "Dated claim — conflict unresolved" marker → SUGGESTION (human review)
6. **Missing backlinks** — A links to B but B doesn't link back → SUGGESTION
7. **Sparse articles** — compiled pages below 200 words → SUGGESTION

**Output:** Markdown report at `logs/lint-{ISO-timestamp}.md` with severity-grouped sections.

**Side effects:** None beyond writing the report and appending to `log.md`.

### 6.5 `/vault-ingest` command (user-initiated clipping compile)

**Purpose:** Trigger `vault-compile` on a user-dropped clipping (or any source) explicitly. Complements the automatic call by `/fb-research` and the orphan-source detection by `vault-lint`.

**Invocation:**
```
/vault-ingest {path}          # compile one clipping
/vault-ingest --pending       # compile all orphan sources detected by lint
```

**Workflow:**
1. Resolve path — default base is `Orbit Vault/sources/raw/`.
2. Verify file exists and is in a `sources/` subfolder (refuse if not).
3. Call `vault-compile` with the path.
4. Surface the compile summary: pages created, pages updated, contradictions flagged, stubs created for deferred backfill.
5. If contradictions were flagged, present them for human review before the command returns.

**Why this exists:** User-dropped clippings (Obsidian Web Clipper output) bypass `vault-capture`. They need an explicit trigger to enter the compiled layer. Lint catches forgotten clippings as a safety net; this command is the intended path.

---

## 7. Testing Strategy

No unit-test framework. Verification is behavioral:

**vault-search:**
- Query with Thai term that matches one topic page → returns that page as strong match
- Query with unrelated term → returns no_match=true
- Query that hits a page via backlinks only (not grep) → still surfaced

**vault-capture:**
- Write new source to `fb-posts/` or `research/` → file created, `log.md` appended
- Write source with existing filename → refused with clear error
- Attempt to write to `sources/raw/` → refused
- Source filename matches `sources/{subfolder}/{YYYY-MM-DD}-{slug}.md` pattern

**vault-compile:**
- Compile single source on empty vault → creates topic + entity + post pages, all with frontmatter, index.md updated
- Compile source that restates known info → updates existing page, no duplicates
- Compile source that contradicts existing claim → writes-both-with-dates, warning marker present, `log.md` contradiction entry present
- Ripple count in `log.md` matches actual files changed
- Compile clipping with `[[wikilinked]]` author in frontmatter and no matching entity page → stub entity page created
- Compile legal-text clipping (>10k tokens, contains `**มาตรา**` markers) → chunked protocol runs: skeleton TOC in `logs/compile-working-*.md`, one entity per section, deferred stubs resolved in post-pass, final summary in `log.md`

**/vault-ingest command:**
- Run on a fresh user-dropped clipping → vault-compile invoked, summary shown
- Run with `--pending` on a vault with 3 orphan sources → all three compiled in sequence

**vault-lint:**
- Introduce broken wikilink manually → lint reports it as ERROR
- Leave source uncompiled → reported as orphan source WARNING
- Run lint on clean vault → report shows 0/0/0

**Integration (once `/fb-research` exists):**
- End-to-end: run `/fb-research` on post #1 → vault-search → vault-capture (source) → deep-research → vault-capture (research output) → vault-compile → draft reply filed to `posts/`. Inspect vault: all four folders have new/updated content, index.md reflects all.

---

## 8. Boundaries

### Always do
- Write frontmatter on every compiled page
- Use `[[wikilinks]]` with full relative path from vault root, no `.md` extension
- Use official Thai script for form names (ภ.ง.ด.53 not PND53) per project rules
- Update `index.md` and `log.md` on every write operation
- Preserve existing content — append, refine, or dated-overwrite
- Return contradictions to the caller so they surface to human

### Ask first
- Schema changes to `CLAUDE.md`
- Deleting or renaming any existing compiled page
- Resolving a contradiction (picking which dated claim is current)
- Adding a new top-level folder beyond the 5 compiled buckets + `sources/`
- Merging two existing pages that turn out to cover the same subject

### Never do
- Edit anything in `sources/` after creation (all three subfolders)
- Rewrite native frontmatter on user-dropped clippings in `sources/raw/`
- Write new files into `sources/raw/` from any skill (that folder is user-owned)
- Silently overwrite a conflicting claim
- Create a compiled page without at least one source citation
- Create a page without at least 2 `[[wikilinks]]` to nearby existing pages (at index time; stub pages are exempt until backfilled)
- Use `Grep` or search without first reading `index.md`
- Invoke deep-research from inside a vault skill (that's `/fb-research`'s job)

---

## 9. Open Questions (None Blocking — Revisit After First Live Use)

1. When the vault grows past ~100 compiled pages, revisit whether `index.md` should be split by folder into per-section indexes.
2. Whether to add Dataview queries to `index.md` (requires Obsidian Dataview plugin); for now a static table suffices.
3. Whether `connections/` pages warrant their own subfolders (e.g. `connections/tax/`, `connections/accounting/`) once the bucket grows.

---

## 10. Implementation Order

Proposed build sequence for Phase 2 Task 2.1 (these four skills before extract_replies.py / fb-research):

1. Update `Orbit Vault/CLAUDE.md` with this spec's schema (frontmatter, index format, log format, contradiction protocol, source-subfolder conventions)
2. Update `Orbit Vault/templates/knowledge-page.md` with frontmatter + sections per page type (or split into 4 templates: topic, entity, connection, post)
3. Create `sources/fb-posts/` and `sources/research/` subfolders (keep existing `sources/raw/` with the มาตรา 38_64 clipping as the first real test subject)
4. Create `connections/` folder
5. Convert existing `index.md` and `log.md` to the new pipe-table / ISO-timestamp formats (empty bodies fine)
6. `skills/vault-capture/SKILL.md` (simplest — no synthesis, two subfolder targets)
7. `skills/vault-search/SKILL.md` (read-only, no writes)
8. `skills/vault-compile/SKILL.md` (most complex — source-kind router, contradiction protocol, chunked compile protocol §6.3.1)
9. `commands/vault-ingest.md` — user-initiated compile trigger
10. `skills/vault-lint/SKILL.md` (last — needs the vault populated to be meaningful)
11. Behavioral verification:
    - Compile `sources/raw/มาตรา 38_64.md` end-to-end via chunked protocol → inspect `entities/` for one page per section, `connections/` for thematic groupings, `log.md` for ripple summary
    - Run `/fb-research` on a real Phase 1 candidate (e.g. post #1 WhiteRabbit8044) → verify full flow: search → capture → deep-research → capture → compile → draft filed to `posts/`
