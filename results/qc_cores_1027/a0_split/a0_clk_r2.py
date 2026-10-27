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
usage: a0_clk_r2.py LIBDIR OUTDIR
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


def build(core):
    """islands: name -> (xy, region note); leaves: (name, kind, xy, island)."""
    isl, lv = {}, []
    # ROM: vertical PAIRS from islands in the 20-um ROM row gaps under each column centre (legs 65.08 / row 4 from the
    # ROM/LSL strip 65.52), i.e. the same pair form as the LSL columns; the 5 channel-cross islands keep the channel-segment
    # parent roots (12.2a: QC infra island site = A0 channel cross). R1's 120-um channel->ROM-centre legs were the outlier.
    for side, cx in (("W", 22.464 + 86.4), ("E", 262.656 + 86.4)):
        for n, gy, rows in ((f"M{side}01", ROMGAP[1], (0, 1)), (f"M{side}23", ROMGAP[3], (2, 3)), (f"M{side}4", ROMGAP[5], (4,))):
            isl[n] = ((cx, gy), "ROM %s column gap rows %s" % (side, rows))
            lv += [(f"rom_{side}{i}", "romleaf", (cx, ROWY[i]), n) for i in rows]
    for i, y in enumerate(ROWY):
        n = f"R{i}"; isl[n] = ((XC, y), "A0 channel cross, ROM row %d" % i)
        lv += [(f"pch{i}", "parent_tap:channel segment row %d" % i, (XC, y), n)]
    for j, y in enumerate(ROMGAP):                   # E-face parent registers (core wide pin face E): islands in ROM row gaps
        n = f"EF{j}"; isl[n] = ((XEF, y), "E strip, ROM gap %d" % j)
        lv += [(f"pef{j}", "parent_tap:E face strip", (XEF, y), n)]
    for c in (0, 2):                                 # LSL row 0 outer children: own island in the ROM/LSL strip below them
        n = f"L{c}0"; isl[n] = ((LSLX[c], 663.48), "ROM/LSL strip under LSL c%dr0" % c)
        lv += [(f"lsl_c{c}r0", "rawleaf", (LSLX[c], LSLY[0]), n)]
    isl["A"] = ((LSLX[1], LSLY[0]), "empty c1r0 slot")
    lv += [("pslot", "parent_tap:c1r0 slot", (LSLX[1], LSLY[0]), "A")]
    for c in (0, 1, 2):                              # LSL rows 1-2: one island per column in the row gap (equal 80.256 legs)
        n = f"G{c}"; isl[n] = ((LSLX[c], GAP12), "LSL row gap 1-2, column %d" % c)
        lv += [(f"lsl_c{c}r1", "rawleaf", (LSLX[c], LSLY[1]), n), (f"lsl_c{c}r2", "rawleaf", (LSLX[c], LSLY[2]), n),
               (f"pgap{c}", "parent_tap:row gap 1-2 column %d" % c, (LSLX[c], GAP12), n)]
    for k, y in enumerate((740.0, 858.66, 1025.0)):   # EN1 shares its site with the node feed (NX) on NK # E strip above the ROM (NK: beside the node child)
        n = f"EN{k}"; isl[n] = ((XEN, y), "E strip above ROM %d" % k)
        lv += [(f"pen{k}", "parent_tap:E face strip (LSL rows)", (XEN, y), n)]
    if core == "nk":                                 # node child: own E-strip island ~80 um (leg) from its centre entry, like the LSL legs
        lv += [("node", "node", (394.416 + 23.76, 688.656 + 216.0), "EN1")]   # EN1 (452, 858.66): leg 46.0 V + 33.8 H = 79.8 um
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
    rep = dict(schema="qc_cores_1027.a0_clk_r2.v2",
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
            res[cor] = dict(leaves=a, P_min=round(min(P), 2), P_max=round(max(P), 2), P_mean=round(mean, 2),
                            window=round(max(P) - min(P), 2), B=round(TGT[cor] - mean, 2),
                            max_slew=round(max(v["slew"] for v in a.values()), 2))
        halo, pin_isl, pin_leg, in_corr = checks(core)
        rep["cores"][core] = dict(sizes=sz, model=res, islands={n: dict(xy=[round(p[0], 3), round(p[1], 3)], where=w) for n, (p, w) in isl.items()},
                                  n_islands=len(isl), n_child_entries=sum(1 for l in lv if not l[1].startswith("parent")),
                                  n_parent_taps=sum(1 for l in lv if l[1].startswith("parent")),
                                  island_in_child_halo=halo, island_in_pin_column=pin_isl, leg_in_pin_column=pin_leg,
                                  islands_in_bus_corridor=in_corr, max_leg_um=max(man(isl[n][0], xy) for _, _, xy, n in lv))
        render(core, rep["cores"][core], isl, lv)
        print(core, "isl", len(isl), "TT P", res["TT"]["P_mean"], "w", res["TT"]["window"], "B", res["TT"]["B"], "| FF P", res["FF"]["P_mean"],
              "w", res["FF"]["window"], "B", res["FF"]["B"], "| slew", res["TT"]["max_slew"], "| halo", halo, "pin_isl", pin_isl,
              "pin_leg", pin_leg, "corr", in_corr, "maxleg", rep["cores"][core]["max_leg_um"])
    json.dump(rep, open(os.path.join(OUT, "a0_clk_r2_plan.json"), "w"), indent=1)


def render(core, r, isl, lv):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(7.4, 15))
    ax.add_patch(Rectangle((0, 0), W, HH, fill=False, lw=2, ec="k"))
    ax.add_patch(Rectangle((200.664, 16.776), 257.256 - 200.664, 658.44 - 16.776, fc="#fff3c4", ec="#d9b300", lw=0.8, ls="--"))
    ax.text(229, 4, "bus corridor", ha="center", fontsize=6, color="#8a7000")
    col = {"ot_qwen_tile_romleaf": "#9ecae1", "rawleaf": "#a1d99b", "ot_qwen_tile_node": "#fdae6b"}
    for nm, k, rr, face in child_rects(core):
        ax.add_patch(Rectangle(rr[:2], rr[2] - rr[0], rr[3] - rr[1], fc=col[k], ec="#333", lw=0.8))
        if face:
            ax.add_patch(Rectangle((face[0], rr[1]), PINCOL, rr[3] - rr[1], fc="none", ec="#555", hatch="////", lw=0.3))
    for l, k, xy, n in lv:
        a = isl[n][0]; par = k.startswith("parent")
        ax.plot([a[0], a[0], xy[0]], [a[1], xy[1], xy[1]], color="#06c" if par else "#a0a", lw=1.4)
        ax.plot(*xy, marker="^" if par else "s", ms=6 if par else 7, color="#06c" if par else "#600", mec="k")
    for n, (p, _) in isl.items():
        ax.add_patch(Rectangle((p[0] - ISL, p[1] - ISL), 2 * ISL, 2 * ISL, fc="#c00", ec="k", lw=0.8, zorder=5))
        ax.text(p[0] + 6, p[1] + 5, n, fontsize=6.5, weight="bold", zorder=6)
    m = r["model"]
    ax.set_xlim(-10, W + 10); ax.set_ylim(-10, HH + 10); ax.set_aspect("equal")
    ax.set_title(f"qfd_tile_{core}_a0c clock R2 (QC-CORES-1 10-27)  PLAN MODEL, UNCHECKED-model\n"
                 f"{r['n_islands']} in-core pushdown islands (red, die mesh M8/M9 drops) -> M6/M7 legs <= {r['max_leg_um']:.0f} um\n"
                 f"island->entry P TT {m['TT']['P_mean']} (w {m['TT']['window']}) / FF {m['FF']['P_mean']} (w {m['FF']['window']}) ps; "
                 f"common child budget B TT {m['TT']['B']} / FF {m['FF']['B']}\n"
                 f"{r['n_child_entries']} child centre entries (square), {r['n_parent_taps']} parent-FF local roots (triangle); "
                 f"hatched = child pin-face column", fontsize=7.5)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, f"a0_clk_r2_{core}.png"), dpi=110); plt.close(fig)


main()
