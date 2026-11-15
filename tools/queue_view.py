#!/usr/bin/env python3
"""REPO-STATE-1 11-14: lanes/COORD-REVIEW-QUEUE.md as a merged view of per-lane post files.

Each lane appends its posts to its OWN file lanes/posts/<LANE>.md (same line format as the queue:
"- YYYY-MM-DD HH:MM PST TAG [LANE -> TO; cc ...] text", continuation lines indented) and commits only that file,
so two lanes never edit the same file.  This generator appends every post block from lanes/posts/*.md that is not
yet in the view to the end of lanes/COORD-REVIEW-QUEUE.md, oldest stamp first.

Compatibility (dozens of running lanes, autopilot, kit_wave and watchdog still append to the queue directly):
  * the view is APPEND-ONLY.  Existing text is never rewritten, reordered or removed, so the direct-append path, the
    tools that read it (loopgaps, ot-autoclean, release_task_watch, element_owner_watch, failure_breakdown, stale_list,
    coord_snapshot, rotate_queue) and the union merge of lanes/*.md keep working unchanged;
  * dedup: a post block is "present" when its first line (trailing blanks ignored) is already in the view or in any
    lanes/archive/COORD-REVIEW-QUEUE-*.md (rotate_queue.py moves old posts there), so a lane that writes both paths
    during the transition, a rotation, or a re-run never duplicates a post;
  * blocks: a block starts at a first-column line that is a bullet ("- "), a heading ("#") or carries a stamp;
    following lines that are indented, or unstamped non-bullet first-column text (pasted logs), belong to it; empty lines are dropped.  A block's time is the first stamp in its first 80 chars
    (PST/PDT/UTC normalised to PST); a block without a stamp takes the time of the block before it in the same file.

Writes: only with --apply.  The caller holds ~/coord/.coord.lock (coord-commit.sh does) or passes --lock to take it.
The batch is one O_APPEND write, so a concurrent `echo >>` from a legacy writer interleaves only between whole writes.
--check prints what would be appended and exits 1 if anything is missing (used by the shadow proof and tests).
Exit 0 always on --apply (prints "appended N").  Python stdlib only; run with python3 -I.
"""
import argparse, datetime as D, fcntl, glob, os, re, sys

TS = re.compile(r"(20\d\d-\d\d-\d\d)[ T](\d\d:\d\d)(?::(\d\d))?\s*(PST|PDT|UTC|Z)?")
QUEUE = "lanes/COORD-REVIEW-QUEUE.md"
POSTS = "lanes/posts"
ARCH_GLOB = "lanes/archive/COORD-REVIEW-QUEUE-*.md"


def stamp(line):
    m = TS.search(line[:80])
    if not m:
        return None
    try:
        t = D.datetime.fromisoformat(f"{m.group(1)} {m.group(2)}:{m.group(3) or '00'}")
    except ValueError:
        return None
    if m.group(4) in ("UTC", "Z"):
        t -= D.timedelta(hours=8)
    elif m.group(4) == "PDT":
        t -= D.timedelta(hours=1)
    return t


def blocks(text):
    """[(first_line, [lines], time_or_None)] in file order"""
    out, cur = [], None
    for ln in text.split("\n"):
        if not ln.strip():
            continue
        if cur is not None and (ln[:1].isspace() or (stamp(ln) is None and not ln.startswith(("- ", "#")))):
            # indented, or an unstamped first-column line that is not a bullet/heading (pasted log output in a
            # legacy post): continuation. "- 2026-11-14 19:0x PST" bullets (no valid stamp) still start a block.
            # Without this, a non-unique unstamped line becomes a block key that dedups against old posts (shadow
            # proof 11-14: 3 lost lines, all inside one legacy post).
            cur[1].append(ln)
            continue
        cur = [ln.rstrip(), [ln], stamp(ln)]
        out.append(cur)
    last = None
    for b in out:
        if b[2] is None:
            b[2] = last
        last = b[2]
    return out


def read(p):
    try:
        with open(p, "rb") as f:
            return f.read().decode("utf-8", errors="surrogateescape")
    except FileNotFoundError:
        return ""


def present_set(coord):
    s = set()
    for p in [os.path.join(coord, QUEUE)] + sorted(glob.glob(os.path.join(coord, ARCH_GLOB))):
        for ln in read(p).split("\n"):
            if ln.strip():
                s.add(ln.rstrip())
    return s


def missing(coord):
    have = present_set(coord)
    todo, seen = [], set()
    for p in sorted(glob.glob(os.path.join(coord, POSTS, "*.md"))):
        if os.path.basename(p).startswith(("_", ".", "README")):
            continue
        for i, (key, lines, t) in enumerate(blocks(read(p))):
            if key in have or key in seen:
                continue
            seen.add(key)
            todo.append((t or D.datetime.min, os.path.basename(p), i, lines))
    todo.sort(key=lambda x: (x[0], x[1], x[2]))
    return todo


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--coord", default=os.environ.get("COORD_DIR", os.path.expanduser("~/coord")))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--lock", help="flock this file (~/coord/.coord.lock) around read+append")
    a = ap.parse_args(argv)
    lk = None
    if a.lock:
        lk = open(a.lock, "a")
        fcntl.flock(lk, fcntl.LOCK_EX)
    todo = missing(a.coord)
    if a.check or not a.apply:
        for t, f, i, lines in todo:
            print(f"missing {f}#{i}: {lines[0][:160]}")
        print(f"missing {len(todo)}")
        return 1 if (a.check and todo) else 0
    if not todo:
        print("appended 0")
        return 0
    q = os.path.join(a.coord, QUEUE)
    body = "".join("\n".join(lines) + "\n" for _, _, _, lines in todo).encode("utf-8", "surrogateescape")
    fd = os.open(q, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o664)
    try:
        if os.fstat(fd).st_size:
            with open(q, "rb") as f:
                f.seek(-1, 2)
                if f.read(1) != b"\n":
                    body = b"\n" + body
        os.write(fd, body)
    finally:
        os.close(fd)
    print(f"appended {len(todo)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
