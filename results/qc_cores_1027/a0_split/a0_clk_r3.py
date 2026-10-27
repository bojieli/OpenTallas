#!/usr/bin/env python3
"""QC-CORES-1 A0 clock re-plan R2 (2026-10-27): answer to GEOM-REVIEW-18 [QC-CORES-A0-SPLIT] FAIL-IN-PLAN (a)-(c) + (i)-(iv).
Planning only: no P&R.  Outline and children are unchanged (split + floorplan PASS, Codex b7da9afaa).

Why R1's single in-core E0 tree is replaced (CHECKED against METHODOLOGY 12.2a / 12.8b):
  * 12.2a: hard cores route their own logic on <= M7 and never use M8/M9. An in-core E0->hub->node tree on M8/M9 (the
    GEOM-18 (ii) reading) is therefore only legal if those wires are DIE-owned. On M6/M7, R1's 3-level tree models at
    P ~200 ps TT before any child-internal tree (UNCHECKED-model), leaving B ~50 ps for 12k-sink children -> infeasible.
  * 12.8b: a core whose entry-to-sink distance exceeds ~200 um is restructured FIRST as an internal H-tree with IN-CORE
    ISLANDS (12.2a1 pushdown). A0 is 457.92 x 1157.76 um.
  * 12.2a: the QC infra island site is the A0 channel cross.
R2 structure:
  die mesh/H-tree (M8/M9, die-owned, signed with the die mesh)
    -> N in-core PUSHDOWN islands (12.2a1: driver cells in the core netlist at plan-fixed coordinates, identical for all 720/48
       instances, die feed-through port in from the M9->M5 stack)
    -> per-branch drivers (12.8 d1 plan-computed sizing)
    -> short M6/M7 legs (core layers; children capped at M5, so M6/M7 over the children belong to the parent)
    -> leaf points.
  Leaf points are:
    (1) each hard child's CENTRE clock entry (re-kit spec, 12.8a);
    (2) the parent-FF local-tree roots, one per parent soft region, built to the SAME leaf budget B as the child-internal
        trees, so parent FFs land at the composed insertion of the child sinks.
  12.3 composed latency is counted at the core clock pins = the island feed ports:
    P (island port -> leaf entry) + B (child/parent-local internal) = 250 TT / 202.5 FF.
  B is ONE value for all three masters.
  Geometry rules:
    * no leg in a row gap (GEOM-18 (ii)), except the island's own vertical stub;
    * no leg or island in a child pin-face column (15.12 um beside a pin face, G5 extended, COORD 10-27);
    * islands outside child + 5.4 um halo; islands in the Codex bus corridor are reported for capacity re-deduction.
Model: the su_tree_uf_ls.py stage model (liberty NLDM RVT TT/FF, Elmore, setRC M5/M6 x rc_cal 0.8/0.9 for M6/M7 legs).
PLAN MODEL, UNCHECKED-model. The su_tree predictor family reads ~15 ps HIGH on TT vs routed (COORD 10-27); numbers are reported raw.
usage: a0_clk_r3.py LIBDIR OUTDIR
R3 (QC-CORES-2 10-27): islands snapped to an A0 TYPE drop lattice (XL x YL) for the die M8/M9 strap plan delta; B split child/parent.
"""
import json
import os
import sys

sys.path.insert(0, sys.argv[1])
import lib  # noqa: E402

LIBDIR, OUT = sys.argv[1], sys.argv[2]
H = os.path.dirname(os.path.abspath(__file__))
SIZES = ["BUFx8_ASAP7_75t_R", "BUFx10_ASAP7_75t_R", "BUFx12f_ASAP7_75t_R", "BUFx16f_ASAP7_75t_R", "BUFx24_ASAP7_75t_R"]
BIG = "BUFx24_ASAP7_75t_R"
LIBS = {k: lib.cells(os.path.join(LIBDIR, f"invbuf_{k.lower()}.lib"), SIZES) for k in ("TT", "FF")}
R_UM = 0.5 * (1.80365e-2 + 1.89935e-2) * 0.8      # su_tree_uf_ls.py constants (M5/M6 setRC) -> conservative for M6/M7
C_UM = 0.5 * (1.78475e-1 + 1.64264e-1) * 0.9
SIN_ISL = 30.0                                     # slew at the island feed port from the die mesh drop (assumption, UNCHECKED)
TGT = {"TT": 250.0, "FF": 202.5}
PINCOL, HALO, ISL = 15.12, 5.4, 4.32               # pin-face column width, child halo, island half-size (8.64 um rect)


