#!/usr/bin/env python3
"""S81-PHY-ASSUME (2026-10-26): check the S81 die plan's SerDes / HBM PHY windows, bump sites, PG domains and the PHY
power figure against the published-figure assumptions in phy_assumptions.json (OWNER 10-26: published figures,
recorded as assumptions).  Read-only: it never edits the plan.

usage: phy_assume_check.py [PLAN.json] [ASSUMPTIONS.json] [--out OUT.json]
Defaults: die_plan.json and phy_assumptions.json next to this file.  Exit 0 always (diagnostic); verdicts are in OUT.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EDGE_UM = 104.0 + 1.0          # seal ring 103.68 um; a rect starting within this of an outline edge touches the shore
IR_TRIAL = {                    # results/die_trial_1024/codex_phy_1025 (standalone VDDPHY, 0.15 W/mm2, 0.7 V)
    "lk_WS0": dict(power_w=0.2361, worst_mv=2.55),
    "lk_WS3": dict(power_w=0.2052, worst_mv=2.74),
}
VNOM = 0.7


def ent(a, i):
    return next(e for e in a["entries"] if e["id"] == i)


def shore_depth(r, W, H):
    """(shoreline, depth, side) of a die-edge rect: the side it touches; a corner rect takes its longer edge."""
    x0, y0, x1, y1 = r
    w, h = x1 - x0, y1 - y0
    sides = []
    if y0 <= EDGE_UM: sides.append(("S", w, h))
    if H - y1 <= EDGE_UM: sides.append(("N", w, h))
    if x0 <= EDGE_UM: sides.append(("W", h, w))
    if W - x1 <= EDGE_UM: sides.append(("E", h, w))
    if not sides:
        return 0.0, min(w, h), "OFFSHORE"
    s = max(sides, key=lambda t: t[1])
    return s[1], s[2], s[0]


def main(argv):
    out = None
    if "--out" in argv:
        k = argv.index("--out"); out = argv[k + 1]; del argv[k:k + 2]
    plan_p = argv[1] if len(argv) > 1 else os.path.join(HERE, "die_plan.json")
    asm_p = argv[2] if len(argv) > 2 else os.path.join(HERE, "phy_assumptions.json")
    plan, a = json.load(open(plan_p)), json.load(open(asm_p))
    die = plan["die"]
    W, H = die["outline_um"]
    dom = {d["io"][0]: d for d in die["pg"]["domains"]}
    area = ent(a, "SER.MACRO6_AREA"); shore = ent(a, "SER.MACRO6_SHORE"); depth = ent(a, "SER.DEPTH_N7")
    pw = ent(a, "SER.MACRO6_POWER"); sig = ent(a, "SER.SIGNALS")["value"]; gr = ent(a, "SER.SIG_GND_RATIO")["value"]
    rows, n_ser = [], 0
    for io in die["io"]:
        if io.get("iface") != "serdes":
            continue
        n_ser += 1
        d = dom.get(io["name"], {})
        mac = d.get("phy_macro_um")
        r = mac or io["rect_um"]
        sh, dp, side = shore_depth(r, W, H)
        a_mm2 = (r[2] - r[0]) * (r[3] - r[1]) / 1e6
        # one-row macro needs the published shoreline and depth; a 2x3 fold needs half the shore at twice the depth
        row1 = sh >= shore["low"] and dp >= depth["low"]
        fold = sh >= shore["low"] / 2 and dp >= 2 * depth["low"]
        need_sites = sig * (1 + gr)
        f = []
        if side == "OFFSHORE":
            f.append("OFFSHORE: macro not on the die edge")
        if a_mm2 < area["low"]:
            f.append("AREA %.2f < %.2f mm2 (published N7 low; central %.2f)" % (a_mm2, area["low"], area["value"]))
        if not (row1 or fold):
            f.append("SHAPE %.0f x %.0f um (shore x depth) fits neither 1 row (>= %.0f x %.0f) nor a 2x3 fold"
                     " (>= %.0f x %.0f)" % (sh, dp, shore["low"], depth["low"], shore["low"] / 2, 2 * depth["low"]))
        if io.get("sites", 0) < need_sites:
            f.append("SITES %d < %d (26 signals + >= 1 ground each)" % (io.get("sites", 0), need_sites))
        if not mac:
            f.append("NO_MACRO: die.pg.domains has no phy_macro_um (VDDPHY domain = whole window)")
        if abs(io.get("pitch_um", 0) - d.get("bumps", {}).get("pitch_um", 0)) > 1e-6:
            f.append("PITCH_MIX: signal sites %.0f um vs PG rows %.0f um in the same rect (one bump technology"
                     " per die face)" % (io.get("pitch_um", 0), d.get("bumps", {}).get("pitch_um", 0)))
        rows.append(dict(io=io["name"], side=side, macro_um=[round(v, 2) for v in r], area_mm2=round(a_mm2, 3),
                         shore_um=round(sh, 1), depth_um=round(dp, 1), sites=io.get("sites"), signals=io.get("signals"),
                         findings=f, verdict="MISMATCH" if [x for x in f if not x.startswith("PITCH_MIX")] else
                         ("NOTE" if f else "OK")))
    ir = {}
    for part, t in IR_TRIAL.items():
        k = t["worst_mv"] * pw["value"] / t["power_w"]
        ir[part] = dict(trial_power_w=t["power_w"], trial_worst_mv=t["worst_mv"], published_power_w=pw["value"],
                        linear_worst_mv=round(k, 1), pct_of_vnom=round(100 * k / (1000 * VNOM), 2),
                        note="linear scaling of the standalone PDNSim result; a re-run at the published power is owed")
    hbm = next((io for io in die["io"] if io.get("iface") == "hbm_phy"), None)
    hb = {}
    if hbm:
        sh, dp, side = shore_depth(hbm["rect_um"], W, H)
        need = hbm["signals"] / 96.0 * ent(a, "HBM.SHORE_PER_96IO")["value"]
        hb = dict(io=hbm["name"], shore_um=round(sh, 1), need_shore_um=round(need, 1), sites=hbm["sites"],
                  signals=hbm["signals"], pg_share=round(1 - hbm["signals"] / hbm["sites"], 3),
                  pitch_um=hbm["pitch_um"], verdict="OK" if sh >= need and hbm["pitch_um"] <= 55 else "MISMATCH")
    die_ser_w = n_ser * pw["value"]
    res = dict(plan=os.path.relpath(plan_p, HERE), assumptions=os.path.relpath(asm_p, HERE), die_outline_um=[W, H],
               serdes_windows=n_ser, serdes=rows, hbm=hb, ir_scaled=ir,
               power=dict(per_macro_w=pw["value"], range_w=[pw["low"], pw["high"]], all_windows_w=round(die_ser_w, 1),
                          rank_die_10_macros_w=round(10 * pw["value"], 1), copy_ab_die_12_macros_w=round(12 * pw["value"], 1),
                          release_rack_die_w=84.1,
                          note="RELEASE_RACK 2.4 charges 16 x 84.1 W die (old 10-04 report) PLUS 160 SerDes macros x 4.37 W; "
                               "whether the 84.1 W includes the PHY is unknown (possible double count, its open item 2); "
                               "the IR trial used 0.15 W/mm2 = 0.21-0.24 W per window, ~18x below the published macro power"),
               counts=dict(mismatch=sum(r["verdict"] == "MISMATCH" for r in rows),
                           ok=sum(r["verdict"] == "OK" for r in rows), note=sum(r["verdict"] == "NOTE" for r in rows)))
    s = json.dumps(res, indent=1)
    if out:
        open(out, "w").write(s + "\n")
    print(s)


if __name__ == "__main__":
    main(sys.argv)
