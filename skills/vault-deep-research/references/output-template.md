# Output File Template

Save to: `Orbit Vault/sources/research/{YYYY-MM-DD}-{slug}.md`

```markdown
---
kind: deep-research
question: "[one-line Thai summary of the question]"
post_id: "[if from /fb-research, else omit]"
researched: YYYY-MM-DD
tier_coverage:
  - tier-1: [n]
  - tier-2: [n]
  - tier-3: [n]
stubs_filled:
  - topics/[slug]
  - entities/[term]
sources_cited: [n]
confidence: HIGH | MEDIUM | LOW
---

# Research: [Question summary in Thai]

## Question (verbatim)
> [copy of the question exactly as received]

## Term Translations
| Colloquial | Formal (TAS/TFRS) |
|---|---|
| ค่าเบี้ยเลี้ยง | ผลประโยชน์พนักงานระยะสั้น |
| … | … |

## Law Text (Tier 1)
Direct quotes from the Revenue Code.

**มาตรา 65 ตรี** [full text]
> [verbatim Thai]
**Source:** [[sources/raw/pdf-cache/{hash}--{basename}]] OR <URL>

## Accounting Standards (Tier 2)
Direct quotes from TAS/TFRS/NPAE.

**TAS 19 — ผลประโยชน์ของพนักงาน (short-term)**
> [verbatim Thai from section 4.x]
**Source:** [[sources/raw/pdf-cache/{hash}--TAS19-Manual-2567]]

## Official Interpretation (Tier 3)
RD ข้อหารือ and TFAC FAQ findings.

**ข้อหารือ 0702/NNNN (ปี 25NN) — [subject]**
- Question: …
- RD Answer: …
- Revenue Code sections cited: …
**Source:** <URL>

## Professional Consensus (Tier 3 — FlowAccount/PeakAccount)
- Their take: …
- Does it align with Tier 1–2? yes/no

## Direct Answer to the Question
Plain-language answer, citing tiers inline.

**Short answer:** [1 sentence]

**Reasoning:**
1. Per [Tier 1 source] → …
2. Per [Tier 2 source] → …
3. Therefore: …

## Classification Decision (for accounting/bookkeeping questions)
If the question involves chart-of-accounts classification:
- Account: …
- Cost centre: …
- Rationale (per TAS/TFRS): …

## Tax Treatment (for tax questions)
If the question involves tax deductibility/exemption/WHT:
- CIT deductibility: …
- PIT treatment for recipient: …
- WHT applicability: …
- VAT applicability: …
- Rationale (per Revenue Code + RD ruling): …

## Stub Mapping (for vault-compile)
Pages this research fills:
- [[topics/{slug}]] → fills: Details, Common Mistakes sections
- [[entities/{form-or-term}]] → fills: Key Facts, When It Applies, Filing Steps
- [[posts/{YYYY-MM-DD}-{post-id}]] → fills: Answer, Draft Reply

## Gaps / Unresolved
Anything the research couldn't answer, flagged for future work.

## Red Team
Document the 3 mandatory challenge responses here.

## Sources Cited
Numbered list:
[N] Title — tier — URL or [[vault wikilink]]

## Candidates Considered, Not Fetched
[URL] — reason (off-topic snippet / Tier 4+ / duplicate domain / token cap)
```

---

## Worked Example

A complete research output is at:
`Orbit Vault/sources/research/2026-04-13-employee-welfare-vs-allowance.md`

This covers ค่าเบี้ยเลี้ยง vs สวัสดิการพนักงาน for warehouse delivery staff — useful as a style reference for classification questions.
