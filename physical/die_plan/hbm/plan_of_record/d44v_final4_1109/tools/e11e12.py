#!/usr/bin/env python3
"""HBM-PLAN-1 E11 + E12 (COORD 11-09 03:0x adds to the final HBM switch).
E11 SPU0-BAND-1109: q_spu0__physical_v1 a3 GRT-0116 (M5 30,571 / M4 9,110 overflow gcells at 2-4% signal usage) sits in
   the type's own NS die band x 380.16-1071.36 [M5, M7] die_share 1.0: the type's three S<->N FT columns L8x1 (3070 b,
   x 479-538), L21x5 (2560 b, x 1022-1080) and L63wx1 (210 b, x 773-832) run INSIDE that band, so partition_ft_reserve
   blocks every M5/M7 track they need; worst boxes are L21x5 station 2 at (840-845, 1180-1186) on every congestion
   report.  Fix: the band's M5 claim drops to die_share 0.5 (M7 stays 1.0): about 7.2k M5 tracks of 14.4k return to the
   type for ~5.8k vertical bits.  q_spu0 has the identical block (same slots, same band) and gets the same edit.
E12 SPB2-NPIN-1109: q_spb2__physical_v1 a3 GRT-0116 (285 of 340 overflow gcells on M6, N-face pin cluster): L40_o
   (1064 b, 6.0 pins/um) window [782.4, 960.0] sits over u_xc_Q2 (x 717-959, top y 1468.8, 34.56 um below the N edge)
   while its source is u_xc_Q3 (x 1322-1564).  Window moves into the macro-free gap [1080.0, 1316.16] (4.5 pins/um);
   partner q_spu1__physical_v1 L40x1 in_window (S face) moves the same die x ([768.96, 1005.12] local); the 13
   internal_stations of bus:L40_o keep their regs, from_um follows the window centre.  The spu1 L40x1 chain is then
   re-sited by ft_s0_resite.py (separate step).  0 PIN CYCLES unless that re-site adds any (its ledger says).
usage: e11e12.py IN_DIR OUT_DIR
"""
import copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plandir as PD

def main(src, dst):
    PD.copy_dir(src, dst)
    P = PD.load(dst); base = copy.deepcopy(P); pt = P["partition_types"]
    ev = {"event": "HBM-PLAN-1-E11E12-1109", "lane": "HBM-PLAN-1", "ruling": "COORD 11-09 03:0x message to HBM-PLAN-1 (q_spu0 pv1 FT reservation, q_spb2 pv1 N-face pin spread)", "e11": [], "e12": {}}
    for tn in ("q_spu0__physical_v1", "q_spu0"):
        bands = pt[tn]["die_ft_bands"]; new = []
        for b in bands:
            if b["dir"] == "NS" and b["span_um"] == [380.16, 1071.36] and b["layers"] == ["M5", "M7"] and b.get("die_share", 1.0) == 1.0:
                m5 = dict(b, layers=["M5"], die_share=0.5, note=b["note"] + " | HBM-PLAN-1 E11 1109: M5 share 1.0 -> 0.5 (type FT columns L8x1/L21x5/L63wx1 run inside the band)")
                m7 = dict(b, layers=["M7"])
                new += [m5, m7]; ev["e11"].append({"type": tn, "from": b, "to": [m5, m7]})
            else:
                new.append(b)
        if len(new) != len(bands) + 1: raise SystemExit(f"E11: band not found on {tn}")
        pt[tn]["die_ft_bands"] = new
    # E12
    OLD, NEW = [782.4, 960.0], [1080.0, 1316.16]
    DX = 311.04  # spb2 local x - spu1 local x (both MY, origins 20848.32 / 20813.76, widths 1745.28 / 1468.8)
    t = pt["q_spb2__physical_v1"]
    b = [b for b in t["buses"] if b["name"] == "L40_o"][0]
    if b["window_um"] != OLD or b["face"] != "N": raise SystemExit("E12: L40_o window")
    occ = [(x["window_um"], x["name"]) for x in t["buses"] if x.get("face") == "N" and x is not b]
    occ += [(s[k + "_window_um"], s["name"]) for s in t["ft_slots"] for k in ("in", "out") if s[k + "_face"] == "N"]
    for w, n in occ:
        if w[0] < NEW[1] and NEW[0] < w[1]: raise SystemExit(f"E12: overlaps {n} {w}")
    for c in t["hard_cores"]:
        (x, y), (cw, ch) = c["origin_um"], c["outline_um"]
        if x < NEW[1] and NEW[0] < x + cw: raise SystemExit(f"E12: new window over core {c['inst']}")
    b["window_um"] = NEW
    cx = round((NEW[0] + NEW[1]) / 2, 3); n = 0
    for s in t["internal_stations"]:
        if s["conn"] == "bus:L40_o":
            s["from_um"] = [cx, s["from_um"][1]]; n += 1
    u = pt["q_spu1__physical_v1"]
    s = [s for s in u["ft_slots"] if s["name"] == "L40x1"][0]
    old_u = [round(v - DX, 3) for v in OLD]
    if [round(v, 3) for v in s["in_window_um"]] != old_u or s["in_face"] != "S": raise SystemExit(f"E12: spu1 L40x1 window {s['in_window_um']}")
    new_u = [round(v - DX, 3) for v in NEW]
    occ = [(x["window_um"], x["name"]) for x in u["buses"] if x.get("face") == "S"]
    occ += [(z[k + "_window_um"], z["name"] + k) for z in u["ft_slots"] for k in ("in", "out") if z[k + "_face"] == "S" and z is not s]
    for w, nm in occ:
        if w[0] < new_u[1] and new_u[0] < w[1]: raise SystemExit(f"E12: spu1 overlaps {nm} {w}")
    s["in_window_um"] = new_u
    ev["e12"] = {"spb2_L40_o": {"from": OLD, "to": NEW, "pins_per_um": round(1064 / (NEW[1] - NEW[0]), 2)},
                 "spu1_L40x1_in": {"from": old_u, "to": new_u}, "internal_stations_from_um": n,
                 "die_x_check": "spb2 MY origin 20848.32 w 1745.28, spu1 MY origin 20813.76 w 1468.8: local x differ by 311.04"}
    for tn in pt:
        a, c = base["partition_types"][tn], pt[tn]
        keys = {k for k in set(a) | set(c) if a.get(k) != c.get(k)}
        allow = {"q_spu0__physical_v1": {"die_ft_bands"}, "q_spu0": {"die_ft_bands"},
                 "q_spb2__physical_v1": {"buses", "internal_stations"}, "q_spu1__physical_v1": {"ft_slots"}}.get(tn, set())
        if keys - allow: raise SystemExit(f"preservation {tn}: {sorted(keys - allow)}")
    for k in P:
        if k != "partition_types" and P[k] != base[k]: raise SystemExit(f"preservation top key {k}")
    P["note"] = "HBM-PLAN-1 E11E12-1109 (q_spu0(+pv1) NS band M5 share 0.5; q_spb2pv1 L40_o N window into the macro gap) <- " + P["note"]
    ev["sha_in"] = PD.sha((Path(src) / "die_plan.json").read_bytes())
    ev["sha_out"] = PD.write_plan(dst, P); ev["pin_cycles"] = 0
    PD.write_event(dst, "e11e12_1109_event.json", ev)
    print(ev["sha_in"][:12], "->", ev["sha_out"][:12], json.dumps(ev["e12"])[:300])

if __name__ == "__main__":
    main(*sys.argv[1:3])
