# Plan: Vault Skills Implementation (Phase 2 Foundation)

Implementation plan for the four vault skills and `/vault-ingest` command defined in `SPEC.md`. Sliced vertically: each slice delivers working end-to-end functionality and leaves the system in a testable state.

## Decisions Locked

1. Templates stay inside `Orbit Vault/templates/` (kept in-vault).
2. `vault-search` uses Grep first, Obsidian CLI second (fixed sequence).
3. User provides synthetic test data for Slice 4.

## Dependency Graph

```
Slice 1: Schema foundation
    │
    ├──→ Slice 2: vault-capture      ┐
    ├──→ Slice 3: vault-search       │  can run in parallel
    └──→ Slice 4: vault-compile (fb-research strategy)
                  │
                  └──→ Slice 5: vault-compile (article strategy)
                        │
                        └──→ Slice 6: vault-compile (legal-text chunked)
                              │
                              └──→ Slice 7: /vault-ingest command
                                    │
                                    └──→ Slice 8: vault-lint
                                          │
                                          └──→ Slice 9: E2E integration test
```

Slices 2, 3, 4 parallelizable after Slice 1. Slices 5–9 sequential.

---

## Slice 1 — Schema Foundation

**Goal:** Vault structure matches `SPEC.md` before any skill is built.

**Tasks:**
- 1a. Rewrite `Orbit Vault/CLAUDE.md` — new schema (page types, frontmatter, pipe-table index, ISO log, contradiction protocol, source-subfolder rules)
- 1b. Split `Orbit Vault/templates/knowledge-page.md` into four: `topic.md`, `entity.md`, `connection.md`, `post.md`
- 1c. Create `Orbit Vault/sources/fb-posts/` and `Orbit Vault/sources/research/` (each with `.gitkeep`)
- 1d. Create `Orbit Vault/connections/` (with `.gitkeep`)
- 1e. Rewrite `Orbit Vault/index.md` to pipe-table with 4 sections
- 1f. Rewrite `Orbit Vault/log.md` to ISO timestamp format

**Acceptance criteria:**
- [ ] CLAUDE.md reflects all SPEC.md decisions including contradiction and chunked compile protocols
- [ ] Four separate templates each have correct frontmatter + page-type-specific sections
- [ ] All three `sources/` subfolders exist; `connections/` exists
- [ ] Index has 4 empty pipe-tables with correct columns
- [ ] Log has one init entry in ISO format

**Verification:** Open Obsidian. Vault loads without errors. Graph view shows the template files.

---

## Slice 2 — vault-capture skill

**Goal:** Deep-research output or FB post captures land immutably in the correct subfolder.

**Tasks:**
- 2a. Create `skills/vault-capture/SKILL.md` with workflow + refusal rules from SPEC §6.2
- 2b. Document input contract (`kind`, `content`, metadata) explicitly

**Acceptance criteria:**
- [ ] Capturing `fb-post` writes to `sources/fb-posts/{date}-{slug}.md` with frontmatter
- [ ] Capturing `deep-research` writes to `sources/research/{date}-{slug}.md` with frontmatter
- [ ] Attempt to write to `sources/raw/` → refused
- [ ] Duplicate filename → refused
- [ ] `log.md` appended with ISO timestamp and path

**Verification:** Simulate two captures (one of each kind). Inspect files and log. Attempt a refused case.

---

## Slice 3 — vault-search skill

**Goal:** Given a question, return ranked matches from the vault.

**Tasks:**
- 3a. Create `skills/vault-search/SKILL.md` — index-first → Grep → Obsidian CLI backlinks/links layered search
- 3b. Define structured return format (`strong_matches`, `weak_matches`, `no_match`, `wikilinks_to_traverse`)

**Acceptance criteria:**
- [ ] On near-empty vault: returns `no_match: true` for any query
- [ ] Reads `index.md` before any Grep
- [ ] Uses Obsidian CLI `backlinks`/`links` after Grep hits (fixed order)
- [ ] Never writes anything

**Verification:** Run after Slice 4 populates pages. Query known-topic keywords; verify surfacing.

---

## Slice 4 — vault-compile (fb-research strategy)

**Goal:** Synthesize an FB-post + research source pair into compiled pages.

**Tasks:**
- 4a. Create `skills/vault-compile/SKILL.md` — source-kind router, create/update decision tree, contradiction protocol
- 4b. Implement `fb-research` strategy only
- 4c. Implement backlink sweep + index update + log append

**Acceptance criteria:**
- [ ] Given a synthetic FB-post source + research source (user-provided), produces: 1 post page, ≥1 topic or entity page created/updated, index.md updated, log.md has `compile |` entry
- [ ] Every new page has frontmatter + ≥2 wikilinks
- [ ] Contradiction test: source contradicts existing page → writes-both-with-dates, log has `contradiction |` entry

**Verification:** Run compile on user-provided synthetic test pair. Inspect all touched files.

---

## Slice 5 — vault-compile (article strategy)

**Goal:** Handle user-dropped clippings without legal-section markers.

**Tasks:**
- 5a. Extend `vault-compile` with `article` strategy: detect non-legal clipping in `sources/raw/`
- 5b. Implement whole-file read (size-chunked if >10k tokens)
- 5c. Implement stub-entity creation from wikilinked frontmatter authors

