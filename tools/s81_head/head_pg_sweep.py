#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-3 PG (task 4): s81_head worst-case power from the head netlists + M8/M9 PG sweep (analytic model
and PDNSim windows) with VSS-locked clock lanes.

    head_pg_sweep.py power --rpt NAME=ACT=FILE ... --out power.json
        hd_tile density from OpenSTA report_power of the hard-core GRT views (4 x elemA + 1 x elemB per hd_tile)
    head_pg_sweep.py sweep PLAN --power power.json --act 0.5 --out sweep.json [--bump 150 ...]
        analytic IR (tools/die_plan/infra_pg.estimate) + track share + clock-lane fit per candidate grid
    head_pg_sweep.py psm PLAN --power power.json --act 0.5 --cand LABEL ... --window NAME=x0,y0,x1,y1 --out DIR
        PDNSim window kits (infra_pg.window_kit) with die.pg.domains dropped (core-only window, no PHY)

Read-only on the plan.  All numbers produced here are own-tool (UNCHECKED until NUMBER-CHECK).
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import infra_pg as G  # noqa: E402
import schema as S  # noqa: E402

CORE_UM = {"elemA": 319.68, "elemB": 285.12}       # rebuilt R12 kit DIE_AREA (pins.json, CHECKED in R2)
PER_TILE = {"elemA": 4, "elemB": 1}
TILE_UM = (708.48, 1036.8)                          # hd_tile outline, plan 674a8ac9
CLK_W = {"16w": 0.64, "2x16w": 1.28}                # qc_clk_mesh3 WIDTH_UM
STRIPE_HALF_EDGE_SPACING = 0.5                      # ASAP7 M8/M9 SPACINGTABLE row for width >= 0.49975


def parse_rpt(path):
    t = Path(path).read_text()
    m = re.search(r"^Total\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", t, re.M)
    mac = re.search(r"^Macro\s+\S+\s+\S+\s+\S+\s+(\S+)", t, re.M)
    clk = re.search(r"^Clock\s+\S+\s+\S+\s+\S+\s+(\S+)", t, re.M)
    return dict(total_w=float(m.group(4)), internal_w=float(m.group(1)), switching_w=float(m.group(2)),
                leakage_w=float(m.group(3)), macro_w=float(mac.group(1)), clock_w=float(clk.group(1)))


def cmd_power(a):
    rows = {}
    for spec in a.rpt:
        name, act, f = spec.split("=", 2)
        r = parse_rpt(f)
        r.update(core=name, activity=float(act), area_mm2=CORE_UM[name] ** 2 * 1e-6, rpt=f)
        r["w_mm2"] = r["total_w"] / r["area_mm2"]
        rows.setdefault(act, {})[name] = r
    tile_a = TILE_UM[0] * TILE_UM[1] * 1e-6
    out = dict(basis=[
        "OpenSTA report_power (openroad/orfs:asap7lock), TT RVT NLDM + ot_rom_4096x274_m8_tt.lib, hold2 GRT views "
        "5_1_grt.odb (estimate_parasitics -global_routing, rc_cal 0.8/0.9), propagated clock 833 ps",
        "activity: set_power_activity -global and -input -activity ACT -duty 0.5 (transitions per cycle); clock nets "
        "toggle every cycle; ROM macros clocked every cycle (worst case: no CE gating credit)",
        "hd_tile = 4 x elemA + 1 x elemB hard cores (plan 674a8ac9); glue = tile - cores area",
        "glue ASSUMPTION (no hd_tile glue netlist power): upper bound glue at the 5-core average W/mm2 (S81-HEAD "
        "~1.07M cells/tile vs 0.658M in the cores -> glue ~0.41M cells, i.e. a full-density glue is plausible); "
        "lower bound glue 0 W",
        "other head types (spine, stations, serdes digital strip, ctl/host/mesh/lep0N): no netlist -> charged at the "
        "hd_tile upper-bound density (ASSUMPTION, conservative); SerDes PHY windows 4.37 W/macro (S81-PHY-ASSUME)"],
        activities={})
    for act, cores in sorted(rows.items()):
        cw = sum(PER_TILE[c] * cores[c]["total_w"] for c in PER_TILE)
        ca = sum(PER_TILE[c] * cores[c]["area_mm2"] for c in PER_TILE)
        dens = cw / ca
        glue_a = tile_a - ca
        out["activities"][act] = dict(cores=cores, tile_cores_w=round(cw, 5), tile_cores_mm2=round(ca, 5),
                                      core_avg_w_mm2=round(dens, 4), glue_mm2=round(glue_a, 5),
                                      tile_w_upper=round(cw + glue_a * dens, 4), tile_w_lower=round(cw, 4),
                                      tile_w_mm2_upper=round(dens, 4), tile_w_mm2_lower=round(cw / tile_a, 4),
                                      die_tiles_w_upper=round(264 * (cw + glue_a * dens), 1))
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "cores"} for k, v in out["activities"].items()},
                     indent=1))


