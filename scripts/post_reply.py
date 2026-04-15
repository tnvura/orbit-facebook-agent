#!/usr/bin/env python3
"""
post_reply.py — Post a reply comment to a Facebook group post as Orbit Advisory

Connects to Chrome via CDP (same session as other scripts), navigates to the
post URL, verifies the active profile is Orbit Advisory, types the reply, and
submits. Newlines in the reply text are sent as Shift+Enter (Facebook's in-comment
line break), with Enter at the end to submit.

Usage:
  python3 scripts/post_reply.py <post_url> <draft_path> <profile_path>

Arguments:
  post_url     URL of the Facebook post to comment on
  draft_path   Path to draft .md file — body text extracted (frontmatter stripped)
  profile_path Path to Chrome user-data-dir

Output:
  Status messages to stderr.

Exit codes:
  0 — comment posted successfully
  1 — error (browser, navigation, comment box not found, etc.)
  2 — wrong profile active (not Orbit Advisory) — nothing was posted
"""

import os
import socket
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CDP_PORT = 9223
ORBIT_ADVISORY_NAME = "Orbit Advisory"

# Selectors tried in order to find the comment textarea
COMMENT_BOX_SELECTORS = [
    'div[role="textbox"][aria-label*="comment" i]',
    'div[role="textbox"][aria-placeholder*="comment" i]',
    'div[role="textbox"][aria-label*="Write" i]',
    'div[data-lexical-editor="true"]',
    'div[role="textbox"]',
]


def read_draft_body(draft_path):
    """Read reply text from draft .md file, stripping YAML frontmatter."""
    with open(draft_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Strip YAML frontmatter delimited by --- ... ---
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3:].strip()
    return content.strip()


def chrome_is_running():
    """Return True if Chrome CDP port is already open."""
    try:
        s = socket.create_connection(("localhost", CDP_PORT), timeout=1)
        s.close()
        return True
    except (ConnectionRefusedError, OSError):
        return False


def launch_chrome(profile_path):
    abs_profile = os.path.abspath(profile_path)
    subprocess.Popen(
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
    time.sleep(4)


def check_profile(page):
    """
    Return the active 'Comment as X' name, or None if not detectable.
    Facebook shows this in the comment box area on a post page.
    """
    try:
        return page.evaluate("""() => {
            // Facebook uses 'Comment as X' on feed and 'Answer as X' on post pages
            const prefixes = ['comment as ', 'answer as ', 'reply as '];
            for (const el of document.querySelectorAll('[aria-label]')) {
                const label = (el.getAttribute('aria-label') || '').toLowerCase();
                for (const prefix of prefixes) {
                    if (label.startsWith(prefix)) {
                        return el.getAttribute('aria-label').substring(prefix.length).trim();
                    }
                }
            }
            // Fallback: text nodes
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let node;
            while (node = walker.nextNode()) {
                const t = node.textContent.trim().toLowerCase();
                for (const prefix of prefixes) {
                    if (t.startsWith(prefix)) {
                        return node.textContent.trim().substring(prefix.length).trim();
                    }
                }
            }
            return null;
        }""")
    except Exception:
        return None


def find_comment_box(page):
    """Try each selector in order; return the first visible element found."""
    for selector in COMMENT_BOX_SELECTORS:
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=2000):
                return el
        except Exception:
            continue
    return None


def type_reply(page, textbox, text):
    """
    Click the comment box and type the reply.
    Uses Shift+Enter for in-comment line breaks, Enter at end to submit.
    """
    textbox.click()
    time.sleep(0.5)

    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line:
            page.keyboard.type(line, delay=30)
        if i < len(lines) - 1:
            page.keyboard.press("Shift+Enter")
            time.sleep(0.1)

    time.sleep(0.5)
    # Submit with Enter
    page.keyboard.press("Enter")


