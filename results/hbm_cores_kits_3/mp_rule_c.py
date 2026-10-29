#!/usr/bin/env python3
"""HBM-CORES-KITS-3: R-SRAM-ENTRY for cores whose SRAMs do not fit one column (estimate first; the kit preflight is
the gate).  Same rule as results/hbm_cores_kits_2/mp_rule.py (R0, columns, 10.8-um channels, split at the clock
entry), written out for C columns:
  1. Macros keep R0 (LEF pins on the W/E edges, horizontal M4 escape into the vertical channels).
  2. C = the fewest columns whose stacks fit the core height (fewest columns = widest channels).  Escape use (macro
     W/E edge pins per M3+M5 vertical track in the adjacent channel) is reported as an UNCHECKED upper bound: logic
     placed in the channel takes most pins locally.  Columns are equally spaced: the free width
     is split into C+1 equal vertical channels (edge channels included), all >= 10.8 um.
  3. Channel widths follow the macro edge pins each channel takes (inner channels serve two columns, edge channels
     one), each >= 10.8 um; the free width is used in full, so the array is symmetric about the core centre (the plan
     entries of these cores sit on the core centre line or on an edge, so the clock tree stays mirror symmetric).
  4. EVERY column is split at the clock entry island (when one side has no room, e.g. an entry near the core edge,
     the whole column goes to the other side) (+ MACRO_PLACE_HALO + one M4 pitch): one horizontal channel
     through the entry crosses the whole core (clock spine E-W, the column's interior channel for macro_channels).
     Inside a stack half, macros sit 2 x halo apart (no std-cell rows between macros; pins are on W/E only).
  5. Macros are assigned to columns in instance order (banks of one generate loop stay together), lower half first.
  6. Escape bound (macro edge pins / vertical tracks of the adjacent channel) > 1.0 -> ESCAPE-RISK (UNCHECKED bound:
     a GRT probe calibrates it).  No C fits -> INFEASIBLE with the deficit: a plan event (outline / macro count), never a kit-local exception.
Outputs macro_placement.v1 (k below the face shell) + estimate JSON."""
import argparse, json, math, re, sys
from pathlib import Path

CH = 10.8
M4P = 0.048
TRK = {"M3": 0.036, "M5": 0.048}
SITE = 0.054


def mk(kd):
    cfg = {}
    for l in (kd / "config.mk").read_text().splitlines():
        m = re.match(r"\s*export\s+(\w+)\s*\??=\s*(.*)$", l)
        if m:
            cfg[m.group(1)] = m.group(2).strip()
    return cfg


