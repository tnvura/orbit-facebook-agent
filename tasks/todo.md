# TODO — Vault Skills Implementation

Task list corresponding to `tasks/plan.md`. Mark each task `[x]` as completed and commit at slice boundaries.

## Slice 1 — Schema Foundation

- [ ] 1a. Rewrite `Orbit Vault/CLAUDE.md` to match SPEC.md
- [ ] 1b. Split `Orbit Vault/templates/knowledge-page.md` into `topic.md`, `entity.md`, `connection.md`, `post.md`
- [ ] 1c. Create `Orbit Vault/sources/fb-posts/` + `Orbit Vault/sources/research/` (with `.gitkeep`)
- [ ] 1d. Create `Orbit Vault/connections/` (with `.gitkeep`)
- [ ] 1e. Rewrite `Orbit Vault/index.md` as 4-section pipe-table
- [ ] 1f. Rewrite `Orbit Vault/log.md` in ISO timestamp format
- [ ] ✅ Checkpoint 1: Obsidian opens clean, schema approved

## Slice 2 — vault-capture

- [ ] 2a. Create `skills/vault-capture/SKILL.md`
- [ ] 2b. Document input contract
- [ ] 2c. Behavioral test: fb-post write
- [ ] 2d. Behavioral test: deep-research write
- [ ] 2e. Behavioral test: refusal on `sources/raw/` write
- [ ] 2f. Behavioral test: refusal on duplicate filename

## Slice 3 — vault-search

- [ ] 3a. Create `skills/vault-search/SKILL.md` (Grep → Obsidian CLI sequence)
- [ ] 3b. Define structured return format
- [ ] 3c. Behavioral test: no_match on empty vault
- [ ] 3d. Behavioral test (deferred — after Slice 4 populates pages): strong_match surfaces known topic

## Slice 4 — vault-compile (fb-research strategy)

- [ ] 4a. Create `skills/vault-compile/SKILL.md` shell with source-kind router
- [ ] 4b. Implement `fb-research` strategy
- [ ] 4c. Implement backlink sweep + index + log update
- [ ] 4d. Behavioral test: clean compile on user-provided synthetic pair
- [ ] 4e. Behavioral test: contradiction triggers write-both-with-dates
- [ ] ✅ Checkpoint 2: fb-research compile reviewed and approved

## Slice 5 — vault-compile (article strategy)

- [ ] 5a. Extend vault-compile with `article` strategy
- [ ] 5b. Implement size-chunked read for >10k clippings
- [ ] 5c. Implement stub-entity creation from frontmatter wikilinks
- [ ] 5d. Behavioral test: short fake clipping compiled cleanly

## Slice 6 — vault-compile (legal-text chunked)

- [ ] 6a. Extend vault-compile with `legal-text` detection
- [ ] 6b. Implement pre-pass skeleton TOC builder
- [ ] 6c. Implement per-chunk loop with working-memory file
- [ ] 6d. Implement post-pass coherence sweep + stub resolution + connections
- [ ] 6e. Behavioral test: full compile of `sources/raw/มาตรา 38_64.md`
- [ ] 6f. Verify all cross-references resolve (no broken wikilinks)
- [ ] ✅ Checkpoint 3: chunked protocol approved on real clipping

## Slice 7 — /vault-ingest command

- [ ] 7a. Create `commands/vault-ingest.md`
- [ ] 7b. Behavioral test: single-path invocation
- [ ] 7c. Behavioral test: `--pending` mode

## Slice 8 — vault-lint

- [ ] 8a. Create `skills/vault-lint/SKILL.md` with all 7 checks
- [ ] 8b. Implement severity-grouped report output
- [ ] 8c. Behavioral test: inject one defect per check type, verify report

## Slice 9 — E2E Integration

- [ ] 9a. Set up: use Phase 1 candidate #1 (WhiteRabbit8044)
- [ ] 9b. Drive manual flow: search → capture ×2 → compile → verify
- [ ] 9c. Run vault-lint post-integration; expect clean report
- [ ] ✅ Checkpoint 4: Phase 2 foundation complete

---

## Notes

- Commit at each slice boundary with message format: `Slice N complete — {short description}`
- If a behavioral test fails, do NOT advance to the next slice — iterate on the current skill first
- Working-memory and lint-report files live in `logs/` (gitignored)

## Known Bridge (Task 2.3)

The step from `tracking/scan-results-{date}.json` → `sources/fb-posts/` is NOT a separate skill.
It is an input-preparation step inside `/fb-research`:
1. Load candidate from scan-results JSON by number
2. Run `extract_replies.py` on post URL → get replies
3. Call `vault-capture(kind=fb-post, content=post+replies, slug=post-{post_id}, ...)`

This is documented in `skills/vault-capture/SKILL.md` § Caller Context.
Wire it explicitly when building `/fb-research` skill (Task 2.3).
