# PDF Parser Reference

How to download, parse, and cache Thai PDF documents using `opendataloader-pdf`.

Used by: `skills/vault-deep-research` (Step 4b)

---

## Dependencies

| Dependency | Location | Notes |
|---|---|---|
| Java 17 | `/opt/homebrew/opt/openjdk@17/bin/java` | Installed via `brew install openjdk@17` (keg-only — must set PATH manually) |
| opendataloader-pdf 1.8.1 | `.venv-pdf/bin/opendataloader-pdf` | Project-local venv at `Orbit Facebook Agent/.venv-pdf/` |
| PDF cache dir | `Orbit Vault/sources/raw/pdf-cache/` | Tracks both raw PDFs and parsed markdown |
| Manifest | `Orbit Vault/sources/raw/pdf-cache/manifest.md` | Dedup index — check before every download |

Java is on `~/.zshrc` PATH (`export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"`). If a new shell session doesn't have it, prefix commands with `PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"`.

---

## Filename Scheme

```
{sha1(url)[:12]}--{human-basename}.{pdf,md}
```

- Hash is the first 12 characters of the SHA-1 of the **exact URL** (no trailing slash, no URL-decoding)
- Human basename is a short slug you choose — keep it descriptive, e.g. `TAS19-Manual-2567`
- Both the `.pdf` and `.md` share the same hash+basename prefix

**Example:**
```
URL  = https://acpro-std.tfac.or.th/.../Manual%20TAS%2019_11_03_2567.pdf
HASH = a9848f2767d6
FILE = a9848f2767d6--TAS19-Manual-2567.pdf
      a9848f2767d6--TAS19-Manual-2567.md
```

---

## Dedup Check

Always check the manifest before downloading. If the `.md` already exists, skip download and parse entirely.

```bash
CACHE_DIR="/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/sources/raw/pdf-cache"
URL="https://acpro-std.tfac.or.th/..."
HASH=$(echo -n "$URL" | shasum -a 1 | cut -c1-12)
BASENAME="TAS19-Manual-2567"
MD="${CACHE_DIR}/${HASH}--${BASENAME}.md"

if [ -f "$MD" ]; then
  echo "Cache hit: $MD — skipping download"
else
  echo "Cache miss — proceeding to download"
fi
```

Also check `manifest.md` by URL before computing the hash — if the URL is already listed, the `.md` file exists.

---

## Full Download + Parse Pipeline

```bash
CACHE_DIR="/Users/tnvura/Desktop/Orbit Advisory/Orbit Vault/sources/raw/pdf-cache"
URL="https://acpro-std.tfac.or.th/..."
HASH=$(echo -n "$URL" | shasum -a 1 | cut -c1-12)
BASENAME="TAS19-Manual-2567"   # choose a human-readable slug
PDF="${CACHE_DIR}/${HASH}--${BASENAME}.pdf"
MD="${CACHE_DIR}/${HASH}--${BASENAME}.md"

if [ ! -f "$MD" ]; then
  # 1. Download
  curl -L -s --max-time 60 -o "$PDF" "$URL"

  # 2. Parse to markdown
  PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH" \
    "/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent/.venv-pdf/bin/opendataloader-pdf" \
    "$PDF" -f markdown -o "$CACHE_DIR" -q

  # 3. Clean up image subfolder (not needed, wastes disk)
  rm -rf "${CACHE_DIR}/${HASH}--${BASENAME}_images"
fi
```

---

## Reading the Parsed Markdown

The `.md` output preserves heading hierarchy, tables, and bullet lists. Thai text is correctly extracted with minor cosmetic tone-mark issues that do not affect meaning.

**Workflow for targeted extraction (budget: ~2k tokens):**

```
# Step 1 — Get table of contents
Grep pattern="^#" path="$MD" output_mode="content" -n=true

# Step 2 — Identify the relevant heading by line number

# Step 3 — Read only that section (typically 20–60 lines)
Read file_path="$MD" offset=<line> limit=<span>
```

Never read the full `.md` unless the document is very short (<100 lines). A 20-page PDF parses to ~400 lines — targeted reads keep token cost low.

---

## Update manifest.md After Each New Parse

After a successful parse, append to `Orbit Vault/sources/raw/pdf-cache/manifest.md`:

```markdown
| {HASH} | {BASENAME} | {TIER} | {TOPIC DESCRIPTION} | {URL} | {YYYY-MM-DD} |
```

Example:
```markdown
| a9848f2767d6 | TAS19-Manual-2567 | 2 | Employee benefits (short-term, post-employment, long-term, termination) | https://acpro-std.tfac.or.th/.../Manual%20TAS%2019_11_03_2567.pdf | 2026-04-13 |
```

---

## Known Quirks

| Issue | Detail |
|---|---|
| Thai tone marks | Minor rendering artefacts (e.g. `ร้ะ` instead of `ระ`) in a small number of characters. Meaning is 100% preserved — safe to quote with minor cleanup |
| Image subfolder | opendataloader-pdf always creates `{hash}--{basename}_images/` alongside the `.md`. Always delete it immediately (step 3 above) |
| Java PATH in new shells | `~/.zshrc` sets the PATH, but sub-shells spawned by Claude Code tools may not source it. Always prefix with `PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"` in the Bash invocation |
| Large PDFs (100+ pages) | Not yet tested. For a 100-page TFRS training deck, consider parsing and checking output size before reading — may need more targeted grep patterns |
| URL encoding in hash | Hash the URL exactly as you have it — do not URL-decode before hashing. `%20` in the URL stays as `%20` when computing the hash |

---

## Common PDF Sources

| Source | Tier | URL Pattern | Notes |
|---|---|---|---|
| TAS/TFRS Manuals | 2 | `acpro-std.tfac.or.th/test_std/uploads/files/มาตรฐาน.../คู่มือ.../` | Standard manuals; 20–40 pages; Thai |
| TFRS for SMEs | 2 | `acpro-std.tfac.or.th/uploads/files/` | Shorter; covers NPAE |
| RD Ministerial Regs | 2 | `rd.go.th/fileadmin/...` | Usually short; sometimes HTML is better |
| RD Seminar materials | 3 | `rd.go.th/publish/seminar/` | Practitioner-level; useful for practical examples |