def interp(tab, s, C):
    i1, i2, v = tab

    def idx(a, x):
        for k in range(len(a) - 1):
            if x <= a[k + 1]:
                return k
        return len(a) - 2
    a, b = idx(i1, s), idx(i2, C)
    ta = (s - i1[a]) / (i1[a + 1] - i1[a])
    tb = (C - i2[b]) / (i2[b + 1] - i2[b])
    return v[a][b] * (1 - ta) * (1 - tb) + v[a + 1][b] * ta * (1 - tb) + v[a][b + 1] * (1 - ta) * tb + v[a + 1][b + 1] * ta * tb


def stage(cor, cell, sin, w, cp):
    L = LIBS[cor][cell]
    C = C_UM * w + cp
    d = 0.5 * (interp(L["rise"], sin, C) + interp(L["fall"], sin, C))
    so = 0.5 * (interp(L["trise"], sin, C) + interp(L["tfall"], sin, C))
    so = (so ** 2 + (2.2 * R_UM * w * (C_UM * w / 2 + cp)) ** 2) ** 0.5
    return d + R_UM * w * (C_UM * w / 2 + cp), so


man = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
fp = json.load(open(os.path.join(H, "input_parent_floorplan_codex_b7da9afaa.json")))
W, HH = fp["nk"]["outline_um"]
XC = W / 2                                           # 228.96 = A0 channel centre line (12.2a channel cross)
ROWY = [22.176 + 55.08, 152.352 + 55.08, 282.528 + 55.08, 412.704 + 55.08, 542.88 + 55.08]
ROMGAP = [11.088, 142.344, 272.52, 402.696, 532.872, 663.48]   # bottom margin, 4 ROM row gaps, ROM-top/LSL-bottom strip
LSLX = [15.984 + 57.672, 142.128 + 57.672, 268.272 + 57.672]
LSLY = [673.92 + 70.2, 834.432 + 70.2, 994.944 + 70.2]
GAP12 = (974.832 + 994.944) / 2
XEF = 446.688                                        # E strip (ROM E col + halo ends 440.856; outline 457.92)
XEN = 452.0                                          # E strip above ROM (node + halo ends 447.336)


XL = [108.864, XC, 349.056, 452.0]                  # R3 core-frame M9 drop columns (ROM column centres, channel, E strip)
GAP01 = (673.92 + 140.4 + 834.432) / 2               # 824.376 LSL row gap 0-1
YL = ROMGAP + [GAP01, GAP12]                         # R3 core-frame M8 drop rows: 6 ROM gaps/strips + 2 LSL row gaps


