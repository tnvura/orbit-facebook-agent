---
name: vault-deep-research
description: This skill should be used when researching a Thai tax or accounting question against authoritative sources, when the user asks to "research this question", "verify this tax rule", "deep research on [topic]", "look up the Revenue Code for [topic]", or when /fb-research needs to verify a question that Orbit Vault doesn't fully cover. Produces a structured research report saved to Orbit Vault/sources/research/ with verified claims traceable to Tier 1–3 sources.
version: 1.0.0
---

# vault-deep-research

Research a Thai tax/accounting question against authoritative sources and produce a structured research report for `vault-compile` to fill vault stubs with verified knowledge.

This is the **truth-finding** skill. Facebook reply content is never compiled as truth — only output from this skill is.

## Inputs

| Field | Description | Required |
|---|---|---|
| `question` | The Thai/English question text | Yes |
| `vault_context` | Output from a prior `vault-search` run (stub pages, weak matches) | No |
| `focus_hints` | Extra narrowing, e.g. `"tax axis only"` or `"focus on VAT"` | No |
| `post_id` | If called from `/fb-research`, the originating FB post ID | No |

## Skills Required

| Skill | When to use |
|---|---|
| `obsidian:obsidian-markdown` | Writing the output file (wikilinks, frontmatter, callouts) |

---

## Source Authority Tiers

Every claim in the final report must be traceable to one of these tiers.

| Tier | Source type | Domain(s) | Treatment |
|---|---|---|---|
| 1 | Revenue Code text (ประมวลรัษฎากร) | `rd.go.th` | Primary tax law — quote verbatim |
| 2 | Ministerial regs, RD announcements | `rd.go.th` | Implementing rules, rate tables |
| 2 | Accounting standards (TAS/TFRS/NPAE) | `acpro-std.tfac.or.th` | Primary accounting authority |
| 3 | RD ข้อหารือภาษีอากร | `rd.go.th` | Scenario-specific official interpretation |
| 3 | TFAC FAQ | `tfac.or.th/Faq` | Professional body interpretation |
| 3 | FlowAccount, PeakAccount guides | `flowaccount.com`, `peakaccount.com` | Practical Thai application |
| 4 | Other accounting firm / CPD content | varies | Supporting only |
| 5–6 | Blogs, Facebook groups | — | Never primary — context only |

**Claim rule:** Vault facts (`topics/`, `entities/`) require ≥1 Tier 1–3 source. Tier 4 may supplement. Tier 5–6 never appear as vault facts.

---

## Step 0 — Vault pre-search

Before any external search, check what is already cached locally.

```
# Prior research on this topic?
Grep pattern="[keyword]" path="Orbit Vault/sources/research/" output_mode="files_with_matches"

# Stubs waiting to be filled?
Grep pattern="Pending deep-research" path="Orbit Vault/topics/" output_mode="files_with_matches"
Grep pattern="Pending deep-research" path="Orbit Vault/entities/" output_mode="files_with_matches"

# PDF cache and law-text clippings?
Read file_path="Orbit Vault/sources/raw/pdf-cache/manifest.md"
Grep pattern="[Revenue Code section or TAS number]" path="Orbit Vault/sources/raw/" output_mode="files_with_matches"
```

- **Prior HIGH-confidence research exists on same scope** → skip to Step 8, write thin stub-fill note
- **Cached PDF exists** → note its hash, skip download+parse in Step 4b
- **Law-text clipping covers the section** → quote from clipping directly, skip WebFetch

---

## Step 1 — Classify the question

| Axis | In scope when question is about… | Primary sources |
|---|---|---|
| **Tax** | Deductibility, PIT/CIT/VAT/WHT rates, exemptions, filing | `rd.go.th` |
| **Accounting** | Recognition, classification, measurement, disclosure | `acpro-std.tfac.or.th` |
| **Practitioner** | How-to, examples, software, edge cases | `flowaccount.com`, `peakaccount.com` |

Most FB questions touch Tax + Accounting. Skip an axis only if the question clearly doesn't touch it.

**Classification question hint:** If the question asks "how to book / which account / which cost centre", TAS 1 (cost-centre split) and TAS 2 (inventory capitalisation) are always in scope. Check `manifest.md`; if not cached, add them to the Step 4b pipeline.

---

## Step 2 — Term translation

Thai tax/accounting has two registers. Translate key terms before searching.

For the canonical term table and register rules, load: **`references/term-glossary.md`**

