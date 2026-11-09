#!/usr/bin/env python3
"""HBM-PLAN-1 E1 + E2 (one-block events for the final HBM switch, COORD RULING 11-09 02:33).
E1 MARGIN-1109: q_hub_ne macros on the S outline edge (inside the 4.32 kit core margin, MPL-0034 class of DIE-HBM-94
   23:18): u_sfus_Q__q0 and the u_pgp_Q__q0 column stack c1..c9 move +4.32 in y (abutted stack moves as one; every
   gap kept >= 4.32; their core clock taps follow). root: kit_core_margins_um [4.32, 0, 4.32, 4.32] (S margin 0, the
   die-edge form gen_phys.kit_core_area documents) because a +4.32 move of u_hb_idx__link would land on 9 station
   regs in the 8.64 street above it.
E2 GQI8-1109: the 4 gqi_issue instances in q_hub_ne/nw point at d44v_gqi's table (main
   plan_of_record/d44v_gqi cores/ot_hgi_coll_gqi_issue__172.8x233.28__d44v_gqi8.json, 6614 pins); plan_final3's
   d44v_split.json already holds the same 6614 rows in place (GQI-E8-PINS-1113) but its .gz is the stale 6618 table.
usage: e1e2.py IN_DIR OUT_DIR GQI8_JSON_GZ
"""
import copy, gzip, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plandir as PD

DY = 4.32
NE_MOVE = ["u_sfus_Q__q0"] + [f"u_pgp_Q__q0__c{i}" for i in range(1, 10)]
GQI_OLD = "cores/ot_hgi_coll_gqi_issue__172.8x233.28__d44v_split.json"
GQI_NEW = "cores/ot_hgi_coll_gqi_issue__172.8x233.28__d44v_gqi8.json"

def box(c):
    (x, y), (w, h) = c["origin_um"], c["outline_um"]
    if c.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, h = h, w
    return x, y, x + w, y + h

def main(src, dst, gqi_gz):
    PD.copy_dir(src, dst)
    P = PD.load(dst); base = copy.deepcopy(P)
    pt = P["partition_types"]
    ev = {"event": "HBM-PLAN-1-E1E2-1109", "lane": "HBM-PLAN-1", "ruling": "COORD RULING 11-09 02:33 ONE FINAL SWITCH PER DIE",
          "sha_in": PD.sha(PD.dump_plan(base)) if False else None, "moves": [], "taps": [], "margins": {}, "gqi": {}}
    # E1 q_hub_ne moves
    t = pt["q_hub_ne"]; W, H = t["outline_um"]
    cores = {c["inst"]: c for c in t["hard_cores"]}
    for n in NE_MOVE:
        c = cores[n]; x, y = c["origin_um"]
        c["origin_um"] = [x, round(y + DY, 4)]
        ev["moves"].append({"type": "q_hub_ne", "inst": n, "from": [x, y], "to": c["origin_um"]})
    for tp in t["clock"]["taps"]:
        base_name = tp["name"].split(".")[0]
        if base_name in NE_MOVE and tp.get("kind") == "core":
            x, y = tp["xy"]; tp["xy"] = [x, round(y + DY, 4)]
            ev["taps"].append({"type": "q_hub_ne", "tap": tp["name"], "from": [x, y], "to": tp["xy"]})
    # overlap / margin check (gap >= 4.32 between moved cores and every other core; inside the 4.32 margin)
    bx = {n: box(c) for n, c in cores.items()}
    bad = []
    for n in NE_MOVE:
        a = bx[n]
        if a[1] < DY - 1e-6 or a[0] < 0 or a[2] > W or a[3] > H - DY + 1e-6:
            bad.append(f"{n} outside margin {a}")
        for m, b in bx.items():
            if m == n: continue
            ix = min(a[2], b[2]) - max(a[0], b[0]); iy = min(a[3], b[3]) - max(a[1], b[1])
            if ix > 1e-6 and iy > 1e-6: bad.append(f"overlap {n}/{m}")
            # vertical gap to cores above/below that overlap in x, unless both moved (stack keeps abutment)
            if ix > 1e-6 and not (m in NE_MOVE) and iy <= 1e-6 and -iy < DY - 1e-6:
                bad.append(f"gap {n}/{m} {-iy:.3f}")
    if bad: raise SystemExit("E1 check: " + "; ".join(bad))
    # root margin
    pt["root"]["kit_core_margins_um"] = [4.32, 0.0, 4.32, 4.32]
    ev["margins"]["root"] = pt["root"]["kit_core_margins_um"]
    # E2 GQI table
    data = gzip.open(gqi_gz).read()
    rows = json.loads(data)
    old = json.loads((Path(dst) / GQI_OLD).read_bytes())
    if [r for r in old] != rows:
        raise SystemExit("E2: plan_final3 gqi table rows differ from d44v_gqi8")
    PD.write_file(dst, GQI_NEW, data)
    n = 0
    for tn in ("q_hub_ne", "q_hub_nw"):
        for c in pt[tn]["hard_cores"]:
            if c["module"] == "ot_hgi_coll_gqi_issue":
                if c["pins_file"] != GQI_OLD: raise SystemExit(f"E2: {tn}.{c['inst']} pins_file {c['pins_file']}")
                c["pins_file"] = GQI_NEW; n += 1
    if n != 4: raise SystemExit(f"E2: {n} gqi instances, expected 4")
    ev["gqi"] = {"instances": n, "old_table": GQI_OLD, "new_table": GQI_NEW, "new_table_sha256": PD.sha(data),
                 "rows": len(rows), "note": "rows equal plan_final3's in-place table; repoint only"}
    # preservation: only the touched keys differ
    for tn in pt:
        a, b = base["partition_types"][tn], pt[tn]
        keys = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
        allow = {"q_hub_ne": {"hard_cores", "clock"}, "q_hub_nw": {"hard_cores"}, "root": {"kit_core_margins_um"}}.get(tn, set())
        if keys - allow: raise SystemExit(f"preservation {tn}: {sorted(keys - allow)}")
    for k in P:
        if k != "partition_types" and P[k] != base[k]: raise SystemExit(f"preservation top key {k}")
    P["note"] = "HBM-PLAN-1 E1E2-1109 (q_hub_ne S-edge macro +4.32, root S margin 0, gqi8 table) <- " + P["note"]
    ev["sha_in"] = PD.sha(PD.dump_plan(base))
    ev["sha_in_file"] = PD.sha((Path(src) / "die_plan.json").read_bytes())
    ev["sha_out"] = PD.write_plan(dst, P)
    ev["pin_cycles"] = 0
    PD.write_event(dst, "e1e2_1109_event.json", ev)
    print(json.dumps({k: ev[k] for k in ("sha_in_file", "sha_out")}), len(ev["moves"]), len(ev["taps"]))

if __name__ == "__main__":
    main(*sys.argv[1:4])