def lef(kd, master):
    t = (kd / "macros" / f"{master}.lef").read_text()
    w, h = map(float, re.search(r"SIZE\s+(\S+)\s+BY\s+(\S+)", t).groups())
    side = {"W": 0, "E": 0, "other": 0}
    for pm in re.finditer(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\b", t, re.M | re.S):
        if re.search(r"USE\s+(POWER|GROUND)", pm.group(2)):
            continue
        r = re.search(r"RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", pm.group(2))
        x = float(r.group(1))
        side["W" if x < 1.0 else "E" if x > w - 1.0 else "other"] += 1
    return w, h, side


def plan(insts, sizes, core, halo, ir, ex, C):
    W = max(sizes[m][0] for _, m in insts)
    cw = core[2] - core[0]
    free = cw - C * W
    if free < (C + 1) * CH - 1e-9:
        return None, f"C={C}: channels {free / (C + 1):.2f} um < {CH}"
    per = math.ceil(len(insts) / C)
    cols = [insts[j * per:(j + 1) * per] for j in range(C)]
    # channel widths in proportion to the macro edge pins they take (inner channels serve two columns), >= CH
    load = [(sum(sizes[m][2]["E"] for _, m in cols[c - 1]) if c > 0 else 0) +
            (sum(sizes[m][2]["W"] for _, m in cols[c]) if c < C else 0) for c in range(C + 1)]
    gaps = [CH] * (C + 1)
    rest = free - CH * (C + 1)
    tot = sum(load) or 1
    gaps = [g + rest * l / tot for g, l in zip(gaps, load)]
    xs, x = [], core[0]
    for j in range(C):
        x += gaps[j]
        xs.append(round(round(x / SITE) * SITE, 3))
        x += W
    gap = min(gaps)
    pl, issues, top_used, bot_used = [], [], 0.0, 0.0
    sep = 2 * halo
    for j, col in enumerate(cols):
        lo = col[:len(col) // 2]
        hi = col[len(col) // 2:]
        below = ir[1] - halo - M4P - core[1]
        above = core[3] - (ir[3] + halo + M4P)
        need = lambda part: sum(sizes[m][1] for _, m in part) + sep * max(len(part) - 1, 0)
        if lo and need(lo) > below + 1e-6 and need(col) <= above + 1e-6:
            lo, hi = [], col
        elif hi and need(hi) > above + 1e-6 and need(col) <= below + 1e-6:
            lo, hi = col, []
        y = ir[1] - halo - M4P
        for k, m in lo:
            y -= sizes[m][1]
            pl.append(dict(k=k, macro=m, origin_um=[xs[j], round(y, 3)], orient="R0"))
            y -= sep
        ymin = y + sep if lo else ir[3] + halo + M4P
        y = ir[3] + halo + M4P
        for k, m in hi:
            pl.append(dict(k=k, macro=m, origin_um=[xs[j], round(y, 3)], orient="R0"))
            y += sizes[m][1] + sep
        ymax = y - sep if hi else ir[1] - halo - M4P
        if ymin < core[1] - 1e-6 or ymax > core[3] + 1e-6:
            issues.append(f"C={C} column {j}: stack y [{ymin:.2f},{ymax:.2f}] leaves core y [{core[1]},{core[3]}] "
                          f"(deficit {max(core[1] - ymin, 0) + max(ymax - core[3], 0):.2f} um)")
    # escape: pins of the macros beside each channel / vertical M3+M5 tracks in the channel (less the halos)
    esc = []
    for c in range(C + 1):
        band = gaps[c] - (2 * halo if 0 < c < C else halo)
        pins = (sum(sizes[m][2]["E"] for _, m in cols[c - 1]) if c > 0 else 0) + \
               (sum(sizes[m][2]["W"] for _, m in cols[c]) if c < C else 0)
        sup = int(band / TRK["M3"]) + int(band / TRK["M5"])
        esc.append(dict(channel=c, band_um=round(band, 3), pins=pins, use=round(pins / sup, 3) if sup > 0 else None))
    return dict(C=C, gap_um=round(gap, 3), gaps_um=[round(g, 3) for g in gaps], column_x_um=xs, placement=pl, escape=esc, issues=issues), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kit")
    ap.add_argument("--inst", action="append", required=True, help="k=master (k below the face shell)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--est", required=True)
    a = ap.parse_args()
    kd = Path(a.kit)
    cfg = mk(kd)
    die = [float(v) for v in cfg["DIE_AREA"].split()]
    core = [float(v) for v in cfg["CORE_AREA"].split()]
    halo = max(float(v) for v in cfg.get("MACRO_PLACE_HALO", "0").split())
    ms = json.loads((kd / "master_slice.json").read_text())
    isl = [i for i in ms.get("islands", []) if i.get("clock_pin")]
    ex, ey = map(float, isl[0]["clock_pin"]["xy_um"])
    ir = [float(v) for v in isl[0]["rect_um"]]
    insts = [tuple(s.split("=", 1)) for s in a.inst]
    sizes = {m: lef(kd, m) for m in {m for _, m in insts}}
    est = dict(rule="R-SRAM-ENTRY (C columns, results/hbm_cores_kits_3/mp_rule_c.py)", kit=kd.name, outline_um=die[2:],
               core_um=core, halo_um=halo, clock_entry_um=[ex, ey], entry_island_um=ir, n_macros=len(insts),
               masters={m: dict(w=s[0], h=s[1], pins_W=s[2]["W"], pins_E=s[2]["E"]) for m, s in sizes.items()},
               tried=[])
    best = None
    for C in range(1, len(insts) + 1):
        r, why = plan(insts, sizes, core, halo, ir, ex, C)
        if r is None:
            est["tried"].append(why)
            break
        worst = max(e["use"] or 0 for e in r["escape"])
        est["tried"].append(dict(C=C, issues=r["issues"], esc_max=worst))
        if not r["issues"]:
            best = r
            break
    carea = (core[2] - core[0]) * (core[3] - core[1])
    marea = sum((sizes[m][0] + 2 * halo) * (sizes[m][1] + 2 * halo) for _, m in insts)
    est["area_um2"] = dict(core=round(carea), macros_with_halo=round(marea), free=round(carea - marea))
    if best is None:
        est["verdict"] = "INFEASIBLE"
        print(json.dumps(dict(verdict="INFEASIBLE", kit=kd.name, tried=est["tried"])))
        Path(a.est).write_text(json.dumps(est, indent=1) + "\n")
        return 2
    worst = max(e["use"] or 0 for e in best["escape"])
    est.update(verdict="FEASIBLE" if worst <= 1.0 else "ESCAPE-RISK", columns=best["C"], channel_um=best["gaps_um"], column_x_um=best["column_x_um"],
               escape=best["escape"])
    far = max(abs(ex - cx) + abs(ey - cy) for cx in (core[0], core[2]) for cy in (core[1], core[3]))
    est["entry_to_far_corner_manhattan_um"] = round(far, 2)
    Path(a.out).write_text(json.dumps(dict(schema="opentallas.macro_placement.v1", design=ms.get("module"),
                                           outline_um=die[2:], macro_placement=best["placement"],
                                           note="HBM-CORES-KITS-3 rule R-SRAM-ENTRY, C columns (mp_rule_c.py): equal "
                                                "10.8+ um channels, array centred on the entry x, every column split "
                                                "at the entry island + halo; k below the face shell"), indent=1) + "\n")
    Path(a.est).write_text(json.dumps(est, indent=1) + "\n")
    print(json.dumps(dict(verdict=est["verdict"], kit=kd.name, C=best["C"], channel=best["gap_um"],
                          esc=[e["use"] for e in best["escape"]])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
