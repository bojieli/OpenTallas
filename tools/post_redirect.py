#!/usr/bin/env python3
"""POST-ROUTE-2200: redirect posts addressed to stood-down lanes to their successor chain.

lanes/LANE-STATUS.tsv columns: lane, status (live|stood-down|done), successor, updated, note (schema: tools/lane_status.py; written only by bin/stand-down.sh).
CLI: post_redirect.py [COORD_DIR] < text  -> rewritten text on stdout (header gets the live successor, a "[redirect]" line is appended), REDIRECTED notes on stderr.
     post_redirect.py --resolve NAME [COORD_DIR]  -> canonical lane spelling
     post_redirect.py --live NAME [COORD_DIR]     -> TAB: live lane at the end of NAME's stood-down chain (NAME itself when live/unknown/none) and the chain "A > B > C"
"""
import os
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
            # FLOW-PROC-B: tolerant read (a hand-typed row must still redirect): the status is its first word, the successor its first lane-name token;
            # "none" / an unparsable successor means nobody inherits.
            st = f[1].split()[0] if f[1].split() else ""
            m = NAME.match(f[2].strip())
            succ = m.group(0) if m and m.group(0) != "none" else ""
            out[f[0]] = (st, succ, f[3])
    except OSError:
        pass
    return out


def resolve_lane(name, status, posts_dir=None):
    """FLOW-FIX-0100 (FABLE-FLOW-2350 b): the ONE lane-name resolver.  Case-folded: the canonical spelling of `name` is, in order, a LANE-STATUS lane,
    an existing posts/<lane>.md file with the same folded name (a spelling that is not all lowercase first), else `name` as typed.
    post.sh (file name), ot-run / ot-wait DONE-DIED posts (they call post.sh) and the successor chain below all use it, so mixed-case twins of one
    lane cannot exist."""
    cf = name.casefold()
    if name in status:
        return name
    for k in status:
        if k.casefold() == cf:
            return k
    if posts_dir:
        try:
            names = [f[:-3] for f in os.listdir(posts_dir) if f.endswith(".md") and f[:-3].casefold() == cf]
        except OSError:
            names = []
        names.sort(key=lambda n: (n == n.lower(), n))
        if names:
            return names[0]
    return name


KNOWN = set()          # lane names with a posts/<lane>.md file (filled by known_lanes(); the CLI does it)
RNUM = re.compile(r"^(.*?)(?:-R(\d+))?$")


def known_lanes(coord):
    try:
        KNOWN.update(f[:-3] for f in os.listdir(os.path.join(coord, "lanes", "posts")) if f.endswith(".md"))
    except OSError:
        pass


def latest_r(lane, status):
    """S81-DIE-R5 11-21 (COORD): a successor that never got a stand-down row (S81-J6-ASSEMBLY-R4 -> R5) still wins: the highest BASE-R<n> above the
    lane's own number among LANE-STATUS lanes and posts files, else ''.  Successors are always numbered upward, so a higher number is the later lane."""
    base, n = RNUM.match(lane).groups()
    n = int(n or 0)
    best, bn = "", n
    for k in set(status) | KNOWN:
        m = re.match(re.escape(base) + r"-R(\d+)$", k)
        if m and int(m.group(1)) > bn:
            best, bn = k, int(m.group(1))
    return best


def resolve(lane, status, limit=10):
    """Follow stood-down chain; returns list of successors (may be empty).  At the end of the registered chain, a higher-numbered
    BASE-R<n> sibling (latest_r) continues it."""
    lane = resolve_lane(lane, status)
    chain, seen = [], {lane}
    cur = lane
    for _ in range(limit):
        st = status.get(cur)
        if st and st[0] == "stood-down" and st[1] and st[1] not in seen:
            nxt = st[1]
        elif not st or st[0] != "done":
            nxt = latest_r(cur, status) if (chain or (st and st[0] == "stood-down") or RNUM.match(cur).group(2)) else ""
            if not nxt or nxt in seen:
                break
            nst = status.get(nxt)      # COORD 11-22 (FAM-S81-COL-R5 reclaim): a higher-numbered lane that stood down BACK to a lane of this chain ends it
            if nst and nst[0] == "stood-down" and nst[1] in seen:
                break
        else:
            break
        cur = nxt
        seen.add(cur)
        chain.append(cur)
    return chain


def live_lane(name, status):
    """-> (live lane at the end of the stood-down chain, chain text); the lane itself when it is live, unknown, or stood down with no successor."""
    chain = resolve(name, status)
    base = resolve_lane(name, status)
    return (chain[-1] if chain else base), " > ".join([base] + chain)


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
    if len(sys.argv) >= 3 and sys.argv[1] == "--resolve":          # post_redirect.py --resolve NAME [COORD_DIR] -> canonical lane name
        _c = sys.argv[3] if len(sys.argv) > 3 else "/home/ubuntu/coord"
        print(resolve_lane(sys.argv[2], load_status(_c), os.path.join(_c, "lanes", "posts")))
        sys.exit(0)
    if len(sys.argv) >= 3 and sys.argv[1] == "--live":
        _c = sys.argv[3] if len(sys.argv) > 3 else "/home/ubuntu/coord"
        known_lanes(_c)
        print("%s\t%s" % live_lane(sys.argv[2], load_status(_c)))
        sys.exit(0)
    coord = sys.argv[1] if len(sys.argv) > 1 else "/home/ubuntu/coord"
    known_lanes(coord)
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
    if notes:                                   # FLOW-PROC-B: the post itself says it was redirected
        new = new + "\n" + "\n".join("  [redirect] " + n[len("REDIRECTED "):] for n in notes)
    sys.stdout.write(new + ("\n" if nl else ""))
