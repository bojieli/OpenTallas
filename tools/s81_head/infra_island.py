#!/usr/bin/env python3
"""S81-HEAD in-core INFRA ISLAND (HEAD-CORE-LAT, owner 2026-10-26 ~06:3x: Qwen SU decision applied to all dies).

The head die has no channels (partitions cover 95.4 %, CLOCK-MESH-B 01:13), so the die clock mesh drivers and the
regional reset drivers get ONE top-owned hole per hard core (elemA_cv x1056, elemB_cv x264):
  * hole = placement keep-out for core cells + core routing obstruction M2..M5 (core MAX_ROUTING_LAYER) -- the die/tile
    places its own FIXED cells there and drops an M9->M1 via stack in the middle; core M1 follow-pin rails continue
    through the hole (shared PG, no core signal or cell inside);
  * contents = die CLOCK + RESET drivers ONLY (COORD correction 1+2, 10-26): die-signal FT stations / repeaters are
    NOT in the island; they stay pushed down into core repeater bays (<= M7 FT slots, every <= 405 um) and are signed
    off with the core.  HEAD census: hd_tile carries no ft_slots, so elemA/elemB need 0 FT bays (core edge <= 318 um);
  * the core clk pin and rst_n pin sit ON the hole edge (M5), so the die stub is inside the hole and the core tree
    root starts at the hole -- the core clock-latency target is measured from that pin.
Lattice rule: every hole edge lands on the die 8.64-um lattice (= PG pitch, 32 rows) in ALL four instance orientations
(R0/MX/MY/R180).  With core origins on the lattice, a hole at core-frame x0 = 8.64 k needs size w = W mod 8.64
(+ 8.64 n) so that W - x0 - w is also a lattice multiple.  The routine below checks all 1320 instances of the plan.

Usage: infra_island.py PLAN.json --out DIR   (writes island_spec.json, island_<type>.tcl, io pin lines)
"""
import argparse, json, math, os, sys

G = 8.64          # die lattice (PG pitch M8/M9, 32 x 0.27 rows)
ROW = 0.27
HALO = 1.08       # core placement halo around the hole (4 rows)
EPS = 1e-6

# measured ASAP7 RVT LEF widths (ORFS asap7sc7p5t_28_R_1x_220121a.lef, height 0.27)
W_CELL = {"BUFx24_ASAP7_75t_R": 1.62, "BUFx12f_ASAP7_75t_R": 0.972, "BUFx4f_ASAP7_75t_R": 0.432,
          "DFFHQNx2_ASAP7_75t_R": 1.134}
# per-island demand: clock + reset only (COORD correction 1)
DEMAND = [
    ("clock", "mesh node driver pair (die mesh strap -> strap), KV/HEAD mesh pattern", "BUFx24_ASAP7_75t_R", 2),
    ("clock", "core-root stub driver -> core clk pin on the hole edge", "BUFx24_ASAP7_75t_R", 1),
    ("clock", "die-absorbed latency trim chain (method item 7), up to ~130 ps TT", "BUFx4f_ASAP7_75t_R", 8),
    ("reset", "regional reset register (sync_stages 2) -> core rst_n pin", "DFFHQNx2_ASAP7_75t_R", 2),
    ("reset", "reset wavefront hop repeater in/out (hop <= 378 um, M8/M9)", "BUFx12f_ASAP7_75t_R", 2),
]
VIA_STACK_KEEP = (1.08, 1.08)   # M9->M1 stack + NDR halo footprint at the hole centre (um)

