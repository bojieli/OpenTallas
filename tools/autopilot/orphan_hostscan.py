#!/usr/bin/env python3
"""orphan_hostscan.py -- host side of orphan_scan.py (FAILFAST-1 scope 2): READ-ONLY inventory of the running docker containers
and ot-heavy scopes of this host.  Prints one JSON document; sends no signal, writes nothing."""
import json
import os
import re
import subprocess
import time


def sh(cmd, timeout=60):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def procs(cid):
    try:
        return [int(x) for x in open("/sys/fs/cgroup/system.slice/docker-%s.scope/cgroup.procs" % cid).read().split()]
    except OSError:
        return []


def rss_threads(pids):
    rss, thr, tools = 0.0, 0, set()
    for p in pids:
        try:
            st = open("/proc/%d/status" % p).read()
            m = re.search(r"VmRSS:\s+(\d+) kB", st)
            rss += int(m[1]) / 1048576.0 if m else 0
            av = open("/proc/%d/cmdline" % p, "rb").read().decode("utf-8", "replace").split("\0")
            b = os.path.basename(av[0]) if av and av[0] else ""
            if b in ("openroad", "yosys", "yosys-abc", "sta", "python3", "python"):
                tools.add(b)
            if b == "openroad" and "-threads" in av:
                thr = max(thr, int(av[av.index("-threads") + 1]))
        except (OSError, ValueError, IndexError):
            pass
    return round(rss, 1), thr, sorted(tools)


def main():
    now = time.time()
    ids = sh(["docker", "ps", "-q", "--no-trunc"]).split()
    rows = []
    if ids:
        try:
            info = json.loads(sh(["docker", "inspect"] + ids, 120) or "[]")
        except ValueError:
            info = []
        for c in info:
            mounts = [(m.get("Source"), m.get("Destination"), m.get("RW", True)) for m in c.get("Mounts", []) if m.get("Type") == "bind"]
            work = next((s for s, d, _ in mounts if d == "/work"), None)
            st = c.get("State", {}).get("StartedAt", "")
            try:
                started = time.mktime(time.strptime(st[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
            except ValueError:
                started = 0
            origin = None
            if work:
                try:                       # ot-job isolated copy: the job spec names the original kit the autopilot row points at
                    jj = json.load(open(os.path.join(os.path.dirname(work.rstrip("/")), ".ot-job", "job.json")))
                    origin = ((jj.get("spec") or {}).get("work") or {}).get("at")
                except (OSError, ValueError):
                    pass
            pids = procs(c["Id"])
            rss, thr, tools = rss_threads(pids)
            rows.append({"name": c.get("Name", "").lstrip("/"), "id": c["Id"][:12], "work": work, "origin": origin or work,
                         "rw_mounts": [s for s, d, rw in mounts if rw][:4], "age_h": round((now - started) / 3600.0, 1) if started else None,
                         "rss_gb": rss, "threads": thr, "tools": tools, "nproc": len(pids),
                         "cmd": " ".join((c.get("Config", {}).get("Cmd") or []))[:200]})
    scopes = []
    for ln in sh(["systemctl", "--user", "list-units", "--type=scope", "--no-legend", "--plain", "--state=active"]).splitlines():
        f = ln.split(None, 4)
        if f and f[0].startswith("oth-"):
            scopes.append({"unit": f[0], "desc": (f[4] if len(f) > 4 else "")[:300]})
    print(json.dumps({"host": os.uname().nodename, "time": now, "containers": rows, "scopes": scopes}))


if __name__ == "__main__":
    main()