def plan(path):
    return S.Plan(S.load(path), Path(path))


def density(pw, act, bound):
    return pw["activities"][act]["tile_w_mm2_upper" if bound == "upper" else "tile_w_mm2_lower"]


def entry(layer, w, p):
    return dict(layer=layer, width_um=w, pitch_um=p, offset_um=round(p / 2, 4), nets=["VDD", "VSS"])


def island_phases(P):
    """abs x of every hd_tile core-island clock tap (M9 straps on island columns) and abs y (M8 straps on island rows),
    mod 8.64."""
    raw = json.loads(Path(P.path).read_text())
    t = raw["partition_types"]["hd_tile"]
    w, h = t["outline_um"]
    xs, ys = set(), set()
    for q in raw["partitions"]:
        if q["type"] != "hd_tile":
            continue
        ox, oy = q["origin_um"]
        for tp in t["clock"]["taps"]:
            x, y = tp["xy"]
            x = w - x if q["orient"] in ("MY", "R180") else x
            y = h - y if q["orient"] in ("MX", "R180") else y
            xs.add(round(ox + x, 3))
            ys.add(round(oy + y, 3))
    return sorted(xs), sorted(ys)


def lanes(stripe, clk_w):
    """Legal clock-lane centres in one period of a VDD/VSS stripe pair (VSS-locked: lane in a VSS-adjacent half-gap,
    wide-wire spacing 0.5 to both neighbouring stripes).  -> (list of (lo, hi) centre intervals relative to the VSS
    stripe centre, gap_um)."""
    p, w = stripe["pitch_um"], stripe["width_um"]
    s = p / 2                                    # VDD at offset, VSS at offset + p/2 (one stripe per net per pitch)
    sp = max(STRIPE_HALF_EDGE_SPACING, G.spacing(w))
    lo = w / 2 + sp + clk_w / 2                  # off the VSS stripe
    hi = s - w / 2 - sp - clk_w / 2              # clear of the VDD stripe on the other side
    hi_vss = min(hi, s / 2)                      # closer to VSS than to VDD (VSS-locked shield side)
    gap = s - w
    if hi < lo:
        return [], gap
    return [(lo, max(lo, hi_vss)), (-max(lo, hi_vss), -lo)], gap


def lane_fit(stripe, clk_w, phases):
    """For each island coordinate: nearest legal VSS-locked lane centre -> riser/jog distance (um)."""
    p = stripe["pitch_um"]
    ivs, gap = lanes(stripe, clk_w)
    if not ivs:
        return dict(fit=False, gap_um=round(gap, 3), max_jog_um=None)
    vss0 = stripe["offset_um"] + p / 2          # VDD at offset, VSS at offset + pitch/2
    worst = 0.0
    for c in phases:
        r = (c - vss0) % p
        best = 1e9
        for k in (-1, 0, 1):
            for a_, b_ in ivs:
                lo, hi = a_ + k * p, b_ + k * p
                d = 0.0 if lo <= r <= hi else min(abs(r - lo), abs(r - hi))
                best = min(best, d)
        worst = max(worst, best)
    return dict(fit=True, gap_um=round(gap, 3), max_jog_um=round(worst, 3))


M9_CANDS = [(0.48, 1.728), (0.48, 2.16), (0.48, 2.88), (0.48, 4.32), (0.96, 2.88), (0.96, 4.32), (1.44, 4.32),
            (1.92, 4.32), (1.92, 8.64), (2.88, 8.64), (3.84, 8.64), (4.32, 17.28)]
M8_CANDS = [(0.48, 8.64), (0.48, 4.32), (0.48, 2.88), (0.96, 4.32), (1.92, 8.64)]