def build(core):
    """R3: every island sits on a crossing of the A0 TYPE drop lattice XL x YL (die M9 straps at x0+XL, M8 straps at
    y0+YL, MX rows mirrored), at a legal parent site (gap/strip/channel, outside child + halo). Leaves (child centre entries,
    parent-FF local roots) keep their R2 positions; legs = vertical M7 at the island x, then horizontal M6 at the leaf y."""
    isl, lv = {}, []
    for side, cx in (("W", XL[0]), ("E", XL[2])):     # ROM pairs from ROM-column-centre islands (unchanged from R2)
        for n, gy, rows in ((f"M{side}01", ROMGAP[1], (0, 1)), (f"M{side}23", ROMGAP[3], (2, 3)), (f"M{side}4", ROMGAP[5], (4,))):
            isl[n] = ((cx, gy), "ROM %s column gap rows %s" % (side, rows))
            lv += [(f"rom_{side}{i}", "romleaf", (cx, ROWY[i]), n) for i in rows]
    lv += [("lsl_c0r0", "rawleaf", (LSLX[0], LSLY[0]), "MW4"), ("lsl_c2r0", "rawleaf", (LSLX[2], LSLY[0]), "ME4")]  # R2 L00/L20 merged
    for i, y in enumerate(ROWY):                       # channel islands move from the row centre to the gap above (M8 row)
        n = f"R{i}"; isl[n] = ((XC, ROMGAP[i + 1]), "A0 channel cross, gap above ROM row %d" % i)
        lv += [(f"pch{i}", "parent_tap:channel segment row %d" % i, (XC, y), n)]
    lv += [("pslot", "parent_tap:c1r0 slot", (LSLX[1], LSLY[0]), "R4")]   # R2 island A merged into R4 (ROM/LSL strip)
    for j, y in enumerate(ROMGAP):                     # E-face parent roots: E strip column x 452 (R2 446.688)
        n = f"EF{j}"; isl[n] = ((XL[3], y), "E strip, ROM gap %d" % j)
        lv += [(f"pef{j}", "parent_tap:E face strip", (XL[3], y), n)]
    lv += [("pen0", "parent_tap:E face strip (LSL rows)", (XEN, 740.0), "EF5")]  # R2 EN0 merged into EF5
    for c in (0, 1, 2):                                # LSL rows 1-2: islands in row gap 1-2 on the lattice columns
        n = f"G{c}"; isl[n] = ((XL[c], GAP12), "LSL row gap 1-2, lattice column %d" % c)
        lv += [(f"lsl_c{c}r1", "rawleaf", (LSLX[c], LSLY[1]), n), (f"lsl_c{c}r2", "rawleaf", (LSLX[c], LSLY[2]), n),
               (f"pgap{c}", "parent_tap:row gap 1-2 column %d" % c, (XL[c], GAP12), n)]
    isl["EN1"] = ((XL[3], GAP01), "E strip, LSL row gap 0-1")
    isl["EN2"] = ((XL[3], GAP12), "E strip, LSL row gap 1-2")
    lv += [("pen1", "parent_tap:E face strip (LSL rows)", (XEN, 858.66), "EN1"), ("pen2", "parent_tap:E face strip (LSL rows)", (XEN, 1025.0), "EN2")]
    if core == "nk":
        lv += [("node", "node", (394.416 + 23.76, 688.656 + 216.0), "EN1")]
    return isl, lv


def evaluate(core, sz, cor):
    isl, lv = build(core)
    out = {}
    for l, k, xy, n in lv:
        L = max(man(isl[n][0], xy), 2.0)             # >= 2 um stub even when the local root sits on the island
        d, s = stage(cor, sz[l], SIN_ISL, L, LIBS[cor][BIG]["cin"])
        out[l] = dict(kind=k, island=n, leg_um=round(L, 2), P=round(d, 2), slew=round(s, 2))
    return out


def optimise(core):
    """12.8 d1: per-branch driver from the fixed list, chosen from plan geometry only. Target = the slowest leaf at BUFx24
    (longest leg); every other branch takes the size whose TT delay is nearest that target (FF as tie-break)."""
    isl, lv = build(core)
    sz = {l: BIG for l, _, _, _ in lv}
    ref = evaluate(core, sz, "TT")
    tgt = max(v["P"] for v in ref.values())
    reff = evaluate(core, sz, "FF"); tgtf = max(v["P"] for v in reff.values())
    for l, _, _, _ in lv:
        best = None
        for c in SIZES:
            sz[l] = c
            a = evaluate(core, sz, "TT")[l]; b = evaluate(core, sz, "FF")[l]
            sc = (a["slew"] > 60, abs(a["P"] - tgt), abs(b["P"] - tgtf))
            if best is None or sc < best[0]:
                best = (sc, c)
        sz[l] = best[1]
    return sz


def child_rects(core):
    rs = []
    for c in fp[core]["hard_children"]:
        k = "rawleaf" if c["view"].startswith("PENDING") else c["view"].split("/")[-1]
        x, y = c["at"]; w, h = c["size_um"]
        face = None
        if k != "ot_qwen_tile_node":                 # romleaf LEF: 530 pins on E face (CHECKED); rawleaf: wide face E (kit pins.json)
            fx = x + w if c["orient"] == "R0" else x
            face = (fx, fx + PINCOL) if c["orient"] == "R0" else (fx - PINCOL, fx)
        rs.append((c["inst"][-34:], k, (x, y, x + w, y + h), face))
    return rs


