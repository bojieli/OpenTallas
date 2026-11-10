#!/usr/bin/env python3
"""DS85: copy each no-routed-view type's newest CTS/GRT-stage odb (inv/cts_select.json) read-only from its run host
to epyc8 <W>/types_cts/<type>/stage.odb (scp pulled by epyc8; source never written)."""
import json, os, shlex, subprocess
from concurrent.futures import ThreadPoolExecutor
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = "/srv/opentallas-scratch2/claude/die-s81-85/clkdie"
sel = json.load(open(f"{B}/inv/cts_select.json"))
def one(kv):
    ty, v = kv
    dst = f"{W}/types_cts/{ty}"
    src = v["odb"] if v["host"] == "epyc8" else f"{v['host']}:{v['odb']}"
    cmd = f"mkdir -p {dst} && test -s {dst}/stage.odb || {'cp' if v['host']=='epyc8' else 'scp -q'} {src} {dst}/stage.odb && echo '{json.dumps(v)}' > {dst}/source.json"
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "epyc8", cmd], capture_output=True, text=True, timeout=3600)
    print(ty, "OK" if r.returncode == 0 else "FAIL " + r.stderr[-200:], flush=True)
with ThreadPoolExecutor(6) as ex:
    list(ex.map(one, sorted(sel.items())))