Quick rules:
- `rd.go.th` → colloquial terms
- `acpro-std.tfac.or.th` → formal TAS/TFRS terms
- FlowAccount/PeakAccount → try both

If unsure of the formal term: `WebSearch: "[colloquial term] ตาม TAS OR TFRS"` before the main searches.

Record the colloquial↔formal mapping used in this run in the output report's "Term Translations" section, and append any new discoveries to `references/term-glossary.md`.

---

## Step 3 — Landscape scan (axis-aware, parallel)

Run all searches in a single message. Do not fetch content yet — discover URLs only.

```
# Tax axis
WebSearch: site:rd.go.th ข้อหารือ [colloquial topic]
WebSearch: site:rd.go.th [colloquial topic] มาตรา

# Accounting axis
WebSearch: site:acpro-std.tfac.or.th [formal topic]
WebSearch: site:tfac.or.th/Faq [formal topic]

# Practitioner axis
WebSearch: site:flowaccount.com [colloquial topic]
WebSearch: site:peakaccount.com [colloquial topic]
```

**Output:** Ranked URL list, max 5 per axis / 15 total, each flagged with tier + source category.

**Relevance pruning:** For each candidate, check snippet for key terms from Step 2 and whether it's a primary source (ruling/standard) vs. article. Discard off-topic URLs and document them with reason — they go in "Candidates Considered, Not Fetched" in the output.

---

## Step 4 — Fetch & process sources

Process in tier priority order (Tier 1 → Tier 3). Skip Tier 4+ unless higher tiers yielded nothing.

### 4a — HTML pages

```
WebFetch url="..." prompt="Extract: (a) relevant Thai text verbatim, (b) Revenue Code section or TAS/TFRS numbers cited, (c) publication/ruling date. Do NOT summarize — return source text answering [specific question]."
```

Budget: ~5k tokens per fetch. Always prefer a cached `sources/raw/` clipping over a WebFetch.

**Error handling:**

| Error | Action |
|---|---|
| 303 redirect | Check `sources/raw/` for clipping first; retry with redirect URL; fallback: `curl -s "https://r.jina.ai/{url}"` |
| 403 / 503 | Try `curl -s "https://r.jina.ai/{url}"`; if still fails, note in Gaps |
| Timeout | Retry once; if still fails, skip and note in Gaps |
| Empty / off-topic | Skip — do not pad report |

### 4b — PDF documents

**Never WebFetch a PDF directly — it consumes 30k+ tokens for a 20-page doc.**

Full pipeline details: **`references/pdf-parser.md`** (project-level reference)

```bash
CACHE_DIR="/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/sources/raw/pdf-cache"
URL="https://acpro-std.tfac.or.th/..."
HASH=$(echo -n "$URL" | shasum -a 1 | cut -c1-12)
BASENAME="[human-readable-slug]"
PDF="${CACHE_DIR}/${HASH}--${BASENAME}.pdf"
MD="${CACHE_DIR}/${HASH}--${BASENAME}.md"

if [ ! -f "$MD" ]; then
  curl -L -s --max-time 60 -o "$PDF" "$URL"
  PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH" \
    "/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent/.venv-pdf/bin/opendataloader-pdf" \
    "$PDF" -f markdown -o "$CACHE_DIR" -q
  rm -rf "${CACHE_DIR}/${HASH}--${BASENAME}_images"
fi

# Targeted read — ~2k tokens total
Grep pattern="^#" path="$MD" output_mode="content" -n=true   # get TOC
Read file_path="$MD" offset=<line> limit=<span>               # read relevant section only
```

After processing, update `pdf-cache/manifest.md`.

### 4c — Token budget caps

| Tier | Max per source | Total cap |
|---|---|---|
| 1–2 | 15k | 50k |
| 3 | 8k | 30k |
| 4+ | 3k | 10k |

Stop fetching if approaching cap; synthesize from available sources and flag "insufficient source depth".

---

## Step 5 — Triangulate & classify claims

| Type | Requirements | Format |
|---|---|---|
| **C1** Definitive | Verbatim Tier 1–2 quote + confirmed by second source | `**Claim** (C1): …` / `**Source:** [1][2]` / `**Confidence:** HIGH` |
| **C2** Official interpretation | Tier 3 (RD ruling, TFAC FAQ) | `**Claim** (C2): …` / `**Confidence:** MEDIUM` |
| **C3** Practitioner consensus | Tier 3–4, practitioner agreement | `**Claim** (C3): …` / `**Confidence:** LOW-MEDIUM` |
| **C4** Unresolved | Contested, no consensus | `**Claim** (C4, unresolved): … / …` |
| **C4-unsourced** | Likely correct but no Tier 1–3 source was read this session | `**Claim** (C4-unsourced): …` — must NOT be compiled to vault as fact |