def checks(core):
    isl, lv = build(core)
    rs = child_rects(core)
    halo, pin_isl, pin_leg = [], [], []
    for n, (p, _) in isl.items():
        R = (p[0] - ISL, p[1] - ISL, p[0] + ISL, p[1] + ISL)
        if R[0] < 0 or R[1] < 0 or R[2] > W or R[3] > HH:
            halo.append([n, "outside outline"])
        for nm, k, r, face in rs:
            if R[0] < r[2] + HALO and R[2] > r[0] - HALO and R[1] < r[3] + HALO and R[3] > r[1] - HALO:
                halo.append([n, nm])
            if face and R[0] < face[1] and R[2] > face[0] and R[1] < r[3] + ISL and R[3] > r[1] - ISL:
                pin_isl.append([n, nm])
    for l, k, xy, n in lv:                           # leg = vertical then horizontal (M7 V / M6 H); test both segments
        a = isl[n][0]
        segs = [((a[0], min(a[1], xy[1])), (a[0], max(a[1], xy[1]))), ((min(a[0], xy[0]), xy[1]), (max(a[0], xy[0]), xy[1]))]
        for nm, kk, r, face in rs:
            if not face:
                continue
            for (x0, y0), (x1, y1) in segs:
                if x0 < face[1] and x1 > face[0] and y0 < r[3] and y1 > r[1]:
                    pin_leg.append([l, nm])
    corr = (200.664, 16.776, 257.256, 658.44)
    in_corr = [n for n, (p, _) in isl.items() if corr[0] <= p[0] <= corr[2] and corr[1] <= p[1] <= corr[3]]
    return halo, pin_isl, pin_leg, in_corr


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = dict(schema="qc_cores_1027.a0_clk_r3.v1",
               scope="PLAN MODEL ONLY, UNCHECKED-model (NLDM RVT + Elmore, setRC M5/M6 x 0.8/0.9 for M6/M7 legs); su_tree predictor "
                     "family reads ~15 ps HIGH on TT vs routed (COORD 10-27), numbers raw",
               structure="die mesh/H-tree (M8/M9, die-owned) -> in-core pushdown islands (12.2a1) -> sized per-branch driver -> M6/M7 leg "
                         "-> child centre entry | parent-FF local root",
               sin_island_ps=SIN_ISL, target=TGT,
               child_reKit={"clk_pin_child_frame": {"ot_qwen_tile_romleaf": [86.4, 55.08], "rawleaf": [57.672, 70.2], "ot_qwen_tile_node": [23.76, 216.0]},
                            "rules": ["clk pin = child centre (12.8a) on the child's own 8.64-um centre island, M7->M5 drop",
                                      "child routing ceiling M5 (OBS <= M5) so parent M6/M7 legs pass over the child",
                                      "child internal tree built to the common budget B (same for all three masters)"]},
               cores={})
    for core in ("nk", "nl"):
        sz = optimise(core)
        isl, lv = build(core)
        res = {}
        for cor in ("TT", "FF"):
            a = evaluate(core, sz, cor)
            P = [v["P"] for v in a.values()]
            mean = sum(P) / len(P)
            Pc = [v["P"] for v in a.values() if not v["kind"].startswith("parent")]
            Pp = {k: v["P"] for k, v in a.items() if v["kind"].startswith("parent")}
            mc = sum(Pc) / len(Pc)
            res[cor] = dict(leaves=a, P_min=round(min(P), 2), P_max=round(max(P), 2), P_mean_all=round(mean, 2),
                            P_child_mean=round(mc, 2), child_window=round(max(Pc) - min(Pc), 2),
                            B_child=round(TGT[cor] - mc, 2), B_par={k: round(TGT[cor] - p, 2) for k, p in Pp.items()},
                            max_slew=round(max(v["slew"] for v in a.values()), 2),
                            B_note="B_child = target - mean P over CHILD entries only (goes into the child re-kits); each parent root "
                                   "builds its local tree to its own B_par. R2's render/json 'B' (212.56 TT) averaged child AND parent "
                                   "taps -- wrong field; R2 README 206 = child-only = the right definition")
        halo, pin_isl, pin_leg, in_corr = checks(core)
        rep["cores"][core] = dict(sizes=sz, model=res, islands={n: dict(xy=[round(p[0], 3), round(p[1], 3)], where=w) for n, (p, w) in isl.items()},
                                  n_islands=len(isl), n_child_entries=sum(1 for l in lv if not l[1].startswith("parent")),
                                  n_parent_taps=sum(1 for l in lv if l[1].startswith("parent")),
                                  island_in_child_halo=halo, island_in_pin_column=pin_isl, leg_in_pin_column=pin_leg,
                                  islands_in_bus_corridor=in_corr, max_leg_um=max(man(isl[n][0], xy) for _, _, xy, n in lv))
        render(core, rep["cores"][core], isl, lv)
        print(core, "isl", len(isl), "TT Pc", res["TT"]["P_child_mean"], "w", res["TT"]["child_window"], "B", res["TT"]["B_child"], "| FF Pc", res["FF"]["P_child_mean"],
              "w", res["FF"]["child_window"], "B", res["FF"]["B_child"], "| slew", res["TT"]["max_slew"], "| halo", halo, "pin_isl", pin_isl,
              "pin_leg", pin_leg, "corr", in_corr, "maxleg", rep["cores"][core]["max_leg_um"])
    json.dump(rep, open(os.path.join(OUT, "a0_clk_r3_plan.json"), "w"), indent=1)


