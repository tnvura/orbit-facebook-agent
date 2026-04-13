# TODO — Orbit Facebook Agent

Task list covering all phases. Corresponds to `tasks/plan.md` and SPRINT.md.

Last updated: 2026-04-13

---

## Phase 0 — Infrastructure ✅

- [x] 0.1 Initialize Orbit Vault structure (CLAUDE.md schema, templates, index.md, log.md, sources/)
- [x] 0.2 Plugin scaffold — `.claude-plugin/plugin.json`, tracking directories, skills/ structure
- [x] 0.3 CLAUDE.md written (business context, Playwright conventions, token optimization rules, vault integration, reply voice guide)
- [x] 0.4 SPRINT.md and CHANGELOG.md created
- [x] 0.5 Git repo initialized, pushed to GitHub (`tnvura/orbit-facebook-agent`)
- [x] 0.6 Plugin registered and discoverable via Claude Code (`--plugin-dir`)
- [x] 0.7 Browser session verified: Orbit Advisory page logged in via CDP, persistent profile

---

## Phase 1 — Scan Pipeline ✅

- [x] 1.1 `scripts/extract_posts.js` — CDP-based incremental extractor with JS keyword filter
- [x] 1.2 `scripts/extract_posts.py` — Python wrapper: launches extract_posts.js, dedup against processed-post-ids.txt, writes scan-results JSON
- [x] 1.3 `skills/fb-scan/SKILL.md` — full scan workflow (extract → classify → save → present candidates)
- [x] Live test: 32 raw posts → 7 genuine candidates (loose filter mode confirmed correct)

### Phase 1 Checkpoint ✅
- [x] `/fb-scan` skill invocable from Claude Code
- [x] CDP connects to system Chrome (no bot detection issues)
- [x] "New posts" feed sort active before scrolling
- [x] Dedup against `tracking/processed-post-ids.txt` working
- [x] Plugin auto-update from GitHub confirmed (version bump triggers cache refresh)

---

## Phase 2 — Research Pipeline ✅

- [x] 2.1 `scripts/extract_replies.py` — CDP-based reply extractor (expands "View more comments", outputs JSON)
- [x] 2.2 `skills/vault-deep-research/SKILL.md` — full research skill with:
  - 3-axis parallel search (Tax / Accounting / Practitioner)
  - 6-tier source authority + C1–C4 claim classification
  - Confidence rubric (HIGH/MEDIUM/LOW)
  - PDF cache dedup protocol
  - 3 mandatory red-team challenges
  - `references/output-template.md` and `references/term-glossary.md`
- [x] 2.3 `skills/vault-capture/SKILL.md` — writes fb-posts and deep-research to sources/ (immutable)
- [x] 2.4 `skills/vault-search/SKILL.md` — Grep-first vault search, returns strong/weak/none coverage signal
- [x] 2.5 `skills/vault-compile/SKILL.md` — compiles sources into topics/, entities/, posts/; updates index.md and log.md
- [x] 2.6 `skills/fb-research/SKILL.md` — FB-specific workflow, delegates knowledge work to vault-research (v1.1.0)
- [x] 2.7 `skills/vault-research/SKILL.md` — canonical research orchestrator (vault-search → deep-research → capture → compile); invocable directly by user or by fb-research
- [x] `reference/pdf-parser.md` — opendataloader-pdf usage guide (dedup, parse, targeted read)
- [x] Live tests: candidate #3 (ค่าเบี้ยเลี้ยง vs สวัสดิการ) — HIGH confidence; candidate #2 (บอจ.5 installment) — MEDIUM confidence
- [x] Vault: 3 topics, 5 entities, 2 research sources, 2 post records compiled

### Phase 2 Checkpoint ✅
- [x] `/fb-research {n}` invocable from Claude Code
- [x] Vault-first logic works (search before deep-research)
- [x] Draft saved to `tracking/drafts/{post_id}.md` after each run
- [x] Community replies validated in each run
- [x] index.md and log.md updated on every compile

---

## Phase 3 — Posting Pipeline ❌ (next)

- [ ] 3.1 `scripts/post_reply.py` — fills comment box via CDP; does NOT auto-submit; returns submit button ref
- [ ] 3.2 `skills/fb-reply/SKILL.md` — list drafts → show draft → confirm → fill comment → user confirms → submit → archive
- [ ] Live test: post `tracking/drafts/27136581685947816.md` as Orbit Advisory

### Phase 3 Checkpoint
- [ ] Reply appears on Facebook as Orbit Advisory page
- [ ] Post ID appended to `tracking/processed-post-ids.txt`
- [ ] Draft moved to `tracking/posted/{post_id}.md`
- [ ] Two confirmation gates work (draft review + post confirmation)

---

## Phase 4 — Polish & Seed ❌

- [ ] 4.1 `agents/fb-engagement-agent.md` — orchestration agent with `<example>` blocks for full scan→research→reply loop
- [ ] 4.2 Seed vault: 5–10 foundation pages on high-frequency topics (ภ.พ.36, WHT rates/forms, VAT threshold, ใบกำกับภาษี requirements, นิติบุคคล registration)
- [ ] 4.3 Update SPRINT.md + CHANGELOG.md to reflect Phase 3/4 completion
- [ ] 4.4 Push final version to GitHub

### Phase 4 Checkpoint (E2E)
- [ ] Full loop: `/fb-scan` → `/fb-research {n}` → `/fb-reply` works end-to-end
- [ ] Reply visible on Facebook as Orbit Advisory
- [ ] Answered post does not reappear in next `/fb-scan`
- [ ] Vault updated with research from the answered post

---

## Backlog (deferred, not blocking)

- [ ] `skills/vault-lint/SKILL.md` — 7-check quality audit (orphan sources, broken wikilinks, missing citations, etc.)
- [ ] Cache TAS 1 Manual PDF (needed for cost-centre classification questions)
- [ ] Formal behavioral tests for vault-capture, vault-search, vault-compile edge cases

### Dropped

- ~~`skills/vault-ingest/SKILL.md` for batch-ingesting sources/raw/ clippings~~ — replaced by `/vault-research` direct queries. sources/raw/ serves as a reference library that vault-deep-research reads when relevant; batch pre-compilation of clippings is not cost-effective.
- ~~vault-compile chunked compile protocol for large legal-text~~ — same reason above.
