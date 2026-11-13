"""CLAND-RELAY-2 (from GEN-CLASS-1's lister): strap-K / boot changes of the CLAND-RING-LOCALITY reach defaults vs the
plan as it stands (WREG +1 only where the plan has NO explicit WREG for the bus; reader START -1 where the reach stage
fires), plus the explicit-WREG buses whose write chunk the branch changes (64 -> 16, 0 cycles, no K).
usage: python3 -I kdelta_list.py TOOLS_DIE_PLAN_DIR PLAN.json SIDECAR.json"""
import json, sys
from collections import defaultdict
sys.path.insert(0, sys.argv[1])
import clock_landings as CL
plan = json.load(open(sys.argv[2])); sc = json.load(open(sys.argv[3]))
ca = sc.get("count_aligned", sc) if isinstance(sc.get("count_aligned", sc), dict) else {}
strap = bool(ca.get("strap_form"))
ports = {p["id"]: p for p in plan["ports"]}; ptype = {p["name"]: p["type"] for p in plan["partitions"]}
rows = defaultdict(lambda: dict(n=0))
cap = ca.get("ports", {}) if isinstance(ca.get("ports", {}), dict) else {}
for pid in cap:
    p = ports.get(pid)
    if p is None:
        continue
    q, bus = p["dst"]["part"], p["dst"]["bus"]; t = ptype[q]
    c = (plan["partition_types"].get(t) or plan["partition_types"].get(t.split("__")[0]) or {}).get("clock") or {}
    cfg = c.get("landing_ring_wreg")
    old_w = bool(isinstance(cfg, dict) and bus in (cfg.get("buses") or []))
    new = CL.ring_write_reg(plan, t, bus) if strap else None
    r = CL.reader_start_reach(plan, t) if strap else 0
    row = rows[(t, bus)]; row["n"] += 1
    row.update(dk=int(bool(new)) - int(old_w) - r, boot=r, w=CL.plan_ring_width(plan, t, bus), old_w=old_w,
               wc_old=(cfg.get("write_chunk", 64) if old_w else None), wc_new=((new or {}).get("write_chunk", 64) if new else None))
print(f"plan {sys.argv[2]}  sidecar {sys.argv[3]}  strap_form={strap}  ca ports={len(cap)}")
kt = sorted({t for (t, b), v in rows.items() if v["dk"] or v["boot"]})
wct = sorted({t for (t, b), v in rows.items() if v["old_w"] and v["wc_old"] != v["wc_new"]})
nk = sum(1 for v in rows.values() if v["dk"]); nb = sum(1 for v in rows.values() if v["boot"])
nwc = sum(1 for v in rows.values() if v["old_w"] and v["wc_old"] != v["wc_new"])
inst_k = sum(v["n"] for v in rows.values() if v["dk"])
print(f"buses with strap K change: {nk} ({inst_k} ring instances); buses with boot +1 (reader START): {nb}; "
      f"types with K/boot change: {len(kt)}; explicit-WREG buses with write chunk change: {nwc} on {len(wct)} types")
for (t, b), v in sorted(rows.items()):
    if v["dk"] or v["boot"] or (v["old_w"] and v["wc_old"] != v["wc_new"]):
        print(f"  {t}.{b}  W={v['w']}  instances={v['n']}  K{v['dk']:+d}  boot+{v['boot']}  "
              f"wreg {'explicit' if v['old_w'] else ('reach' if v['wc_new'] else '-')}"
              + (f"  write_chunk {v['wc_old']}->{v['wc_new']}" if v["old_w"] and v["wc_old"] != v["wc_new"] else ""))
