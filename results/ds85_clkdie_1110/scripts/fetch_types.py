#!/usr/bin/env python3
"""DS85: copy (read-only sources, never written) each selected type view's base/6_final.v + 6_final.spef to
epyc8 <W>/types/<type>/ : from the run host when the file is still there, else from the AGIdock signed archive
(streamed through localhost, which alone has the archive key)."""
import glob
import json
import os
import shlex
import subprocess
import sys

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = "/srv/opentallas-scratch2/claude/die-s81-85/clkdie"
ARCH = "ubuntu@155.103.253.53"
AK = ["-i", os.path.expanduser("~/.ssh/agidock_ot"), "-o", "IdentitiesOnly=yes"]
sel = json.load(open(f"{B}/inv/type_select.json"))["selection"]
cache = json.load(open(os.path.expanduser("~/.local/state/fleet-viz/release_tree_plan_cache.json")))
arch = {}
for r in cache["signed_records"]:
    if r.get("routed_db") and r.get("archive"):
        arch.setdefault(r["routed_db"], r["archive"])
where = {}
for f in glob.glob(f"{B}/inv/odb_*.txt"):
    h = f.split("odb_")[1][:-4]
    for ln in open(f):
        x = ln.split(" ", 2)
        if len(x) == 3:
            where.setdefault(x[2].strip(), h)


def sh(cmd, **k):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600, **k)


log = {}
only = set(sys.argv[1:])
for ty, v in sorted(sel.items()):
    if only and ty not in only:
        continue
    base = os.path.dirname(v["odb"])
    dst = f"{W}/types/{ty}"
    chk = sh(f"ssh -o BatchMode=yes epyc8 test -s {dst}/6_final.spef -a -s {dst}/6_final.v && echo have")
    if "have" in chk.stdout:
        log[ty] = dict(kind=v["kind"], src="already", base=base)
        continue
    h = where.get(v["odb"])
    ok = False
    src = None
    r = None
    if h:
        r = sh(f"ssh -o BatchMode=yes epyc8 {shlex.quote(f'mkdir -p {dst} && scp -q {h}:{base}/6_final.v {h}:{base}/6_final.spef {dst}/')}")
        ok = r.returncode == 0
        src = f"{h}:{base}"
    if not ok and v["odb"] in arch:
        ab = arch[v["odb"]] + base
        r = sh(f"ssh -o BatchMode=yes {' '.join(AK)} {ARCH} {shlex.quote(f'tar -C {ab} -cf - 6_final.v 6_final.spef')} | "
               f"ssh -o BatchMode=yes epyc8 {shlex.quote(f'mkdir -p {dst} && tar -C {dst} -xf -')}")
        ok = r.returncode == 0
        src = f"agidock:{ab}"
    log[ty] = dict(kind=v["kind"], src=src if ok else None, base=base, ok=ok, err=None if ok else (r.stderr[-300:] if r else "no source"))
    print(ty, v["kind"], "OK" if ok else "FAIL", log[ty]["src"], flush=True)
json.dump(log, open(f"{B}/inv/fetch_log.json", "w"), indent=1)
