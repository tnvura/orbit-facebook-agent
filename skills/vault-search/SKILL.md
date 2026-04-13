---
name: vault-search
description: This skill should be used when the user asks to "search the vault", "look up existing knowledge", "check the vault before researching", or "find what we already know about a topic". Performs a read-only search of Orbit Vault — called by /fb-research before deciding whether deep-research is needed.
version: 1.0.0
---

# vault-search

Search Orbit Vault for existing knowledge relevant to a question before invoking deep-research. Read-only — never writes to any file.

---

## Skills Required

| Skill | When to use |
|---|---|
| `obsidian:obsidian-cli` | Running `obsidian backlinks` and `obsidian links` for graph-aware searches |

---

## Inputs

| Field | Description | Required |
|---|---|---|
| `question` | The Thai/English question text or topic to search for | Yes |
| `folder_hint` | Limit search to one folder (`topics`, `entities`, `connections`, `posts`) | No |

---

## Pipeline Context

This skill is Step 1 of the `/fb-research` pipeline:

```
/fb-research
  └── vault-search  ← this skill (read-only lookup)
       ├── Strong match → draft reply directly from vault pages
       ├── Weak match   → pass matched pages as context to deep-research
       └── No match     → invoke deep-research with no vault context
```

The vault-first rule exists for two reasons:
1. **Token efficiency** — reading compiled vault pages is cheaper than a full web research cycle.
2. **Consistency** — when a question has been answered before, the vault holds the validated answer. Drafting from it avoids contradicting a previously posted reply.

Do not skip vault-search even when the question appears novel. The vault may contain a related topic or entity page that gives a 70% head-start on the research.

