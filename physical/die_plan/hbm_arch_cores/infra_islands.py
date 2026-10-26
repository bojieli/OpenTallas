#!/usr/bin/env python3
"""HBM-CORE-LAT 2026-10-26 (owner: SU decision for all dies): in-core INFRA ISLANDS + one die clock-latency target.

    python3 infra_islands.py --plan PLAN --mesh MESH.json [--core-insertion TABLE] --out DIR

Inputs: the die plan the clock build used and the CLOCK-2 regional mesh build (die_clock_mesh.py --clock-floorplan
with hard_core_drivers=drop).  Its mesh.json 'hole_drivers' rows of class 'hard_core' are mesh intersections
inside a hard core with no legal driver site within max-move along either strap (= the measured demand).

ISLAND (COORD corrections 06:xx: top-owned hole, die CLOCK + RESET drivers only; FT stations/repeaters stay pushed
down in partition/core repeater bays <= 405 um):
  * one vertical INFRA STRIP per core master at the core x-centre (mirror-invariant: MY/R180 instances see the same
    strip), full core height minus the core margin, width --strip-w: hard PLACEMENT blockage for the core (no core
    cells), core ROUTING blockage on M1-M2 (cell/pin layers belong to the die inside the strip);
  * VIA WINDOWS every --win-pitch along the strip, --strip-w x --win-h: full core routing blockage M1-M5 (the die
    drops its M9->M1 via stack + M8 jog there); the core keeps its M3-M5 crossings between windows.
  Why a strip and not point islands: die_clock_mesh slides a driver only ALONG a strap (x along M8, y along M9);
  the M8 strap y and the M9 strap x over a core differ per instance (the mesh lattice is not commensurate with the
  SM 734.4-um column pitch, and NW_sm0/NW_sm1 columns are 241.9 um out of phase), so only a full-height strip is a
  legal x-slide target for every instance.  A driver in a window reaches its M8 strap with a <= win_pitch/2 jog.
LATENCY: one die-wide core clock-latency target = plan clock.common_latency_ps (250 TT, the QC/INFRA-FIRST
convention agreed 05:41) +- insertion_tol_ps; FF from the FLOW 0.81 FF/TT basis.  Per-core action from the measured
natural insertion I (core_insertion table): I < target-tol -> PAD (tap_balance pads up, no early tap); within tol ->
OK; I > target+tol -> REBUILD (in-core MSCTS: clock entries fed from strip windows, sub-trees <= target);
not measured -> MEASURE (kit to CTS with the target).
"""
import argparse
import collections
import json
import math
from pathlib import Path

IP_MACROS = {"ot_pdie_serdes"}        # PHY/SerDes IP: no rebuild; stays a declared driverless hole (io-macro class)


def core_rects(plan):
    pt = plan["partition_types"]
    for q in plan["partitions"]:
        t = pt[q["type"]]
        W, H = t["outline_um"]
        ox, oy = q["origin_um"]
        o = q.get("orient", "R0")
        for hc in t.get("hard_cores", []) or []:
            (hx, hy), (w, h) = hc["origin_um"], hc["outline_um"]
            x0 = {"R0": hx, "MX": hx, "MY": W - hx - w, "R180": W - hx - w}[o]
            y0 = {"R0": hy, "MY": hy, "MX": H - hy - h, "R180": H - hy - h}[o]
            yield dict(part=q["name"], inst=hc["inst"], module=hc["module"], orient=o,
                       rect=(ox + x0, oy + y0, ox + x0 + w, oy + y0 + h), outline=(w, h))


