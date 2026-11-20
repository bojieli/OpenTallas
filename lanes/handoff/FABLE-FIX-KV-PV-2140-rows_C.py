"""FABLE-FIX-KV-PV-2140 class C (11-20): pv hold form C = lockup at every tap-group boundary of the pad delay lines.
usage: python3 -I rows_C.py PLAN_C.json [--check]      (in place unless --check; needs tools with kit_dly_lockup.py / budgets.r_dly_lockup)
Rows (budgets, gen-only: no bind input changes, 0 cycles, 0 lanes; LATCHECK / R8 unchanged):
  r_dly_lockup            {"kv3_pv": {"seg": 8, "tail_groups": 0}}   every kv3_pv* kit: trunks split into <= 8-stage segments, tail copies one group
                          per stage, ot_dp_lk u_fl_* latch on every segment boundary, delay -> delay input and tail copy -> core pin
  r_dly_spread_station_um {"kv3_pv": 405}                            station form for the latch-free runs (form A, main 9cdfbe5bc0f)
  r_dly_spread            must already cover kv3_pv (list form or true); the script refuses otherwise instead of widening it."""
import hashlib, json, os, sys, tempfile
from pathlib import Path
p = Path(sys.argv[1]); check = "--check" in sys.argv
plan = json.loads(p.read_bytes())
b = plan.setdefault("budgets", {})
sp = b.get("r_dly_spread", False)
if not (sp is True or (isinstance(sp, list) and any(x and "kv3_pv".startswith(x) for x in sp))):
    sys.exit(f"REFUSED: budgets.r_dly_spread = {sp!r} does not cover every kv3_pv* type")
was = dict(r_dly_lockup=b.get("r_dly_lockup"), r_dly_spread_station_um=b.get("r_dly_spread_station_um"))
lk = dict(b.get("r_dly_lockup") or {}); lk["kv3_pv"] = {"seg": 8, "tail_groups": 0}; b["r_dly_lockup"] = lk
st = dict(b.get("r_dly_spread_station_um") or {}); st.setdefault("kv3_pv", 405); b["r_dly_spread_station_um"] = st
types = sorted(t for t in plan["partition_types"] if t.startswith("kv3_pv"))
print(json.dumps(dict(types=len(types), names=types, was=was, now=dict(r_dly_lockup=lk, r_dly_spread_station_um=st)), indent=1))
if not check:
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".rowsC.")
    with os.fdopen(fd, "w") as f:
        json.dump(plan, f, indent=1)
    os.replace(tmp, p)
    print("plan sha", hashlib.sha256(p.read_bytes()).hexdigest()[:12])
