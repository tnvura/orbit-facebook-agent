#!/usr/bin/env python3
"""
list_open_candidates.py — List unresearched Facebook post candidates / skip a candidate

Collects candidates from ALL tracking/scan-results-*.json files, deduplicates
by post_id (newest scan wins), filters out candidates that already have a draft
in tracking/drafts/ or a skip record in tracking/skipped/, and outputs the
remaining open candidates re-numbered sequentially starting from 1.

Usage:
  python3 scripts/list_open_candidates.py [--tracking-dir <path>]
  python3 scripts/list_open_candidates.py --skip <number> [--reason <text>] [--tracking-dir <path>]

Options:
  --skip <number>  Skip the candidate at position <number> in the open list
  --reason <text>  Optional reason for skipping (recorded in the skip file)
  --tracking-dir   Path to tracking directory (default: tracking/)

Output (list mode):
  JSON array to stdout — each item: {number, id, author, text, url,
                                      timestamp, topic, priority, notes, scan_date}
  Summary line to stderr.

Output (skip mode):
  Confirmation line to stderr.
  Updated open list JSON to stdout (same format as list mode, skip removed).

Exit codes:
  0 — success (even if 0 open candidates)
  1 — error (missing dir, malformed JSON, invalid number, etc.)
  2 — no scan-results files found
"""

import glob
import json
import os
import sys
from datetime import date, datetime


STALE_DAYS = 7  # warn if most recent scan is older than this


def find_scan_files(tracking_dir):
    """Return all scan-results-*.json paths sorted oldest → newest."""
    pattern = os.path.join(tracking_dir, "scan-results-*.json")
    files = sorted(glob.glob(pattern))  # YYYY-MM-DD lexicographic sort = chronological
    return files


def parse_scan_date(filepath):
    """Extract date from filename like scan-results-2026-04-14.json."""
    basename = os.path.basename(filepath)
    name = basename.replace("scan-results-", "").replace(".json", "")
    try:
        return datetime.strptime(name, "%Y-%m-%d").date()
    except ValueError:
        return None


def load_all_candidates(scan_files):
    """
    Load candidates from all scan files.
    Oldest files processed first — newest scan wins on duplicate post_id.
    Returns (candidates_by_id dict, most_recent_date).
    """
    candidates_by_id = {}
    most_recent_date = None

    for filepath in scan_files:
        scan_date = parse_scan_date(filepath)
        if scan_date and (most_recent_date is None or scan_date > most_recent_date):
            most_recent_date = scan_date

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: could not read {filepath}: {e}", file=sys.stderr)
            continue

        candidates = data.get("candidates", [])
        if not isinstance(candidates, list):
            print(f"Warning: 'candidates' is not a list in {filepath}", file=sys.stderr)
            continue

        scan_date_str = str(scan_date) if scan_date else os.path.basename(filepath)

        for candidate in candidates:
            post_id = candidate.get("id")
            if not post_id:
                continue
            entry = dict(candidate)
            entry["scan_date"] = scan_date_str
            candidates_by_id[post_id] = entry

    return candidates_by_id, most_recent_date


def filter_open(candidates_by_id, drafts_dir, skipped_dir):
    """
    Return candidates that have neither a draft nor a skip record.
    Uses os.path.exists per candidate — O(1) per check regardless of
    total files in either directory.
    """
    open_candidates = []
    for post_id, candidate in candidates_by_id.items():
        if os.path.exists(os.path.join(drafts_dir, f"{post_id}.md")):
            continue
        if os.path.exists(os.path.join(skipped_dir, f"{post_id}.md")):
            continue
        open_candidates.append(candidate)
    return open_candidates


def renumber(candidates):
    """Assign sequential number field starting from 1, sorted by scan_date then original number."""
    def sort_key(c):
        return (c.get("scan_date", ""), c.get("number", 0))

    sorted_candidates = sorted(candidates, key=sort_key)
    for i, candidate in enumerate(sorted_candidates, start=1):
        candidate["number"] = i
    return sorted_candidates


def write_skip_file(skipped_dir, candidate, reason):
    """Create tracking/skipped/{post_id}.md to mark a candidate as skipped."""
    os.makedirs(skipped_dir, exist_ok=True)
    post_id = candidate["id"]
    skip_path = os.path.join(skipped_dir, f"{post_id}.md")
    content = (
        f"---\n"
        f"post_id: \"{post_id}\"\n"
        f"author: \"{candidate.get('author', '')}\"\n"
        f"scan_date: \"{candidate.get('scan_date', '')}\"\n"
        f"skipped: \"{date.today()}\"\n"
        f"reason: \"{reason}\"\n"
        f"---\n"
    )
    with open(skip_path, "w", encoding="utf-8") as f:
        f.write(content)
    return skip_path


