#!/usr/bin/env python3
"""Hourly fleet disk sweeper (systemd --user fleet-sweep.timer; fleet disk guard 2026-10-07).

Per host of tools/closure_loop/hosts.json: (1) alert when any watched filesystem is >= 85 % full (line in
ALERT_LOG and in the takeover integrate.log); (2) run tools/fleet/sweep.py in apply mode over the host's sweep roots:
it removes only top-level items untouched for 24 h, with no live process (cwd/fd/docker mount/cmdline), no git
checkout, and not under or above a protected path.  Protected: every absolute path named in a closure-loop job state
(run dirs of every job, any status) and every absolute fleet path named in committed physical/ tools/ files on
origin/main, every fleet path named in /home/ubuntu/claude-takeover-20261007/* written in the last 48 h; sweep.py also
keeps argv/env-referenced paths, dirs holding a STATUS.md, src-* regions beside a live sibling, and holds anything
>= 10 GB for one sweep with an alert.  Git checkouts are never removed here (worktree / clone passes back them up first)."""
import json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
JOBS = Path.home() / ".local/state/closure_loop/jobs"
WORK = Path("/tmp/fleet_sweep")
LOG = Path.home() / ".local/state/fleet_sweep/sweep.log"
ALERT_LOG = Path.home() / ".local/state/fleet_sweep/alerts.log"
TAKEOVER_LOG = Path("/home/ubuntu/claude-takeover-20261007/integrate.log")
ALERT_PCT = 85
SWEEP_ROOTS = {"ot-epyc1tb": ["/srv/opentallas-scratch", "/srv/opentallas-scratch2", "/tmp"],
               "ot-epyc2": ["/srv/opentallas-scratch", "/srv/opentallas-scratch2", "/tmp"],
               "ot-epyc3": ["/srv/opentallas-scratch", "/srv/opentallas-scratch2", "/tmp"],
               "ot-pve1": ["/srv/opentallas-scratch", "/tmp"],
               "ot-agidock128": ["/srv/opentallas-scratch", "/tmp"],
               "localhost": ["/tmp"]}
PATH_RE = re.compile(r"/(?:srv|home/ubuntu|tmp)/[A-Za-z0-9_.+@:=,-]+(?:/[A-Za-z0-9_.+@:=,-]+)*")


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace", **kw)


def protect_list():
    paths = set()
    for f in JOBS.glob("*.json"):
        paths.update(PATH_RE.findall(f.read_text(errors="replace")))
    r = sh(["git", "-C", str(ROOT), "grep", "-ohIE", PATH_RE.pattern, "origin/main", "--", "physical", "tools"])
    paths.update(r.stdout.split())
    # run roots named by the stream agents (takeover logs / STATUS / READY_TO_MERGE) in the last 48 h
    for f in TAKEOVER_LOG.parent.glob("*"):
        if f.is_file() and f.suffix in (".log", ".md", ".txt", ".json") and time.time() - f.stat().st_mtime < 48 * 3600:
            paths.update(PATH_RE.findall(f.read_text(errors="replace")))
    paths.update(str(p) for p in (ROOT, Path.home() / ".cache", Path.home() / "bin", WORK))
    return sorted(p.rstrip("/.") for p in paths if p.count("/") >= 2)


def remote(host, script, inp=None, timeout=3600):
    cmd = ["bash", "-c", script] if host == "localhost" else ["ssh", "-o", "ConnectTimeout=20", host, script]
    return subprocess.run(cmd, input=inp, capture_output=True, text=True, errors="replace", timeout=timeout)


def log(line, alert=False):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M")
    with LOG.open("a") as f:
        f.write(f"{stamp} {line}\n")
    if alert:
        with ALERT_LOG.open("a") as f:
            f.write(f"{stamp} {line}\n")
        if TAKEOVER_LOG.parent.exists():
            with TAKEOVER_LOG.open("a") as f:
                f.write(f"{stamp} PT fleet-sweep ALERT: {line}\n")


def main():
    apply = "--plan" not in sys.argv
    hosts = json.loads((ROOT / "tools/closure_loop/hosts.json").read_text())["hosts"]
    prot = "\n".join(protect_list()) + "\n"
    sweep_src = (HERE / "sweep.py").read_text()
    for h in hosts:
        name = h["name"]
        watch = sorted({h["base"], *h.get("disk_roots", {})})
        r = remote(name, "df -P " + " ".join(watch) + " | awk 'NR>1{print $5, $6}' | sort -u", timeout=120)
        for line in r.stdout.splitlines():
            pct, mnt = line.split()
            if int(pct.rstrip("%")) >= ALERT_PCT:
                log(f"{h['label']} {mnt} at {pct} (>= {ALERT_PCT}%)", alert=True)
        if r.returncode:
            log(f"{h['label']} unreachable: {r.stderr.strip()[-200:]}")
            continue
        roots = " ".join(SWEEP_ROOTS.get(name, ["/tmp"]))
        script = f"set -e; mkdir -p {WORK}; cat > {WORK}/protect.txt; "
        # ship sweep.py, then run it
        rr = remote(name, f"mkdir -p {WORK} && cat > {WORK}/sweep.py", inp=sweep_src, timeout=120)
        if rr.returncode:
            log(f"{h['label']} ship failed: {rr.stderr.strip()[-200:]}")
            continue
        rr = remote(name, script + f"cd {WORK} && SWEEP_SKIP={WORK} SWEEPLOG={WORK}/sweep.log python3 sweep.py "
                    f"{h['label']} {WORK}/protect.txt {'apply' if apply else 'plan'} {roots} | grep -E '^(TOTAL|DELETED|HOLD_BIG)' | tail -80",
                    inp=prot, timeout=3600)
        for line in rr.stdout.splitlines():
            log(f"{h['label']} {line}", alert=line.startswith("HOLD_BIG"))
        if rr.returncode:
            log(f"{h['label']} sweep rc={rr.returncode}: {rr.stderr.strip()[-300:]}")


if __name__ == "__main__":
    main()
