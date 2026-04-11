# Playwright CLI — Facebook Group Controls Reference

Validated 2026-04-11 against Facebook group: อยากรู้เรื่องบัญชี เรื่องภาษี เชิญที่นี่คะ (598953943470618)

Session: Logged in as Orbit Advisory page account (linked to personal account).

---

## Prerequisites

- Playwright CLI: `/opt/homebrew/bin/playwright-cli`
- **Always use `--headed` flag** when opening browser (user needs visibility)
- **Always use `--profile` flag** to persist login session (see below)

## Persistent Session (Orbit Advisory Profile)

Login is stored in a persistent browser profile directory. After first-time login, the session persists across browser close/reopen — no re-login needed.

**Profile path**: `/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent/.browser-profile`

**First-time setup** (done once):
1. Open browser with `--profile` flag
2. User logs in with personal Facebook account
3. User switches to Orbit Advisory page profile via "Your profile" dropdown
4. Both login and profile selection are saved to the profile directory

**Important**: The persistent profile stores the Orbit Advisory page profile as active. All interactions (browsing, commenting) happen as "Orbit Advisory", not the personal account. The comment boxes will show "Comment as Orbit Advisory".

**Available profiles on this account**:
- **Orbit Advisory** (active — the one we use)
- Thanavat Urairerkkul (personal — do not use)
- Araya Herbs (other page — do not use)

## Opening & Closing

```bash
# STANDARD OPEN COMMAND — always use this exact form
playwright-cli open "https://www.facebook.com/groups/598953943470618" --headed --profile "/Users/tnvura/Desktop/Orbit Advisory/Orbit Facebook Agent/.browser-profile"

# Close browser when done
playwright-cli close
```

## Navigation

```bash
# Go to group feed
playwright-cli goto "https://www.facebook.com/groups/598953943470618/"

# Go to specific post by ID
playwright-cli goto "https://www.facebook.com/groups/598953943470618/posts/{POST_ID}/"

# Back / forward / reload
playwright-cli go-back
playwright-cli go-forward
playwright-cli reload
```

## Snapshots (Reading Page State)

```bash
# Capture accessibility snapshot — returns element refs for interaction
playwright-cli snapshot
```

Snapshot output is saved to `.playwright-cli/page-{timestamp}.yml`. Use `Read` tool to inspect. Each interactive element has a `ref=eNNN` ID used for click/fill commands.

## Scrolling (Loading More Posts)

Facebook uses infinite scroll. Posts load as you scroll down.

```bash
# Scroll down to load more posts
playwright-cli eval "() => window.scrollBy(0, 1500)"

# Scroll to top
playwright-cli eval "() => window.scrollTo(0, 0)"

# Multiple scrolls to load many posts
playwright-cli eval "() => { for(let i=0;i<5;i++) { window.scrollBy(0, 1500); } return 'done'; }"
```

After scrolling, take a new snapshot or run eval to see newly loaded content.

## Extracting Post Content

### Post text from feed (truncated by default)

```bash
playwright-cli eval "() => {
  const msgs = document.querySelectorAll('div[data-ad-comet-preview=\"message\"]');
  const texts = [];
  for (const m of msgs) { texts.push(m.innerText.substring(0, 800)); }
  return JSON.stringify(texts, null, 2);
}"
```

### Expanding truncated posts ("See more")

Posts longer than ~3 lines show "See more" button. **Must use Playwright native click, not JS click** — Facebook's React framework doesn't respond to `element.click()`.

```bash
# Step 1: Take snapshot to find the See more button ref
playwright-cli snapshot
# Look for: button "See more" [ref=eNNN]

# Step 2: Click using the ref
playwright-cli click eNNN

# Alternative: Click first See more found
# (from snapshot, Playwright resolves to .first())
playwright-cli click eNNN  # where eNNN is the ref from snapshot
```

After clicking, re-run the text extraction eval to get the full expanded text.

### Extract all substantial text blocks

Useful for grabbing both post text and visible comments:

```bash
playwright-cli eval "() => {
  const all = document.querySelectorAll('div[dir=\"auto\"]');
  const texts = [];
  for (const el of all) {
    const t = el.innerText.trim();
    if (t.length > 50 && !t.includes('Facebook') && !t.includes('Log in'))
      texts.push(t.substring(0, 500));
  }
  return JSON.stringify(texts.slice(0, 20));
}"
```

