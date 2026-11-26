#!/usr/bin/env python3
"""evidence_check.py -- P-EVIDENCE-VOLATILE (FABLE-FLOW-0847 A15).  REPORT ONLY.

A review record (REVIEW / GOOD / ISSUES / BAD / RESULT post, geom note) must cite evidence that outlives the session: a file under the hub
(~/coord, intel2 /srv/opentallas-scratch2) with its sha.  Flags every cited path under /tmp, /var/tmp, a user's ~/tmp or a localhost scratchpad,
and (with --exists) a hub path that is not on this host.  `sha` = a 12+ hex token on the same line.

    evidence_check.py --posts lanes/posts --since "2026-11-26 00:00" [--tags REVIEW,GOOD,ISSUES,BAD,RESULT] [--exists]
"""
import argparse
import os
import re
import sys

STAMP = re.compile(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+(?:P[SD]T\s+)?([A-Z][A-Z0-9-]+)\b")
PATH = re.compile(r"(?<![\w./-])(/(?:tmp|var/tmp|home|srv|mnt)[\w./@+=,-]*)")
SHA = re.compile(r"\b[0-9a-f]{12,64}\b")
VOLATILE = re.compile(r"^(/tmp/|/var/tmp/|/home/[^/]+/(?:tmp|\.claude)/|/home/[^/]+/OpenTallas/)")
DURABLE = re.compile(r"^(/srv/opentallas-scratch\d?/|/home/[^/]+/coord/|/home/[^/]+/wt/)")


def classify(path):
    if VOLATILE.match(path):
        return "VOLATILE"
    return "OK" if DURABLE.match(path) else "UNKNOWN"


def scan_line(line, exists=False):
    out = []
    has_sha = bool(SHA.search(line))
    for p in PATH.findall(line):
        p = p.rstrip(".,;:)")
        c = classify(p)
        if c == "OK" and exists and not os.path.exists(p):
            c = "MISSING"
        out.append((p, c, has_sha))
    return out


def scan_posts(posts_dir, since, tags, exists=False):
    rows = []
    for fn in sorted(os.listdir(posts_dir)):
        if not fn.endswith(".md"):
            continue
        with open(os.path.join(posts_dir, fn), errors="replace") as fh:
            for ln in fh:
                m = STAMP.match(ln)
                if not m or m.group(1) < since or (tags and m.group(2) not in tags):
                    continue
                for p, c, s in scan_line(ln, exists):
                    if c != "OK" or not s:
                        rows.append((fn[:-3], m.group(1), m.group(2), c if c != "OK" else "NO-SHA", p))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--posts", required=True)
    ap.add_argument("--since", required=True)
    ap.add_argument("--tags", default="REVIEW,GOOD,ISSUES,BAD,RESULT,REVIEW-1")
    ap.add_argument("--exists", action="store_true")
    a = ap.parse_args(argv)
    rows = scan_posts(a.posts, a.since, set(a.tags.split(",")), a.exists)
    print("lane\tstamp\ttag\tfinding\tpath")
    for r in rows:
        print("\t".join(r))
    print(f"# {len(rows)} findings", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
