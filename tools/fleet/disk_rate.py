#!/usr/bin/env python3
"""DISK-RATE (FLEET-OPS-R, FABLE-FLOW-2000): every run samples the free bytes of every scratch disk of every host (ssh df), keeps a short history, and
posts ONE alert per host+disk per hour to FLEET-OPS-R when the disk is projected to hit the 50 GB floor within 6 h at its last 60-minute rate.
Read-only by default: it deletes and changes nothing.
AUTO-RETIRE (FABLE-FLOW-2200): when a disk is projected to hit the floor within AUTO_HOURS (2 h) and the switch file ~/.config/ot-auto-retire/ON exists
(created only after COORD approval), the alert also runs ot-auto-retire-run.sh apply on that host: superseded source trees only, reference proof +
guard + signed-store check, stops at the target, df before / after in the post.  Without the switch file the post says what it would have done."""
import json, os, shlex, subprocess, sys, time
HOSTS = ["intel1", "epyc2", "epyc7", "epyc8", "epyc9", "epyc10", "intel2"]
DISKS = ["/srv/opentallas-scratch2", "/srv/opentallas-scratch"]
HIST = os.path.expanduser("~/.local/state/disk-rate.json")
FLOOR_GB, HORIZON_H, WINDOW_S, ALERT_EVERY_S = 50.0, 6.0, 3600, 3600
AUTO_HOURS = 2.0
AUTO_SWITCH = os.path.expanduser('~/.config/ot-auto-retire/ON')
AUTO_WRAPPER = '/srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-auto-retire-run.sh'


def sample(host):
    cmd = "for d in %s; do echo $(stat -c %%d $d) $(df -k --output=avail $d | tail -n 1) $d; done" % " ".join(DISKS)
    argv = ["bash", "-c", cmd] if host == "intel2" else ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ControlPath=none", host, cmd]
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return {}
    seen, res = set(), {}
    for ln in out.splitlines():
        p = ln.split()
        if len(p) == 3 and p[0] not in seen:                      # scratch and scratch3 can be the same device: one entry per device
            seen.add(p[0]); res[p[2]] = int(p[1]) * 1024
    return res


def project(points, now, floor=FLOOR_GB * 1e9):
    """points = [(t, free_bytes)] -> hours until the floor at the rate over the last WINDOW_S (None = not falling / too little data)"""
    pts = [(t, f) for t, f in points if now - t <= WINDOW_S + 300]
    if len(pts) < 2 or pts[-1][0] - pts[0][0] < 900:
        return None
    rate = (pts[0][1] - pts[-1][1]) / (pts[-1][0] - pts[0][0])      # bytes/s falling
    if rate <= 0:
        return None
    return max(0.0, (pts[-1][1] - floor) / rate / 3600), rate * 3600 / 1e9


