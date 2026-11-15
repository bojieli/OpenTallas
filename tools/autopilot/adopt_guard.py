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
        cmd = " ; ".join(f"test -e {shlex.quote(f)} || echo {shlex.quote(f)}" for f in files)
        rc, txt = run((["bash", "-c", cmd] if h == "localhost" else SSH + [h, cmd]))
        out[h] = sorted(set(txt.split())) if rc == 0 or txt else list(files)
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


def guard(cfg, die, check=False, run=sh, log=print):
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
    return left_n == 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("die")
    ap.add_argument("--config", default=os.path.expanduser("~/coord/autopilot/kit_wave.json"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if guard(json.load(open(a.config)), a.die, a.check) else 1)
