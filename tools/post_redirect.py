#!/usr/bin/env python3
"""POST-ROUTE-2200: redirect posts addressed to stood-down lanes to their successor chain.

lanes/LANE-STATUS.tsv columns: lane, status (live|stood-down), successor, updated.
CLI: post_redirect.py [COORD_DIR] < text  -> rewritten text on stdout, REDIRECTED notes on stderr.
"""
import re
import sys
from pathlib import Path

HDR = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9._-]*)\s*->\s*([^\]]*)\]")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def load_status(coord):
    p = Path(coord) / "lanes" / "LANE-STATUS.tsv"
    out = {}
    try:
        for ln in p.read_text().splitlines():
            if not ln.strip() or ln.startswith("#") or ln.startswith("lane\t"):
                continue
            f = ln.split("\t") + ["", "", "", ""]
            out[f[0]] = (f[1], f[2], f[3])
    except OSError:
        pass
    return out


def resolve(lane, status, limit=10):
    """Follow stood-down chain; returns list of successors (may be empty)."""
    chain, seen = [], {lane}
    cur = lane
    for _ in range(limit):
        st = status.get(cur)
        if not st or st[0] != "stood-down" or not st[1] or st[1] in seen:
            break
        cur = st[1]
        seen.add(cur)
        chain.append(cur)
    return chain


def addressees(text):
    m = HDR.search(text.split("\n", 1)[0])
    if not m:
        return None, []
    head = m.group(2).split(";", 1)[0]
    return m, NAME.findall(head)


def rewrite(text, status):
    """Add live successors of stood-down addressees to the first-line header."""
    first, _, rest = text.partition("\n")
    m, to = addressees(first)
    notes, add = [], []
    if not m:
        return text, notes
    for y in to:
        chain = resolve(y, status)
        if not chain:
            continue
        final = chain[-1]
        if final not in to and final not in add:
            add.append(final)
        notes.append("REDIRECTED %s -> %s (stood down; chain %s)" % (y, final, " > ".join([y] + chain)))
    if add:
        body = m.group(2)
        head, sep, tail = body.partition(";")
        head = head.rstrip() + ", " + ", ".join(add)
        newbody = head + (sep + tail if sep else "")
        first = first[: m.start(2)] + newbody + first[m.end(2):]
    return first + ("\n" + rest if rest or text.endswith("\n") and "\n" in text else ""), notes


if __name__ == "__main__":
    coord = sys.argv[1] if len(sys.argv) > 1 else "/home/ubuntu/coord"
    t = sys.stdin.read()
    nl = t.endswith("\n")
    t = t.rstrip("\n")
    try:
        new, notes = rewrite(t, load_status(coord))
    except Exception as e:  # never block a post
        new, notes = t, []
        print("post_redirect: skipped (%s)" % e, file=sys.stderr)
    for n in notes:
        print(n, file=sys.stderr)
    sys.stdout.write(new + ("\n" if nl else ""))