After `/fb-research` completes (regardless of this skill's outcome), `vault-ingest` writes the new research back to the vault. This skill's "Wikilinks to traverse" output in the result block is consumed by `vault-compile` to decide which existing pages need updating.

---

## Vault Structure

Orbit Vault is at `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/`. Understand the layout before searching:

| Folder | Contents | Naming convention |
|---|---|---|
| `topics/` | Broad subject pages — VAT, WHT, depreciation, etc. | kebab-case English (`foreign-service-vat.md`) |
| `entities/` | Specific forms, laws, organizations | Official Thai with dots (`ภ.ง.ด.53.md`, `กรมสรรพากร.md`) |
| `connections/` | Cross-cutting synthesis linking two or more compiled pages | kebab-case English (`platform-wht-and-seller-accounting.md`) |
| `posts/` | Filed Facebook Q&A records with question, research, and reply | `{YYYY-MM-DD}-{post-id}.md` |
| `sources/` | Immutable raw material — do not search here for compiled answers |  |
| `templates/` | Page layout templates — skip entirely |  |

The `index.md` at vault root contains four pipe-tables (one per searchable folder) with summaries and wikilinks. Reading `index.md` first is faster than blind Grep — it surfaces candidates in one read before opening individual pages.

Page types most likely to answer a Thai tax/accounting question:
- **entities/** — when the question is about a specific form, law, or organisation
- **topics/** — when the question is about a concept, rate, or procedure
- **connections/** — when the question involves the relationship between two distinct concepts
- **posts/** — when the question closely matches one already filed (same scenario, same client type)

---

## Step 1 — Extract search terms

From the question, derive:
- **Thai terms**: accounting/tax terms present (`ภ.ง.ด.53`, `ใบกำกับภาษี`, `VAT`, etc.)
- **English terms**: conceptual equivalents (`withholding tax`, `tax invoice`, etc.)
- **Form codes**: any form references (`ภ.พ.36`, `ภ.ง.ด.1`, etc.)

### Search term examples by question type

| Question type | Thai terms to extract | English terms to add |
|---|---|---|
| "ต้องยื่น ภ.ง.ด.53 ไหม?" | `ภ.ง.ด.53`, `หัก ณ ที่จ่าย` | `withholding tax`, `WHT`, `corporate payee` |
| "ใบกำกับภาษีออกช้า มีปัญหาไหม?" | `ใบกำกับภาษี`, `ภ.พ.30`, `ภาษีซื้อ` | `tax invoice`, `input VAT`, `VAT return` |
| "ขายของ TikTok Shop ต้องจด VAT ไหม?" | `VAT`, `ภ.พ.30`, `จดทะเบียน`, `TikTok` | `VAT registration`, `1.8M threshold`, `e-commerce` |
| "ค่าเดินทางหักภาษีได้ไหม?" | `ค่าเดินทาง`, `ค่าใช้จ่าย`, `ภ.ง.ด.50` | `travel expense`, `deductible`, `corporate income tax` |
| "พนักงาน Part-time ต้องหัก ณ ที่จ่ายไหม?" | `ภ.ง.ด.1`, `เงินเดือน`, `พนักงาน` | `salary WHT`, `PIT`, `part-time` |

Use the glossary at `Orbit Advisory/.claude/rules/thai-tax-and-accounting.md` if a Thai term is ambiguous or if an English question needs Thai equivalents. Do not fabricate form codes — only use codes that appear in the question or the glossary.

---

## Step 2 — Read `index.md` first

Read `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/index.md`.

Scan all four pipe-tables (Topics, Entities, Connections, Posts). Select rows whose summaries are plausibly relevant to the search terms. This is the primary routing step — read the full page only for candidates identified here.

If `folder_hint` is provided, scan only that table.

---

## Step 3 — Grep the vault

For each search term, run Grep on the vault directory:

```
Grep pattern="{term}" path="/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/"
```

When `folder_hint` is provided, restrict to the matching subfolder:

| `folder_hint` value | Absolute path to use |
|---|---|
| `topics` | `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/topics/` |
| `entities` | `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/entities/` |
| `connections` | `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/connections/` |
| `posts` | `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/posts/` |

Run at minimum:
- One grep per Thai term
- One grep per form code
- One grep per English term if vault has English content

Thai terms contain Unicode characters — pass them verbatim in the pattern string; the Grep tool handles Thai correctly.

Collect all matching file paths. Deduplicate. Exclude `sources/`, `templates/`, `CLAUDE.md`, `index.md`, `log.md` — compiled knowledge pages only.

---

## Step 4 — Expand via Obsidian CLI graph traversal

For each candidate page identified in Steps 2–3:

```bash
obsidian vault="Orbit Vault" backlinks file="{page-name}"
obsidian vault="Orbit Vault" links file="{page-name}"
```

`{page-name}` is the filename without extension and without folder prefix — e.g. for `topics/employee-welfare-vs-allowance.md`, use `file="employee-welfare-vs-allowance"`. The Obsidian CLI resolves by name across the vault.

Add any new pages surfaced by backlinks/links to the candidate list. This catches pages that are conceptually related but use different terminology. For Thai-named entity pages (e.g. `entities/ภ.ง.ด.53.md`), pass the Thai name verbatim: `file="ภ.ง.ด.53"`.

Cap total candidates at 15 before reading.

---

## Step 5 — Read candidate pages

Read each candidate page in full. Do not read more than 10 pages. If candidates exceed 10, prioritise:
1. Direct term matches from Step 3 — highest confidence, matched on exact content
2. Index-matched candidates from Step 2 — summary-level relevance confirmed
3. Graph-traversal additions from Step 4 — related by link graph, lower certainty

Within each priority tier, prefer pages in this folder order: `entities/` > `topics/` > `connections/` > `posts/`. Entity pages are most precise for form-specific questions; topic pages cover the broader concept. Only fall through to `connections/` or `posts/` if higher-priority candidates are exhausted.

When reading, pay particular attention to the **Common Mistakes** section on topic pages — this section contains the highest-value content for drafting Facebook replies, as it directly addresses what Thai e-commerce sellers get wrong.

---

## Step 6 — Classify and return

For each page read, classify:

- **Strong match**: page directly answers the question with complete, accurate information. The question could be answered from this page alone.
- **Weak match**: page covers a related topic but doesn't fully answer this specific case (e.g. covers VAT generally but not the specific scenario asked).

Return a structured result:

```
VAULT SEARCH RESULT
===================
Strong matches: {n}
  - [[topics/deductible-expenses]] — covers expense deductibility under CIT; does not address VAT input specifically
  - [[entities/ใบกำกับภาษี]] — defines ใบกำกับภาษี and its role in VAT; directly relevant

Weak matches: {n}
  - [[topics/vat-registration]] — mentions ใบกำกับภาษี in passing but not the focus

No match: false

Wikilinks to traverse (for vault-compile ripple): [[topics/deductible-expenses]], [[entities/ใบกำกับภาษี]]
```

---

## Decision guidance for caller (`/fb-research`)

| Result | Action |
|---|---|
| ≥1 strong match | Draft reply from vault. Skip deep-research unless the question has an unusual edge case. |
| Weak matches only | Invoke deep-research. Use weak-match pages as context to focus the research query. |
| No match | Invoke deep-research. No vault context available. |

---

## Edge Cases

**Empty vault** — if `index.md` does not exist or contains no table rows, skip Step 2 and proceed directly to Step 3 Grep. Return `No match: true` if Grep also yields nothing.

**Single-topic question with no Thai terms** — if the question is in English only, derive Thai equivalents from the `Orbit Advisory/.claude/rules/thai-tax-and-accounting.md` glossary before grepping. Do not skip the Thai-language search; vault content is primarily Thai.

**Ambiguous form codes** — if a form code appears in multiple contexts (e.g. `ภ.ง.ด.1` could relate to salary WHT broadly), run Grep for both the form code alone and paired with the topic keyword.

**Contradictory vault pages** — if two strong-match pages give conflicting information, flag this in the result block:
```
⚠ Contradiction detected: [[topics/foo]] and [[topics/bar]] conflict on {point}. Recommend deep-research to resolve before drafting.
```

---

## Invariants

- Never writes to any file.
- Never modifies `index.md`, `log.md`, or any compiled page.
- Always reads `index.md` before any Grep — no exceptions.
- Grep before Obsidian CLI — fixed order.
- Hard stop at 10 pages read.
- Vault base path: `/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/` — always absolute, never relative.
