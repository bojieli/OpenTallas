#!/usr/bin/env python3
"""orphan_watch.py -- P-ORPHAN-PROCESS (COORD FLOW-1447 11-26), REPORT ONLY: it never kills, signals or touches anything.

Hourly on the hub (cron), for every live host: processes that are older than OT_ORPHAN_AGE_H (6) hours, have ppid 1, and whose cwd or command line sits
in a lane dir (/srv/opentallas-scratch*/claude/<LANE>/...) of a lane with NO hub post in the last OT_ORPHAN_QUIET_H (12) hours (the lane's
~/coord/lanes/posts/<LANE>.md mtime; a lane without a post file counts as silent).  The list goes to the hub through bin/post.sh as lane ORPHAN-WATCH
(one post, only when the set of (host, pid) changed since the last post) and to stdout.  Infra dirs (rt, wt, warm, kw43-wave-*, ot-jobs, tree-cache, CLASS-TRACK,
autopilot) are not lanes.  HBM / skyhum lines are listed too but marked, never acted on.

  python3 -I orphan_watch.py [--hosts h1,h2] [--post] [--age-h 6] [--quiet-h 12]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HOSTS = ["intel2", "intel1", "epyc2", "epyc7", "epyc8", "epyc9", "epyc10", "epyc11", "epyc12"]
POSTS = os.path.expanduser(os.environ.get("OT_ORPHAN_POSTS", "~/coord/lanes/posts"))
STATE = os.path.expanduser(os.environ.get("OT_ORPHAN_STATE", "~/.local/state/orphan-watch.json"))
POST_SH = os.path.expanduser(os.environ.get("OT_ORPHAN_POST_SH", "~/coord/bin/post.sh"))
LANE_RE = re.compile(r"/srv/opentallas-scratch\d*/claude/([^/\s]+)/")
INFRA = re.compile(r"^(rt|wt|warm|ot-jobs|tree-cache|CLASS-TRACK|autopilot|hub-coord|git|\.cache|kw43-wave-[0-9a-z]+|kw4[0-9]|kw45)$")
PROBE = r'''
import os, time
hz = os.sysconf("SC_CLK_TCK"); up = float(open("/proc/uptime").read().split()[0])
for p in os.listdir("/proc"):
    if not p.isdigit(): continue
    try:
        st = open("/proc/%s/stat" % p).read()
        rest = st[st.rindex(")") + 2:].split()
        ppid = int(rest[1]); start = int(rest[19]) / hz
        age_h = (up - start) / 3600.0
        if ppid != 1 or age_h < AGE: continue
        cmd = open("/proc/%s/cmdline" % p, "rb").read().replace(b"\0", b" ").decode(errors="replace").strip()
        try: cwd = os.readlink("/proc/%s/cwd" % p)
        except OSError: cwd = ""
        print("%s\t%.1f\t%s\t%s" % (p, age_h, cwd, cmd[:300]))
    except (OSError, ValueError, IndexError):
        continue
'''


def lane_of(cwd, cmd):
    for text in (cwd, cmd):
        for m in LANE_RE.finditer(text or ""):
            if not INFRA.match(m.group(1)):
                return m.group(1)
    return None


def last_post_age_h(lane, now=None):
    """hours since the lane's hub post file changed; None when it has none (case-insensitive file name)"""
    now = time.time() if now is None else now
    try:
        names = os.listdir(POSTS)
    except OSError:
        return None
    for n in names:
        if n.lower() in (lane.lower() + ".md", lane.lower()):
            try:
                return (now - os.stat(os.path.join(POSTS, n)).st_mtime) / 3600.0
            except OSError:
                return None
    return None


def parse(host, text, quiet_h, now=None):
    """-> [(host, pid, age_h, lane, post_age_h|None, cmd)] of the orphans of lanes silent for quiet_h hours"""
    out = []
    for ln in text.splitlines():
        f = ln.split("\t", 3)
        if len(f) < 4:
            continue
        pid, age, cwd, cmd = f
        lane = lane_of(cwd, cmd)
        if not lane:
            continue
        pa = last_post_age_h(lane, now)
        if pa is not None and pa < quiet_h:
            continue
        out.append((host, int(pid), float(age), lane, pa, cmd))
    return out


def probe(host, age_h, run=subprocess.run):
    try:
        r = run(["ssh", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", "-o", "ControlPath=none", host, "python3", "-I", "-c",
                 "'AGE=%s\n%s'" % (age_h, PROBE.replace("'", "'\"'\"'"))], capture_output=True, text=True, timeout=90)
    except Exception:
        return ""
    return r.stdout if r.returncode == 0 else ""


def render(rows, quiet_h):
    lines = [f"ORPHAN-WATCH {len(rows)} process(es) older than the age limit, ppid 1, lane silent > {quiet_h:g} h on the hub (REPORT ONLY, nothing killed):"]
    for host, pid, age, lane, pa, cmd in sorted(rows, key=lambda r: (-r[2], r[0]))[:40]:
        tag = " [HBM/skyhum: parked, never touch]" if re.search(r"hbm|skyhum", lane + cmd, re.I) else ""
        lines.append(f"- {host} pid {pid} {age:.0f} h lane {lane} (last post {'never' if pa is None else '%.0f h ago' % pa}){tag}: {cmd[:110]}")
    return "\n".join(lines)


def main(argv=None, probe_fn=probe, post_fn=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hosts", default=",".join(HOSTS))
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--age-h", type=float, default=float(os.environ.get("OT_ORPHAN_AGE_H", "6")))
    ap.add_argument("--quiet-h", type=float, default=float(os.environ.get("OT_ORPHAN_QUIET_H", "12")))
    a = ap.parse_args(argv)
    rows = []
    for h in a.hosts.split(","):
        rows += parse(h, probe_fn(h, a.age_h), a.quiet_h)
    if not rows:
        print("ORPHAN-WATCH none")
        return 0
    text = render(rows, a.quiet_h)
    print(text)
    if a.post:
        keys = sorted(f"{r[0]}:{r[1]}" for r in rows)
        try:
            old = json.load(open(STATE))
        except (OSError, ValueError):
            old = []
        if keys != old:
            (post_fn or (lambda t: subprocess.run(["bash", POST_SH, "ORPHAN-WATCH", t], timeout=120)))(text)
            os.makedirs(os.path.dirname(STATE), exist_ok=True)
            json.dump(keys, open(STATE, "w"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
