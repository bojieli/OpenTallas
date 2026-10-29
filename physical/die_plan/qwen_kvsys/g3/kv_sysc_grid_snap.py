#!/usr/bin/env python3
"""DIE-KV-13 10-28 (COORD faf936223 item 1; KV-KITS macro grid finding, ~/coord/lanes/KV-CORES.md 13:1x): kv3_sys_c hard-macro
origins snapped so their pins sit on the KV core track grid (child pins on 0.012 + 0.048k, M4/M5 tracks at pitch/2 = 0.024):
4 d2d SRAMs y +12 nm, ot_qkvd_ucie_x64_phy x +12 nm, ot_rom_64x32_m2 y +12 nm (snaps CHECKED by KV-KITS with the FG2 macro
pin-grid check).  Plan delta on die_plan contents only (origin_um); idempotent (an already-snapped origin is kept); fails
closed on an origin that is neither the old nor the snapped value.

    kv_sysc_grid_snap.py PLAN_IN.json PLAN_OUT.json
"""
import json
import sys

SNAP = {  # module -> [(old origin, snapped origin)]
    "d2d_sram_1r1w_64x137_m1_r2c2_p288": [((596.16, y), (596.16, round(y + 0.012, 3))) for y in (17.28, 103.68, 190.08, 276.48)],
    "ot_qkvd_ucie_x64_phy": [((691.2, 60.48), (691.212, 60.48))],
    "ot_rom_64x32_m2": [((302.4, 250.56), (302.4, 250.572))],
}


def snap(plan, tn="kv3_sys_c"):
    rows = []
    for c in plan["partition_types"][tn]["contents"]:
        if c.get("module") not in SNAP:
            continue
        o = tuple(round(v, 3) for v in c["origin_um"])
        hit = [(a, b) for a, b in SNAP[c["module"]] if o in (a, b)]
        if not hit:
            raise SystemExit(f"{c['inst']}: origin {o} is neither a known pre-snap nor a snapped origin")
        a, b = hit[0]
        rows.append(dict(inst=c["inst"], module=c["module"], before=list(o), after=list(b), moved=o != b))
        c["origin_um"] = list(b)
    n = sum(len(v) for v in SNAP.values())
    if len(rows) != n:
        raise SystemExit(f"{tn}: {len(rows)} of {n} snap macros found")
    return rows


if __name__ == "__main__":
    p = json.load(open(sys.argv[1]))
    r = snap(p)
    json.dump(p, open(sys.argv[2], "w"), indent=1)
    print(json.dumps(dict(snapped=sum(x["moved"] for x in r), rows=r)))