def cmd_sweep(a):
    P = plan(a.plan)
    pw = json.loads(Path(a.power).read_text())
    d = density(pw, a.act, a.bound)
    xs, ys = island_phases(P)
    rows = []
    types = {tn: d for tn in json.loads(Path(a.plan).read_text())["partition_types"]}
    for bump in a.bump:
        model = G.load_model(P, Path(a.plan).parent, dict(core_w_mm2=d, types=types), 4.37)
        m8c = [tuple(map(float, c.split("@"))) for c in a.m8] if a.m8 else M8_CANDS
        m9c = [tuple(map(float, c.split("@"))) for c in a.m9] if a.m9 else M9_CANDS
        for w8, p8 in m8c:
            for w9, p9 in m9c:
                g = [entry("M8", w8, p8), entry("M9", w9, p9)]
                reg, worst, det = G.estimate(P, model, g, bump, 0.7)
                tr = G.tracks_of(P, g)
                f9 = lane_fit(g[1], CLK_W["16w"], xs)
                f8 = lane_fit(g[0], CLK_W["16w"], ys)
                f9s = lane_fit(g[1], CLK_W["2x16w"], xs)
                core = max(v for k, v in reg.items() if k == "core" or k.startswith("core:"))
                rows.append(dict(label=f"M8 {w8}@{p8} / M9 {w9}@{p9} / bump {bump}", bump_um=bump, grid=g,
                                 tracks=tr, core_ir_mv=core, worst_ir_mv=worst, local_mv=det["local_mv"],
                                 coarse_mv=det["coarse_max_mv"], lane_m9_16w=f9, lane_m9_2x16w=f9s, lane_m8_16w=f8,
                                 pass_ir=core <= 35.0, pass_lanes=f9["fit"] and f8["fit"]))
                print(f"{rows[-1]['label']:44s} M8 {tr['M8']:.3f} M9 {tr['M9']:.3f} core {core:8.2f} mV "
                      f"(loc {det['local_mv']:.1f}) lanes M9 {f9['fit']}/{f9['max_jog_um']} M8 {f8['fit']}/{f8['max_jog_um']}",
                      flush=True)
    out = dict(plan_sha256=__import__("hashlib").sha256(Path(a.plan).read_bytes()).hexdigest(), activity=a.act,
               bound=a.bound, core_w_mm2=d, budget_mv=35.0, island_x_mod=sorted({round(x % 8.64, 3) for x in xs}),
               island_y_mod=sorted({round(y % 8.64, 3) for y in ys}), rows=rows,
               note="analytic infra_pg.estimate (core region, gate=core; PHY windows on their own VDDPHY domains); "
                    "lane fit = 16W (0.64 um) clock trunk in a VSS-adjacent half-gap with 0.5-um wide spacing to both "
                    "stripes; max_jog = distance from an island coordinate to the nearest legal lane centre")
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")


class _NoDom(G._PG):
    def __init__(self, P, grid):
        super().__init__(P, grid)
        self.die = dict(self.die, pg={k: v for k, v in self.die["pg"].items() if k != "domains"})


def cmd_psm(a):
    P = plan(a.plan)
    pw = json.loads(Path(a.power).read_text())
    d = density(pw, a.act, a.bound)
    raw = json.loads(Path(a.plan).read_text())
    raw["die"]["pg"] = {k: v for k, v in raw["die"]["pg"].items() if k != "domains"}
    nd = Path(a.out) / "plan_nodomains.json"
    nd.parent.mkdir(parents=True, exist_ok=True)
    nd.write_text(json.dumps(raw))
    Pn = plan(str(nd))
    for spec in a.cand:
        lab, g8, g9 = spec.split(":")
        w8, p8 = map(float, g8.split("@"))
        w9, p9 = map(float, g9.split("@"))
        g = [entry("M8", w8, p8), entry("M9", w9, p9)]
        pg = dict(grid=g, regions=[], core_w_mm2=d, bump_pitch_um=a.bump, vdd=0.7, budget_mv=35.0)
        for win in a.window:
            name, r = win.split("=")
            rect = [float(v) for v in r.split(",")]
            outd = Path(a.out) / f"{lab}_{name}"
            m = G.window_kit(Pn, nd.parent, pg, outd, f"{lab}_{name}", rect, core_w_mm2=d)
            m["plan"] = str(nd.resolve())
            m["tracks"] = G.tracks_of(Pn, g)
            (outd / "irwin.json").write_text(json.dumps(m, indent=1) + "\n")
            print(lab, name, m["window_um"], m["power_w"], "W est", m["est_worst_mv"], "mV", m["tracks"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("power")
    p.add_argument("--rpt", action="append", required=True)
    p.add_argument("--out", required=True)
    for n in ("sweep", "psm"):
        s = sub.add_parser(n)
        s.add_argument("plan")
        s.add_argument("--power", required=True)
        s.add_argument("--act", default="0.5")
        s.add_argument("--bound", choices=("upper", "lower"), default="upper")
        s.add_argument("--out", required=True)
        if n == "sweep":
            s.add_argument("--bump", type=float, action="append")
            s.add_argument("--m8", action="append", help="W@P (default M8_CANDS)")
            s.add_argument("--m9", action="append", help="W@P (default M9_CANDS)")
        else:
            s.add_argument("--bump", type=float, default=150.0)
            s.add_argument("--cand", action="append", required=True, help="LABEL:W8@P8:W9@P9")
            s.add_argument("--window", action="append", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "power":
        return cmd_power(a)
    if a.cmd == "sweep":
        a.bump = a.bump or [150.0]
        return cmd_sweep(a)
    return cmd_psm(a)


if __name__ == "__main__":
    sys.exit(main())
