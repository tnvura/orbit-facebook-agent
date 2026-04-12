#!/usr/bin/env python3
"""
extract_posts.py — Facebook Group Post Extractor with JS Pre-filter

Launches Chrome without automation flags, connects via CDP, extracts posts
from a Facebook group feed, applies Thai keyword filter in JavaScript (zero
LLM tokens), and deduplicates against already-processed post IDs.

Usage:
  python3 scripts/extract_posts.py <group_url> <profile_path> <keywords_path> <processed_ids_path>

Output:
  JSON array to stdout — each item: {id, author, text, url, timestamp}

Exit codes:
  0 — success (even if 0 candidates found)
  1 — error
"""

import json
import os
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CDP_PORT = 9223  # Use 9223 to avoid conflicts with other Chrome instances


def load_keywords(keywords_path):
    with open(keywords_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_processed_ids(processed_ids_path):
    if not os.path.exists(processed_ids_path):
        return set()
    with open(processed_ids_path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def launch_chrome(profile_path):
    """Launch Chrome without automation flags, with remote debugging enabled."""
    abs_profile = os.path.abspath(profile_path)
    process = subprocess.Popen(
        [
            CHROME_PATH,
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={abs_profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait for Chrome to be ready
    time.sleep(4)
    return process


def build_js_filter(keywords, filter_mode="strict"):
    """
    JS function that extracts posts from the feed and applies keyword filter.
    Runs entirely in-browser — zero LLM tokens.
    Returns array of matching post objects (playwright deserializes automatically).

    filter_mode:
      "strict" (default) — post must have question_markers AND accounting_tax_terms
      "loose"            — only exclude_terms applied; everything else passes (for diagnostics)
    """
    question_markers = json.dumps(keywords["question_markers"])
    accounting_terms = json.dumps(keywords["accounting_tax_terms"])
    exclude_terms = json.dumps(keywords["exclude_terms"])
    exclude_authors = json.dumps(keywords.get("exclude_authors", []))
    strict_mode = json.dumps(filter_mode == "strict")

    return f"""() => {{
        const questionMarkers = {question_markers};
        const accountingTerms = {accounting_terms};
        const excludeTerms = {exclude_terms};
        const excludeAuthors = {exclude_authors};
        const strictMode = {strict_mode};

        function containsAny(text, terms) {{
            const lower = text.toLowerCase();
            return terms.some(t => lower.includes(t.toLowerCase()));
        }}

        function isExcludedAuthor(author) {{
            return excludeAuthors.some(a => author.trim() === a.trim());
        }}

        const results = [];
        const added = new Set();      // post IDs already in results
        const addedTexts = new Set(); // normalized text snippets (dedup same post with diff IDs)
        const groupId = (window.location.pathname.match(/\/groups\/([0-9]+)/) || [])[1] || '';

        function textKey(t) {{
            // First 80 chars, whitespace-collapsed — enough to identify duplicates
            return t.replace(/\\s+/g, ' ').substring(0, 80);
        }}

        function isArticleShare(text) {{
            // Shared articles/infographics often have separator lines (______) as decoration
            return /_{6,}/.test(text);
        }}

        // Strategy 1: find posts via /posts/ links → walk up to find message element
        const postLinks = document.querySelectorAll('a[href*="/posts/"]');

        for (const link of postLinks) {{
            const href = link.href || '';
            const match = href.match(/\\/posts\\/(\\d+)/);
            if (!match) continue;
            const postId = match[1];
            if (added.has(postId)) continue;

            // Skip posts from other groups
            if (groupId && !href.includes('/groups/' + groupId + '/')) continue;

            let article = link.closest('div[role="article"]') || link.closest('div[data-pagelet]');
            if (!article) article = link.parentElement;
            while (article && !article.querySelector('div[data-ad-comet-preview="message"]')) {{
                article = article.parentElement;
                if (!article || article === document.body) {{ article = null; break; }}
            }}
            if (!article) continue;

            const msgEl = article.querySelector('div[data-ad-comet-preview="message"]');
            const text = msgEl ? msgEl.innerText.trim() : '';
            if (text.length < 20) continue;

            const key = textKey(text);
            if (addedTexts.has(key)) continue;

            if (isArticleShare(text)) continue;

            const headings = article.querySelectorAll('h3, h2');
            const author = headings.length > 0 ? headings[0].innerText.trim() : 'Unknown';

            if (isExcludedAuthor(author)) continue;

            const timeLinks = article.querySelectorAll('a[href*="__cft__"], a[href*="story_fbid"]');
            let timestamp = '';
            for (const tl of timeLinks) {{
                const t = tl.innerText.trim();
                if (t && /^\\d+\\s*[mhdw]$/.test(t)) {{
                    timestamp = t;
                    break;
                }}
            }}

            const cleanUrl = href.split('?')[0];

            if (containsAny(text, excludeTerms)) continue;
            if (!strictMode || (containsAny(text, questionMarkers) && containsAny(text, accountingTerms))) {{
                added.add(postId);
                addedTexts.add(key);
                results.push({{ id: postId, author, text: text.substring(0, 500), url: cleanUrl, timestamp }});
            }}
        }}

        // Strategy 2: find posts via feed children that have message elements
        // (fallback when /posts/ links not available)
        const feed = document.querySelector('[role="feed"]');
        if (feed) {{
            for (const child of feed.children) {{
                const msgEl = child.querySelector('div[data-ad-comet-preview="message"]');
                if (!msgEl) continue;
                const text = msgEl.innerText.trim();
                if (text.length < 20) continue;

                const key = textKey(text);
                if (addedTexts.has(key)) continue;  // same text seen under a different ID already

                if (isArticleShare(text)) continue;

                // Try to find post ID — check all links in this child AND parent elements
                let postId = null;
                let postUrl = '';

                function extractIdFromHref(h) {{
                    return h.match(/\\/posts\\/(\\d+)/) ||
                           h.match(/story_fbid=(\\d+)/) ||
                           h.match(/permalink\\/(\\d+)/) ||
                           h.match(/pcb\\.([0-9]{{10,}})/) ||
                           h.match(/fbid=([0-9]{{10,}})/);
                }}

                // Search in the child itself — prefer links pointing to OUR group
                for (const a of child.querySelectorAll('a[href]')) {{
                    const h = a.href || '';
                    if (!h.includes('/groups/' + groupId + '/')) continue;  // skip other groups
                    const m = extractIdFromHref(h);
                    if (m) {{
                        postId = m[1];
                        postUrl = h.includes('/posts/') ? h.split('?')[0] :
                                  `https://www.facebook.com/groups/${{groupId}}/posts/${{postId}}/`;
                        break;
                    }}
                }}

                // Fallback: any link in child (may be from another group — will be validated below)
                if (!postId) {{
                    for (const a of child.querySelectorAll('a[href]')) {{
                        const h = a.href || '';
                        const m = extractIdFromHref(h);
                        if (m) {{
                            postId = m[1];
                            postUrl = h.includes('/posts/') ? h.split('?')[0] :
                                      `https://www.facebook.com/groups/${{groupId}}/posts/${{postId}}/`;
                            break;
                        }}
                    }}
                }}

                // Search in parent elements (up to 5 levels)
                if (!postId) {{
                    let el = child.parentElement;
                    for (let k = 0; k < 5 && el && el !== document.body; k++, el = el.parentElement) {{
                        for (const a of el.querySelectorAll('a[href*="/posts/"], a[href*="pcb."]')) {{
                            const h = a.href || '';
                            const m = extractIdFromHref(h);
                            if (m) {{
                                postId = m[1];
                                postUrl = h.includes('/posts/') ? h.split('?')[0] :
                                          `https://www.facebook.com/groups/${{groupId}}/posts/${{postId}}/`;
                                break;
                            }}
                        }}
                        if (postId) break;
                    }}
                }}

                // Skip if URL points to a different group
                if (postUrl && groupId && !postUrl.includes('/groups/' + groupId + '/')) continue;

                // Fallback: synthetic ID from text hash (no URL available)
                if (!postId) {{
                    const syntheticId = 'syn_' + btoa(encodeURIComponent(text.substring(0, 60))).replace(/[^a-zA-Z0-9]/g, '').substring(0, 24);
                    postId = syntheticId;
                }}

                if (added.has(postId)) continue;

                const headings = child.querySelectorAll('h3, h2');
                const author = headings.length > 0 ? headings[0].innerText.trim() : 'Unknown';

                if (isExcludedAuthor(author)) continue;

                if (containsAny(text, excludeTerms)) continue;
                if (!strictMode || (containsAny(text, questionMarkers) && containsAny(text, accountingTerms))) {{
                    added.add(postId);
                    addedTexts.add(key);
                    results.push({{ id: postId, author, text: text.substring(0, 500), url: postUrl, timestamp: '' }});
                }}
            }}
        }}

        return results;
    }}"""


def set_feed_to_recent(page):
    """Click 'sort group feed by New posts' button to sort feed newest-first."""
    try:
        btn = page.get_by_role("button", name="sort group feed by New posts").first
        if btn.is_visible(timeout=4000):
            btn.click()
            print("  Feed sorted: New posts", file=sys.stderr)
            time.sleep(2)
        else:
            print("  Feed sort button not visible — feed may already be sorted or button label changed", file=sys.stderr)
    except Exception as e:
        print(f"  Feed sort skipped: {e}", file=sys.stderr)


ORBIT_ADVISORY_NAME = "Orbit Advisory"


def check_active_profile(page):
    """Return the active Facebook profile name, or None if can't detect."""
    try:
        name = page.evaluate("""() => {
            // Look for profile name in the top navigation
            const profileBtn = document.querySelector('[aria-label*="profile"], [data-testid="blue_bar_profile_link"]');
            if (profileBtn) return profileBtn.getAttribute('aria-label') || profileBtn.innerText || null;

            // Look for the account name in the nav bar (usually appears as a link near top right)
            const navLinks = document.querySelectorAll('a[role="link"]');
            for (const l of navLinks) {
                const text = (l.innerText || '').trim();
                if (text && text.length > 2 && text.length < 60 && !text.includes('\\n')) {
                    // Skip generic nav items
                    if (!['Home', 'Watch', 'Marketplace', 'Groups', 'Gaming', 'Profile'].includes(text)) {
                        return text;
                    }
                }
            }
            return null;
        }""")
        return name
    except Exception:
        return None


def extract_posts(group_url, profile_path, keywords_path, processed_ids_path, num_scrolls=50, filter_mode="loose"):
    keywords = load_keywords(keywords_path)
    processed_ids = load_processed_ids(processed_ids_path)

    # Check if Chrome with our profile is already running
    import socket
    already_running = False
    try:
        s = socket.create_connection(("localhost", CDP_PORT), timeout=1)
        s.close()
        already_running = True
    except (ConnectionRefusedError, OSError):
        pass

    if already_running:
        print("Chrome already running — connecting to existing session...", file=sys.stderr)
        chrome_proc = None
    else:
        print("Launching Chrome (no automation flags)...", file=sys.stderr)
        chrome_proc = launch_chrome(profile_path)

    try:
        with sync_playwright() as p:
            print(f"Connecting to Chrome via CDP on port {CDP_PORT}...", file=sys.stderr)
            browser = p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")

            # Use existing context or create new page
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                pages = context.pages
                page = pages[0] if pages else context.new_page()
            else:
                context = browser.new_context()
                page = context.new_page()

            # Navigate directly to the group — check login + profile in one step
            print(f"Navigating to group...", file=sys.stderr)
            page.goto(group_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            current_url = page.url
            title = page.title()

            # Handle login redirect
            if "login" in current_url or "login" in title.lower() or "log in" in title.lower():
                print(
                    "\n⚠ Not logged in. Please log in to Facebook in the Chrome window.",
                    file=sys.stderr,
                )
                print("Press Enter here when you are logged in and on the group page: ", end="")
                sys.stdout.flush()
                input()
                page.goto(group_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

            # Check active profile via "Comment as [name]" on the group page
            # This is the definitive test — it reflects how posts will be attributed
            print("Checking active profile...", file=sys.stderr)
            time.sleep(2)
            comment_as = page.evaluate("""() => {
                // Only look for 'Comment as X' — specific enough to identify the active profile.
                // Ignore 'Write something...' — that's a textarea placeholder, not a profile indicator.
                const all = document.querySelectorAll('[aria-label]');
                for (const el of all) {
                    const label = el.getAttribute('aria-label') || '';
                    if (label.toLowerCase().startsWith('comment as ')) {
                        return label;
                    }
                }
                // Fallback: text nodes starting with 'Comment as '
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                let node;
                while (node = walker.nextNode()) {
                    const t = node.textContent.trim();
                    if (t.startsWith('Comment as ')) {
                        return t;
                    }
                }
                return null;
            }""")

            print(f"  Profile context: {comment_as or '(not detected — assuming Orbit Advisory)'}", file=sys.stderr)

            # Only warn when we explicitly detect a different profile name.
            # If comment_as is None, we couldn't read it — don't interrupt the scan.
            if comment_as and ORBIT_ADVISORY_NAME.lower() not in comment_as.lower():
                print(
                    f"\n⚠ Active profile is NOT Orbit Advisory (detected: '{comment_as}').",
                    file=sys.stderr,
                )
                print(
                    "  Please switch: click your profile picture (top right) → Orbit Advisory.",
                    file=sys.stderr,
                )
                print("Press Enter here when switched to Orbit Advisory: ", end="")
                sys.stdout.flush()
                input()
                time.sleep(2)

            print("Waiting for feed to load...", file=sys.stderr)
            # Wait for the feed element to appear (confirms we're on the group page)
            try:
                page.wait_for_selector('[role="feed"]', timeout=20000)
            except Exception:
                pass  # Proceed anyway — feed may load with a different structure
            time.sleep(3)

            # Set feed to Recent Activity (newest posts first)
            print("Setting feed sort to Recent Activity...", file=sys.stderr)
            set_feed_to_recent(page)

            # Scroll and collect incrementally — Facebook unloads text content as you scroll past,
            # so we must capture posts at each scroll position, not just at the end.
            print(f"Scrolling and collecting posts (filter_mode={filter_mode})...", file=sys.stderr)
            js_filter = build_js_filter(keywords, filter_mode)
            accumulated = {}  # post_id → post dict (dedup across scroll positions)

            for i in range(num_scrolls):
                try:
                    batch = page.evaluate(js_filter)
                    for post in (batch or []):
                        pid = post.get("id", "")
                        if pid and pid not in accumulated:
                            accumulated[pid] = post
                    diag = page.evaluate("""() => ({
                        feedChildren: (document.querySelector('[role="feed"]') || {children:[]}).children.length,
                        msgEls: document.querySelectorAll('div[data-ad-comet-preview="message"]').length,
                    })""")
                    print(
                        f"  Scroll {i+1}/{num_scrolls}: feedChildren={diag['feedChildren']} "
                        f"msgEls={diag['msgEls']} accumulated={len(accumulated)}",
                        file=sys.stderr,
                    )
                    page.evaluate("() => window.scrollBy(0, 1500)")
                    time.sleep(2)
                except Exception as e:
                    time.sleep(3)
                    try:
                        page.evaluate("() => window.scrollBy(0, 1500)")
                        time.sleep(2)
                    except Exception:
                        break

            candidates_raw = list(accumulated.values())

            # Just exit — don't close Chrome. It keeps running and flushes cookies to disk.
    finally:
        pass  # Chrome stays running after script exits (session saved)

    candidates = candidates_raw if isinstance(candidates_raw, list) else []
    new_candidates = [c for c in candidates if c["id"] not in processed_ids]

    print(
        f"Found {len(candidates)} raw matches, {len(new_candidates)} new after dedup",
        file=sys.stderr,
    )
    return new_candidates


def main():
    if len(sys.argv) not in (5, 6, 7):
        print(
            "Usage: python3 extract_posts.py <group_url> <profile_path> <keywords_path> <processed_ids_path> [num_scrolls] [filter_mode]",
            file=sys.stderr,
        )
        print("  filter_mode: 'strict' (default) or 'loose' (exclude_terms only, for diagnostics)", file=sys.stderr)
        sys.exit(1)

    group_url, profile_path, keywords_path, processed_ids_path = sys.argv[1:5]
    num_scrolls = int(sys.argv[5]) if len(sys.argv) >= 6 else 50
    filter_mode = sys.argv[6] if len(sys.argv) == 7 else "loose"

    try:
        candidates = extract_posts(group_url, profile_path, keywords_path, processed_ids_path, num_scrolls, filter_mode)
        print(json.dumps(candidates, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
