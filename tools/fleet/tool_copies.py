#!/usr/bin/env python3
"""TOOL-COPY (FLOW-FLEET-R1 11-22, FABLE-FLOW-0000 F3): cron and timer entries that run a COPIED fleet tool instead of rt/current.

The hourly FLOW-HEALTH cron ran an 11-15 copy (~/.local/lib/fleet/flowhealth1-20b88ef3834/flow_health.py) that lacked the live-tree fix,
so the SKEW block listed parked trees.  Installers copy a script into a sha-named dir and point cron at it; nothing compared the targets
to rt/current.  This reads, on every host: `crontab -l` and the ExecStart / ExecStartPre lines of every --user and system service that a
timer activates, and lists each script path that is a copy:
    COPY        ~/.local/lib/<dir>/...                  (installer copies)
    PINNED-RT   /srv/opentallas-scratch*/claude/rt/<sha12>/...   (an rt snapshot other than rt/current)
    WORKTREE    /srv/opentallas-scratch*/claude/wt/...  (a lane worktree)
rt/current/... paths and system binaries are fine.  Age = the script file's mtime; > 24 h = ALERT.  Read-only.
Prints one line per copy, then "TOOL-COPY ok" or "TOOL-COPY N copies (M ALERT > 24 h): host:path age ..." last (host_report.sh appends it).

    python3 -I tools/fleet/tool_copies.py [--hosts h1,h2] [--file DUMP --host NAME]
"""
import argparse
import re
import shlex
import subprocess
import sys
import time

HOSTS = ["intel2", "intel1", "epyc2", "epyc7", "epyc8", "epyc9", "epyc10"]
ALERT_H = 24.0
PATH_RE = re.compile(r"(/[\w.@+-]+(?:/[\w.@+-]+)+\.(?:py|sh)|/[\w.@+-]+(?:/[\w.@+-]+)*/(?:ot-[\w-]+|[\w-]+\.py))")
KINDS = (("COPY", re.compile(r"^/home/[^/]+/\.local/lib/")),
         ("PINNED-RT", re.compile(r"^/srv/opentallas-scratch\d*/claude/rt/(?!current/)[0-9a-f]{7,40}/")),
         ("WORKTREE", re.compile(r"^/srv/opentallas-scratch\d*/claude/wt/")))
# one shell pass per host: crontab, then every timer-activated unit's Exec lines, then "STAT <mtime> <path>" for each candidate path
DUMP = r'''
echo "### CRON"; crontab -l 2>/dev/null | grep -v '^\s*#'
for scope in --user --system; do
  for t in $(systemctl $scope list-timers --all --no-legend --plain 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i ~ /\.timer$/) print $i}'); do
    u=$(systemctl $scope show -p Unit --value "$t" 2>/dev/null)
    [ -n "$u" ] && systemctl $scope cat "$u" 2>/dev/null | grep -E '^ExecStart' | sed "s|^|### UNIT $scope $u |"
  done
done
'''


def kind_of(path):
    for k, rx in KINDS:
        if rx.search(path):
            return k
    return ""


def entries(text):
    """dump text -> [(where, path, kind)] for every copied tool path"""
    out, where = [], "cron"
    for line in text.splitlines():
        if line.startswith("### CRON"):
            where = "cron"
            continue
        src = where
        if line.startswith("### UNIT "):
            parts = line.split(" ", 4)
            src, line = f"{parts[2].lstrip('-')}:{parts[3]}", parts[4] if len(parts) > 4 else ""
        for p in PATH_RE.findall(line):
            k = kind_of(p)
            if k:
                out.append((src, p, k))
    seen, uniq = set(), []
    for e in out:
        if e not in seen:
            seen.add(e)
            uniq.append(e)
    return uniq


def ssh(host, script, timeout=120):
    p = subprocess.run(["timeout", str(timeout), "ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", host, "bash -s"],
                       input=script, capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def mtimes(host, paths):
    if not paths:
        return {}
    out = ssh(host, "".join("stat -c '%Y %n' " + shlex.quote(p) + " 2>/dev/null || echo MISSING " + shlex.quote(p) + "\n" for p in paths)) or ""
    got = {}
    for line in out.splitlines():
        a, _, b = line.partition(" ")
        got[b] = None if a == "MISSING" else float(a)
    return got


def report(host, ents, mt, now):
    lines, flagged, alerts = [], [], 0
    for where, p, k in ents:
        m = mt.get(p)
        age = (now - m) / 3600 if m else None
        al = age is None or age > ALERT_H
        alerts += al
        tag = "ALERT" if al else "copy"
        a = "missing" if age is None else f"{age:.0f} h"
        lines.append(f"TOOL-COPY {tag} {host} {where} {k} {p} ({a})")
        flagged.append(f"{host}:{p.rsplit('/', 1)[-1]}[{k},{a}]")
    return lines, flagged, alerts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hosts", default=",".join(HOSTS))
    ap.add_argument("--file", help="a saved dump (tests)")
    ap.add_argument("--host", default="file")
    a = ap.parse_args(argv)
    now = time.time()
    allf, alla = [], 0
    targets = [(a.host, open(a.file).read())] if a.file else [(h, None) for h in a.hosts.split(",") if h]
    for host, text in targets:
        text = text if text is not None else ssh(host, DUMP)
        if text is None:
            print(f"TOOL-COPY UNREAD {host}")
            continue
        ents = entries(text)
        mt = {} if a.file else mtimes(host, sorted({p for _, p, _ in ents}))
        if a.file:
            mt = {p: now for _, p, _ in ents}
        lines, fl, al = report(host, ents, mt, now)
        print("\n".join(lines)) if lines else None
        allf += fl
        alla += al
    print(f"TOOL-COPY {len(allf)} copies ({alla} ALERT > {ALERT_H:g} h): {' '.join(allf[:30])}" if allf else "TOOL-COPY ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
