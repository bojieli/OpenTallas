#!/usr/bin/env python3
"""HEAD-START-3 step 1: routed START proof = the planner's own proof (codex-head-start-0251/input/proof, same keys and
tree paths) with every NUMBER replaced by the HEAD-START-2 routed vehicle readout (r1/out_<C>/arr_<C>.txt, OT_EDGES v1,
GRT50 RC, real START loads + 1356 local clock-entry BUFx8):
  node_{late,early}_ps      <- N <cell>    node_fall_{late,early}_ps <- M <cell>   (via the proof's node_cell map)
  cppr_node_range_ps        <- late - early of the same node (rise)
  core taps late/early/slew <- T <port>;  fall_{late,early} <- F <port>
  NEW measured START clock pins: '__st__<path>' taps (part None, cppr_node 'h') from T/F t_st_<cell>__clk = max late /
  min early over that stage's FF CLK pins (node -> local BUF8 -> FF), so die_sta_related.virtual_tap uses the MEASURED
  stage clock instead of node + median core-tap leg (core leg ~2 ps vs measured START leg 16..103 ps TT).
  clock_masters on __st__ taps: CKINVDCx16 + BUFx8 (the local entry).
No re-fit, no scaling: re-packaging of measured numbers only.
usage: mk_proof_routed.py OLD_PROOF_DIR RUN_DIR OUT_DIR"""
import json, shutil, sys
from pathlib import Path
old, run, out = map(Path, sys.argv[1:4])
out.mkdir(parents=True, exist_ok=True)
for f in ("mesh.json", "droop_regions.json"):
    shutil.copy(old / f, out / f)
rep = {}
for C in ("TT", "FF"):
    d = json.loads((old / f"tap_arrivals_{C}.json").read_text())
    R = {k: {} for k in "TFNM"}
    for ln in (run / f"out_{C}" / f"arr_{C}.txt").read_text().splitlines():
        x = ln.split()
        if x and x[0] in R:
            R[x[0]][x[1]] = [float(v) for v in x[2:]]
    nc = d["node_cell"]
    miss = [p for p, c in nc.items() if c not in R["N"] or c not in R["M"]]
    if miss:
        sys.exit(f"{C}: {len(miss)} proof nodes without routed N/M (e.g. {miss[:3]})")
    dl = []
    for p, c in nc.items():
        dl.append(R["N"][c][0] - d["node_late_ps"][p])
        d["node_late_ps"][p], d["node_early_ps"][p] = R["N"][c][0], R["N"][c][1]
        d["node_fall_late_ps"][p], d["node_fall_early_ps"][p] = R["M"][c][0], R["M"][c][1]
        d["cppr_node_range_ps"][p] = max(0.0, R["N"][c][0] - R["N"][c][1])
    for t in d["taps"]:
        p = t["port"]
        t["late_ps"], t["early_ps"], t["slew_ps"] = R["T"][p][0], R["T"][p][1], R["T"][p][2]
        t["fall_late_ps"], t["fall_early_ps"] = R["F"][p][0], R["F"][p][1]
    path_of = {}
    for p, c in nc.items():
        if all(ord(ch) >= 0x100 for ch in p[1:]) and p.startswith("h"):
            path_of.setdefault(c, p)
    st = 0
    for port, v in sorted(R["T"].items()):
        if not port.startswith("t_st_"):
            continue
        c = port[5:-5]
        p = path_of[c]
        d["taps"].append(dict(port=f"__st__{p}", part=None, cppr_node="h", tree_path=p, late_ps=v[0], early_ps=v[1],
                              fall_late_ps=R["F"][port][0], fall_early_ps=R["F"][port][1],
                              stages_from_root=int(d["node_stages"][p]) + 2, xy_um=d["node_xy_um"][p],
                              clock_masters=["CKINVDCx16_ASAP7_75t_R", "BUFx8_ASAP7_75t_R"], measured_start_cell=c))
        st += 1
    d["basis"] = f"HEAD-START-3 routed START proof: numbers from {run}/out_{C}/arr_{C}.txt (GRT50 RC, real START loads + local BUF8); keys from {old}"
    d["fall_arrivals"] = dict(source="HEAD-START-3 mk_proof_routed (measured M/F rows)", taps=len(d["taps"]))
    (out / f"tap_arrivals_{C}.json").write_text(json.dumps(d, indent=0) + "\n")
    dl.sort()
    rep[C] = dict(nodes=len(nc), core_taps=len(d["taps"]) - st, start_taps=st,
                  node_late_shift_ps=dict(min=dl[0], median=dl[len(dl) // 2], max=dl[-1]))
print(json.dumps(rep, indent=1))
(out / "mk_proof_routed.json").write_text(json.dumps(rep, indent=1) + "\n")
