#!/usr/bin/env python3
"""QC-CORES-2 A0-CLK-R3 (GEOM-19 (4)): signal-gap / corridor track capacity re-deducted for the island footprints.
Island = 8.64 x 8.64 um, blocks M1-M5 (driver cells + M5->M1 stack); M9->M5 drop stack through M6/M7 taken as a 1.0-um via column
(assumption); clock legs = M7 vertical / M6 horizontal, NDR 2W2S taken as 3 tracks per leg (assumption).  ASAP7 pitches
M2/M3 0.036, M4/M5 0.048, M6/M7 0.064 um.  Capacity is per cross-section at the island; demand is listed only where a
number exists (labelled).  usage: a0_gap_capacity.py R3PLAN OUT.json"""
import json, sys
P = {"M2": 0.036, "M3": 0.036, "M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064}
plan = json.load(open(sys.argv[1]))["cores"]["nk"]
isl = plan["islands"]
ISL, VIA, NDR = 8.64, 1.0, 3
# (name, along-direction, width across the routing direction, layers routed along it, island names inside)
regions = []
for nm, w, lo, hi in (("bottom margin y0-22.176", 22.176, 0, 22.176), ("ROM gap 0-1", 20.016, 132.336, 152.352),
                      ("ROM gap 1-2", 20.016, 262.512, 282.528), ("ROM gap 2-3", 20.016, 392.688, 412.704),
                      ("ROM gap 3-4", 20.016, 522.864, 542.88), ("ROM/LSL strip", 20.88, 653.04, 673.92),
                      ("LSL gap 0-1", 20.112, 814.32, 834.432), ("LSL gap 1-2", 20.112, 974.832, 994.944)):
    ins = sorted(k for k, v in isl.items() if lo <= v["xy"][1] <= hi)
    regions.append((nm, "H", w, ("M2", "M4", "M6"), ins))
regions.append(("bus corridor x200.664-257.256 (y<=658.44)", "V", 56.592, ("M3", "M5", "M7"),
                sorted(k for k, v in isl.items() if 200.664 <= v["xy"][0] <= 257.256 and v["xy"][1] <= 658.44)))
regions.append(("E strip x440.856-457.92", "V", 17.064, ("M3", "M5", "M7"), sorted(k for k, v in isl.items() if v["xy"][0] > 440.856)))
rows = []
for nm, d, w, layers, ins in regions:
    cap = {}
    for L in layers:
        full = int(w / P[L])
        blk = ISL if L in ("M2", "M3", "M4", "M5") else VIA
        left = int(max(w - blk, 0) / P[L]) - (NDR if L in ("M6", "M7") else 0)
        cap[L] = dict(full=full, at_island=left, frac=round(left / full, 3))
    tot_full = sum(c["full"] for c in cap.values()); tot_isl = sum(c["at_island"] for c in cap.values())
    rows.append(dict(region=nm, dir=d, width_um=w, islands=ins, n_islands=len(ins), tracks=cap,
                     total_full=tot_full, total_at_island=tot_isl, usable_at_0p6=int(0.6 * tot_isl)))
dem = {"bus corridor x200.664-257.256 (y<=658.44)": dict(bits=1024, src="Codex A0 parent plan corridor budget (MODE9 historical, UNCHECKED)"),
       "LSL gap 1-2": dict(bits=250, src="fault raw flags converging on fault_q hub (191.5,984.888): <=5 E-side leaves x 50 flags crossing G1 (UNCHECKED bound)")}
for r in rows:
    if r["region"] in dem:
        r["demand"] = dem[r["region"]]
        r["use_at_island"] = round(dem[r["region"]]["bits"] / r["total_at_island"], 3)
        r["use_full"] = round(dem[r["region"]]["bits"] / r["total_full"], 3)
        r["verdict_0p6"] = "PASS" if r["use_at_island"] <= 0.6 else "FAIL"
json.dump(dict(schema="qc_cores_1027.a0_gap_capacity.v1", assumptions=__doc__, rows=rows), open(sys.argv[2], "w"), indent=1)
for r in rows:
    print(f"{r['region']:44s} {r['dir']} w{r['width_um']:7.3f} isl {r['n_islands']} {','.join(r['islands']):22s} "
          + " ".join(f"{L}:{c['at_island']}/{c['full']}" for L, c in r["tracks"].items())
          + (f"  demand {r['demand']['bits']} use {r['use_full']}->{r['use_at_island']} {r['verdict_0p6']}" if "demand" in r else ""))
