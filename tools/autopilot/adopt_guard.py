#!/usr/bin/env python3
"""ADOPT-GUARD (KIT-OPS-6 11-14, COORD item 9): run BEFORE a READY+ADOPT switches a die's wave plan / src / bind (kit_wave.json).
Twice on 11-14 a die bind manifest named files in a private lane tree that existed on ONE host (QC tree6 on epyc9, KV kv-102/cg3/kv_out15
on epyc10); every other host then reported SRC-INCOMPLETE and the die's whole wave stopped.  This checks that every input the wave
reads for the die (kit_wave.src_inputs: plan, src tools, asbuilt / script, bind_report.json and every HDL source the bind names)
exists on ALL the die's wave hosts, copies what is missing from a host that has it (tar over ssh through the hub, existing files
kept = rsync --ignore-existing, one ADOPT-GUARD log line per copy) and exits 1 listing whatever is still missing (fail closed).
    adopt_guard.py DIE [--config kit_wave.json] [--check]      (--check: list only, copy nothing)"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
SSH = ["ssh", "-n", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes", "-o", "ControlPath=none"]
OK_PATH = re.compile(r"^/srv/opentallas-scratch[0-9]*/claude/[^\0\s]+$")
MAX_MB = 2048


def sh(argv, timeout=900):
    r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout


def missing_by_host(files, hosts, run=sh):
    """{host: [missing file]} ('' host list entry 'localhost' runs locally); a host that cannot be reached is reported with every file"""
    out = {}
    for h in hosts:
        got, ok = set(), True
        for i in range(0, len(files), 100):            # chunks: one ssh command line must stay below ARG_MAX (S81 has thousands of sources)
            cmd = " ; ".join(f"test -e {shlex.quote(f)} || echo {shlex.quote(f)}" for f in files[i:i + 100])
            rc, txt = run(["bash", "-c", cmd] if h == "localhost" else SSH + [h, cmd])
            if rc != 0 and not txt:
                ok = False
                break
            got |= set(txt.split())
        out[h] = sorted(got) if ok else list(files)
    return out


def sync_missing(miss, hosts, run=sh, log=print):
    """copy each missing file (or dir) from a host that has it to the hosts that lack it (keep-old-files); -> still-missing {host: [f]}"""
    left = {}
    for h, fs in miss.items():
        for f in fs:
            if not OK_PATH.match(f) or ".." in f:
                left.setdefault(h, []).append(f); continue
            src = next((g for g in hosts if g != h and f not in miss.get(g, [])), None)
            if not src:
                left.setdefault(h, []).append(f); continue
            q = shlex.quote(f)
            pipe = (f"{' '.join(SSH)} {src} 'test -e {q} && [ $(du -sm {q} | cut -f1) -le {MAX_MB} ] && tar -C / -cf - {shlex.quote(f.lstrip('/'))}' | "
                    f"{' '.join(SSH).replace('-n ', '')} {h} 'mkdir -p {shlex.quote(os.path.dirname(f))} && tar -C / -xf - --keep-old-files'")
            rc, _ = run(["bash", "-c", "set -o pipefail; " + pipe])
            log(f"ADOPT-GUARD copy {src}:{f} -> {h} rc={rc}")
            if rc:
                left.setdefault(h, []).append(f)
    return left


TREE_DIRS = ("tools", "rtl", "physical/die_plan", "physical/common_flow")
TREE_MIN_FRAC = 0.99


def tree_stats(host, src, run=sh, dirs=TREE_DIRS):
    """{dir: (file count, manifest sha12)} of the die src tree on one host (KIT-OPS-6 11-14 item 9b: kvgeom6 passed the per-file check, yet epyc7's
    tools/ held 1 file against 17,486 and rtl/ was absent).  Manifest = sha256 of the sorted 'relative path size' lines; a missing dir = (0, '')."""
    out = {}
    for d in dirs:
        q = shlex.quote(f"{src}/{d}")
        cmd = f"test -d {q} && {{ n=$(find {q} -type f | wc -l); m=$(cd {q} && find . -type f -printf '%P %s\\n' | LC_ALL=C sort | sha256sum | cut -c1-12); echo \"$n $m\"; }} || echo '0 -'"
        rc, txt = run(["bash", "-c", cmd] if host == "localhost" else SSH + [host, cmd])
        f = txt.split()
        out[d] = (int(f[0]), f[1] if len(f) > 1 and f[1] != "-" else "") if f and f[0].isdigit() else (0, "")
    return out


def tree_gaps(stats, frac=TREE_MIN_FRAC):
    """{host: [dir]}: a host whose count of a dir is below frac of the best copy on any host (or that lacks it) has a gap"""
    gaps = {}
    for d in TREE_DIRS:
        best = max((st[d][0] for st in stats.values() if d in st), default=0)
        if not best:
            continue
        for h, st in stats.items():
            if d in st and st[d][0] < frac * best:
                gaps.setdefault(h, []).append(d)
    return gaps


def tree_fill(src, stats, gaps, run=sh, log=print):
    """copy each gap dir from the host with the most files (tar over ssh, --keep-old-files = rsync --ignore-existing); -> still-gapped {host: [dir]}"""
    left = {}
    for h, ds in gaps.items():
        for d in ds:
            donor = max((g for g in stats if g != h), key=lambda g: stats[g][d][0], default=None)
            if donor is None or stats[donor][d][0] == 0:
                left.setdefault(h, []).append(d); continue
            q = shlex.quote(f"{src}/{d}")
            pipe = (f"{' '.join(SSH)} {donor} 'cd {shlex.quote(src)} && tar -cf - {shlex.quote(d)}' | "
                    f"{' '.join(SSH).replace('-n ', '')} {h} 'mkdir -p {shlex.quote(src)} && tar -C {shlex.quote(src)} -xf - --keep-old-files'")
            rc, _ = run(["bash", "-c", "set -o pipefail; " + pipe], 3600)
            log(f"ADOPT-GUARD tree copy {donor}:{src}/{d} -> {h} ({stats[h][d][0]} -> {stats[donor][d][0]} files) rc={rc}")
            if rc:
                left.setdefault(h, []).append(d)
    return left


def guard_tree(cfg, die, hosts, check=False, run=sh, log=print):
    src = str((cfg["dies"][die].get("src")) or "")
    if not src or len(hosts) < 2:
        return True
    stats = {h: tree_stats(h, src, run) for h in hosts}
    gaps = tree_gaps(stats)
    for h, st in sorted(stats.items()):
        log(f"ADOPT-GUARD tree {die} {h}: " + " ".join(f"{d}={n}/{m}" for d, (n, m) in st.items()))
    if gaps and not check:
        left = tree_fill(src, stats, gaps, run, log)
        if len(left) < len(gaps) or any(len(v) for v in left.values()) < len(gaps):
            stats2 = {h: tree_stats(h, src, run) for h in hosts}
            gaps = tree_gaps(stats2)
        else:
            gaps = left
    for h, ds in sorted(gaps.items()):
        log(f"ADOPT-GUARD TREE GAP {h}:{src} {' '.join(ds)}")
    log(f"ADOPT-GUARD tree {die}: {'OK' if not gaps else 'FAIL closed'}")
    return not gaps


def guard(cfg, die, check=False, run=sh, log=print, no_tree=False):
    import kit_wave as K
    d = cfg["dies"][die]
    hosts = list(d.get("gen_hosts") or cfg.get("gen_hosts") or d.get("hosts") or cfg.get("hosts") or [])
    _trees, files = K.src_inputs(cfg, die)
    files = sorted(set(files))
    miss = missing_by_host(files, hosts, run)
    n = sum(len(v) for v in miss.values())
    log(f"ADOPT-GUARD {die}: {len(files)} inputs, {len(hosts)} wave hosts, {n} missing host/file pairs")
    if n and not check:
        left = sync_missing({h: v for h, v in miss.items() if v}, hosts, run, log)
        miss = left
    left_n = sum(len(v) for v in miss.values())
    for h, v in sorted(miss.items()):
        for f in v:
            log(f"ADOPT-GUARD MISSING {h}:{f}")
    log(f"ADOPT-GUARD {die}: {'OK' if not left_n else 'FAIL closed: ' + str(left_n) + ' still missing'}")
    tree_ok = True if no_tree else guard_tree(cfg, die, hosts, check, run, log)
    return left_n == 0 and tree_ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("die")
    ap.add_argument("--config", default=os.path.expanduser("~/coord/autopilot/kit_wave.json"))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-tree", action="store_true", help="skip the whole-src-tree comparison (per-top-dir counts + manifest sha)")
    a = ap.parse_args()
    sys.exit(0 if guard(json.load(open(a.config)), a.die, a.check, no_tree=a.no_tree) else 1)
