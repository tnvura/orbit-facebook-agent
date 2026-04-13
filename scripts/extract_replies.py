#!/usr/bin/env python3
"""
extract_replies.py — Facebook Post Reply Extractor

Connects to Chrome via CDP (same session as extract_posts.py), navigates to a
single post URL, expands all comments, and extracts replies via JS eval.
Zero LLM tokens.

Usage:
  python3 scripts/extract_replies.py <post_url> <profile_path>

Output:
  JSON array to stdout — each item: {author, text, timestamp}

Exit codes:
  0 — success (even if 0 replies found)
  1 — error
"""

import json
import os
import socket
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CDP_PORT = 9223


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
    time.sleep(4)
    return process


def expand_comments(page):
    """
    Click all 'View more comments' and 'See more' buttons until none remain.
    Runs up to 20 expansion rounds to handle deeply nested threads.
    """
    for round_num in range(20):
        expanded = page.evaluate("""() => {
            let clicked = 0;

            // Expand 'View more comments' / 'View N more comments' buttons
            const allRoles = document.querySelectorAll('[role="button"]');
            for (const btn of allRoles) {
                const text = (btn.innerText || btn.textContent || '').trim().toLowerCase();
                if (
                    text.startsWith('view more comments') ||
                    text.startsWith('view') && text.includes('more comment') ||
                    text === 'view previous comments'
                ) {
                    btn.click();
                    clicked++;
                }
            }

            // Expand 'See more' on truncated comment text
            const seeMoreLinks = document.querySelectorAll('[role="button"]');
            for (const el of seeMoreLinks) {
                const text = (el.innerText || '').trim().toLowerCase();
                if (text === 'see more') {
                    el.click();
                    clicked++;
                }
            }

            return clicked;
        }""")

        if expanded == 0:
            print(f"  Expand round {round_num + 1}: nothing left to expand", file=sys.stderr)
            break

        print(f"  Expand round {round_num + 1}: clicked {expanded} buttons", file=sys.stderr)
        time.sleep(2)


JS_EXTRACT_REPLIES = """() => {
    const results = [];
    const seen = new Set();

    // Comments live in article elements that are NOT the main post article.
    // The main post is typically the first [role="article"], comments follow.
    const articles = Array.from(document.querySelectorAll('[role="article"]'));

    // Skip the first article (the post itself) — comments start from index 1
    const commentArticles = articles.slice(1);

    for (const article of commentArticles) {
        // Author: first link that looks like a person's name (not a page name or timestamp)
        let author = '';
        const links = article.querySelectorAll('a[role="link"]');
        for (const link of links) {
            const text = (link.innerText || '').trim();
            // Skip empty, very long, or numeric-only strings
            if (text && text.length > 1 && text.length < 80 && !/^\\d+$/.test(text)) {
                author = text;
                break;
            }
        }

        // Text: find the comment body — typically a div or span with dir="auto"
        // Exclude author name, timestamps, reaction counts
        let text = '';
        const textEls = article.querySelectorAll('[dir="auto"]');
        for (const el of textEls) {
            const t = (el.innerText || '').trim();
            // Skip very short strings (likely reactions or single emojis)
            // Skip the author name if it appears as a text node
            if (t.length > 5 && t !== author) {
                text = t;
                break;
            }
        }

        // Timestamp: look for relative time strings (e.g. "2h", "1d", "5 minutes")
        let timestamp = '';
        const timeEl = article.querySelector('a[href*="comment_id"], abbr[data-utime]');
        if (timeEl) {
            timestamp = (timeEl.innerText || timeEl.getAttribute('title') || '').trim();
        }
        if (!timestamp) {
            // Fallback: scan for short time strings in all text nodes
            const walker = document.createTreeWalker(article, NodeFilter.SHOW_TEXT);
            let node;
            while (node = walker.nextNode()) {
                const t = node.textContent.trim();
                if (/^\\d+\\s*(s|m|h|d|w|min|sec|hour|day|week)/.test(t.toLowerCase())) {
                    timestamp = t;
                    break;
                }
            }
        }

        if (!author && !text) continue;

        // Dedup by author + first 60 chars of text
        const key = `${author}::${text.substring(0, 60)}`;
        if (seen.has(key)) continue;
        seen.add(key);

        results.push({ author, text, timestamp });
    }

    return results;
}"""


def extract_replies(post_url, profile_path):
    # Check if Chrome is already running on CDP port
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

    replies = []

    try:
        with sync_playwright() as p:
            print(f"Connecting to Chrome via CDP on port {CDP_PORT}...", file=sys.stderr)
            browser = p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")

            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                pages = context.pages
                page = pages[0] if pages else context.new_page()
            else:
                context = browser.new_context()
                page = context.new_page()

            print(f"Navigating to post: {post_url}", file=sys.stderr)
            page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            # Handle login redirect
            current_url = page.url
            title = page.title()
            if "login" in current_url or "login" in title.lower():
                print(
                    "\n⚠ Not logged in. Please log in in the Chrome window.",
                    file=sys.stderr,
                )
                print("Press Enter when logged in and on the post page: ", end="")
                sys.stdout.flush()
                input()
                page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

            # Wait for comments section to load
            print("Waiting for comments to load...", file=sys.stderr)
            try:
                page.wait_for_selector('[role="article"]', timeout=15000)
            except Exception:
                pass
            time.sleep(2)

            # Count articles before expansion
            initial_count = page.evaluate(
                "() => document.querySelectorAll('[role=\"article\"]').length"
            )
            print(f"  Articles before expansion: {initial_count}", file=sys.stderr)

            # Expand all comments and 'See more' truncations
            print("Expanding comments...", file=sys.stderr)
            expand_comments(page)

            # Count after expansion
            final_count = page.evaluate(
                "() => document.querySelectorAll('[role=\"article\"]').length"
            )
            print(f"  Articles after expansion: {final_count}", file=sys.stderr)

            # Extract replies via JS eval
            print("Extracting replies...", file=sys.stderr)
            replies = page.evaluate(JS_EXTRACT_REPLIES)
            print(f"  Extracted {len(replies)} replies", file=sys.stderr)

    finally:
        pass  # Chrome stays running

    return replies


def main():
    if len(sys.argv) not in (2, 3):
        print(
            "Usage: python3 extract_replies.py <post_url> [profile_path]",
            file=sys.stderr,
        )
        sys.exit(1)

    post_url = sys.argv[1]
    profile_path = (
        sys.argv[2]
        if len(sys.argv) == 3
        else os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".browser-profile",
        )
    )

    try:
        replies = extract_replies(post_url, profile_path)
        print(json.dumps(replies, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