def render(core, r, isl, lv):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(8.2, 16))
    ax.add_patch(Rectangle((0, 0), W, HH, fill=False, lw=2, ec="k"))
    ax.add_patch(Rectangle((200.664, 16.776), 257.256 - 200.664, 658.44 - 16.776, fc="#fff3c4", ec="#d9b300", lw=0.8, ls="--"))
    ax.text(229, 4, "bus corridor", ha="center", fontsize=6, color="#8a7000")
    for x in XL:                                     # die M9 drop straps over the type (R24 plan-delta request)
        ax.axvline(x, color="#e08", lw=0.6, ls=(0, (6, 3)), zorder=1)
    for y in YL:                                     # die M8 drop straps
        ax.axhline(y, color="#08c", lw=0.6, ls=(0, (6, 3)), zorder=1)
    col = {"ot_qwen_tile_romleaf": "#9ecae1", "rawleaf": "#a1d99b", "ot_qwen_tile_node": "#fdae6b"}
    for nm, k, rr, face in child_rects(core):
        ax.add_patch(Rectangle(rr[:2], rr[2] - rr[0], rr[3] - rr[1], fc=col[k], ec="#333", lw=0.8))
        if face:
            ax.add_patch(Rectangle((face[0], rr[1]), PINCOL, rr[3] - rr[1], fc="none", ec="#555", hatch="////", lw=0.3))
    ax.add_patch(Rectangle((191.5 - 3, 984.888 - 3), 6, 6, fc="#ff0", ec="k", lw=0.6, zorder=4))
    ax.text(170, 992, "fault_q hub", fontsize=5.5, zorder=6)
    for l, k, xy, n in lv:
        a = isl[n][0]; par = k.startswith("parent")
        ax.plot([a[0], a[0], xy[0]], [a[1], xy[1], xy[1]], color="#06c" if par else "#a0a", lw=1.4, zorder=3)
        ax.plot(*xy, marker="^" if par else "s", ms=8 if par else 7, color="#2a9df4" if par else "#600", mec="k", zorder=7)
        if par:
            ax.text(xy[0] - 4, xy[1] - 12, l, fontsize=5.5, color="#036", zorder=8, ha="right")
    for n, (p, _) in isl.items():
        ax.add_patch(Rectangle((p[0] - ISL, p[1] - ISL), 2 * ISL, 2 * ISL, fc="#c00", ec="k", lw=0.8, zorder=5))
        ax.text(p[0] + 6, p[1] + 5, n, fontsize=6.5, weight="bold", zorder=6)
    m = r["model"]
    ax.set_xlim(-10, W + 10); ax.set_ylim(-10, HH + 10); ax.set_aspect("equal")
    ax.set_title(f"qfd_tile_{core}_a0c clock R3 (QC-CORES-2 10-27)  PLAN MODEL, UNCHECKED-model\n"
                 f"{r['n_islands']} islands (red) ALL on type drop lattice: M9 x {XL} (pink) x M8 rows (blue dashed)\n"
                 f"child entry P TT {m['TT']['P_child_mean']} (w {m['TT']['child_window']}) / FF {m['FF']['P_child_mean']} (w {m['FF']['child_window']}) ps; "
                 f"child budget B TT {m['TT']['B_child']} / FF {m['FF']['B_child']}; legs <= {r['max_leg_um']:.0f} um\n"
                 f"{r['n_child_entries']} child centre entries (square), {r['n_parent_taps']} parent-FF local roots (triangle, labelled); "
                 f"hatched = child pin-face column", fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, f"a0_clk_r3_{core}.png"), dpi=110); plt.close(fig)

main()
