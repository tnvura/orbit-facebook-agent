# Changelog

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