### Extract post URLs from feed

```bash
playwright-cli eval "() => {
  const links = document.querySelectorAll('a[href*=\"598953943470618/posts/\"]');
  const hrefs = new Set();
  for (const l of links) { hrefs.add(l.href.split('?')[0]); }
  return JSON.stringify([...hrefs]);
}"
```

Replace `598953943470618` with the target group ID.

### Count loaded posts

```bash
playwright-cli eval "() => {
  return document.querySelectorAll('div[data-ad-comet-preview=\"message\"]').length + ' posts';
}"
```

## Extracting Post Metadata

### Author name, text, and URL

```bash
playwright-cli eval "() => {
  const articles = document.querySelectorAll('div[role=\"article\"]');
  const results = [];
  for (const art of articles) {
    const headings = art.querySelectorAll('h3, h2');
    const author = headings.length > 0 ? headings[0].innerText : '';
    const msgs = art.querySelectorAll('div[dir=\"auto\"]');
    let text = '';
    for (const m of msgs) {
      const t = m.innerText.trim();
      if (t.length > 30 && !t.includes('Facebook')) { text = t.substring(0, 300); break; }
    }
    const links = art.querySelectorAll('a[href*=\"/posts/\"]');
    const url = links.length > 0 ? links[0].href.split('?')[0] : '';
    if (author || text) results.push({author, text, url});
  }
  return JSON.stringify(results.slice(0, 10), null, 2);
}"
```

## Clicking & Interaction

```bash
# Click by element ref (from snapshot)
playwright-cli click eNNN

# Fill a text field
playwright-cli fill eNNN "text to type"

# Type text (simulates keystrokes)
playwright-cli type "text to type"
```

## Key DOM Selectors (as of 2026-04-11)

| Purpose | Selector | Notes |
|---------|----------|-------|
| Post text | `div[data-ad-comet-preview="message"]` | Primary post content container |
| Text blocks | `div[dir="auto"]` | All user-authored text (posts + comments) |
| Post articles | `div[role="article"]` | Each post card in feed |
| Post links | `a[href*="/posts/"]` | Links to individual posts |
| Author names | `h2, h3` inside article | Post author heading |
| See more button | `button` with text "See more" | Expand truncated posts |
| Comment button | `button` with text "Comment" | Opens comment section |
| Feed container | `feed` role | The main feed element |
| Write post | `button` with text "Write something..." | Create new post |
| Search in group | `button` with text "Search within this group" | Group-specific search |
| Sort posts | `button` with text "sort group feed by New posts" | Feed sort control |

**Warning**: These selectors may change when Facebook updates its frontend. The `role`-based selectors (article, feed, button names) are more stable than `data-*` attributes. If a selector breaks, take a fresh snapshot and inspect the new structure.

## Group Info Available

From the logged-in group page:

- Group name and member count (184.9K)
- Member list with profile links
- Post sorting (New posts, Top posts)
- Tabs: About, Discussion, Featured, People, Events, Media, Files
- Current account: Orbit Advisory (page account)
- "Joined" status confirmed

## Limitations & Notes

1. **Login required** — Facebook shows limited content (partial posts, login dialog) without authentication
2. **Infinite scroll** — Must scroll to load more posts; only ~2-3 visible initially
3. **"See more" expansion** — Must use Playwright native `click` on the button ref, not JavaScript `element.click()`
4. **Comments** — Not expanded by default in feed view; need to click into individual post or click Comment button
5. **Session persistence** — Login AND profile selection persist via `--profile` flag. Verified: close browser → reopen → still logged in as Orbit Advisory. Session cookies may eventually expire (weeks/months), requiring one-time re-login.
6. **Rate/detection** — Low-volume usage (dozens of posts/day) with headed real browser is low risk for detection
7. **Account context** — Persistent profile is locked to Orbit Advisory page. Comment boxes confirm "Comment as Orbit Advisory". Do not switch to personal profile.
8. **Profile directory** — `.browser-profile/` should be gitignored (contains cookies and session data)
