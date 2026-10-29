#!/usr/bin/env python3
"""HBM-CORES-KITS-2: one SRAM placement rule per HBM hard core (COORD ruling (a), 10-28 19:30), estimate first.

RULE R-SRAM-ENTRY (one rule, every core):
  1. Macros keep R0 (pins stay on their LEF M4 W/E edges, horizontal escape on M4).
  2. Macros of a core form ONE column (stack) when the stack fits the core height; a column keeps a >= 10.8 um
     vertical routing channel to the core edge on both sides (kit_contract.macro_channels).
  3. The column is centred on the plan clock entry x (clamped so both channels stay >= 10.8 um): the core clock tree
     from the centre entry is then mirror-symmetric about the entry.
  4. The stack is split at the clock entry: n_lo = n//2 macros below, the rest above, with the entry island + the
     MACRO_PLACE_HALO (+ one M4 pitch for the kit's track snap) kept clear on both sides (clock_entry_clear,
     island_macro_clear); further macros on each side keep 10.8 um gaps.  The split band is the interior horizontal
     channel of the stack (>= 10.8 um by construction: island 8.64 + 2 x 4.32 halo).
  5. If the column cannot be centred on the entry (stack too tall for the core even when split), the rule reports
     INFEASIBLE with the deficit; the fix is then a plan event (outline or entry), never a kit-local exception.
Outputs: macro_placement.v1 JSON (k = instance path BELOW the face shell: gen_core_kit_hbm adds 'u_fcore.') + an
estimate record (area/util, channel widths, escape tracks vs pins, entry-to-corner reach).
"""
import argparse, json, re, sys
from pathlib import Path

CH = 10.8          # kit_contract.MIN_CHANNEL_UM
M4P = 0.048
TRK = {"M2": 0.036, "M3": 0.036, "M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064}


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kit")
    ap.add_argument("--inst", action="append", required=True, help="k=master (k below the face shell)")
    ap.add_argument("--logic-um2", type=float, default=None, help="std-cell area estimate (synth)")
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
    insts = [s.split("=", 1) for s in a.inst]
    masters = {m for _, m in insts}
    sizes = {m: lef(kd, m) for m in masters}
    W = max(sizes[m][0] for m in masters)
    est = dict(rule="R-SRAM-ENTRY", kit=kd.name, outline_um=die[2:], core_um=core, halo_um=halo,
               clock_entry_um=[ex, ey], entry_island_um=ir, macros=[[k, m] for k, m in insts], issues=[])
    # x: centre on the entry, clamp to the channels
    x0 = ex - W / 2.0
    lo_x, hi_x = core[0] + CH, core[2] - CH - W
    if lo_x > hi_x:
        est["issues"].append(f"INFEASIBLE x: column {W:g} + 2x{CH:g} channels > core width {core[2]-core[0]:g}")
    x0 = min(max(x0, lo_x), hi_x)
    x0 = round(round(x0 / 0.054) * 0.054, 3)                       # placement-site grid
    spans_entry = x0 - halo < ir[2] and ir[0] < x0 + W + halo
    n = len(insts)
    lo_n = n // 2 if spans_entry else 0
    below, above = insts[:lo_n], insts[lo_n:]
    pl = []
    # below: top of the stack at entry island - halo - one pitch, stacking downwards with CH gaps
    ytop = ir[1] - halo - M4P
    for k, m in below:
        h = sizes[m][1]
        y0 = ytop - h
        pl.append(dict(k=k, macro=m, origin_um=[x0, round(y0, 3)], orient="R0"))
        ytop = y0 - CH
    ybot = (ir[3] + halo + M4P) if spans_entry else None
    if not spans_entry:
        tot = sum(sizes[m][1] for _, m in above) + CH * (len(above) - 1)
        ybot = (core[1] + core[3]) / 2.0 - tot / 2.0
    for k, m in above:
        h = sizes[m][1]
        pl.append(dict(k=k, macro=m, origin_um=[x0, round(ybot, 3)], orient="R0"))
        ybot = ybot + h + CH
    # checks (estimate level; kit_preflight is the gate)
    ys = [(p["origin_um"][1], p["origin_um"][1] + sizes[p["macro"]][1]) for p in pl]
    ymin, ymax = min(y for y, _ in ys), max(y for _, y in ys)
    if ymin < core[1] - 1e-6 or ymax > core[3] + 1e-6:
        est["issues"].append(f"INFEASIBLE y: stack y [{ymin:.3f},{ymax:.3f}] leaves core y [{core[1]},{core[3]}]")
    est["column_x_um"] = [x0, round(x0 + W, 3)]
    est["channels_um"] = dict(W=round(x0 - core[0], 3), E=round(core[2] - x0 - W, 3),
                              S_band=round(ymin - core[1], 3), N_band=round(core[3] - ymax, 3))
    est["entry_split"] = spans_entry
    carea = (core[2] - core[0]) * (core[3] - core[1])
    marea = sum((sizes[m][0] + 2 * halo) * (sizes[m][1] + 2 * halo) for _, m in insts)
    est["area_um2"] = dict(core=round(carea), macros_with_halo=round(marea), free=round(carea - marea))
    if a.logic_um2:
        est["area_um2"]["logic"] = a.logic_um2
        est["logic_util_free"] = round(a.logic_um2 / (carea - marea), 3)
    # escape: macro W/E edge pins vs vertical tracks (M3+M5) in the band beside the column
    pins_w = sum(sizes[m][2]["W"] for _, m in insts)
    pins_e = sum(sizes[m][2]["E"] for _, m in insts)
    for side, band, pins in (("W", x0 - core[0] - halo, pins_w), ("E", core[2] - x0 - W - halo, pins_e)):
        sup = int(band / TRK["M3"]) + int(band / TRK["M5"])
        est.setdefault("escape", {})[side] = dict(band_um=round(band, 3), vtracks_M3_M5=sup, macro_pins=pins,
                                                   use=round(pins / sup, 3) if sup else None)
    far = max(abs(ex - cx) + abs(ey - cy) for cx in (core[0], core[2]) for cy in (core[1], core[3]))
    est["entry_to_far_corner_manhattan_um"] = round(far, 2)
    est["verdict"] = "FEASIBLE" if not est["issues"] else "INFEASIBLE"
    Path(a.out).write_text(json.dumps(dict(schema="opentallas.macro_placement.v1", design=ms.get("module"),
                                           outline_um=die[2:], macro_placement=pl,
                                           note="HBM-CORES-KITS-2 rule R-SRAM-ENTRY (results/hbm_cores_kits_2/mp_rule.py): "
                                                "column centred on the plan clock entry x, stack split at the entry "
                                                "island + halo, 10.8 um channels; k below the face shell"), indent=1) + "\n")
    Path(a.est).write_text(json.dumps(est, indent=1) + "\n")
    print(json.dumps(est))
    return 0 if not est["issues"] else 2


if __name__ == "__main__":
    sys.exit(main())
