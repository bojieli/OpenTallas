#!/usr/bin/env python3
"""waiter_fail_relay: a failed waiter result must reach its die owner in the same tick, not 1.5 h later
(PLAN-GATE-PRE-1115, ruling r196, FABLE-FLOW-1800 class 1: S81 G1d RESULT FAIL sat unread 1.5 h).

Hub script, run every 10 min by a timer.  Reads the queue (lanes/COORD-REVIEW-QUEUE.md), finds queue lines

    - <stamp> RESULT [LANE -> TO; cc ...] text         where the first 300 characters of text match
                                                        (did NOT pass|FAIL|REFUSE|Traceback)

and, for each new one, posts one line addressed to the poster (the die owner whose waiter wrote it), the addressees and COORD:

    NEEDS-ACTION [PLAN-GATE-PRE-1115 -> LANE, COORD; cc TO ...] WAITER-FAIL <hash12> (<stamp>) ...

Idempotent: a line is keyed by the sha256 of its text (the stamp included, so a re-posted identical result at a new time is a new
event); the key goes to the state file and to the posted line, and a line whose key is already in the queue is never posted again,
even with the state file lost.  Lines posted by this relay, by FABLE-* reviewers and by COORD are skipped (a review that quotes a
failure is not a waiter result).  On the first run (no state) only lines younger than --max-age-min are relayed; older lines are
recorded as seen.  A failed post is not recorded and is retried by the next run.

usage: waiter_fail_relay.py [--queue F] [--state F] [--post-sh F] [--max-age-min N] [--max-posts N] [--dry]
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
LANE = "PLAN-GATE-PRE-1115"
VERDICT = re.compile(r"did NOT pass|FAIL|REFUSE|Traceback")
LINE = re.compile(r"^- (?P<stamp>\d{4}-\d\d-\d\d [^\[]*?)\s*\bRESULT\s+\[(?P<lane>[A-Za-z0-9][A-Za-z0-9._-]*)\s*->\s*"
                  r"(?P<to>[^\];]*)(?:;\s*cc\s*(?P<cc>[^\]]*))?\]\s*(?P<text>.*)$")
SKIP_LANES = ("FABLE-", "COORD", LANE)
WINDOW = 300


def line_key(line):
    return hashlib.sha256(line.strip().encode()).hexdigest()[:12]


def stamp_age_min(stamp, now=None):
    """minutes since the line's stamp (America/Los_Angeles clock as post.sh writes it); None when unparsable (UTC-style stamps)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    m = re.match(r"(\d{4}-\d\d-\d\d) (\d\d):(\d\d) (PST|PDT)\b", stamp.strip())
    if not m:
        return None
    try:
        t = datetime.strptime(f"{m.group(1)} {m.group(2)}:{m.group(3)}", "%Y-%m-%d %H:%M").replace(
            tzinfo=ZoneInfo("America/Los_Angeles")).timestamp()
    except ValueError:
        return None
    return ((now if now is not None else time.time()) - t) / 60.0


def parse(line):
    """dict(lane, to, cc, stamp, text, key) for a waiter FAIL result line, else None."""
    m = LINE.match(line.rstrip("\n"))
    if not m:
        return None
    lane = m.group("lane")
    if lane.startswith(SKIP_LANES) or "NEEDS-ACTION" in line[:200]:
        return None
    text = m.group("text")
    if not VERDICT.search(text[:WINDOW]):
        return None
    tos = [x.strip() for x in re.split(r"[,\s]+", (m.group("to") or "").strip()) if x.strip()]
    cc = [x.strip() for x in re.split(r"[,\s]+", (m.group("cc") or "").strip()) if x.strip()]
    return dict(lane=lane, to=tos, cc=cc, stamp=m.group("stamp").strip(), text=text, key=line_key(line))


def post_text(r):
    rcpt = [r["lane"]] + [x for x in r["to"] if x not in (r["lane"], "COORD")]
    ccs = [x for x in r["cc"] if x not in rcpt and x != "COORD"]
    head = f"NEEDS-ACTION [{LANE} -> {', '.join(rcpt)}, COORD" + (f"; cc {', '.join(ccs)}" if ccs else "") + "]"
    ex = re.sub(r"\s+", " ", r["text"])[:260]
    return (f"{head} WAITER-FAIL {r['key']} ({r['stamp']}) waiter result of {r['lane']} is a failure and not answered: {ex} "
            f"-- owner: read the full RESULT line in the queue, post the cause + next step (or NEEDS-LANE); "
            f"this relay does not repeat (key {r['key']}).")


def load_state(p):
    try:
        d = json.loads(Path(p).read_text())
        return d if isinstance(d, dict) and isinstance(d.get("seen"), dict) else None
    except (OSError, ValueError):
        return None


def save_state(p, st):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(st, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, p)


def run(queue, state, post_sh, max_age_min=120, max_posts=10, dry=False, poster=None, now=None):
    """returns (posted keys, seen-only keys, failed keys)."""
    qtext = Path(queue).read_text(errors="replace")
    qlines = qtext.splitlines()
    st = load_state(state)
    first = st is None
    st = st or {"seen": {}}
    already = set(re.findall(r"WAITER-FAIL ([0-9a-f]{12})\b", qtext))
    now = time.time() if now is None else now
    posted, noted, failed = [], [], []
    for ln in qlines:
        r = parse(ln)
        if not r or r["key"] in st["seen"]:
            continue
        if r["key"] in already:                     # posted earlier, state lost
            st["seen"][r["key"]] = int(now)
            noted.append(r["key"])
            continue
        age = stamp_age_min(r["stamp"], now)
        if first and (age is None or age > max_age_min):
            st["seen"][r["key"]] = int(now)
            noted.append(r["key"])
            continue
        if len(posted) >= max_posts:
            continue                                # next run
        text = post_text(r)
        if dry:
            print("DRY", text)
            posted.append(r["key"])
            continue
        ok = (poster or _post)(post_sh, text)
        if ok:
            st["seen"][r["key"]] = int(now)
            posted.append(r["key"])
        else:
            failed.append(r["key"])
    if not dry:
        save_state(state, st)
    return posted, noted, failed


def _post(post_sh, text):
    try:
        r = subprocess.run(["bash", str(post_sh), LANE, text], capture_output=True, text=True, timeout=120, cwd="/")
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"post failed: {e}", file=sys.stderr)
        return False
    if r.returncode != 0:
        print(f"post.sh rc {r.returncode}: {r.stderr.strip()[-300:]}", file=sys.stderr)
    return r.returncode == 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--queue", default=str(HOME / "coord/lanes/COORD-REVIEW-QUEUE.md"))
    ap.add_argument("--state", default=str(HOME / ".local/state/waiter-fail-relay.json"))
    ap.add_argument("--post-sh", default=str(HOME / "coord/bin/post.sh"))
    ap.add_argument("--max-age-min", type=int, default=120)
    ap.add_argument("--max-posts", type=int, default=10)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    try:
        posted, noted, failed = run(a.queue, a.state, a.post_sh, a.max_age_min, a.max_posts, a.dry)
    except OSError as e:
        print(f"waiter_fail_relay: {e}", file=sys.stderr)
        return 2
    print(f"waiter_fail_relay: posted={len(posted)} seen_only={len(noted)} post_failed={len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
