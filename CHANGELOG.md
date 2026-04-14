# Changelog

## [0.1.9] 2026-04-14 — Fix: move pdf-parser reference into vault-deep-research skill

### Fixed
- `skills/vault-deep-research/references/pdf-parser.md` — moved from project-level `reference/pdf-parser.md` so the skill is self-contained and works for all plugin users without path traversal
- `skills/vault-deep-research/SKILL.md` — updated both `pdf-parser.md` references from `../../reference/pdf-parser.md` to `references/pdf-parser.md`

### Removed
- `reference/pdf-parser.md` — superseded by the skill-local copy above

---

## [0.1.8] 2026-04-13 — Phase 2 Complete: Research Pipeline + Vault Skills

### Added
- `skills/vault-research/SKILL.md` v1.0.0 — canonical research orchestrator; invokable directly by user or internally by fb-research; vault-first → deep-research fallback
- `skills/vault-deep-research/SKILL.md` v1.0.0 — 8-step truth-finding skill with Tier 1–6 source authority, C1–C4-unsourced claim classification; "Sources That Do NOT Count" rule prevents training-knowledge misclassification
- `skills/vault-search/SKILL.md` — read-only vault lookup; returns strong/weak/none coverage signal
- `skills/vault-capture/SKILL.md` — immutable source writer for fb-posts and deep-research outputs
- `skills/vault-compile/SKILL.md` — ripple compiler; creates/updates topics, entities, posts, index, log
- `scripts/extract_replies.py` — CDP-based comment extractor
- `scripts/hooks/pre-commit` — auto-increments plugin.json patch version on every commit
- `scripts/hooks/install.sh` — one-time hook setup after fresh clone

### Changed
- `skills/fb-research/SKILL.md` v1.1.0 — refactored to delegate all knowledge work to vault-research; retains only FB-specific steps (load candidate, extract replies, capture fb-post, validate replies, draft reply)
- `tasks/todo.md` — rewritten with accurate phase completion status

### Fixed
- vault-deep-research: added C4-unsourced claim type + "Sources That Do NOT Count" invariant — prevents training knowledge from being misclassified as C2
- `topics/assessable-income-types`: removed unsourced WHT rate table; replaced with cross-link to withholding-tax-rates
- `sources/research/2026-04-13-assessable-income-types-sme.md`: WHT claims reclassified C4-unsourced

### Vault (Orbit Vault updates this session)
- Researched and compiled: `topics/withholding-tax-rates`, `entities/ภ.ง.ด.3`, `entities/ภ.ง.ด.53` (HIGH confidence, T1=1 T2=3 T3=1)
- Vault now: 5 topics, 8 entities, 3 posts
- 2 C4 gaps flagged: 40(3) royalties form (ภ.ง.ด.2 vs ภ.ง.ด.3), transportation rate 1% (Tier 3 only)

---

## [0.1.2] 2026-04-13 — Phase 1 Complete: /fb-scan skill

### Added
- `scripts/extract_posts.py` — CDP-based Facebook post extractor
  - Incremental scroll + accumulate pattern (Facebook unloads DOM on scroll)
  - Two-strategy JS filter: `/posts/` link traversal + feed children fallback
  - Feed sort to "New posts" before scrolling (`get_by_role` with exact aria-label)
  - `filter_mode`: `loose` (exclude_terms only) or `strict` (full keyword match)
  - Author exclusion list (`exclude_authors` in keywords.json)
  - Cross-group URL filter, text dedup (first-80-chars key), article share detection
  - Profile check: warns only on confirmed wrong profile, not on undetected
- `commands/fb-scan.md` — slash command entry point
- `skills/fb-scan/SKILL.md` — full 5-step scan workflow
- `reference/thai-keywords.json` — keyword lists: question_markers, accounting_tax_terms, exclude_terms, exclude_authors

### Changed
- `reference/playwright-facebook-controls.md` — updated for CDP approach (replaces playwright-cli docs)
- Default: 50 scrolls, loose mode

### Architecture decisions
- **loose mode**: JS filter rejects known ads/noise; Claude classifies candidates inline — better recall than strict keyword matching
- **CDP not playwright-cli**: System Chrome via `--remote-debugging-port=9223` bypasses Facebook bot detection

---

## [2026-04-12] — Project Initialized

- Created project from design spec (brainstorming session 2026-04-11/12)
- Playwright persistent session validated and documented
- Reference guide: `reference/playwright-facebook-controls.md`
- Design spec: `../docs/superpowers/specs/2026-04-12-orbit-facebook-agent-design.md`
- Implementation plan: `~/.claude/plans/snuggly-jumping-shore.md`
- Git repo initialized, foundational docs created (CLAUDE.md, SPRINT.md, CHANGELOG.md)