# Hole sites in the R0 core frame.  elemA ROMs (125.304 x 62.952, halo 4.32): rom0 (95.04,146.88), rom1 (95.04,233.28);
# elemB ROMs MY at (77.76,103.68)/(77.76,190.08).  Hole under rom0, near the core x centre (sink centroid band).
# OUTLINE SNAP (measured, 10-26): with the old outlines (317.672 / 277.652, not lattice multiples) the cores inside the
# 132 MY hd_tile instances sit off the 8.64 lattice (origin 708.48-17.28-317.672 = 373.528), so NO hole size is
# lattice-invariant over all 1320 instances (660 errors).  Rebuilt cores therefore take lattice-multiple outlines:
# elemA 317.672 -> 319.68 (37 G, +1.3 % area), elemB 277.652 -> 285.12 (33 G, +5.4 %), same tile-frame origins (tile
# outline unchanged; gaps stay >= 17.28).  E/N face pins move out by the growth.  Hole = one 8.64 x 8.64 lattice cell.
OLD_W = {"ot_s81hd_elemA_cv": 317.672, "ot_s81hd_elemB_cv": 277.652}
TYPES = {
    "ot_s81hd_elemA_cv": {"short": "elemA", "W": 319.68, "x0": 155.52, "y0": 120.96,
                          "roms": [(95.04, 146.88), (95.04, 233.28)]},
    "ot_s81hd_elemB_cv": {"short": "elemB", "W": 285.12, "x0": 129.6, "y0": 86.4,
                          "roms": [(77.76, 103.68), (77.76, 190.08)]},
}
ROM_WH = (125.304, 62.952)
ROM_HALO = 4.32


def on_lat(v):
    return abs(v / G - round(v / G)) < 1e-6


def hole_size(W):
    r = W - G * round(W / G)
    if abs(r) > EPS:
        raise SystemExit(f"outline {W} is not a lattice multiple")
    return G   # one lattice cell; holds the demand at < 10 % row use


def demand():
    rows = []
    tot = 0.0
    for kind, what, cell, n in DEMAND:
        L = W_CELL[cell] * n
        tot += L
        rows.append({"kind": kind, "what": what, "cell": cell, "n": n, "row_len_um": round(L, 3)})
    return rows, round(tot, 3)


def place(orient, ox, oy, W, x, y, w, h, H=None):
    H = W if H is None else H
    """core-frame rect -> parent rect for ORFS orientations (origin = lower-left of the placed outline)."""
    if orient == "R0":
        return ox + x, oy + y
    if orient == "MX":       # mirror about x axis: y flips
        return ox + x, oy + H - y - h
    if orient == "MY":
        return ox + W - x - w, oy + y
    if orient == "R180":
        return ox + W - x - w, oy + H - y - h
    raise ValueError(orient)


def build(plan):
    rows, tot = demand()
    spec = {"schema": "opentallas.infra_island.v1", "die": "s81_head", "lattice_um": G, "halo_um": HALO,
            "contents": "die clock + reset drivers ONLY; FT stations stay in core repeater bays (<=M7, <=405 um)",
            "demand": rows, "demand_row_len_um": tot, "types": {}, "instances": [], "errors": []}
    for mod, t in TYPES.items():
        W = t["W"]; w = h = hole_size(W)
        x0, y0 = t["x0"], t["y0"]
        rows_in = int(h / ROW + EPS)
        cap = rows_in * w - VIA_STACK_KEEP[0] * math.ceil(VIA_STACK_KEEP[1] / ROW) * 1.0
        util = tot / cap
        for rx, ry in t["roms"]:
            a = (rx - ROM_HALO - HALO, ry - ROM_HALO - HALO, rx + ROM_WH[0] + ROM_HALO + HALO, ry + ROM_WH[1] + ROM_HALO + HALO)
            if not (x0 + w <= a[0] or x0 >= a[2] or y0 + h <= a[1] or y0 >= a[3]):
                spec["errors"].append(f"{mod}: hole overlaps ROM at {rx},{ry} (+halo)")
        if not (on_lat(x0) and on_lat(y0) and on_lat(W - x0 - w) and on_lat(W - y0 - h)):
            spec["errors"].append(f"{mod}: hole not lattice-invariant")
        cx, cy = x0 + w / 2, y0 + h / 2
        spec["types"][mod] = {
            "outline_um": [W, W], "hole_um": [round(x0, 4), round(y0, 4), round(x0 + w, 4), round(y0 + h, 4)],
            "hole_size_um": w, "hole_area_um2": round(w * h, 3), "hole_area_pct": round(100 * w * h / (W * W), 4),
            "keepout_um": [round(x0 - HALO, 4), round(y0 - HALO, 4), round(x0 + w + HALO, 4), round(y0 + h + HALO, 4)],
            "keepout_area_pct": round(100 * (w + 2 * HALO) * (h + 2 * HALO) / (W * W), 4),
            "core_route_obs_layers": ["M2", "M3", "M4", "M5"],
            "via_stack_um": [round(cx, 4), round(cy, 4)], "via_stack": "M9->M1, die-owned, NDR halo 1.08",
            "rows_in_hole": rows_in, "demand_util": round(util, 4),
            "pins": {"clk": {"layer": "M5", "xy": [round(cx, 4), round(y0 + h, 4)], "edge": "hole N"},
                     "rst_n": {"layer": "M5", "xy": [round(cx, 4), round(y0, 4)], "edge": "hole S"}},
        }
    # every instance of the plan
    types = plan["partition_types"]
    origin = {p["name"]: (p["origin_um"], p.get("orient", "R0")) for p in plan["partitions"]}
    n = 0
    for pname, (porg, pori) in origin.items():
        pt = next(p["type"] for p in plan["partitions"] if p["name"] == pname)
        for hc in types[pt].get("hard_cores", []):
            mod = hc["module"]
            if mod not in TYPES:
                continue
            ts = spec["types"][mod]
            x0, y0, x1, y1 = ts["hole_um"]
            hx, hy = place(hc["orient"], hc["origin_um"][0], hc["origin_um"][1], ts["outline_um"][0], x0, y0, x1 - x0, y1 - y0)
            if pori != "R0":
                PW, PH = types[pt]["outline_um"]
                hx, hy = place(pori, 0, 0, PW, hx, hy, x1 - x0, y1 - y0, PH)
            dx, dy = porg[0] + hx, porg[1] + hy
            if not (on_lat(hx) and on_lat(hy) and on_lat(dx) and on_lat(dy)):
                spec["errors"].append(f"{pname}/{hc['inst']}: hole off lattice ({dx:.3f},{dy:.3f})")
            spec["instances"].append({"part": pname, "inst": hc["inst"], "module": mod, "orient": hc["orient"],
                                      "tile_hole_um": [round(hx, 4), round(hy, 4)], "die_hole_um": [round(dx, 4), round(dy, 4)]})
            n += 1
    spec["n_instances"] = n
    spec["n_by_type"] = {m: sum(1 for i in spec["instances"] if i["module"] == m) for m in TYPES}
    return spec