def build_open_list(tracking_dir):
    """Full pipeline: load → merge → filter → renumber. Returns (open_candidates, total, most_recent_date)."""
    scan_files = find_scan_files(tracking_dir)
    if not scan_files:
        return None, 0, None

    print(f"Found {len(scan_files)} scan file(s):", file=sys.stderr)
    for f in scan_files:
        print(f"  {os.path.basename(f)}", file=sys.stderr)

    candidates_by_id, most_recent_date = load_all_candidates(scan_files)
    total_candidates = len(candidates_by_id)

    drafts_dir = os.path.join(tracking_dir, "drafts")
    skipped_dir = os.path.join(tracking_dir, "skipped")

    # Treat missing directories as empty — no drafts/skips yet
    if not os.path.isdir(drafts_dir) and not os.path.isdir(skipped_dir):
        open_candidates = list(candidates_by_id.values())
    else:
        open_candidates = filter_open(candidates_by_id, drafts_dir, skipped_dir)

    open_candidates = renumber(open_candidates)
    return open_candidates, total_candidates, most_recent_date


def print_summary(open_candidates, total_candidates, most_recent_date):
    drafted_or_skipped = total_candidates - len(open_candidates)
    print(
        f"Total unique candidates: {total_candidates} | "
        f"Drafted/Skipped: {drafted_or_skipped} | "
        f"Open: {len(open_candidates)}",
        file=sys.stderr,
    )
    if most_recent_date:
        age_days = (date.today() - most_recent_date).days
        if age_days > STALE_DAYS:
            print(
                f"Warning: most recent scan is {age_days} days old ({most_recent_date}). "
                f"Consider running /fb-scan for fresh candidates.",
                file=sys.stderr,
            )


def parse_args(argv):
    """Parse CLI arguments. Returns namespace dict."""
    args = argv[1:]
    result = {"tracking_dir": "tracking", "skip_number": None, "reason": ""}

    i = 0
    while i < len(args):
        if args[i] == "--tracking-dir":
            if i + 1 >= len(args):
                print("Error: --tracking-dir requires a path argument", file=sys.stderr)
                sys.exit(1)
            result["tracking_dir"] = args[i + 1]
            i += 2
        elif args[i] == "--skip":
            if i + 1 >= len(args):
                print("Error: --skip requires a number argument", file=sys.stderr)
                sys.exit(1)
            try:
                result["skip_number"] = int(args[i + 1])
            except ValueError:
                print(f"Error: --skip argument must be an integer, got '{args[i + 1]}'", file=sys.stderr)
                sys.exit(1)
            i += 2
        elif args[i] == "--reason":
            if i + 1 >= len(args):
                print("Error: --reason requires a text argument", file=sys.stderr)
                sys.exit(1)
            result["reason"] = args[i + 1]
            i += 2
        else:
            print(f"Error: unknown argument '{args[i]}'", file=sys.stderr)
            sys.exit(1)

    return result


def main():
    args = parse_args(sys.argv)
    tracking_dir = args["tracking_dir"]
    skip_number = args["skip_number"]
    reason = args["reason"]

    if not os.path.isdir(tracking_dir):
        print(f"Error: tracking directory not found: {tracking_dir}", file=sys.stderr)
        sys.exit(1)

    open_candidates, total_candidates, most_recent_date = build_open_list(tracking_dir)

    if open_candidates is None:
        print("No scan-results files found. Run /fb-scan first.", file=sys.stderr)
        sys.exit(2)

    if skip_number is not None:
        # --- Skip mode ---
        match = next((c for c in open_candidates if c["number"] == skip_number), None)
        if match is None:
            print(
                f"Error: no open candidate with number {skip_number}. "
                f"Valid range: 1–{len(open_candidates)}.",
                file=sys.stderr,
            )
            sys.exit(1)

        skipped_dir = os.path.join(tracking_dir, "skipped")
        skip_path = write_skip_file(skipped_dir, match, reason)
        print(
            f"Skipped: [{match['number']}] {match['author']} — {match['text'][:60]}...\n"
            f"  Recorded at: {skip_path}",
            file=sys.stderr,
        )

        # Rebuild open list so output reflects the skip just recorded
        open_candidates, total_candidates, most_recent_date = build_open_list(tracking_dir)

    print_summary(open_candidates, total_candidates, most_recent_date)
    print(json.dumps(open_candidates, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
