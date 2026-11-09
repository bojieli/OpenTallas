#!/usr/bin/env python3
"""HBM-PLAN-1: switch table of the one final HBM switch.
For every HBM type: wave key (plan + bind), new key, what changed (plan type block, bound type RTL), superseded = yes when
either changed.  usage: switch_table.py NEWPLAN NEWBIND_RTL OUT.tsv"""
import json, sys, hashlib
from pathlib import Path
F2 = "/srv/opentallas-scratch2/claude/die-hbm-93/plan_final2/die_plan.json"
F3 = "/srv/opentallas-scratch2/claude/die-hbm-93/plan_final3/die_plan.json"
VJ = Path("/srv/opentallas-scratch3/claude/die-hbm-93/lat/bind_lat_vJ/rtl")
B3 = Path("/srv/opentallas-scratch3/claude/die-hbm-93/lat/bind_F3/rtl")
FINAL3 = {"NE_io", "NW_io", "q_hub_ne", "q_hub_nw", "q_sm0", "q_sm1", "q_sm2", "q_sm3", "q_spb0", "q_spb0__physical_v1", "vsN0"}
def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest()[:12] if p.is_file() else "-"
def main(newplan, newrtl, out):
    new = json.load(open(newplan)); newrtl = Path(newrtl)
    f2, f3 = json.load(open(F2)), json.load(open(F3))
    rows = []
    for t in sorted(new["partition_types"]):
        old = (f3 if t in FINAL3 else f2)["partition_types"].get(t)
        nb = new["partition_types"][t]
        blocks = sorted(k for k in set(nb) | set(old or {}) if json.dumps(nb.get(k), sort_keys=True) != json.dumps((old or {}).get(k), sort_keys=True))
        mod = nb.get("module", t)
        cands = [f"hbm_arch_{t}.sv", f"{mod}.sv", f"{mod}__{t}.sv"]
        f = next((c for c in cands if (newrtl / c).is_file()), cands[0])
        o = md5((B3 if t in FINAL3 else VJ) / f); n = md5(newrtl / f)
        if n == "-":
            raise SystemExit(f"no bound file for {t}: {cands}")
        rtl = "same" if o == n else f"{o}->{n}"
        sup = "SUPERSEDED" if blocks or o != n else "keep"
        rows.append([t, "final3+F3" if t in FINAL3 else "final2+vJ", ",".join(blocks) or "-", rtl, sup])
    with open(out, "w") as fh:
        fh.write("type\twave_key\tplan_blocks_changed\tbound_rtl_md5\trow\n")
        for r in rows: fh.write("\t".join(r) + "\n")
    print(sum(r[-1] == "SUPERSEDED" for r in rows), "superseded of", len(rows))
if __name__ == "__main__":
    main(*sys.argv[1:4])