def tcl(mod, ts):
    """core-kit hook (appended to MACRO_PLACEMENT_TCL): placement blockage + M2..M5 obstruction over the hole."""
    k = ts["keepout_um"]; h = ts["hole_um"]
    return f"""# GENERATED by tools/s81_head/infra_island.py ({mod}): top-owned INFRA ISLAND (die clock + reset drivers only)
set ii_b [ord::get_db_block]
set ii_t [ord::get_db_tech]
set ii_u [$ii_t getDbUnitsPerMicron]
proc ii_d {{v}} {{ return [expr {{round($v * $::ii_u)}}] }}
set ii_pb [odb::dbBlockage_create $ii_b [ii_d {k[0]}] [ii_d {k[1]}] [ii_d {k[2]}] [ii_d {k[3]}]]
puts "INFRA_ISLAND placement keep-out {' '.join(str(v) for v in k)}"
foreach ln {{M2 M3 M4 M5}} {{
  set l [$ii_t findLayer $ln]
  odb::dbObstruction_create $ii_b $l [ii_d {h[0]}] [ii_d {h[1]}] [ii_d {h[2]}] [ii_d {h[3]}]
}}
puts "INFRA_ISLAND route obstruction M2-M5 {' '.join(str(v) for v in h)}"
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    spec = build(plan)
    os.makedirs(a.out, exist_ok=True)
    json.dump(spec, open(os.path.join(a.out, "island_spec.json"), "w"), indent=1)
    for mod, ts in spec["types"].items():
        open(os.path.join(a.out, f"island_{TYPES[mod]['short']}.tcl"), "w").write(tcl(mod, ts))
        with open(os.path.join(a.out, f"island_{TYPES[mod]['short']}_pins.tcl"), "w") as f:
            for pn, p in ts["pins"].items():
                f.write(f"place_pin -pin_name {{{pn}}} -layer {p['layer']} -location {{{p['xy'][0]:.4f} {p['xy'][1]:.4f}}} -pin_size {{0.1920 0.1920}}\n")
    print(json.dumps({m: {k: v for k, v in t.items() if k != 'pins'} for m, t in spec["types"].items()}, indent=1))
    print("instances", spec["n_instances"], spec["n_by_type"], "errors", len(spec["errors"]), spec["errors"][:5])
    return 1 if spec["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
