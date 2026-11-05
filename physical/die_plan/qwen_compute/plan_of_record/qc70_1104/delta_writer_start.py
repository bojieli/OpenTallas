#!/usr/bin/env python3
"""DIE-QC-70 11-04: QC start strobe, relay types. cland_start_d = cland_rstart_in reaches each output FSTART face flop
unregistered, across the whole tile in one cycle (slw_hc3 form B GRT TT -101.42, 1588 um, 755 ps pin to D, its only setup
violator). EXISTING opt-in clock.landing_writer_start (DIE-HEAD-38, same form as KV geom93b/96): W registered relays before
the far face flops; receiving crossings bind K+W, boot cycles +W, data cycles 0.
NEED_UM: pin to pin Manhattan over this gets a stage. Read on slw_hc3 GRT TT, forms A and B: 320 um +473, 1587 um +7.5 and -98;
worst slope 0.45 ps/um crosses 0 near 1370 um, so 1200 keeps about 75 ps. Stage sites: Manhattan L from pin to target, split evenly, moved along the path off blockages;
raw reset = nearest RAW wavefront relay of the type (rst_n_t<i> are gated by START, so they cannot release a START stage). Idempotent. usage (repo root): delta_writer_start.py PLAN [OUT] [REPORT.json]"""
import json
import math
import sys
from pathlib import Path

sys.path[:0] = ["tools/die_plan"]
import reset_tree as RT
import schema as S

NEED_UM = 1200.0
STEP_UM = 1200.0
INSET = 14.0


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def on_path(o, t, d, w):
    tx = min(max(t[0], INSET), w - INSET)
    l1 = abs(tx - o[0])
    if d <= l1:
        return [o[0] + math.copysign(d, tx - o[0]), o[1]]
    return [tx, o[1] + math.copysign(d - l1, t[1] - o[1])]


def site(o, t, d, w, boxes):
    """nearest point of the L path to d that lies clear of every blockage (+3 um), or None"""
    tot = abs(min(max(t[0], INSET), w - INSET) - o[0]) + abs(t[1] - o[1])
    for off in range(0, int(tot), 5):
        for s in (d + off, d - off):
            if not 0 < s < tot:
                continue
            xy = on_path(o, t, s, w)
            if not any(b[0] - 3 <= xy[0] <= b[2] + 3 and b[1] - 3 <= xy[1] <= b[3] + 3 for b in boxes):
                return [round(xy[0], 3), round(xy[1], 3)]
    return None


path = sys.argv[1]
text = open(path).read()
plan = json.loads(text)
seps = next(sp for sp in ((", ", ": "), (",", ":")) if json.dumps(plan, separators=sp) + "\n" == text)
P = S.Plan(S.load(path), Path(path).resolve())
rep = {}
for tn in sorted({p["type"] for p in P.parts.values()}):
    t = P.types[tn]
    pins = {p["name"]: p["xy_um"] for p in ((t.get("clock") or {}).get("landing_contract") or {}).get("pins") or []}
    if "cland_rstart_in" not in pins:
        continue
    o = pins["cland_rstart_in"]
    far = {n[len("cland_fstart_out_"):]: man(o, xy) for n, xy in pins.items() if n.startswith("cland_fstart_out_")}
    far = {b: d for b, d in far.items() if d > NEED_UM}
    if not far:
        continue
    W = max(math.ceil(d / STEP_UM) - 1 for d in far.values())
    w = t["outline_um"][0]
    boxes = RT.blockages(t)
    T = RT.for_type(P, tn)
    # DIE-QC-71 11-04: rr_t<i> of an rst_o tap drives its output port; a port flop feeds only its port (clock_landings EMIT)
    nck = RT.consumer_count(T)
    port_q = {f"rr_t{i}" for i in range(nck, nck + len(T.get("outs", [])))}
    raws = [r for r in (RT.start_relays(T) if T.get("start") else T["relays"]) if r.get("role") == "raw" and r["q"] not in port_q]
    assert raws, tn
    branches, hops = {}, []
    for b, d in sorted(far.items()):
        tgt = pins["cland_fstart_out_" + b]
        tot = abs(min(max(tgt[0], INSET), w - INSET) - o[0]) + abs(tgt[1] - o[1])
        st = []
        for k in range(1, W + 1):
            xy = site(o, tgt, tot * k / (W + 1), w, boxes)
            assert xy, (tn, b)
            r = min(raws, key=lambda q: (man(xy, q["xy"]), q["q"]))
            hops.append(round(man(xy, r["xy"])))
            st.append({"xy_um": xy, "raw_reset": r["q"]})
        branches[b] = {"stages": st}
    plan["partition_types"][tn].setdefault("clock", {})["landing_writer_start"] = {"depth": W, "branches": branches}
    rep[tn] = {"W": W, "branches": {b: round(d) for b, d in sorted(far.items())}, "raw_hop_max_um": max(hops)}
open(sys.argv[2] if len(sys.argv) > 2 else path, "w").write(json.dumps(plan, separators=seps) + "\n")
if len(sys.argv) > 3:
    json.dump(rep, open(sys.argv[3], "w"), indent=1)
print(len(rep), "types", sum(len(r["branches"]) for r in rep.values()), "branches, W", sorted({r["W"] for r in rep.values()}))