def auto_retire(host, disk, hours, switch=None, run=None):
    """-> text for the post.  Only the scratch2 disk, only under AUTO_HOURS, only with the approval switch file"""
    if hours > AUTO_HOURS or not disk.endswith('scratch2'):
        return ''
    if not os.path.exists(switch or AUTO_SWITCH):
        return ' AUTO-RETIRE would run on %s (superseded source trees only), OFF: no approval switch file' % host
    run = run or subprocess.run
    cmd = ['bash', '-c', 'bash %s apply' % AUTO_WRAPPER] if host == 'intel2' else ['ssh', '-n', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ControlPath=none', host, 'bash %s apply' % AUTO_WRAPPER]
    try:
        r = run(cmd, capture_output=True, text=True, timeout=3600)
    except Exception as e:
        return ' AUTO-RETIRE failed to start on %s: %s' % (host, str(e)[:80])
    out = [l for l in (r.stdout or '').splitlines() if l.startswith(('df ', 'DELETED', 'REFUSED', 'WOULD'))]
    n = sum(1 for l in out if l.startswith('DELETED'))
    return ' AUTO-RETIRE rc %s: %s; deleted %d, %s' % (r.returncode, ' / '.join(l for l in out if l.startswith('df ')), n, '; '.join(l for l in out if l.startswith('REFUSED'))[:200])


ETA_FILE = ".local/state/disk_eta"                 # per host: "<GB/h falling> <epoch>"; ot-run's probe reads it (disk-ETA admission hold)
LANE_HOLD_FILE = ".local/state/disk_eta_lanes"
STOP_HOURS = 1.0                                   # FABLE-FLOW-1900 (C): floor within 1 h at the current rate -> stop the top writer's lane
STOP_OFF = os.path.expanduser("~/.config/ot-disk-eta/OFF")
STOP_KEEP = {"rt", "git", "signed-store", "hub-coord", "mq1", "mq-gate", "autopilot", "kw45", "fleet-ops-r", "ot-jobs", "kit-store", "hub"}
LANE_ROOT = "/srv/opentallas-scratch2/claude"
LANE_SCAN = "python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/fleet/lane_quota.py scan --root %s --window-h 1 --quota-gb 0"


def sh_host(host, cmd, run=None, timeout=120):
    run = run or subprocess.run
    argv = ["bash", "-c", cmd] if host == "intel2" else ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ControlPath=none", host, cmd]
    return run(argv, capture_output=True, text=True, timeout=timeout)


def push_eta(host, rate_gb_h, now, run=None):
    """write the measured fall rate where ot-run's probe finds it (0 = not falling); best effort"""
    try:
        sh_host(host, "mkdir -p ~/.local/state && printf '%%.1f %%d\\n' %.1f %d > ~/%s" % (rate_gb_h, int(now), ETA_FILE), run, 60)
    except Exception:
        pass


def top_writer_lane(host, run=None, root=LANE_ROOT):
    """-> (lane, GB written in the last hour) of the biggest writer lane that is not infrastructure, or None"""
    try:
        r = sh_host(host, LANE_SCAN % root, run, 600)
        rows = json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception:
        return None
    rows = {k: v for k, v in rows.items() if k.split(":")[-1] not in STOP_KEEP}
    return max(rows.items(), key=lambda kv: kv[1]) if rows else None


def hold_top_lane(host, run=None, switch_off=None):
    """-> post text.  COORD 11-17: NEVER cancel a running unit.  ALERT naming the top writer lane + its directory, and a per-host lane hold file
    (~/.local/state/disk_eta_lanes: '<epoch> <dir>') that ot-run's probe reads: no NEW admission under that directory on that host (not --priority plan) until
    the hold is cleared (free space recovered: every run rewrites the file) or ~/.config/ot-disk-eta/OFF exists."""
    if os.path.exists(switch_off or STOP_OFF):
        return " LANE-HOLD disabled (OFF file)"
    top = top_writer_lane(host, run)
    if not top:
        return " LANE-HOLD: no writer lane found"
    lane, gb = top
    path = os.path.join(LANE_ROOT, lane.split(":")[-1])
    try:
        sh_host(host, "mkdir -p ~/.local/state && printf '%%d %%s\\n' $(date +%%s) %s > ~/%s" % (shlex.quote(path), LANE_HOLD_FILE), run, 60)
    except Exception as e:
        return " LANE-HOLD %s failed to write: %s" % (lane, str(e)[:80])
    return " ALERT top writer lane %s (%s, %.0f GB written in the last hour): no new admission under it on %s until space recovers; running units untouched" % (lane, path, gb, host)


def clear_lane_hold(host, run=None):
    try:
        sh_host(host, ": > ~/%s 2>/dev/null; true" % LANE_HOLD_FILE, run, 60)
    except Exception:
        pass


HOLDER_CMD = "lsof -nP +L1 -F pcsn 2>/dev/null"


def parse_holders(text, disk):
    """lsof -F pcsn +L1 output -> [(pid, cmd, GB)] for deleted-but-open files under disk, biggest first (one row per pid)"""
    per, pid, cmd, size = {}, None, "", 0
    for ln in text.splitlines():
        if not ln:
            continue
        t, v = ln[0], ln[1:]
        if t == "p":
            pid, cmd = v, ""
        elif t == "c":
            cmd = v
        elif t == "s":
            try:
                size = int(v)
            except ValueError:
                size = 0
        elif t == "n" and pid and v.startswith(disk):
            e = per.setdefault(pid, [cmd, 0]); e[1] += size
    return sorted(((p_, c, b / 1e9) for p_, (c, b) in per.items()), key=lambda r: -r[2])


def holders_text(host, disk, run=None, top=3):
    """top deleted-but-open holders on that mount: pid, cmdline (from /proc), held GB.  best effort, never raises"""
    try:
        rows = parse_holders(sh_host(host, HOLDER_CMD, run, 180).stdout or "", disk)
    except Exception as e:
        return " LSOF+L1 failed: %s" % str(e)[:60]
    rows = [r for r in rows if r[2] >= 0.01][:top]
    if not rows:
        return " LSOF+L1 holders: none (>=10 MB) on %s" % disk
    out = []
    for pid, c, gb in rows:
        try:
            cl = (sh_host(host, "tr '\\0' ' ' < /proc/%s/cmdline | cut -c1-160" % int(pid), run, 60).stdout or "").strip() or c
        except Exception:
            cl = c
        out.append("pid %s [%s] %.1f GB" % (pid, cl, gb))
    return " LSOF+L1 top holders on %s: %s" % (disk, "; ".join(out))


def level(hours):
    """alert state: 3 = floor within 1 h, 2 = within 2 h, 1 = within HORIZON_H, 0 = fine"""
    return 0 if hours is None else 3 if hours <= STOP_HOURS else 2 if hours <= AUTO_HOURS else 1 if hours <= HORIZON_H else 0


def main(post=True, now=None, pusher=None, stopper=None, clearer=None, holder=None):
    now = now or time.time()
    try:
        h = json.load(open(HIST))
    except (OSError, ValueError):
        h = {"pts": {}, "alerted": {}}
    alerts = []
    for host in HOSTS:
        for disk, free in sample(host).items():
            k = host + "|" + disk
            h["pts"].setdefault(k, []).append((now, free)); h["pts"][k] = [(t, f) for t, f in h["pts"][k] if now - t < 3 * 3600]
            pr = project(h["pts"][k], now)
            if disk.endswith("scratch2"):
                (pusher or push_eta)(host, pr[1] if pr else 0.0, now)
                if not (pr and pr[0] <= STOP_HOURS):
                    (clearer or clear_lane_hold)(host)        # recovered (or never held): the lane hold ends
            lv = level(pr[0] if pr else None)
            prev = h.setdefault("level", {}).get(k, 0)
            h["level"][k] = lv
            if lv > prev:                                   # one alert per state change (entering or escalating), never a repeat
                h["alerted"][k] = now
                alerts.append("DISK-RATE %s %s: free %.0f GB, falling %.0f GB/h, floor 50 GB in %.1f h (state %d, was %d)" % (host, disk, free / 1e9, pr[1], pr[0], lv, prev)
                              + (holder or holders_text)(host, disk) + auto_retire(host, disk, pr[0])
                              + ((stopper or hold_top_lane)(host) if pr[0] <= STOP_HOURS and disk.endswith("scratch2") else ""))
    os.makedirs(os.path.dirname(HIST), exist_ok=True)
    json.dump(h, open(HIST, "w"))
    for a in alerts:
        print(a)
        if post:
            subprocess.run(["bash", os.path.expanduser("~/coord/bin/post.sh"), "FLEET-OPS-R", a + " (cron disk_rate.py; read-only)"], capture_output=True, timeout=120)
    return alerts


if __name__ == "__main__":
    main()
