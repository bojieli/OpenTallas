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
# DIE-HEAD-10 plan event LEP-C0 (2026-10-28): child 0's coll face (W, vertical, M4/M6 pins) cannot face the N window, and
# a legal orientation never turns a std-cell child by 90 deg.  The old origin (432.0, 790.56) put the window's x432-587 part
# over the child itself (4.32 um above its top edge: no carry path).  Child 0 moves east so the whole N window lies WEST of its
# W face (x 604.8): the carry is a monotone L-fan through the free NW corner (x 393-605 between g_pp[1] and child 0, and above
# g_pp[1]); child 3 moves south (y 328.32) so child 0's E (K) face has the open NE quadrant and child 3's coll face still
# covers the E coll3 window (y 521-760).  All 4 origins on the G0C 8.64-um hard-core lattice.  Die plan pins / windows unchanged.
WINDOWS = {0: ("N", 160.0, 587.2), 1: ("W", 640.0, 1067.2), 2: ("W", 120.0, 547.2), 3: ("E", 521.19, 759.64)}
PAIRS = [
    ("u_core.u.g_pp[0].u_pair", (604.8, 786.24), "R0",
     "coll window N x160-587 entirely west of the W face (x604.8): parent L-fan carry (DIE-HEAD-10 LEP-C0)"),
    ("u_core.u.g_pp[1].u_pair", (8.64, 639.36), "R0", "coll window W y640-1067"),
    ("u_core.u.g_pp[2].u_pair", (8.64, 120.96), "R0", "coll window W y120-547 (face y120.96-552.96: 0.96-um jog)"),
    ("u_core.u.g_pp[3].u_pair", (1028.16, 328.32), "MY",
     "coll window E y521-760 inside the E face y328-760; 21.6-um E channel keeps E ctl/fault/lw (y769-1124) and lepk "
     "(y10-511) reachable (DIE-HEAD-10 LEP-C0: moved south from y521.28)"),
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


def carry_estimate(crs, errs):
    """Parent carry from each plan coll window to its child's coll face (W for R0, E for MY), monotone (order-keeping)
    fan: window end a <-> face end a.  Window must not project over the child itself (a carry would cross the child),
    and the free channel beside the face must hold the bits that turn there (vertical tracks M5+M7, 0.048/0.064 um ASAP7
    pitch, <= 50 % use).  UNCHECKED estimate: no route."""
    out = {}
    for k, (n, r) in enumerate(crs):
        face, lo, hi = WINDOWS[k]
        ori = PAIRS[k][2]
        fx = r[0] if ori == "R0" else r[2]
        bits = 1026
        if face == "N":
            over = max(0.0, min(hi, r[2]) - max(lo, r[0]))
            if over > 0:
                errs.append(f"carry: child {k} coll window N x{lo}-{hi} lies {over:.1f} um over the child (no path)")
            # rightmost window pin -> top face pin; leftmost -> bottom
            worst = max(abs(fx - lo) + (LEP[1] - r[1]), abs(fx - hi) + (LEP[1] - r[3]))
            # bits that turn into the face below the neighbour's top run down the channel west of the face
            nb = [c for j, (_, c) in enumerate(crs) if j != k and c[2] <= fx + 1e-6 and c[3] > r[1]]
            ch_x0 = max([c[2] for c in nb], default=0.0)
            ch_w = fx - ch_x0
            low = min([c[3] for c in nb], default=r[1])
            n_ch = bits * max(0.0, min(low, r[3]) - r[1]) / (r[3] - r[1])
            supply = 0.5 * (ch_w / 0.048 + ch_w / 0.064)
            if n_ch > supply:
                errs.append(f"carry: child {k} channel {ch_w:.1f} um holds {supply:.0f} < {n_ch:.0f} bits")
            # window pins west of the channel cross OVER no child: they run east in the band above the neighbour(s)
            # (horizontal M4+M6, <= 50 %) before turning down the channel
            band_h = LEP[1] - max([c[3] for c in nb], default=r[1])
            n_band = bits * max(0.0, min(hi, ch_x0) - lo) / (hi - lo)
            band_supply = 0.5 * (band_h / 0.048 + band_h / 0.064)
            if n_band > band_supply:
                errs.append(f"carry: child {k} band {band_h:.1f} um above the neighbour holds {band_supply:.0f} < {n_band:.0f}")
            out[k] = dict(window=[face, lo, hi], face_x=fx, worst_manhattan_um=round(worst, 1), channel_um=round(ch_w, 1),
                          channel_x0_um=round(ch_x0, 2), channel_bits=round(n_ch), channel_supply_50pct=round(supply),
                          band_um=round(band_h, 2), band_bits=round(n_band), band_supply_50pct=round(band_supply),
                          over_child_um=round(over, 1))
        else:
            # DIE-HEAD-10: hard-core origins on the G0C 8.64-um lattice; a window end may sit < one lattice step
            # outside the face (a parent jog of that length)
            jog = max(0.0, r[1] - lo, hi - r[3])
            inside = jog <= 8.64 - 1e-6
            edge = 0.0 if face == "W" else LEP[0]
            worst = abs(fx - edge) + max(0.0, r[1] - lo, hi - r[3])
            if not inside:
                errs.append(f"carry: child {k} coll window {face} y{lo}-{hi} not inside its face y{r[1]}-{r[3]}")
            out[k] = dict(window=[face, lo, hi], face_x=fx, worst_manhattan_um=round(worst, 1), window_inside_face=inside, jog_um=round(jog, 2))
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
    carry = carry_estimate(crs, errs)
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
        "coll_carry": carry,
        "placed_total": sum(expanded.values()), "errors": errs,
        "status": "UNCHECKED estimate: packing + area only; no placement/route of the child yet",
    }
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    delta = {
        "note": "DIE-HEAD-9 LEP split plan delta + DIE-HEAD-10 plan event LEP-C0 (child 0 east of the N coll window, child 3 "
                "south); applied to die_plan.json by head_lep_pair_apply.py",
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
    # DIE-HEAD-10: child 0 carry fan (window ends -> W face ends)
    (o0, ), = [(o,) for n, o, _, _ in PAIRS[:1]]
    nb_top, ch_x = PAIRS[1][1][1] + CHILD[1], PAIRS[1][1][0] + CHILD[0]      # g_pp[1] top edge / E edge: band above it, channel east of it
    for wx, fy in ((WINDOWS[0][1], o0[1]), (WINDOWS[0][2], o0[1] + CHILD[1])):
        if wx < ch_x:
            yb = nb_top + 0.5 * (LEP[1] - nb_top)
            xc = ch_x + 0.5 * (o0[0] - ch_x)
            ax.plot([wx, wx, xc, xc, o0[0]], [LEP[1], yb, yb, fy, fy], lw=1.2, ls="--", color="#59a14f")
        else:
            ax.plot([wx, wx, o0[0]], [LEP[1], fy, fy], lw=1.2, ls="--", color="#59a14f")
    ax.text(ch_x + 4, o0[1] + 6, "coll0 carry", fontsize=7, color="#59a14f")
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
