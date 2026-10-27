#!/usr/bin/env python3
"""S81-UNBLOCK-3 10-27 (COORD ruling on TOK-DS-11 (a)): frame-internal seam lanes fi_* priced from geometry.

TOK-DS-11 (claude/tok-ds-11-1027@15b76fe3fa) found the col_h* band seams (r0<->r1, r1<->r2) are 2 register stages
in RTL band port to band port (s81b_fint = src out + dst in boundary flop), while die_plan.json latency.lanes fi_*
said 6 (7 for h10 r0->r1).  COORD rule: the plan's cycle count must come from the measured distance at the 405-um
repeated reach; a distance-derived count gets RTL stations, an over-count is corrected in the plan.

Measured (this script, every fi port): the src and dst band partitions ABUT (gap 0 um) on the port face and the
port window is the same die-coordinate window on both sides, so the seam is pin-to-pin 0 um and the 405-um reach
needs 0 stations (latency table stations 0 on all 288 lanes).  The extra cycles were lanes[].fixed_cycles 4/5 =
1 + FRAME_BAND_STATION_EDGES (gen_plan_v4.py): the band pass-through stations INSIDE the band contents
(dsfd_qbank_N/_S, dsfd_rstg, ot_s81_sstn_* pin registers, KITS-RTLC 10-24), which exist in the band RTL and are
counted there by the as-built schedule walk; pricing them again on the port-to-port lane double counts.  So the
plan over-counts: fixed_cycles is removed from every fi_* lane (lane = boundary 2 = the RTL), nothing else changes.

    python3 delta_fi_seam_1027.py PLAN_IN PLAN_OUT REPORT.json
Then: python3 tools/die_plan/gen.py latency PLAN_OUT --inplace --out LATDIR
"""
import json
import sys

ABUT_UM = 0.01
REACH_UM = 405.0


def box(plan, part):
    t = plan["partition_types"][part["type"]]
    w, h = t["outline_um"]
    x, y = part["origin_um"]
    return x, y, x + w, y + h


def main(src, dst, rep):
    plan = json.load(open(src))
    parts = {p["name"]: p for p in plan["partitions"]}
    lanes = {l["id"]: l for l in plan["lanes"]}
    lat = plan.get("latency", {}).get("lanes", {})
    rows, fails = [], []
    for port in plan["ports"]:
        lid = port["id"].rsplit("__", 1)[0]
        if not lid.startswith("fi_"):
            continue
        a, b = box(plan, parts[port["src"]["part"]]), box(plan, parts[port["dst"]["part"]])
        gx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
        gy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
        gap = gx + gy
        st = lat.get(lid, {}).get("stations")
        row = dict(lane=lid, port=port["id"], src=port["src"]["part"], dst=port["dst"]["part"], face=port.get("face"),
                   window_um=port.get("window_um"), width=port["width"], seam_gap_um=round(gap, 6),
                   stations_by_reach=0 if gap <= REACH_UM else None, latency_stations=st,
                   fixed_cycles_old=lanes[lid].get("fixed_cycles", 0))
        if gap > ABUT_UM or st != 0:
            fails.append(row)
        rows.append(row)
    if fails:
        json.dump(dict(verdict="FAIL", fails=fails), open(rep, "w"), indent=1)
        raise SystemExit(f"delta_fi_seam: {len(fails)} fi ports are not abutted 0-station seams; plan unchanged")
    n = 0
    for lid, l in lanes.items():
        if lid.startswith("fi_") and l.pop("fixed_cycles", None) is not None:
            n += 1
    json.dump(plan, open(dst, "w"), indent=1)
    open(dst, "a").write("\n")
    json.dump(dict(schema="opentallas.s81.fi_seam_delta.v1", verdict="PASS", plan_in=src, ports=len(rows),
                   lanes_changed=n, max_seam_gap_um=max(r["seam_gap_um"] for r in rows), reach_um=REACH_UM,
                   rule="COORD 10-27 TOK-DS-11 (a): cycles from measured distance at 405-um reach; over-count -> plan",
                   rows=rows), open(rep, "w"), indent=1)
    print(json.dumps(dict(ports=len(rows), lanes_changed=n)))


if __name__ == "__main__":
    main(*sys.argv[1:4])
