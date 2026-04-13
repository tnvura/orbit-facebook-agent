# Sprint Status

## Current Sprint: Phase 2 — Research Pipeline (`/fb-research`)

**Started**: 2026-04-13
**Goal**: Given a candidate post from `/fb-scan`, research the correct answer, validate existing replies, update Orbit Vault, and draft a Thai reply as Orbit Advisory.

---

## Phase 1 Complete ✅ — Scan Pipeline

**Completed**: 2026-04-13

- [x] Task 1.1 — `scripts/extract_posts.py` — CDP-based extractor with incremental JS filter
- [x] Task 1.2 — `/fb-scan` command + `skills/fb-scan/SKILL.md`

### Phase 1 Checkpoint
- [x] `/fb-scan` skill registered and invocable via Claude Code plugin
- [x] Feed sorted to "New posts" before scrolling
- [x] Profile detection works (warns only on confirmed wrong profile)
- [x] `filter_mode=loose` — exclude_terms only; Claude classifies in Step 3
- [x] Author exclusion: Boonruk Ngamkiatikul, "New posts" feed label
- [x] Cross-group URL filter, text dedup, article share detection
- [x] 50 scrolls covers ~1–2 days of group activity
- [x] Live test: 32 raw results → 7 genuine candidates correctly identified
- [x] Plugin pushed to GitHub (v0.1.2), auto-update confirmed working

### Key Design Decisions (Phase 1)
- **loose mode default**: JS filter only rejects known noise; Claude does real classification — better recall, fewer missed questions
- **Incremental scroll + accumulation**: Facebook unloads DOM on scroll; must capture at each step
- **CDP over playwright-cli**: System Chrome via CDP bypasses Facebook bot detection; playwright-cli subprocess has no shared state

---

## Phase 2 Tasks

- [ ] Task 2.1 — `skills/vault-ingest/SKILL.md` — search and update Orbit Vault
- [ ] Task 2.2 — `scripts/extract_replies.py` — extract existing comments from a post
- [ ] Task 2.3 — `skills/fb-research/SKILL.md` + `commands/fb-research.md`

---

## Upcoming Phases

- **Phase 3**: Posting pipeline (`/fb-reply` command)
- **Phase 4**: Agent definition + vault seeding + E2E test
