#!/usr/bin/env python3
"""COORD-COMMIT-SPEED-1 11-13: rotate lanes/COORD-REVIEW-QUEUE.md.
Posts before --cutoff (PST) move verbatim to --archive.  The live file keeps a short header, the archived posts that the
tools still need (READY/ASK posts inside ot-autoclean's 168 h window with no closing post: CLEAN-2 path protection;
'[COORD ...] GEOM-FAIL-AFTER-SUBMIT <id> ...: KEEP|CANCEL' rulings: autopilot loop gaps) and every post from the cutoff on.
--check compares the tools' own parsers on the old full text and on the new live text.  --apply writes (caller holds
~/coord/.coord.lock); lines appended to the old inode while it runs are carried over."""
import argparse, datetime as D, importlib.util, os, re, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("--queue", required=True)
ap.add_argument("--archive", required=True)
ap.add_argument("--cutoff", default="2026-11-12 00:00")
ap.add_argument("--tools", default=os.path.expanduser("~/OpenTallas/tools"))
ap.add_argument("--apply", action="store_true")
ap.add_argument("--lock", help="flock this file (~/coord/.coord.lock) for the write + commit")
ap.add_argument("--commit-msg", help="under the lock: git add + commit the queue, the archive and --also paths")
ap.add_argument("--also", nargs="*", default=[])
a = ap.parse_args()


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


AC = load("ot_autoclean_cli", os.path.join(a.tools, "fleet/ot-autoclean.py"))
sys.path.insert(0, os.path.join(a.tools, "autopilot"))
LG = load("loopgaps", os.path.join(a.tools, "autopilot/loopgaps.py"))

TS = re.compile(r"(20\d\d-\d\d-\d\d)[ T](\d\d:\d\d)(?::\d\d)?\s*(PST|PDT|UTC|Z)?")
cut_t = D.datetime.fromisoformat(a.cutoff)


def pst(m):
    t = D.datetime.fromisoformat(m.group(1) + " " + m.group(2))
    if m.group(3) in ("UTC", "Z"):
        t -= D.timedelta(hours=8)
    elif m.group(3) == "PDT":
        t -= D.timedelta(hours=1)
    return t


fd = os.open(a.queue, os.O_RDONLY)
st0 = os.fstat(fd)
raw = b""
while True:
    b = os.read(fd, 1 << 24)
    if not b:
        break
    raw += b
text = raw.decode("utf-8", errors="surrogateescape")
lines = text.split("\n")
assert lines[-1] == "", "queue does not end in a newline"
lines = lines[:-1]

# cut: the first post start (non-space line with a stamp in its first 80 chars) dated >= cutoff
cut = None
for i, l in enumerate(lines):
    if l[:1] and not l[:1].isspace():
        m = TS.search(l[:80])
        if m and cut_t <= pst(m) < cut_t + D.timedelta(days=3):
            cut = i
            break
assert cut, "no post at/after the cutoff"
arch, tail = lines[:cut], lines[cut:]

# archived posts, split the way ot-autoclean parse_open_readyask splits them
posts, cur = [], None
for i, l in enumerate(arch):
    if l[:1] and not l[:1].isspace() and AC.STAMP_RE.search(l[:80]):
        cur = [i, i + 1]
        posts.append(cur)
    elif cur is not None:
        cur[1] = i + 1
