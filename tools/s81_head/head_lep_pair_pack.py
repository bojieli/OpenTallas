"""DIE-HEAD-9 LEP split packing (estimate before build; COORD 2026-10-28 06:30 ruling (4)).

    python3 tools/s81_head/head_lep_pair_pack.py --census lep_hierarchy_census.json --out DIR [--png]

hd_lep0N -> 4 peer PAIR children ot_s81hd_lep_pair (g_lane[k] = lnland + safe8 coll lane, ot_s81hd_lep0N_core PAIR=1)
+ parent (u_lep + u_land + glue).  Emits, from the exact macro census (265 SRAM, 5 real types in
physical/asap7_memory_macros_v2), plan-form contents[] with lef / lib / origin_um / orient for
  - the child type (55 SRAM, child-relative inst names, identical for all 4 children), and
  - the parent type (45 SRAM + the 4 child placements as hard_cores without a lef until the child is signed off),
checks that every census instance is placed exactly once (4 x 55 + 45 = 265), inside its frame, without overlap and with
the stated channels, and renders the packing.  Coordinates: 1.08-um placement grid, outlines on the 4.32-um PDN pitch.
Geometry facts (LEF): every SRAM has its signal pins on BOTH vertical edges (x=0 and x=w, y 0.77..20.2) on M4, so the
lattice leaves a vertical channel on each side of every macro; cell areas are the hierarchy-preserving Yosys numbers.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

MD = "physical/asap7_memory_macros_v2"
G = 1.08          # placement grid
SIZE = {}         # module -> (w, h) from LEF


def lef_size(mod):
    s = Path(f"{MD}/{mod}/{mod}.lef").read_text()
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", s)
    return float(m.group(1)), float(m.group(2))


def snap(v):
    return round(round(v / G) * G, 3)


# ---- child: 388.8 x 432 (coll face W on M4/M6, K face E on M4/M6) ----------------------------------------------------
CHILD = (388.8, 432.0)
CH_STD_UM2 = 5893.03 + 10650.76      # lnland + coll lane std-cell area (synth_stat, hierarchy-preserving)
PAR_STD_UM2 = 93173.68 - 4 * CH_STD_UM2
CH_COL_X0, CH_COL_PITCH = 34.56, 49.68   # W band 34.56 (coll face flops) | 6 macro columns | E band (K landing ring)
CH_ROW_Y0, BIG_PITCH, SMALL_PITCH = 21.6, 47.52, 21.6


def child_pack(insts):
    big = [i for i in insts if i[1] == "ot_sram_1r1w2c_256x64_m1"]
    small = [i for i in insts if i[1] == "ot_sram_1r1w2c_32x64_m1"]
    assert len(big) == 36 and len(small) == 19, (len(big), len(small))
    out = []
    col = 0
    y = CH_ROW_Y0
    # columns 0..3: 8 big each; column 4: 4 big + 9 small; column 5: 10 small
    plan = [("b", 8), ("b", 8), ("b", 8), ("b", 8), ("b", 4, "s", 9), ("s", 10)]
    bi = si = 0
    for c, spec in enumerate(plan):
        x = snap(CH_COL_X0 + c * CH_COL_PITCH)
        y = CH_ROW_Y0
        for k in range(0, len(spec), 2):
            kind, n = spec[k], spec[k + 1]
            for _ in range(n):
                if kind == "b":
                    inst, mod = big[bi]; bi += 1; pitch = BIG_PITCH
                else:
                    inst, mod = small[si]; si += 1; pitch = SMALL_PITCH
                out.append((inst, mod, x, snap(y), "R0"))
                y += pitch
    assert bi == 36 and si == 19
    return out


# ---- parent: LEP 1442.88 x 1226.88 -----------------------------------------------------------------------------------
LEP = (1442.88, 1226.88)
# child origins (lower-left of the placed outline) and orient; coll face W for R0, E for MY
PAIRS = [
    ("u_core.u.g_pp[0].u_pair", (432.0, 790.56), "R0",
     "coll window N x160-587: parent jog from the N edge into the child W face (open: plan window move)"),
    ("u_core.u.g_pp[1].u_pair", (4.32, 637.2), "R0", "coll window W y640-1067"),
    ("u_core.u.g_pp[2].u_pair", (4.32, 116.64), "R0", "coll window W y120-547"),
    ("u_core.u.g_pp[3].u_pair", (1032.48, 521.28), "MY",
     "coll window E y521-760; 21.6-um E channel keeps the E ctl/fault/lw pins (y769-1124) reachable"),
]


def parent_pack(insts):
    by = {m: [i for i in insts if i[1] == m] for m in set(i[1] for i in insts)}
    out = []
    # u_lep: 20 x 512x128 (169.368 x 29.16) in 2 columns x 10, 20 x 32x128 (51.432 x 20.808) in 2 columns x 10,
    # south-centre region beside the E lepk window (y 10-511); 21.6-um vertical channels at both pin edges.
    a = by["ot_sram_1r1w_512x128_m4_r0c0"]
    assert len(a) == 20
    for k, (inst, mod) in enumerate(a):
        c, r = divmod(k, 10)
        out.append((inst, mod, snap(453.6 + c * (169.368 + 21.6 + 0.032)), snap(21.6 + r * 37.8), "R0"))
    b = by["ot_sram_1r1w_32x128_m1_r0c0"]
    assert len(b) == 20
    for k, (inst, mod) in enumerate(b):
        c, r = divmod(k, 10)
        out.append((inst, mod, snap(838.08 + c * (51.432 + 21.6 + 0.048)), snap(21.6 + r * 29.16), "R0"))
    # u_land: 5 x 128x256 (91.8 x 39.432) in one column, centre, north of the u_lep bank
    d = by["ot_sram_1r1w_128x256_m1_r0c0"]
    assert len(d) == 5
    for k, (inst, mod) in enumerate(d):
        out.append((inst, mod, snap(453.6), snap(421.2 + k * 48.6), "R0"))
    return out


def overlaps(r1, r2, gap=0.0):
    return not (r1[2] + gap <= r2[0] or r2[2] + gap <= r1[0] or r1[3] + gap <= r2[1] or r2[3] + gap <= r1[1])


def rect(mod_or_wh, x, y):
    w, h = SIZE[mod_or_wh] if isinstance(mod_or_wh, str) else mod_or_wh
    return (x, y, round(x + w, 3), round(y + h, 3))


def check(frame, placed, xgap, ygap, label):
    errs = []
    rs = [(p[0], rect(p[1], p[2], p[3])) for p in placed]
    for n, r in rs:
        if r[0] < 0 or r[1] < 0 or r[2] > frame[0] + 1e-6 or r[3] > frame[1] + 1e-6:
            errs.append(f"{label}: {n} outside frame {r}")
        if abs(r[0] / G - round(r[0] / G)) > 1e-6 or abs(r[1] / G - round(r[1] / G)) > 1e-6:
            errs.append(f"{label}: {n} off grid {r[:2]}")
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            a, b = rs[i][1], rs[j][1]
            # x channel between macros side by side, y gap between stacked ones
            if not (a[2] + xgap <= b[0] or b[2] + xgap <= a[0] or a[3] + ygap <= b[1] or b[3] + ygap <= a[1]):
                errs.append(f"{label}: {rs[i][0]} / {rs[j][0]} closer than x{xgap}/y{ygap}")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--png", action="store_true")
    a = ap.parse_args()
    C = json.loads(Path(a.census).read_text())
    for m in C["macro_types"]:
        SIZE[m] = lef_size(m)
    lanes = {}
    par = []
    for m in C["macros"]:
        mm = re.match(r"u_core\.u\.g_lane\[(\d)\]\.(.*)$", m["inst"])
        if mm:
            lanes.setdefault(int(mm.group(1)), []).append((mm.group(2), m["module"]))
        else:
            par.append((m["inst"], m["module"]))
    rel = [sorted(lanes[k]) for k in range(4)]
    assert rel[0] == rel[1] == rel[2] == rel[3], "children differ: not one replicated type"
    child = child_pack(sorted(rel[0]))
    parent = parent_pack(sorted(par))
    errs = check(CHILD, child, 15.0, 4.0, "child") + check(LEP, parent, 21.6, 7.5, "parent")
    # children vs frame / each other / parent macros (5.4-um keepout)
    crs = [(n, rect(CHILD, o[0], o[1])) for n, o, _, _ in PAIRS]
    for n, r in crs:
        if r[0] < 0 or r[1] < 0 or r[2] > LEP[0] or r[3] > LEP[1]:
            errs.append(f"parent: child {n} outside LEP {r}")
    for i in range(4):
        for j in range(i + 1, 4):
            if overlaps(crs[i][1], crs[j][1], 4.32):
                errs.append(f"parent: children {crs[i][0]} / {crs[j][0]} overlap")
        for p in parent:
            if overlaps(crs[i][1], rect(p[1], p[2], p[3]), 5.4):
                errs.append(f"parent: {p[0]} inside child {crs[i][0]}")
    expanded = Counter()
    for k in range(4):
        for p in child:
            expanded[f"u_core.u.g_lane[{k}].{p[0]}"] += 1
    for p in parent:
        expanded[p[0]] += 1
    census = Counter(m["inst"] for m in C["macros"])
    if expanded != census:
        errs.append(f"census mismatch: {sum(expanded.values())} placed vs {sum(census.values())}")

    def ent(p, kind):
        return {"inst": p[0], "module": p[1], "kind": "sram", "origin_um": [p[2], p[3]], "orient": p[4],
                "lef": f"{MD}/{p[1]}/{p[1]}.lef", "lib": f"{MD}/{p[1]}/{p[1]}_tt.lib",
                "lib_ff": f"{MD}/{p[1]}/{p[1]}_ff.lib", "note": kind}
    mac_child = sum(SIZE[p[1]][0] * SIZE[p[1]][1] for p in child)
    mac_par = sum(SIZE[p[1]][0] * SIZE[p[1]][1] for p in parent)
    ca, la = CHILD[0] * CHILD[1], LEP[0] * LEP[1]
    est = {
        "child": {"outline_um": list(CHILD), "area_um2": ca, "macros": len(child), "macro_um2": round(mac_child, 1),
                  "std_um2": round(CH_STD_UM2, 1), "std_cells": 109242,
                  "std_util_of_free": round(CH_STD_UM2 / (ca - mac_child), 3),
                  "ports": {"k_in": 1 + 553 + 1 + 1, "k_out": 1 + 1 + 553 + 3, "coll_in": 514, "coll_out": 512},
                  "k_face_pins_per_um": round((556 + 558) / CHILD[1], 2),
                  "coll_face_pins_per_um": round(1026 / CHILD[1], 2)},
        "parent": {"outline_um": list(LEP), "area_um2": la, "macros": len(parent), "macro_um2": round(mac_par, 1),
                   "std_um2": round(PAR_STD_UM2, 1), "std_cells": 183691, "children_um2": 4 * ca,
                   "std_util_of_free": round(PAR_STD_UM2 / (la - 4 * ca - mac_par), 3)},
        "placed_total": sum(expanded.values()), "errors": errs,
        "status": "UNCHECKED estimate: packing + area only; no placement/route of the child yet",
    }
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    delta = {
        "note": "DIE-HEAD-9 LEP split plan delta (proposal; not applied to die_plan.json until the child kit is built)",
        "child_type": {"name": "hd_lep_pair", "module": "ot_s81hd_lep_pair", "params": {"CHB": "1'b1"},
                       "outline_um": list(CHILD), "hard": True, "cells": 109242,
                       "contents": [ent(p, "child SRAM (u_lane coll FIFO)") for p in child]},
        "parent_type": {"name": "hd_lep0N", "params": {"PAIR": 1}, "cells": 183691,
                        "hard_cores": [{"inst": n, "module": "ot_s81hd_lep_pair", "origin_um": list(o),
                                        "outline_um": list(CHILD), "orient": ori, "note": note,
                                        "lef": None} for n, o, ori, note in PAIRS],
                        "contents": [ent(p, "parent SRAM") for p in parent]},
    }
    (out / "lep_pair_plan_delta.json").write_text(json.dumps(delta, indent=1) + "\n")
    (out / "lep_pair_pack_estimate.json").write_text(json.dumps(est, indent=1) + "\n")
    print(json.dumps({k: v for k, v in est.items() if k != "errors"}, indent=1))
    print("ERRORS", len(errs), errs[:10])
    if a.png:
        render(out, child, parent)
    return 1 if errs else 0


def render(out, child, parent):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    col = {"ot_sram_1r1w2c_256x64_m1": "#4e79a7", "ot_sram_1r1w2c_32x64_m1": "#76b7b2",
           "ot_sram_1r1w_512x128_m4_r0c0": "#e15759", "ot_sram_1r1w_32x128_m1_r0c0": "#f28e2b",
           "ot_sram_1r1w_128x256_m1_r0c0": "#b07aa1"}
    fig, axs = plt.subplots(1, 2, figsize=(18, 8.5), gridspec_kw={"width_ratios": [1, 2.4]})
    ax = axs[0]
    ax.add_patch(Rectangle((0, 0), *CHILD, fill=False, lw=1.5))
    for p in child:
        w, h = SIZE[p[1]]
        ax.add_patch(Rectangle((p[2], p[3]), w, h, color=col[p[1]], alpha=.85))
        ax.add_patch(Rectangle((p[2], p[3] + 0.77), 0.6, 10, color="k"))
        ax.add_patch(Rectangle((p[2] + w - 0.6, p[3] + 0.77), 0.6, 10, color="k"))
    ax.axvspan(0, CH_COL_X0, color="#59a14f", alpha=.2)
    ax.axvspan(CH_COL_X0 + 5 * CH_COL_PITCH + 34.584, CHILD[0], color="#edc948", alpha=.25)
    ax.text(2, CHILD[1] + 4, "coll face W (514 in/512 out)", fontsize=8)
    ax.text(CHILD[0] - 120, CHILD[1] + 4, "K face E (556 in/558 out)", fontsize=8)
    ax.set_title(f"PAIR child ot_s81hd_lep_pair {CHILD[0]}x{CHILD[1]} um, 55 SRAM")
    ax.set_xlim(-10, CHILD[0] + 10); ax.set_ylim(-10, CHILD[1] + 20); ax.set_aspect("equal")
    ax = axs[1]
    ax.add_patch(Rectangle((0, 0), *LEP, fill=False, lw=1.5))
    for n, o, ori, _ in PAIRS:
        ax.add_patch(Rectangle(o, *CHILD, fill=True, color="#bab0ac", alpha=.5, lw=1))
        for p in child:
            w, h = SIZE[p[1]]
            x = p[2] if ori == "R0" else CHILD[0] - p[2] - w
            ax.add_patch(Rectangle((o[0] + x, o[1] + p[3]), w, h, color=col[p[1]], alpha=.6))
        ax.text(o[0] + 8, o[1] + CHILD[1] - 18, n.split(".")[-2] + " " + ori, fontsize=8)
    for p in parent:
        w, h = SIZE[p[1]]
        ax.add_patch(Rectangle((p[2], p[3]), w, h, color=col[p[1]], alpha=.9))
    # plan bus windows
    for face, lo, hi, lab in [("N", 160, 587.2, "coll0"), ("W", 640, 1067.2, "coll1"), ("W", 120, 547.2, "coll2"),
                              ("E", 521.19, 759.64, "coll3"), ("E", 10, 511.19, "lepk"), ("E", 769.6, 1124.7, "ctl")]:
        if face == "N":
            ax.plot([lo, hi], [LEP[1] + 6, LEP[1] + 6], lw=4, color="k")
            ax.text(lo, LEP[1] + 12, lab, fontsize=8)
        else:
            x = -6 if face == "W" else LEP[0] + 6
            ax.plot([x, x], [lo, hi], lw=4, color="k")
            ax.text(x + (-40 if face == "W" else 4), (lo + hi) / 2, lab, fontsize=8)
    ax.set_title(f"hd_lep0N {LEP[0]}x{LEP[1]}: 4 PAIR children + 45 parent SRAM (u_lep 40, u_land 5)")
    ax.set_xlim(-60, LEP[0] + 60); ax.set_ylim(-20, LEP[1] + 30); ax.set_aspect("equal")
    hs = [Rectangle((0, 0), 1, 1, color=c) for c in col.values()]
    ax.legend(hs, [k.replace("ot_sram_", "") for k in col], fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(out / "lep_pair_pack.png", dpi=110)


if __name__ == "__main__":
    raise SystemExit(main())
