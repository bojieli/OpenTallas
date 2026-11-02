#!/usr/bin/env python3
"""DIE-QC-62 11-01: SC landing-ring band class fix (plan_qc52 delta; the DIE-QC-49 stm mechanism applied to the sc family).

Measured failure (QC kit wave 5346b95c915 on d90): sle_sc_v1__cl115da35f and sle_sc_v1__cl7479a5ec FAIL 3_5 DPL-0033.
DPL check (3_5_place_dp.log): 1006 / 1006 overlaps sit in u_cland_* ring bands; 920 of the violators are the rings' OWN
repair_design buffers (u_cland_<bus>/placeNNN BUFx6f/BUFx3) plus a few FT cells; NegotiationLegalizer left 4431
violations at 10.6 % core utilisation.  Cause: every sc band is sized at the ring_ff reserve (ring FLOP count x the
measured footprint, ~100 % + 5 %) but packed ring_place "all" (every ring cell, flops AND the ~1.7x CA logic, FIRM),
159,231 FIRM cells, so the band has no room for the buffers repair_design inserts on the ring nets.  slw_sc_v1__cl63e5a7a2
fails earlier on the same bands (GPL: OT_CLAND no legal nonoverlapping row/site).  The stm types had the same form until
DIE-QC-49 (plan_qc49, COORD-approved): wide bands re-composed at ring_ff reserve x spread 2.0 + ring_place ff (only the
ring flops FIRM, bit-major; ring logic and its buffers to GPL), GRT overflow -97.7 %.
Delta: every landing-ring band with ring_width >= 256 of the 9 sc types is re-composed by MAIN
clock_landing_plan._storage_band (same 405-um reach, macro/island/clock-site/FT-site/PHY-supply obstacles, spread step-
down 2.0 -> 1.0 by 0.05) with BAND_RESERVE ring_ff, BAND_SPREAD 2.0, BAND_RING ff; the type's other bands, its reset
relay/collector boxes (+12.96 um, as DIE-QC-49), collector group rects and START relay boxes are obstacles.  Bus geometry
comes from the paired clock-landing sidecar.  N/S-face (x-row) bands get fill_axis "x" (AUTOBUILD-PIPE-2 10-31: the
FLOW-12 pinslot column form needs it; the stm bands carry it).  Small control rings (< 256), pins, outlines, ports,
hard cores, reset trees, RTL and every other type are unchanged.
usage: delta_scband_1101.py PLAN_IN SIDECAR PLAN_OUT [REPORT.json]"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import clock_landing_plan as CLP  # noqa: E402
import schema as S  # noqa: E402

TYPES = ["sle_sc_v1__cl115da35f", "sle_sc_v1__cl7479a5ec", "sle_sc_v2", "sle_sc_v3",
         "slw_sc_v1__cl63e5a7a2", "slw_sc_v1__cl64543eaf__cl4590432d", "slw_sc_v1__cl64543eaf__cl5e017c6f",
         "slw_sc_v2", "slw_sc_v3"]
MIN_RW, SPREAD, RESET_MARGIN = 256, 2.0, 12.96
TAG = "DIE-QC-62 sc band class fix (DIE-QC-49 mechanism): ring_ff reserve x spread 2.0, ring_place ff (main _storage_band)"


def grow(r, m):
    return [r[0] - m, r[1] - m, r[2] + m, r[3] + m]


def obstacles_for(t, lc, geom):
    import landing_place as LP
    boxes = CLP.reset_site_rects(lc.get("collector_tree")) + CLP.reset_site_rects(geom.get("tree"))
    out = [grow(b, RESET_MARGIN) for b in boxes]
    out += [list(r) for _p, r, _t in LP._reader_start_groups(t) + LP._writer_start_groups(t) + LP._status_reset_groups(t)]
    out += [list(r) for r in lc.get("group_rects_um", {}).values()]
    return [list(r) for r in dict.fromkeys(tuple(round(v, 6) for v in r) for r in out)]


def redo_type(raw, P, tn, geom):
    t = raw["partition_types"][tn]
    lc = t["clock"]["landing_contract"]
    bands = lc["bands"]
    targets = sorted(b for b, v in bands.items() if not b.startswith("monitor_") and v.get("rect_um")
                     and int(v.get("ring_width", 0)) >= MIN_RW and v.get("ring_place") != "ff")
    fixed = [list(r) for b, v in bands.items() if b not in targets and v.get("rect_um")
             for r in (v.get("rects_um") or [v["rect_um"]])]
    tt = copy.deepcopy(t)
    tt["_cland_geom"] = copy.deepcopy(geom["bus_geometry"])
    phy = CLP.phy_supply_rects(P, tn) if P is not None else []
    rst = obstacles_for(t, lc, geom)
    err = None
    for order_name, order in (("name", targets),
                              ("largest_first", sorted(targets, key=lambda b: (-int(bands[b]["width"]), b)))):
        used, got = list(fixed), {}
        try:
            for bus in order:
                nb = CLP._storage_band(tt, bus, int(bands[bus]["width"]), used, phy=phy, resets=rst)
                used.append(nb["rect_um"])
                got[bus] = nb
        except ValueError as e:
            err = e
            continue
        break
    else:
        raise ValueError(f"{tn}: sc band class fix does not fit: {err}")
    rep = {}
    for bus in targets:
        old, nb = bands[bus], got[bus]
        face = CLP._bus_geom(tt, bus)["face"]
        nb["instance"] = old.get("instance", "u_cland_" + bus)
        nb["placement"] = TAG + f"; was {old['rect_um']} ({old.get('area_reserve_um2')} um2, ring_place all)"
        if face in ("N", "S"):
            nb["fill_axis"] = "x"
        o, r = old["rect_um"], nb["rect_um"]
        rep[bus] = dict(face=face, old_rect=o, old_area=round((o[2] - o[0]) * (o[3] - o[1]), 1), rect=r,
                        area=round((r[2] - r[0]) * (r[3] - r[1]), 1), reserve_um2=nb["area_reserve_um2"],
                        spread=nb.get("spread"), hop_um=nb["max_pin_to_band_hop_um"], fill_axis=nb.get("fill_axis"))
        bands[bus] = nb
    # legality on the exact coordinates: no two bands overlap, none overlaps a reset/collector box or macro blockage
    rects = [(b, r) for b, v in bands.items() if v.get("rect_um") for r in (v.get("rects_um") or [v["rect_um"]])]
    for i, (a, ra) in enumerate(rects):
        for b, rb in rects[i + 1:]:
            assert not CLP._rect_overlap(ra, rb), (tn, a, b)
    for b in targets:
        assert not any(CLP._rect_overlap(bands[b]["rect_um"], o) for o in rst + phy), (tn, b)
        assert bands[b]["max_pin_to_band_hop_um"] <= 405, (tn, b)
    return dict(order=order_name, bands=rep, unchanged=sorted(set(bands) - set(targets)))


def main(argv):
    pin, side, pout = argv[1:4]
    raw = json.load(open(pin))
    sc = json.load(open(side))
    geoms = sc["collector"]["types"]
    P = S.Plan(raw) if (raw.get("die") or {}).get("pg", {}).get("domains") and raw.get("partitions") else None
    saved = (CLP.BAND_RESERVE, CLP.BAND_SPREAD, CLP.BAND_RING)
    CLP.BAND_RESERVE, CLP.BAND_SPREAD, CLP.BAND_RING = "ring_ff", SPREAD, "ff"
    report = dict(spread=SPREAD, ring_place="ff", min_ring_width=MIN_RW, reset_margin_um=RESET_MARGIN, types={})
    try:
        for tn in TYPES:
            report["types"][tn] = redo_type(raw, P, tn, geoms[tn])
    finally:
        CLP.BAND_RESERVE, CLP.BAND_SPREAD, CLP.BAND_RING = saved
    before = json.load(open(pin))
    for tn in before["partition_types"]:
        if tn not in TYPES:
            assert before["partition_types"][tn] == raw["partition_types"][tn], tn
    for k in before:
        if k != "partition_types":
            assert before[k] == raw[k], k
    for tn in TYPES:   # only landing_contract.bands changed
        a, b = copy.deepcopy(before["partition_types"][tn]), copy.deepcopy(raw["partition_types"][tn])
        a["clock"]["landing_contract"].pop("bands"), b["clock"]["landing_contract"].pop("bands")
        assert a == b, tn
    Path(pout).write_text(json.dumps(raw) + "\n")   # plan_of_record format: one line, default separators
    n = sum(len(v["bands"]) for v in report["types"].values())
    print(f"SCBAND {n} bands re-composed in {len(TYPES)} types")
    for tn, v in report["types"].items():
        for bus, r in v["bands"].items():
            print(f"SCBAND {tn} {bus} {r['face']} {r['old_area']} -> {r['area']} um2 spread {r['spread']} hop {r['hop_um']}"
                  f" fill_axis {r['fill_axis']}")
    if len(argv) > 4:
        Path(argv[4]).write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv)