now = time.time()
lo = now - 168 * 3600 - 3600
full_posts_after = None
carry = set()
alltext_lines = lines
for (s, e) in posts:
    body = arch[s:e]
    m = AC.STAMP_RE.search(body[0][:80])
    t = time.mktime(time.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M"))
    if t >= lo and any(AC.READYASK_RE.search(x) for x in body):
        carry.add((s, e))
    if any(LG.GFAS_COORD.search(x) for x in body):
        carry.add((s, e))
# keep only posts that ot-autoclean parse_open_readyask counts as open on the full text (its own loop, per post)
fposts, cur = [], None
for i, l in enumerate(lines):
    if l[:1] and not l[:1].isspace() and AC.STAMP_RE.search(l[:80]):
        cur = [i, i + 1]
        fposts.append(cur)
    elif cur is not None:
        cur[1] = i + 1
def is_open(k):
    s, e = fposts[k]
    pl = lines[s:e]
    head = pl[0][:200]
    for j, ln in enumerate(pl):
        if not (AC.READYASK_RE.search(head) if j == 0 else AC.READYASK_RE.search(ln.lstrip()[:12])):
            continue
        body = "\n".join(pl) if j == 0 else ln
        keys = set(AC.KEY_RE.findall(body))
        closed = bool(keys) and any(AC.CLOSE_RE.search(lines[q0][:200]) and any(x in "\n".join(lines[q0:q1]) for x in keys)
                                    for q0, q1 in fposts[k + 1:])
        if not closed and AC.text_paths(body):
            return True
    return False
start_of = {s: k for k, (s, e) in enumerate(fposts)}
kept = []
for (s, e) in sorted(carry):
    body = arch[s:e]
    if any(LG.GFAS_COORD.search(x) for x in body) or (s in start_of and is_open(start_of[s])):
        kept.append((s, e))

span = f"{arch[0][:0]}"
first_day = "2026-10-24"
last_day = (cut_t - D.timedelta(days=1)).strftime("%Y-%m-%d")
arch_rel = os.path.relpath(a.archive, os.path.dirname(os.path.dirname(os.path.abspath(a.queue))))
hdr = [
    "# COORD-REVIEW-QUEUE (live)",
    "",
    f"Rotated by COORD-COMMIT-SPEED-1 on {time.strftime('%Y-%m-%d')}: every post dated before {a.cutoff.split()[0]} midnight PST "
    f"moved verbatim to {arch_rel} (git history kept). Each coord/state push carried this whole file (28 MB),",
    "which made every post wait on GitHub. Append new posts at the end as before.",
    f"Carried from the archive (verbatim, original stamps): {len(kept)} posts still open for the tools",
    "(open READY or ASK posts inside the 168 h cleanup window, and GEOM-FAIL-AFTER-SUBMIT rulings).",
    "",
]
carried = []
for (s, e) in kept:
    carried += arch[s:e]
sep = ["", "# ---- live posts (from the rotation cutoff on) ----", ""]
new_lines = hdr + carried + sep + tail
new_text = "\n".join(new_lines) + "\n"

# checks with the tools' own parsers
chk = {
    "open_readyask": (AC.parse_open_readyask(text, now), AC.parse_open_readyask(new_text, now)),
    "geom_fail_cleared": (LG.geom_fail_cleared("", text), LG.geom_fail_cleared("", new_text)),
    "gaps_ready": (sorted(LG.gaps_ready(text, now)), sorted(LG.gaps_ready(new_text, now))),
}
bad = 0
for k, (x, y) in chk.items():
    same = x == y
    sup = k == "open_readyask" and x <= y          # fail-safe: the live file may protect more paths, never fewer
    bad += not (same or sup)
    print(f"check {k}: {'SAME' if same else 'SUPERSET (loses none)' if sup else 'DIFF'} ({len(x)} vs {len(y)})")
    if not same and isinstance(x, set):
        print("  only old:", sorted(x - y)[:10]); print("  only new:", sorted(y - x)[:10])
print(f"lines {len(lines)} -> archive {len(arch)} + live {len(new_lines)} (carried {len(carried)} lines / {len(kept)} posts); "
      f"bytes {len(raw)} -> live {len(new_text.encode('utf-8', 'surrogateescape'))}")
print("cut line", cut + 1, ":", lines[cut][:120])
if bad:
    sys.exit("checks differ: not applying")
if not a.apply:
    sys.exit(0)

assert not os.path.exists(a.archive), "archive exists"
import fcntl, subprocess
lk = None
if a.lock:
    lk = open(a.lock, "a")
    t = time.time()
    fcntl.flock(lk, fcntl.LOCK_EX)
    print(f"lock {a.lock} after {time.time() - t:.1f} s")
with open(a.queue, "rb") as f:          # the file only grows while we computed: carry what was appended since
    now_raw = f.read()
assert now_raw.startswith(raw), "queue was rewritten (not only appended) since the read: not applying"
late = now_raw[len(raw):]
os.makedirs(os.path.dirname(a.archive), exist_ok=True)
with open(a.archive, "wb") as f:
    f.write(("\n".join(arch) + "\n").encode("utf-8", "surrogateescape"))
tmp = a.queue + ".rotate.tmp"
with open(tmp, "wb") as f:
    f.write(new_text.encode("utf-8", "surrogateescape") + late)
os.chmod(tmp, st0.st_mode & 0o777)
os.replace(tmp, a.queue)
time.sleep(1)
os.lseek(fd, len(now_raw), 0)
extra = b""
while True:                              # writers that opened the old inode before the replace
    b = os.read(fd, 1 << 20)
    if not b:
        break
    extra += b
if extra:
    with open(a.queue, "ab") as f:
        f.write(extra)
print("applied; bytes appended during compute:", len(late), "during replace:", len(extra))
if a.commit_msg:
    paths = [a.queue, a.archive] + a.also
    subprocess.run(["git", "add", "--", *paths], check=True)
    subprocess.run(["git", "commit", "-q", "-m", a.commit_msg, "--", *paths], check=True)
    print("committed", subprocess.run(["git", "rev-parse", "--short=11", "HEAD"], capture_output=True, text=True).stdout.strip())