def verify_posted(page, timeout=8):
    """
    Wait for the comment box to clear — Facebook empties it after a successful post.
    Returns True if confirmed posted, False if box still has content after timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            box = find_comment_box(page)
            if box is None:
                time.sleep(0.5)
                continue
            content = box.inner_text()
            if not content.strip():
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python3 scripts/post_reply.py <post_url> <draft_path> <profile_path>",
            file=sys.stderr,
        )
        sys.exit(1)

    post_url, draft_path, profile_path = sys.argv[1], sys.argv[2], sys.argv[3]

    # Read draft body
    if not os.path.exists(draft_path):
        print(f"Error: draft file not found: {draft_path}", file=sys.stderr)
        sys.exit(1)

    reply_text = read_draft_body(draft_path)
    if not reply_text:
        print("Error: draft file has no body text after frontmatter.", file=sys.stderr)
        sys.exit(1)

    print(f"Reply text loaded ({len(reply_text)} chars)", file=sys.stderr)

    # Connect to Chrome
    if chrome_is_running():
        print("Connecting to existing Chrome session...", file=sys.stderr)
    else:
        print("Launching Chrome...", file=sys.stderr)
        launch_chrome(profile_path)

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
            contexts = browser.contexts
            context = contexts[0] if contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()

            # Navigate to post
            print(f"Navigating to post: {post_url}", file=sys.stderr)
            page.goto(post_url, wait_until="domcontentloaded", timeout=30000)

            # Wait for post article to render (same pattern as extract_replies.py)
            print("Waiting for post to load...", file=sys.stderr)
            try:
                page.wait_for_selector('[role="article"]', timeout=15000)
            except Exception:
                pass
            time.sleep(3)

            # Scroll down to expose the comment section
            print("Scrolling to comment section...", file=sys.stderr)
            page.evaluate("() => window.scrollBy(0, 600)")
            time.sleep(2)

            # Profile safety check — attempt after full load
            print("Checking active profile...", file=sys.stderr)
            active_profile = check_profile(page)
            if active_profile is not None:
                print(f"  Active profile: {active_profile}", file=sys.stderr)
                if ORBIT_ADVISORY_NAME.lower() not in active_profile.lower():
                    print(
                        f"\nWrong profile active: '{active_profile}'.\n"
                        f"Please switch to Orbit Advisory in Chrome before retrying.",
                        file=sys.stderr,
                    )
                    sys.exit(2)
            else:
                print(
                    "  Profile not detected — proceeding (could not confirm Orbit Advisory).",
                    file=sys.stderr,
                )

            # Find comment box — try Playwright locators first
            print("Looking for comment box...", file=sys.stderr)
            textbox = find_comment_box(page)

            if textbox is None:
                # Activate comment area via JS click on any textbox/contenteditable
                print(
                    "  Not found via locators — trying JS-based activation...",
                    file=sys.stderr,
                )
                activated = page.evaluate("""() => {
                    const candidates = [
                        ...document.querySelectorAll('[role="textbox"]'),
                        ...document.querySelectorAll('[contenteditable="true"]'),
                    ];
                    for (const el of candidates) {
                        const label = (el.getAttribute('aria-label') || '').toLowerCase();
                        const placeholder = (el.getAttribute('aria-placeholder') || '').toLowerCase();
                        if (
                            label.includes('comment') || placeholder.includes('comment') ||
                            label.includes('ความคิดเห็น') || placeholder.includes('ความคิดเห็น')
                        ) {
                            el.click();
                            el.focus();
                            return true;
                        }
                    }
                    // Fallback: click the first contenteditable that is not the post itself
                    if (candidates.length > 0) {
                        candidates[0].click();
                        candidates[0].focus();
                        return true;
                    }
                    return false;
                }""")
                time.sleep(1)
                if activated:
                    textbox = find_comment_box(page)

            if textbox is None:
                # Last resort: click the Comment button to open the reply area
                print(
                    "  Trying Comment button as last resort...",
                    file=sys.stderr,
                )
                try:
                    comment_btn = page.get_by_role("button", name="Comment").first
                    if comment_btn.is_visible(timeout=4000):
                        comment_btn.click()
                        time.sleep(2)
                        textbox = find_comment_box(page)
                except Exception:
                    pass

            if textbox is None:
                print("Error: could not find comment box after all attempts.", file=sys.stderr)
                sys.exit(1)

            print("Comment box found. Typing reply...", file=sys.stderr)
            type_reply(page, textbox, reply_text)

            print("Reply submitted. Verifying...", file=sys.stderr)
            if verify_posted(page):
                print("Posted successfully.", file=sys.stderr)
            else:
                print(
                    "Warning: could not confirm post — comment box did not clear. "
                    "Check Facebook manually.",
                    file=sys.stderr,
                )
                sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
