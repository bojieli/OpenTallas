"""old vs new clock_landings: write_rtl(plan, landing=sidecar) for every type; usage: bytecheck.py TOOLS_DIE_PLAN OUT PLAN SIDECAR"""
import sys, json, hashlib
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import gen_rtl as G
out, plan, side = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
raw = json.load(open(plan)); land = json.load(open(side))
G.write_rtl(raw, out, rtl_root=(sys.argv[5] if len(sys.argv)>5 else None), plan_path=plan, landing=land)
h = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*.sv"))}
print(len(h), "files", hashlib.sha256(json.dumps(h, sort_keys=True).encode()).hexdigest()[:16])
