#!/usr/bin/env python3
"""writer_watch.py: report-only; WARN when a lane writes > 50 GB/h on this host.

Every run (cron, 10 min) sums st_size of files with mtime since the previous run (capped at 10 min) per lane dir under
/srv/opentallas-scratch2/claude/<LANE>/ (depth<=6, only dirs with recent mtime, skipping rt/wt/warm/ot-jobs/.cache/objects,
120 s total budget), appends a sample to ~/.local/state/writer-watch.json, converts the last 60 min to GB/h and posts
once per 3 h per (host, lane).  A file rewritten in place counts its whole size each window (upper bound).  Never deletes.
"""
import json
import os
import socket
import subprocess
import sys
import time

BASE = "/srv/opentallas-scratch2/claude"
STATE = os.path.expanduser("~/.local/state/writer-watch.json")
SKIP = {"rt", "wt", "warm", "ot-jobs", ".cache", "objects"}
WINDOW = 3600.0
STEP = 600.0
THRESH_GB_H = 50.0
REPOST = 3 * 3600.0
BUDGET = 120.0
MAXDEPTH = 6
GB = 1e9


def scan_lane(lane_dir, since, deadline, now_fn=time.time):
    """-> (bytes, {top-level entry: bytes}) of files with mtime >= since"""
    total, tops = 0, {}
    stack = [(lane_dir, 0, None)]
    while stack:
        if now_fn() > deadline:
            break
        d, depth, top = stack.pop()
        try:
            it = list(os.scandir(d))
        except OSError:
            continue
        for e in it:
            try:
                if e.is_symlink():
                    continue
                t = top or e.name
                if e.is_dir(follow_symlinks=False):
                    if e.name in SKIP or depth + 1 > MAXDEPTH:
                        continue
                    if e.stat(follow_symlinks=False).st_mtime >= since:
                        stack.append((e.path, depth + 1, t))
                else:
                    st = e.stat(follow_symlinks=False)
                    if st.st_mtime >= since:
                        total += st.st_size
                        tops[t] = tops.get(t, 0) + st.st_size
            except OSError:
                continue
    return total, tops


def rate_gb_h(samples, now, window=WINDOW):
    """samples: [{t, dt, bytes}] each covering (t-dt, t]; GB/h over the last `window` seconds"""
    cut = now - window
    use = [s for s in samples if s["t"] > cut]
    if not use:
        return 0.0
    start = max(min(s["t"] - s["dt"] for s in use), cut)
    span = max(now - start, STEP)
    return sum(s["bytes"] for s in use) / GB / (span / 3600.0)


def should_post(rate, last_post, now, thresh=THRESH_GB_H, repost=REPOST):
    return rate > thresh and (last_post is None or now - last_post >= repost)


def decide(state, host, now, thresh=THRESH_GB_H):
    """-> list of (lane, rate, topdir); mutates state['posted']"""
    out = []
    for lane, rec in state.get("lanes", {}).items():
        r = rate_gb_h(rec.get("samples", []), now)
        key = f"{host}/{lane}"
        if should_post(r, state.setdefault("posted", {}).get(key), now, thresh):
            state["posted"][key] = now
            out.append((lane, r, rec.get("top", "?")))
    return out


def post(msg, host, run=subprocess.run):
    if host.startswith("intel2"):
        cmd = ["bash", os.path.expanduser("~/coord/bin/post.sh"), "FLEET-WATCH-WRITER", msg]
    else:
        cmd = ["ssh", "-o", "BatchMode=yes", "intel2", "bash", "~/coord/bin/post.sh", "FLEET-WATCH-WRITER", msg]
    try:
        return run(cmd, capture_output=True, text=True, timeout=60).returncode == 0
    except Exception:
        return False


def load(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return {}


def run_once(now=None, base=BASE, state_path=STATE, host=None, post_fn=None, free_fn=None, now_fn=time.time):
    now = now_fn() if now is None else now
    host = host or socket.gethostname()
    post_fn = post_fn or (lambda m: post(m, host))
    free_fn = free_fn or (lambda: (lambda v: v.f_bavail * v.f_frsize / GB)(os.statvfs(base)))
    state = load(state_path)
    state.setdefault("lanes", {})
    prev = state.get("last_run")
    dt = min(now - prev, WINDOW) if prev else STEP
    dt = max(dt, 1.0)
    since = now - dt
    deadline = now_fn() + BUDGET
    try:
        lanes = sorted(e.name for e in os.scandir(base) if e.is_dir(follow_symlinks=False) and e.name not in SKIP)
    except OSError:
        lanes = []
    for lane in lanes:
        b, tops = scan_lane(os.path.join(base, lane), since, deadline, now_fn)
        rec = state["lanes"].setdefault(lane, {"samples": []})
        rec["samples"] = [s for s in rec["samples"] if s["t"] > now - WINDOW] + [{"t": now, "dt": dt, "bytes": b}]
        if tops:
            rec["top"] = max(tops, key=tops.get)
    state["last_run"] = now
    for lane in [l for l in state["lanes"] if l not in lanes]:
        del state["lanes"][lane]
    posts = decide(state, host, now)
    free = free_fn()
    for lane, r, top in posts:
        post_fn(f"WARN {host} lane {lane} writes {r:.0f} GB/h (top dir {top}); free {free:.0f} GB")
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    tmp = state_path + ".tmp"
    json.dump(state, open(tmp, "w"))
    os.replace(tmp, state_path)
    return posts


if __name__ == "__main__":
    for lane, r, top in run_once():
        print(f"WARN lane {lane} {r:.0f} GB/h top {top}")
    sys.exit(0)
