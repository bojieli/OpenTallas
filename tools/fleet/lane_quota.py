#!/usr/bin/env python3
"""lane_quota (FLEET-OPS-R, COORD r550 quota ruling): per-lane disk quota as an ALERT, not a kill.  On a build host: bytes written (ctime newer than WINDOW_H, hardlinks counted
once) per claude/<lane> directory; a lane over QUOTA_GB new in WINDOW_H hours (default 150 GB / 6 h) is reported.  Hub mode (--hub HOST...): runs the scan over ssh, posts one
ALERT line per offending lane through bin/post.sh, once per lane per day.
usage: lane_quota.py scan [--root R] [--window-h 6] [--quota-gb 150]          (prints JSON {lane: GB} for lanes over quota)
       lane_quota.py hub HOST... [--coord ~/coord]"""
import argparse, json, os, subprocess, sys, time

WINDOW_H, QUOTA_GB = 6.0, 150.0
BURST_H, BURST_GB = 1.0, 30.0      # 11-17: a 39 GB lane clone (QC-TYPES-R3) never reached 150 GB / 6 h; a burst tier alerts at 30 GB / 1 h
ROOTS = ("/srv/opentallas-scratch2/claude", "/srv/opentallas-scratch3/claude")   # epyc2 lanes live on scratch3 too
SKIP = {"rt", "git", "signed-store", "hub-coord", "mq1", "mq-gate"}


def scan_all(roots=ROOTS, now=None):
    """-> {lane: GB} for lanes over either tier on any root that exists on this host ('lane' keys carry the root when it is not scratch2)"""
    out = {}
    for r in roots:
        if not os.path.isdir(r):
            continue
        vol = os.path.basename(os.path.dirname(r.rstrip("/")))
        tag = "" if vol.endswith("scratch2") else vol.replace("opentallas-", "") + ":"
        for h, g in ((WINDOW_H, QUOTA_GB), (BURST_H, BURST_GB)):
            for lane, gb in scan(r, h, g, now).items():
                out.setdefault(tag + lane, gb)
                out[tag + lane] = max(out[tag + lane], gb)
    return out


def scan(root, window_h=WINDOW_H, quota_gb=QUOTA_GB, now=None, skip=SKIP):
    now = now or time.time(); cut = now - window_h * 3600; over = {}
    for lane in sorted(os.listdir(root)):
        p = os.path.join(root, lane)
        if lane in skip or lane.startswith(".") or not os.path.isdir(p) or os.path.islink(p):
            continue
        tot, seen = 0, set()
        for r, ds, fs in os.walk(p):
            for f in fs:
                try:
                    st = os.lstat(os.path.join(r, f))
                except OSError:
                    continue
                if st.st_ctime >= cut and st.st_nlink >= 1 and (st.st_dev, st.st_ino) not in seen:
                    seen.add((st.st_dev, st.st_ino)); tot += st.st_blocks * 512
        if tot / 2**30 >= quota_gb:
            over[lane] = round(tot / 2**30, 1)
    return over


# 11-18: the scan walks every file of every lane (3 TB): it ran 52 min in D state on epyc7 and its IO pressure stalled container creation (overlay umount -> syncfs).  Idle IO class, hard 600 s cap on the host.
def hub(hosts, coord, run=subprocess.run, state=None, now=None):
    """-> list of posted lines.  state = json file with {host/lane: day} so a lane alerts once per day"""
    now = now or time.time(); day = time.strftime("%F", time.localtime(now))
    state = state or os.path.expanduser("~/.local/state/lane_quota_state.json")
    try: seen = json.load(open(state))
    except (OSError, ValueError): seen = {}
    posted = []
    for h in hosts:
        try:                      # one slow or dead host must not abort the other hosts (epyc7 timed out and no alert was ever posted)
            r = run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", h, "ionice -c3 nice -n 19 timeout 600 python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/fleet/lane_quota.py scan"],
                    capture_output=True, text=True, timeout=900)
            over = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            continue
        for lane, gb in over.items():
            k = "%s/%s" % (h, lane)
            if seen.get(k) == day: continue
            seen[k] = day
            line = "ALERT [FLEET-OPS-R -> COORD] lane quota: %s on %s wrote %.0f GB in the last window (quota %g GB/lane/%g h or %g GB/%g h burst; alert only, nothing stopped); owner please prune or confirm" % (lane, h, gb, QUOTA_GB, WINDOW_H, BURST_GB, BURST_H)
            run(["bash", os.path.join(coord, "bin/post.sh"), "FLEET-OPS-R", line], capture_output=True, text=True)
            posted.append(line)
    os.makedirs(os.path.dirname(state), exist_ok=True)
    json.dump(seen, open(state, "w"))
    return posted


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["scan", "hub"]); ap.add_argument("hosts", nargs="*"); ap.add_argument("--root", default="/srv/opentallas-scratch2/claude")
    ap.add_argument("--window-h", type=float, default=WINDOW_H); ap.add_argument("--quota-gb", type=float, default=QUOTA_GB); ap.add_argument("--coord", default=os.path.expanduser("~/coord"))
    a = ap.parse_args(argv)
    if a.cmd == "scan":
        print(json.dumps(scan_all() if a.root == "/srv/opentallas-scratch2/claude" and a.window_h == WINDOW_H and a.quota_gb == QUOTA_GB else scan(a.root, a.window_h, a.quota_gb)))
    else:
        for l in hub(a.hosts, a.coord): print(l)
    return 0


if __name__ == "__main__":
    sys.exit(main())