**Vault rule:** `topics/` and `entities/` pages accept C1 and C2 only. C3 may supplement. C4 and C4-unsourced must be flagged — vault-compile records them as dated unverified claims pending sourcing.

### Sources That Do NOT Count

The following are **not valid sources** for any claim classification, regardless of how authoritative they feel:

| Not a source | Why |
|---|---|
| Training knowledge / general knowledge | Not traceable to a source read this session |
| `.claude/rules/` files (thai-tax-and-accounting.md, etc.) | Internal reference summaries, not primary sources |
| `CLAUDE.md` files | Project documentation, not law text |
| Other compiled vault pages (`topics/`, `entities/`) | Circular — these were compiled from sources, not the source itself |
| Rules-of-thumb ("well-known rates") | Practitioner lore without a citation is C4-unsourced |

**The test:** Can you point to a specific URL or file path that was actually fetched or read in Steps 3–4 of this session? If no → the claim is C4-unsourced, not C1/C2/C3.

---

## Step 6 — Synthesize

- Quote verbatim from Tier 1–2 — paraphrasing introduces drift
- Cross-reference where TAS and RD ruling both address the question — show alignment or disagreement
- Answer the original question directly in a dedicated section
- Flag gaps explicitly where no Tier 1–3 source was found

---

## Step 7 — Red team

Three mandatory challenges before finalising:

**Challenge 1 — Contradicting law:** "What Revenue Code section or TAS/TFRS paragraph would most plausibly contradict my conclusion?" Search for it. If found and it changes the answer, downgrade to C4.

**Challenge 2 — Term confusion:** "Did I use a colloquial term where a formal was needed?" Re-read each claim against its source.

**Challenge 3 — Missing standard:** "Is there a TAS/TFRS this answer depends on that I haven't cited?" For classification questions, verify TAS 1 and TAS 2 are cited or explicitly excluded.

**Confidence rubric:**

| Level | Requirements |
|---|---|
| **HIGH** | ≥1 verbatim Tier 1–2 quote + ≥1 Tier 3 source + no contradictions + all 3 challenges passed |
| **MEDIUM** | Tier 3 only, OR Tier 1–2 not confirmed by second source, OR minor open challenge |
| **LOW** | Tier 4+ only, OR Tier 3 contested, OR mandatory challenge failed and unresolved |

---

## Step 8 — Save output to vault

Save to `Orbit Vault/sources/research/{YYYY-MM-DD}-{slug}.md` using the Write tool directly.

For the full output template and frontmatter schema, load: **`references/output-template.md`**

The slug must match the stub being filled (e.g., `employee-welfare-vs-allowance`).

---

## Invariants

- Never treat FB replies as sources
- Never WebFetch a PDF — always use the cache + opendataloader-pdf pipeline
- Never synthesize from zero Tier 1–3 sources — output "insufficient sources" instead
- Always translate terms before searching (colloquial-only misses TAS/TFRS)
- Always save to `Orbit Vault/sources/research/` with correct frontmatter
- Preserve verbatim quotes from Tier 1–2 — do not paraphrase law text
- **Never classify a claim as C1/C2/C3 based on training knowledge, `.claude/rules/` files, CLAUDE.md, or other compiled vault pages** — these are always C4-unsourced regardless of how authoritative they feel. The only valid sources are URLs or file paths actually fetched or read in Steps 3–4 of this session.

---

## Return Value

```
DEEP-RESEARCH RESULT
====================
File:           sources/research/{YYYY-MM-DD}-{slug}.md
Tier coverage:  T1={n} T2={n} T3={n} T4={n}
Confidence:     HIGH | MEDIUM | LOW
Stubs filled:   {list of wikilinks}
Gaps:           {list or "none"}
Contradictions: {list or "none"}
```

If `Confidence: LOW` or gaps are non-trivial, the caller (`/fb-research`) must warn the user before drafting a reply.

---

## References

- **`references/output-template.md`** — Full output file structure, frontmatter schema, worked example pointer
- **`references/term-glossary.md`** — Canonical colloquial↔formal term table, register rules, quick lookup by question type
- **`references/pdf-parser.md`** (project-level) — PDF parser installation, pipeline, dedup protocol, quirks
