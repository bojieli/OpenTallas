"""DIE-QC-49 plan_qc49 = plan_qc48 + stm landing-ring band class fix (COORD 13:4x ruling (3), QC-KITS-Z ASK 13:32).

Why: all 10 plan_qc45 stm kits stall in 3_3 GPL routability (weighted congestion 2.7, 3.1-3.5 % overflowed tiles); the
GRT probe puts 99.8 % of overflow on u_cland ring nets inside the FIRM landing-ring bands (~17 signal pins/um2,
total usage 20 %). Those bands were sized by the default "padded" reserve (2636 um2 for a 553-bit ring = ~97 % filled)
and the whole ring (flops + dch/dsel logic) is packed FIRM in netlist order.
Fix = the same main mechanism HEAD uses (DIE-HEAD-11/12/13, tools/s81_head/head_band_ringff_delta.py HK3):
re-run ONLY main clock_landing_plan._storage_band for every band of the stm types (compose order, same obstacles, same
405-um reach rule, same spread step-down) at band_reserve ring_ff x band_spread S with ring_place ff (only ring flops
FIRM, ring logic to GPL) and fill_axis x (column fill), only for rings with padded ring_width >= 256 (all congestion hot spots; the small
64/128-bit control rings keep their bands: in a 8.64-um strip their few flops get a spread whose reserved footprint is
wider than the strip, measured OT_CLAND fail on flt_ctl_i). Extra obstacles: the unchanged small bands,
and (inflated by 12.96 um) the type's reset-relay/collector boxes (FLOW-7 reset_site_rects) and any
landing_contract.group_rects_um box, so collectors keep their sites. No pin, outline, port, hard core, RTL or cycle change.
"""
import argparse, copy, hashlib, json, sys
from pathlib import Path
R = Path(sys.argv[0]).resolve().parents[3]
sys.path[:0] = [str(R / "tools/die_plan"), str(R / "tools/s81_head")]
import clock_landing_plan as CLP
import head_band_ringff_delta as H

ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("--types", required=True)
ap.add_argument("--sidecar", required=True, help="QC collector sidecar with collector.types[tn].bus_geometry (main results/qc_die33_1029/bind/sidecar.json)")
ap.add_argument("--spread", type=float, default=2.0)
ap.add_argument("--min-ring-width", type=int, default=256, help="re-compose only bands whose padded ring_width >= this; smaller rings keep their rect (and are obstacles)"); ap.add_argument("--report", required=True)
a = ap.parse_args()
SC = json.load(open(a.sidecar))
P = json.load(open(a.plan)); T = P["partition_types"]; rep = {"spread": a.spread, "ring_place": "ff", "types": {}}
for tn in a.types.split(","):
    t = T[tn]; lc = t["clock"]["landing_contract"]; old = copy.deepcopy(lc["bands"])
    # Reset relay/collector boxes are inflated by GAP: a ring_place=ff flop at the band edge reserves w/0.4*spread
    # (~10.7 um at spread ~4) past its body, which took the rst_n_t1 collector box sites (measured, 3_2 probe).
    GAP = 12.96
    boxes = CLP.reset_site_rects(lc.get("collector_tree")) + [list(r) for r in (lc.get("group_rects_um") or {}).values()]
    fixed = [[r[0]-GAP, r[1]-GAP, r[2]+GAP, r[3]+GAP] for r in boxes]
    v = H.fixed_view(t); v["_cland_geom"] = copy.deepcopy(SC["collector"]["types"][tn]["bus_geometry"])
    for bus, ob in old.items():   # the sidecar geometry must reproduce the plan's recorded pin-to-band hop exactly
        if bus.startswith("monitor_") or not ob.get("rect_um") or ob.get("max_pin_to_band_hop_um") is None: continue
        px, py = CLP._bus_xy(v, bus); r = ob["rect_um"]
        hop = max(abs(x-px)+abs(y-py) for x in (r[0], r[2]) for y in (r[1], r[3]))
        assert abs(hop-ob["max_pin_to_band_hop_um"]) < 0.01, (tn, bus, hop, ob["max_pin_to_band_hop_um"])
    CLP.BAND_RESERVE, CLP.BAND_SPREAD, CLP.BAND_RING = "ring_ff", a.spread, "ff"
    new, fail = {}, {}
    try:
        keep = [b for b, ob in old.items() if b.startswith("monitor_") or not ob.get("rect_um")
                or int(ob.get("ring_width") or 0) < a.min_ring_width]
        used = list(fixed) + [list(old[b]["rect_um"]) for b in keep if old[b].get("rect_um")]
        for bus in sorted(old):
            ob = old[bus]
            if bus in keep:
                continue
            try:
                nb = CLP._storage_band(v, bus, int(ob["width"]), used, has_epoch=H.has_epoch(ob))
            except ValueError as e:
                fail[bus] = str(e); continue
            used.append(nb["rect_um"])
            if "instance" in ob: nb["instance"] = ob["instance"]
            # DIE-HEAD-32 column fill (+x+ff): transactional padding fit; the row scan at a 0.90 area estimate loses a
            # partial footprint per row end and failed x_ctl_fw_p1_i s_d[3][591] (measured, 3_2 probe)
            nb["fill_axis"] = "x"
            nb["placement"] = (f"DIE-QC-49 stm band class fix: ring_ff reserve x spread {a.spread}, ring_place ff "
                               f"(main _storage_band); was {ob.get('rect_um')} ({ob.get('area_reserve_um2')} um2 padded)")
            new[bus] = nb
    finally:
        CLP.BAND_RESERVE, CLP.BAND_SPREAD, CLP.BAND_RING = "padded", 1.0, "all"
    if fail:
        rep["types"][tn] = {"fail": fail}; continue
    nres = H.apply_bands(t, new)
    ar = lambda r: (r[2]-r[0])*(r[3]-r[1])
    errs = H.check_type(P, tn)
    for bus, nb in new.items():
        for f in fixed:
            if CLP._rect_overlap(nb["rect_um"], f): errs.append(f"band {bus} x reset/collector box+gap {f}")
    rep["types"][tn] = dict(reserved_bank_rects_updated=nres, overlaps=errs, bands={
        b: dict(old_rect=old[b]["rect_um"], old_area=round(ar(old[b]["rect_um"]), 1), rect=nb["rect_um"],
                area=round(ar(nb["rect_um"]), 1), ratio=round(ar(nb["rect_um"]) / ar(old[b]["rect_um"]), 2),
                reserve_um2=nb["area_reserve_um2"], spread=nb.get("spread"), hop_um=nb["max_pin_to_band_hop_um"],
                old_hop_um=old[b].get("max_pin_to_band_hop_um")) for b, nb in new.items()})
P["note"] = P.get("note", "") + (f" | plan_qc49 (DIE-QC-49): stm landing bands ring_ff x spread {a.spread}, ring_place ff "
                                 f"on {len(a.types.split(','))} types")
open(a.out, "w").write(json.dumps(P, indent=1) + "\n")
rep["src_sha256"] = hashlib.sha256(open(a.plan, "rb").read()).hexdigest()
rep["dst_sha256"] = hashlib.sha256(open(a.out, "rb").read()).hexdigest()
open(a.report, "w").write(json.dumps(rep, indent=1) + "\n")
for tn, r in rep["types"].items():
    if "fail" in r: print("FAIL", tn, r["fail"]); continue
    print(tn, "overlaps", len(r["overlaps"]), " ".join(f"{b}:{x['ratio']}x/hop{x['hop_um']}/sp{x['spread']}" for b, x in sorted(r["bands"].items())))
print("dst", rep["dst_sha256"][:8])