def design(plan, mesh, max_move, strip_w, win_pitch, win_h, margin):
    cores = list(core_rects(plan))
    by_inst = {f"{c['part']}/{c['inst']}": c for c in cores}
    xs, ys = mesh["xs"], mesh["ys"]
    demand = collections.defaultdict(list)
    for i, j, cls, name in mesh["hole_drivers"]:
        if cls != "hard_core":
            continue
        c = by_inst[name]
        demand[c["module"]].append(dict(inst=name, xy=(xs[i], ys[j]), rect=c["rect"]))
    count = collections.Counter(c["module"] for c in cores)
    out, checks = {}, []
    for mod, pts in sorted(demand.items()):
        w, h = next(c["outline"] for c in cores if c["module"] == mod)
        if mod in IP_MACROS:
            out[mod] = dict(action="DRIVERLESS_IP", instances=count[mod], points=len(pts),
                            note="IP macro: no in-core island; CLOCK-2 keeps the intersection driverless (io-macro class)")
            continue
        xc = round(w / 2, 3)
        strip = [round(xc - strip_w / 2, 3), margin, round(xc + strip_w / 2, 3), round(h - margin, 3)]
        n_win = int((h - 2 * margin - win_h) // win_pitch) + 1
        y_first = margin + ((h - 2 * margin - win_h) - (n_win - 1) * win_pitch) / 2
        wins = [[strip[0], round(y_first + k * win_pitch, 3), strip[2], round(y_first + k * win_pitch + win_h, 3)]
                for k in range(n_win)]
        worst_slide, worst_jog, per_inst = 0.0, 0.0, collections.Counter()
        for p in pts:
            r = p["rect"]
            sx = (r[0] + r[2]) / 2                          # strip centre in die frame (mirror-invariant)
            slide = max(0.0, abs(p["xy"][0] - sx) - strip_w / 2)
            ly = p["xy"][1] - r[1]                          # strap y in core frame (any orientation: windows are
            if abs((r[3] - r[1]) - h) > 1e-3:                # outline sanity (windows are checked for R0 and MX)
                raise SystemExit(f"{p['inst']}: outline mismatch")
            jog = min(abs(ly - (wy0 + win_h / 2)) for _, wy0, _, _ in wins)
            jog_mx = min(abs((h - ly) - (wy0 + win_h / 2)) for _, wy0, _, _ in wins)
            jog = max(jog, jog_mx)
            worst_slide, worst_jog = max(worst_slide, slide), max(worst_jog, jog)
            per_inst[p["inst"]] += 1
            checks.append(dict(module=mod, inst=p["inst"], xy=p["xy"], slide_um=round(slide, 2),
                               jog_um=round(jog, 2), legal=slide <= max_move))
        area = strip_w * (strip[3] - strip[1])
        out[mod] = dict(action="ISLAND", instances=count[mod], outline_um=[w, h], points=len(pts),
                        max_points_per_instance=max(per_inst.values()),
                        strip_um=strip, strip_w_um=strip_w, windows_um=wins, n_windows=n_win,
                        win_pitch_um=win_pitch, win_h_um=win_h,
                        core_blockage=dict(placement="strip", routing_strip=["M1", "M2"], routing_windows=["M1", "M2", "M3", "M4", "M5"]),
                        die_owner="clock mesh drivers (2 x BUFx24 per intersection) + regional reset drivers only",
                        worst_slide_um=round(worst_slide, 2), worst_jog_um=round(worst_jog, 2),
                        all_legal=worst_slide <= max_move,
                        strip_area_um2=round(area, 1), strip_area_pct=round(100 * area / (w * h), 2),
                        window_porosity_pct=round(100 * win_h / win_pitch, 1),
                        window_fill_pct=round(100 * (2 * 1.62 + 1.62) * 0.27 / (strip_w * 0.27), 1))
    return out, checks


def latency_table(plan, table, target, tol):
    cores = list(core_rects(plan))
    count = collections.Counter(c["module"] for c in cores)
    meas = {}
    if table:
        for v in json.load(open(table))["views"]:
            if v.get("status") == "MEASURED":
                meas.setdefault(v["module"], []).append(v["insertion_mean_ps"])
    rows = {}
    for mod, n in sorted(count.items()):
        if mod in IP_MACROS:
            act, I = "IP_DECLARED", max(meas.get(mod, [0])) or None
        elif mod in meas:
            I = max(meas[mod])
            act = "PAD" if I < target - tol else ("OK" if I <= target + tol else "REBUILD")
        else:
            I, act = None, "MEASURE"
        rows[mod] = dict(instances=n, measured_tt_ps=I, action=act)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--mesh", required=True)
    ap.add_argument("--core-insertion", default=None)
    ap.add_argument("--max-move", type=float, default=250.0)
    ap.add_argument("--strip-w", type=float, default=8.64)
    ap.add_argument("--win-pitch", type=float, default=69.12)
    ap.add_argument("--win-h", type=float, default=4.32)
    ap.add_argument("--margin", type=float, default=4.32)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    mesh = json.load(open(a.mesh))
    target = float(plan["clock"].get("common_latency_ps", plan["clock"]["insertion_ps"]))
    tol = float(plan["clock"]["insertion_tol_ps"])
    isl, checks = design(plan, mesh, a.max_move, a.strip_w, a.win_pitch, a.win_h, a.margin)
    lat = latency_table(plan, a.core_insertion, target, tol)
    od = Path(a.out)
    od.mkdir(parents=True, exist_ok=True)
    doc = dict(schema="opentallas.hbm.core_infra_islands.v1", lane="HBM-CORE-LAT",
               plan_sha256=mesh["meta"].get("plan_sha256"), mesh_meta={k: mesh["meta"].get(k) for k in
               ("delta_id", "clock_floorplan", "driverless_hard_cores", "hole_drivers")},
               latency_target=dict(tt_ps=target, ff_ps=round(0.81 * target, 1), tol_ps=tol,
                                   rule="one die-wide core clock-latency target at the core clock pin = plan common latency; "
                                        "die feeds every core pin with ZERO early offset; PAD/OK/REBUILD/MEASURE per core"),
               islands=isl,
               latency_actions=dict(collections.Counter(r["action"] for r in lat.values())),
               latency_instances=dict(sum((collections.Counter({r["action"]: r["instances"]}) for r in lat.values()), collections.Counter())))
    (od / "core_infra_islands.json").write_text(json.dumps(doc, indent=1) + "\n")
    (od / "island_checks.json").write_text(json.dumps(checks, indent=0) + "\n")
    (od / "core_latency_actions.json").write_text(json.dumps(lat, indent=1) + "\n")
    print(json.dumps(dict(islands={m: {k: v.get(k) for k in ("action", "instances", "points", "worst_slide_um", "worst_jog_um", "all_legal", "strip_area_pct")} for m, v in isl.items()},
                          illegal=sum(1 for c in checks if not c["legal"]), latency=doc["latency_actions"], latency_instances=doc["latency_instances"]), indent=1))


if __name__ == "__main__":
    main()
