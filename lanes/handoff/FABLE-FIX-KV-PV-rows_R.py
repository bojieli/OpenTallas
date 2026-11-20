"""FABLE-FIX-KV-PV class R (11-20, COORD-approved form): reset_replicate tail_clear "sync" on every kv3_pv* rsync row.
usage: python3 -I rows_R.py PLAN_C.json [--check]   (in place unless --check; needs tools at or after main 6e2f4ee27af8)
Effect per type: the ot_dp_rtail copies of u_rs_ri_* lose the spine on their clear pins; reset release unchanged (same edge),
assert +copy_depth clk (4 on the live rows) at every pv core, same edge for all copies.  0 data cycles, 0 lanes, 0 flops."""
import json, os, re, sys, tempfile, hashlib
from pathlib import Path
p = Path(sys.argv[1]); check = "--check" in sys.argv
b = p.read_bytes(); plan = json.loads(b)
rows = []
for tn, t in sorted(plan["partition_types"].items()):
    if not re.fullmatch(r"kv3_pv.*", tn):
        continue
    for r in t.get("reset_replicate") or []:
        if r.get("form") == "rsync":
            rows.append(dict(type=tn, driver=r.get("driver") or r.get("driver_re"), copy_depth=r.get("copy_depth"), was=r.get("tail_clear", "async")))
            r["tail_clear"] = "sync"
print(json.dumps(dict(rows=len(rows), types=sorted({x["type"] for x in rows}), detail=rows), indent=1))
if not check and rows:
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".rowsR.")
    with os.fdopen(fd, "w") as f:
        json.dump(plan, f, indent=1)
    os.replace(tmp, p)
    print("plan sha", hashlib.sha256(p.read_bytes()).hexdigest()[:12])