**Acceptance criteria:**
- [ ] Compiling a small non-legal clipping creates 3–10 compiled pages
- [ ] `author: [[กรมสรรพากร]]` in clipping frontmatter → creates `entities/กรมสรรพากร.md` stub if missing
- [ ] Clipping frontmatter NOT modified

**Verification:** Short fake clipping (~500 words) in `sources/raw/`; compile; inspect.

---

## Slice 6 — vault-compile (legal-text chunked protocol)

**Goal:** Process `sources/raw/มาตรา 38_64.md` end-to-end via three-layer chunked protocol.

**Tasks:**
- 6a. Extend `vault-compile` — detect `legal-text` (path=`sources/raw/` + `**มาตรา NN**` markers)
- 6b. Pre-pass: skeleton TOC via Grep on section markers + defined terms + cross-refs → `logs/compile-working-{ISO}.md`
- 6c. Per-chunk loop: section-aligned chunks, Read with offset/limit, append to working memory
- 6d. Post-pass: coherence sweep, stub creation, connection pages, archive working memory

**Acceptance criteria:**
- [ ] Skeleton TOC covers all ~27 sections
- [ ] One `entities/มาตรา-NN.md` per section
- [ ] Defined-term entities created (e.g. `entities/เงินได้พึงประเมิน.md`)
- [ ] ≥1 `connections/` page for thematic groupings
- [ ] All cross-references resolve (no broken wikilinks)
- [ ] `log.md` has single `compile |` entry with ripple count
- [ ] Clipping frontmatter unchanged

**Verification:** Full compile of `sources/raw/มาตรา 38_64.md`. Inspect new pages + archived working memory.

---

## Slice 7 — /vault-ingest command

**Goal:** User-friendly trigger for clipping compile.

**Tasks:**
- 7a. Create `commands/vault-ingest.md` with single-path and `--pending` modes

**Acceptance criteria:**
- [ ] `/vault-ingest {path}` invokes vault-compile with that source
- [ ] `/vault-ingest --pending` queries lint for orphan sources and compiles each
- [ ] Contradictions surfaced before command exits

**Verification:** Drop a new clipping; run `/vault-ingest`; verify full cycle.

---

## Slice 8 — vault-lint skill

**Goal:** Seven health checks from SPEC §6.4.

**Tasks:**
- 8a. Create `skills/vault-lint/SKILL.md` implementing all 7 checks
- 8b. Report format: severity-grouped, written to `logs/lint-{ISO}.md`

**Acceptance criteria:**
- [ ] Broken wikilink → ERROR
- [ ] Orphan page, orphan source, stale page → WARNING
- [ ] Contradictions, missing backlinks, sparse pages → SUGGESTION
- [ ] Orphan-source report grouped by subfolder (`raw/`, `fb-posts/`, `research/`)

**Verification:** Inject one defect of each type; run lint; confirm report.

---

## Slice 9 — E2E Integration (simulated /fb-research path)

**Goal:** Prove the four skills compose correctly for the eventual `/fb-research` use.

**Tasks:**
- 9a. Use Phase 1 candidate post #1 (WhiteRabbit8044 — expenses without ใบกำกับภาษี)
- 9b. Manually drive: vault-search → simulated deep-research output → vault-capture ×2 → vault-compile → verify

**Acceptance criteria:**
- [ ] All four skills invoked in sequence
- [ ] Post filed in `posts/`, research synthesized into topics/entities
- [ ] `vault-lint` reports clean after integration

**Verification:** End-to-end run on real candidate. Vault inspected.

---

## Checkpoints

| After | Gate |
|---|---|
| Slice 1 | Schema correct & Obsidian-compatible? → proceed to 2–4 in parallel |
| Slice 4 | fb-research compile produces clean output on synthetic data? → proceed to 5–6 |
| Slice 6 | Chunked protocol preserves whole-document coherence on real มาตรา clipping? → proceed to 7–8 |
| Slice 9 | Phase 2 foundation complete → ready for `/fb-research` skill + `extract_replies.py` |

---

## Risks

| Risk | Mitigation |
|---|---|
| Obsidian CLI requires Obsidian app running | Test early in Slice 3; if blocking, fall back to Grep-only search (documented in skill) |
| Chunked compile on มาตรา 38_64 produces broken cross-references | Post-pass coherence sweep (Slice 6d) catches this; worst case we iterate on the skill |
| Contradiction protocol conflicts with existing page structure | Test with hand-crafted contradiction in Slice 4; adjust template if needed |
| Obsidian indexes working-memory / lint reports as content pages | Place them in `logs/` (outside vault scope) or add naming convention Obsidian can filter |

---

## Estimated Effort

Rough per-slice:
- Slice 1: 1 session (schema rewrite is straightforward)
- Slices 2–3: 1 session each
- Slice 4: 1 session (core compile logic)
- Slice 5: 0.5 session (extension of 4)
- Slice 6: 1.5 sessions (chunked protocol is new ground)
- Slices 7–8: 0.5 session each
- Slice 9: 1 session (integration + any fixes surfaced)

Total: ~7 sessions for full Phase 2 foundation.
