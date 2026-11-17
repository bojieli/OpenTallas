#!/usr/bin/env python3
"""DISK-RATE (FLEET-OPS-R, FABLE-FLOW-2000): every run samples the free bytes of every scratch disk of every host (ssh df), keeps a short history, and
posts ONE alert per host+disk per hour to FLEET-OPS-R when the disk is projected to hit the 50 GB floor within 6 h at its last 60-minute rate.
Read-only: it deletes and changes nothing."""
import json, os, subprocess, sys, time
HOSTS = ["intel1", "epyc2", "epyc7", "epyc8", "epyc9", "epyc10", "intel2"]
DISKS = ["/srv/opentallas-scratch2", "/srv/opentallas-scratch"]
HIST = os.path.expanduser("~/.local/state/disk-rate.json")
FLOOR_GB, HORIZON_H, WINDOW_S, ALERT_EVERY_S = 50.0, 6.0, 3600, 3600


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


def main(post=True, now=None):
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
            if pr and pr[0] <= HORIZON_H and now - h["alerted"].get(k, 0) >= ALERT_EVERY_S:
                h["alerted"][k] = now
                alerts.append("DISK-RATE %s %s: free %.0f GB, falling %.0f GB/h, floor 50 GB in %.1f h" % (host, disk, free / 1e9, pr[1], pr[0]))
    os.makedirs(os.path.dirname(HIST), exist_ok=True)
    json.dump(h, open(HIST, "w"))
    for a in alerts:
        print(a)
        if post:
            subprocess.run(["bash", os.path.expanduser("~/coord/bin/post.sh"), "FLEET-OPS-R", a + " (cron disk_rate.py; read-only)"], capture_output=True, timeout=120)
    return alerts


if __name__ == "__main__":
    main()
