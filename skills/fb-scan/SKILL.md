# Skill: fb-scan

Scan the target Facebook group for new tax/accounting questions worth answering as Orbit Advisory. Extracts posts via browser automation, filters with Thai keywords (zero LLM tokens), deduplicates, then classifies the remaining candidates inline.

---

## Configuration

```
GROUP_URL   = https://www.facebook.com/groups/598953943470618
PROFILE     = Orbit Facebook Agent/.browser-profile
KEYWORDS    = Orbit Facebook Agent/reference/thai-keywords.json
PROCESSED   = Orbit Facebook Agent/tracking/processed-post-ids.txt
RESULTS_DIR = Orbit Facebook Agent/tracking/
```

---

## Workflow

### Step 1 — Run extraction script

```bash
cd "/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent"
python3 scripts/extract_posts.py \
  "https://www.facebook.com/groups/598953943470618" \
  ".browser-profile" \
  "reference/thai-keywords.json" \
  "tracking/processed-post-ids.txt" \
  50 \
  loose
```

Arguments: `num_scrolls` (default: 50), `filter_mode` (default: `loose`).

| Scrolls | ~Posts scanned | ~Time window covered | Total wait |
|---------|---------------|---------------------|-----------|
| 10      | 15–25         | Last 2–4 hours      | ~20s      |
| 20      | 35–50         | Last 5–8 hours      | ~40s      |
| 30      | 55–75         | Last 10–16 hours    | ~60s      |

**Recommendation**: 20 scrolls if scanning 2×/day. 30 scrolls if scanning 1×/day.

**Filter modes:**
- `loose` (default): only `exclude_terms` applied in JS. Everything else passes to Step 3 for Claude classification. Better recall, a few false positives are expected and handled in Step 3.
- `strict`: also requires `question_markers` AND `accounting_tax_terms`. Higher precision but misses edge cases.

**What happens:**
- Chrome launches (no automation flags) or connects to existing session on port 9223
- Checks active Facebook profile — warns only if a different profile is explicitly detected
- Sets feed sort to Recent Activity (newest posts first)
- Navigates to group feed, scrolls incrementally collecting posts at each step
- JS filter runs in-browser (zero LLM tokens): rejects known ads/service offers via `exclude_terms`, passes everything else
- Deduplicates against `tracking/processed-post-ids.txt`
- Outputs JSON array to stdout

**On fresh Chrome launch (each session):**
The script will print:
```
⚠ Current profile is 'Your profile', not Orbit Advisory.
  Please switch to Orbit Advisory: click your profile picture → switch to Orbit Advisory.
Press Enter here when you have switched to Orbit Advisory:
```
Switch to Orbit Advisory in the Chrome window, then press Enter in the terminal.

### Step 2 — Parse extraction output

Parse the JSON array from stdout. Each item:
```json
{
  "id": "27132155816390403",
  "author": "Author Name",
  "text": "Post text (up to 500 chars)",
  "url": "https://www.facebook.com/groups/598953943470618/posts/27132155816390403/",
  "timestamp": "1h"
}
```

If output is `[]` — no new matching posts found. Inform user and stop.

### Step 3 — Classify candidates (inline, zero external API)

For each candidate (up to 5), evaluate:

1. **Is this genuinely a question?** (not a statement, not a service offer that slipped through)
2. **What is the specific topic?** Choose from:
   - `VAT` — registration, ภ.พ.30, ภ.พ.36, input/output tax
   - `WHT` — ภ.ง.ด.1/3/53/54, rates, certificates
   - `CIT` — corporate income tax, ภ.ง.ด.50/51
   - `PIT` — personal income tax, ภ.ง.ด.90/91
   - `E-commerce` — Shopee/TikTok/Lazada platform fees, reconciliation
   - `Bookkeeping` — journal entries, chart of accounts, ใบกำกับภาษี
   - `Registration` — company formation, VAT registration, จดทะเบียน
   - `Other` — anything else tax/accounting related
3. **Is Orbit Advisory well-positioned to answer?** Consider:
   - Do we have knowledge in `reference/` or `Orbit Vault/`?
   - Is the question within e-commerce / SME scope?
   - Is it specific enough to answer definitively?
4. **Priority** (1–3): 1 = high (clear question, our expertise), 2 = medium, 3 = low

### Step 4 — Save scan results

Save results to `tracking/scan-results-{YYYY-MM-DD}.json`:

```json
{
  "scan_date": "2026-04-12",
  "group_url": "https://www.facebook.com/groups/598953943470618",
  "candidates": [
    {
      "number": 1,
      "id": "27132155816390403",
      "author": "...",
      "text": "...",
      "url": "...",
      "timestamp": "1h",
      "topic": "VAT",
      "priority": 1,
      "notes": "Asking about forex trading and VAT registration threshold"
    }
  ]
}
```

### Step 5 — Present results to user

Show a numbered list:

```
Found N new candidates:

1. [VAT] ⭐ PinkChipmunk2571 (1h ago)
   "สอบถามครับการเทรด forex ทองคำไม่ต้องเอารายได้จากเงินที่เข้าไปยื่นจดvat..."
   https://www.facebook.com/groups/598953943470618/posts/27132155816390403/

2. [WHT] AuthorName (3h ago)
   "..."
   ...

Run /fb-research <number> to research and draft a reply for any candidate.
```

If 0 candidates: "No new matching posts found. Group feed may not have tax questions right now — try again later."

---

## Token Budget

| Step | LLM tokens |
|------|-----------|
| JS extraction + keyword filter | 0 |
| Bash dedup | 0 |
| Classification (Step 3) | ~200–400 per candidate |
| Total for 5 candidates | ~1,000–2,000 |

---

## Files Modified

- `tracking/scan-results-{date}.json` — written with candidates + classification
- Chrome `.browser-profile` — session cookies updated (Chrome stays running)

## Files NOT Modified

- `tracking/processed-post-ids.txt` — only updated when a reply is posted (`/fb-reply`)

---

## Notes

- Chrome stays running after the script exits — subsequent scans in the same session skip the profile switch
- If Chrome crashed or was closed, the script relaunches it on port 9223
- Lock files (SingletonLock etc.) in `.browser-profile/` are auto-created by Chrome; remove them if Chrome crashes before next run:
  ```bash
  rm -f .browser-profile/SingletonLock .browser-profile/SingletonCookie .browser-profile/SingletonSocket
  ```
