#!/usr/bin/env python3
"""PATH-S81/PHY (2026-10-26): can the 14 S81 SerDes windows each get a one-row N7 6-lane 112G macro (published
figure, phy_assumptions.json: shore 3078 low / 3318 central + 2 x 63.64 guard, depth 937 low / 1011 central, on the
die edge) by a RE-LAY of the die plan?  Read-only study, no plan delta.  Successor of phy_shore_budget.py (which
re-laid the SerDes partitions only and found 12/10 of 14).

Options measured on the plan geometry (die outline, 1442.88 x 1226.88 cell grid, partition rects, edge segments):
  a  corners / L-arrangement      b  rotated macros on the W/E edges (fabric shift or die growth)
  c  orientation / depth on N/S   d  move gunit + bk_sel (and S-row parts) off the shoreline rows
  e  minimum die growth with every non-SerDes partition left in place
If a candidate plan is given (--cand, e.g. Codex B2 die_plan_phyfit_allocated.json), it is checked for legality
(no overlap, inside the core, every SerDes on the edge with >= shore+2*guard width and >= depth) and its lane cycle
ledger (--ledger) is summarised.

usage: phy_relay_study.py [PLAN.json] [ASSUMPTIONS.json] [--cand CAND.json] [--ledger LEDGER.json]
                          [--out OUT.json] [--png OUT.png]
"""
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD_UM = 63.64          # pg_domains.PHY_GUARD_UM
GRID = 8.64
REACH_UM = 405.0          # registered-hop reach (owner 10-17)
JUNCTION_STRIP_UM = 900.0  # phy_shore_budget.py (lk_WN3 -> s_0N_x06 coll windows)
SLOT_PAIR_UM = 230.0
RETICLE = (33000.0, 26000.0)
MOVABLE_N = ("gunit", "bk_sel")
MOVABLE_S = ("iqf", "eng", "s_7S_x10")


def snap_up(v):
    return math.ceil(round(v / GRID, 6)) * GRID


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]


def load(path):
    p = json.load(open(path))
    T = p["partition_types"]
    R = {}
    for q in p["partitions"]:
        w, h = T[q["type"]]["outline_um"]
        x, y = q["origin_um"]
        R[q["name"]] = (x, y, x + w, y + h)
    ser = [io["part"] for io in p["die"]["io"] if io.get("iface") == "serdes"]
    return p, R, ser


def grid_of(R):
    xs = sorted({round(r[0], 2) for r in R.values()})
    ys = sorted({round(r[1], 2) for r in R.values()})
    return xs, ys


def segments(R, ser, row, W, margin, skip=()):
    """free shoreline segments of an edge row ('S' or 'N') after removing non-SerDes edge parts (except skip)."""
    H_edge = lambda r: r[1] <= margin + 1 if row == "S" else None
    edge = []
    ymax = max(r[3] for r in R.values())
    for n, r in R.items():
        on = r[1] <= margin + 1 if row == "S" else r[3] >= ymax - 1
        if on and n not in ser and n not in skip:
            edge.append((r[0], r[2], n))
    edge.sort()
    segs, pos = [], margin
    for a, b, n in edge:
        if a - pos > 1:
            segs.append((pos, a))
        pos = max(pos, b)
    if W - margin - pos > 1:
        segs.append((pos, W - margin))
    return segs, [e[2] for e in edge]


def fit(segs, pitch, junction=0.0):
    return sum(int(max(0.0, (b - a) - junction + 1e-6) // pitch) for a, b in segs)


def centre(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def manh(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def main(argv):
    opt = {}
    for k in ("--cand", "--ledger", "--out", "--png"):
        if k in argv:
            i = argv.index(k); opt[k] = argv[i + 1]; del argv[i:i + 2]
    plan_path = argv[1] if len(argv) > 1 else os.path.join(HERE, "die_plan.json")
    asm_path = argv[2] if len(argv) > 2 else os.path.join(HERE, "phy_assumptions.json")
    p, R, ser = load(plan_path)
    ent = {e["id"]: e for e in json.load(open(asm_path))["entries"]}
    W, H = p["die"]["outline_um"]
    xs, ys = grid_of(R)
    margin = xs[0]
    cw, rh = xs[1] - xs[0], ys[1] - ys[0]
    fig = {}
    for tag, key in (("low", "low"), ("central", "value")):
        shore = ent["SER.MACRO6_SHORE"][key]; depth = ent["SER.DEPTH_N7"][key]
        fig[tag] = dict(shore_um=shore, depth_um=depth, pitch_um=round(snap_up(shore + 2 * GUARD_UM), 2),
                        depth_grid_um=round(snap_up(depth), 2))
    res = dict(plan=os.path.relpath(plan_path, HERE) if plan_path.startswith(HERE) else os.path.basename(plan_path),
               plan_sha256_12=sha(plan_path), die_outline_um=[W, H], die_mm2=round(W * H / 1e6, 2),
               cell_um=[round(cw, 2), round(rh, 2)], core_margin_um=margin, figures=fig, reticle_um=RETICLE,
               options={})
    shore_row = W - 2 * margin
    side_len = H - 2 * margin - 2 * rh            # W/E edge between the N and S SerDes rows (rows 1..18)
    lanes = {l["id"]: l.get("fixed_cycles") for l in p["lanes"] if "lk_" in l["id"]}
    target = {}
    for lid in lanes:
        a, b = lid.split("__")[1:3]
        lk, other = (a, b) if a.startswith("lk_") else (b, a)
        target[lk] = other

    # ---------- base: SerDes-only re-lay (phy_shore_budget.py) ----------
    sS, fS = segments(R, ser, "S", W, margin)
    sN, fN = segments(R, ser, "N", W, margin)
    base = {t: dict(fit=fit(sS, f["pitch_um"]) + fit(sN, f["pitch_um"]),
                    fit_junction=fit(sS, f["pitch_um"], JUNCTION_STRIP_UM) + fit(sN, f["pitch_um"], JUNCTION_STRIP_UM))
            for t, f in fig.items()}
    res["options"]["base_serdes_only"] = dict(S_fixed=fS, N_fixed=fN, S_segments=[[round(a, 2), round(b, 2)] for a, b in sS],
                                              N_segments=[[round(a, 2), round(b, 2)] for a, b in sN], fits=base)

    # ---------- a: corners ----------
    corners = {}
    for cname, (cx, cy) in dict(SW=(margin, margin), SE=(W - margin - cw, margin),
                                NW=(margin, H - margin - rh), NE=(W - margin - cw, H - margin - rh)).items():
        occ = [n for n, r in R.items() if r[0] <= cx + 1 < r[2] and r[1] <= cy + 1 < r[3]]
        corners[cname] = occ[0] if occ else None
    res["options"]["a_corners"] = dict(
        corner_cells=corners,
        fits={t: dict(fit=base[t]["fit"], fit_junction=base[t]["fit_junction"], extra=0) for t in fig},
        why="corner cells are already SerDes (or free shore counted in the S-E segment); a corner adds no shoreline "
            "of its own (the 103.68-um core margin is the corner/seal keep-out). An L macro must stand on the W/E edge "
            "rotated, i.e. it is option b (3 fabric rows per macro).")

    # ---------- b: rotated macros on W/E edges ----------
    fab = {}
    for side, x0 in (("W", margin), ("E", W - margin - cw)):
        cells = [n for n, r in R.items() if abs(r[0] - x0) < 1 and rh * 0.9 < r[1] < H - margin - rh - 1]
        T = p["partition_types"]
        ext = 0.0
        for n in cells:
            q = next(q for q in p["partitions"] if q["name"] == n)
            hc = T[q["type"]].get("hard_cores") or []
            for h in hc:   # edge-side extent of hard cores (W side: from the left of the cell, E: from the right)
                lo, hi = h["origin_um"][0], h["origin_um"][0] + h["outline_um"][0]
                ext = max(ext, hi if side == "E" else cw - lo)
            fab[side] = dict(cells=len(cells), max_core_reach_from_inner_face_um=round(ext, 2))
    b = dict(side_length_um=round(side_len, 2), per_side={}, fits={}, fabric=fab)
    for t, f in fig.items():
        rows_per = math.ceil(f["pitch_um"] / rh)
        per_side = int(side_len // (rows_per * rh))
        left = cw - f["depth_grid_um"]
        b["per_side"][t] = dict(rows_per_macro=rows_per, macros_per_side=per_side, fabric_cells_displaced_per_side=per_side * rows_per,
                                fabric_cell_width_left_um=round(left, 2))
        grow1 = f["depth_grid_um"]
        b["fits"][t] = dict(
            zero_area="NO: each macro takes %d fabric rows x %.0f um of a %.0f-um fW/fE cell (%.0f um left); the qbank "
                      "cores of those cells reach %.0f um from the inner face and no free cells exist to re-home them"
                      % (rows_per, f["depth_grid_um"], cw, left, max(v["max_core_reach_from_inner_face_um"] for v in fab.values())),
            one_side_strip_um=grow1, die_w_um=round(W + grow1, 2), fits_reticle=W + grow1 <= RETICLE[0],
            two_side_die_w_um=round(W + 2 * grow1, 2), two_side_fits_reticle=W + 2 * grow1 <= RETICLE[0],
            area_delta_mm2=round(grow1 * H / 1e6, 2), area_mm2=round((W + grow1) * H / 1e6, 2),
            fit=min(14, per_side + base[t]["fit"]), fit_junction=min(14, per_side + base[t]["fit_junction"]))
    # link impact for W-strip: 6 W links on the W edge (rows centred like the fW blocks), others stay; the whole
    # die shifts +strip in x, so fabric-internal links are unchanged.
    f = fig["central"]
    rows_per = b["per_side"]["central"]["rows_per_macro"]
    wl = sorted([s for s in ser if s.startswith("lk_W")], key=lambda s: (s[4], s))  # WN*, WS*
    side_slots = [(margin + rh + k * rows_per * rh, margin + rh + (k + 1) * rows_per * rh)
                  for k in range(b["per_side"]["central"]["macros_per_side"])]
    # south links take the low slots, north links the high slots
    south = [s for s in wl if s[4] == "S"][:3]; north = [s for s in wl if s[4] == "N"][:3]
    mv = {}
    for k, s in enumerate(south):
        y0, y1 = side_slots[k]; mv[s] = (margin, y0, margin + f["depth_grid_um"], y1)
    for k, s in enumerate(north):
        y0, y1 = side_slots[-1 - k]; mv[s] = (margin, y0, margin + f["depth_grid_um"], y1)
    links = {}
    for s, r in mv.items():
        tgt = R[target[s]]
        old = R[s]
        tr = (tgt[0] + f["depth_grid_um"], tgt[1], tgt[2] + f["depth_grid_um"], tgt[3])
        orr = (old[0] + f["depth_grid_um"], old[1], old[2] + f["depth_grid_um"], old[3])
        d0, d1 = manh(centre(orr), centre(tr)), manh(centre(r), centre(tr))
        links[s] = dict(target=target[s], old_mm=round(d0 / 1e3, 2), new_mm=round(d1 / 1e3, 2),
                        hop_delta=math.ceil(d1 / REACH_UM) - math.ceil(d0 / REACH_UM))
    b["w_strip_link_estimate_central"] = dict(note="Manhattan centre-to-centre to the coll target; hops = ceil(d/405)",
                                              links=links)
    b["rects_central"] = {s: [round(v, 2) for v in r] for s, r in mv.items()}
    res["options"]["b_side_columns"] = b

    # ---------- c: orientation / depth ----------
    c = {}
    for t, f in fig.items():
        two_row_shore = snap_up(f["shore_um"] / 2 + 2 * GUARD_UM)
        c[t] = dict(row_um=rh, strip_left_under_macro_um=round(rh - f["depth_um"], 1),
                    ft_pairs_under_macro=int((rh - f["depth_um"]) // SLOT_PAIR_UM),
                    rotated_on_NS_shore_um=f["depth_um"], rotated_ok=False,
                    stacked_rows01_ok=False,
                    two_lane_row_macro=dict(shore_um=round(two_row_shore, 2), depth_um=2 * f["depth_um"],
                                            needs_rows=2, fit_segments=fit(sS, two_row_shore) + fit(sN, two_row_shore),
                                            displaced_row1_18_cells=math.ceil(14 * two_row_shore / cw),
                                            published="NO (3 lanes x 2 rows is not the published one-row figure)"))
    res["options"]["c_orientation"] = dict(
        fits={t: dict(fit=base[t]["fit"], fit_junction=base[t]["fit_junction"], extra=0) for t in fig}, detail=c,
        why="rotating on N/S puts only the 937-1011-um depth on the edge (published shore is the long side); a second "
            "macro stacked in row 1/18 is 1226.88 um off the edge; a taller edge row adds no shore. Only a 3x2-lane "
            "macro (assumption change) trades shore for depth, and it needs ~%d row-1/18 cells that are all occupied."
            % c["central"]["two_lane_row_macro"]["displaced_row1_18_cells"])

    # ---------- d: move non-SerDes parts off the shoreline rows ----------
    d = {}
    variants = {"gunit+bk_sel": MOVABLE_N, "gunit+bk_sel+iqf": MOVABLE_N + ("iqf",),
                "all_but_phy_hbm": MOVABLE_N + MOVABLE_S}
    free = []
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            if not any(r[0] <= x + 1 < r[2] and r[1] <= y + 1 < r[3] for r in R.values()):
                free.append([j, i])
    for vn, skip in variants.items():
        s1, _ = segments(R, ser, "S", W, margin, skip)
        n1, _ = segments(R, ser, "N", W, margin, skip)
        moved_area = sum((R[n][2] - R[n][0]) * (R[n][3] - R[n][1]) for n in skip) / 1e6
        d[vn] = dict(moved=list(skip), moved_mm2=round(moved_area, 2),
                     S_segments=[[round(a, 2), round(b, 2)] for a, b in s1],
                     N_segments=[[round(a, 2), round(b, 2)] for a, b in n1],
                     fits={t: dict(fit=fit(s1, f["pitch_um"]) + fit(n1, f["pitch_um"]),
                                   fit_junction=fit(s1, f["pitch_um"], JUNCTION_STRIP_UM) + fit(n1, f["pitch_um"], JUNCTION_STRIP_UM))
                           for t, f in fig.items()})
    ser_growth = sum(14 * fig[t]["pitch_um"] for t in ("central",)) * rh / 1e6 - \
        sum((R[s][2] - R[s][0]) * (R[s][3] - R[s][1]) for s in ser) / 1e6
    gl = 9 * fig["low"]["pitch_um"] + (R["gunit"][2] - R["gunit"][0])
    d["_area_book"] = dict(free_cells_rc=free, free_mm2=round(len(free) * cw * rh / 1e6, 2),
                           serdes_growth_central_mm2=round(ser_growth, 2),
                           note="SerDes slots grow more than the free cells, so a zero-area re-lay must shrink "
                                "low-fill parts (gunit 484k / bk_sel 811k cells in 3.5 / 5.3 mm2) or move a station")
    d["low_gunit_stays"] = dict(n_row_need_um=round(gl, 2), n_row_um=round(shore_row, 2), slack_um=round(shore_row - gl, 2),
                                note="low figure only: 9 N-row macros + full-size gunit fit with 8.6 um slack; only "
                                     "bk_sel (+ one station) moves; central figure does not")
    res["options"]["d_move_shore_parts"] = d

    # ---------- e: minimum growth with every non-SerDes part in place ----------
    e = {}
    for t, f in fig.items():
        pitch = f["pitch_um"]; best = None
        # insertion dW in the west band (x < first S fixed part: widens S-W and N-W) and dE east of x=23189.76
        # (widens S-E and N-E); SerDes may be re-assigned to any segment.
        segW = [(a, b) for a, b in sS + sN if b <= W / 2]
        segE = [(a, b) for a, b in sS + sN if a >= W / 2]
        for iw in range(0, 800):
            dW = iw * GRID * 5
            nW = sum(int((b - a + dW) // pitch) for a, b in segW)
            for ie in range(0, 800):
                dE = ie * GRID * 5
                nE = sum(int((b - a + dE) // pitch) for a, b in segE)
                if nW + nE >= 14:
                    if best is None or dW + dE < best[0]:
                        best = (dW + dE, dW, dE)
                    break
        dw = best[0]
        e[t] = dict(dW_um=round(best[1], 2), dE_um=round(best[2], 2), die_w_um=round(W + dw, 2),
                    area_delta_mm2=round(dw * H / 1e6, 2), area_mm2=round((W + dw) * H / 1e6, 2),
                    fits_reticle=W + dw <= RETICLE[0])
    res["options"]["e_growth_parts_fixed"] = e

    # ---------- candidate plan (e.g. Codex B2 phyfit) ----------
    if "--cand" in opt:
        cp, CR, cser = load(opt["--cand"])
        cW, cH = cp["die"]["outline_um"]
        names = list(CR)
        ov = []
        import itertools
        for a_, b_ in itertools.combinations(names, 2):
            ra, rb = CR[a_], CR[b_]
            if ra[0] < rb[2] - 0.5 and rb[0] < ra[2] - 0.5 and ra[1] < rb[3] - 0.5 and rb[1] < ra[3] - 0.5:
                ov.append([a_, b_])
                if len(ov) > 20:
                    break
        inside = all(r[0] >= margin - 0.5 and r[1] >= margin - 0.5 and r[2] <= cW - margin + 0.5 and r[3] <= cH - margin + 0.5
                     for r in CR.values())
        sers = {}
        for s in cser:
            r = CR[s]
            onS, onN = r[1] <= margin + 1, r[3] >= cH - margin - 1
            w = r[2] - r[0]; h = r[3] - r[1]
            sers[s] = dict(rect=[round(v, 2) for v in r], edge="S" if onS else ("N" if onN else "?"),
                           width_um=round(w, 2), ok_low=(onS or onN) and w >= fig["low"]["pitch_um"] - 0.01 and h >= fig["low"]["depth_um"],
                           ok_central=(onS or onN) and w >= fig["central"]["pitch_um"] - 0.01 and h >= fig["central"]["depth_um"])
        moved = {}
        for n in CR:
            if n in R and [round(v, 2) for v in CR[n]] != [round(v, 2) for v in R[n]]:
                moved[n] = dict(base=[round(v, 2) for v in R[n]], cand=[round(v, 2) for v in CR[n]],
                                area_ratio=round((CR[n][2] - CR[n][0]) * (CR[n][3] - CR[n][1]) /
                                                 ((R[n][2] - R[n][0]) * (R[n][3] - R[n][1])), 3),
                                dist_mm=round(manh(centre(CR[n]), centre(R[n])) / 1e3, 2))
        cand = dict(path=os.path.basename(opt["--cand"]), sha256_12=sha(opt["--cand"]), die_outline_um=[cW, cH],
                    overlaps=ov, inside_core=inside, serdes=sers,
                    fits_low=sum(v["ok_low"] for v in sers.values()), fits_central=sum(v["ok_central"] for v in sers.values()),
                    moved=moved)
        if "--ledger" in opt:
            lg = json.load(open(opt["--ledger"]))
            ch = lg.get("lane_cycle_changes", {})
            dl = sorted(((v["delta"], k) for k, v in ch.items()), reverse=True)
            cand["ledger"] = dict(path=os.path.basename(opt["--ledger"]), sha256_12=sha(opt["--ledger"]),
                                  status=lg.get("status"), lanes_changed=len(ch),
                                  cycles_added=sum(x for x, _ in dl if x > 0), cycles_removed=sum(x for x, _ in dl if x < 0),
                                  worst=[[k, x] for x, k in dl[:8]], best=[[k, x] for x, k in dl[-5:]],
                                  max_slot_hop_um=lg.get("max_slot_hop_um"))
        res["candidate"] = cand

    s = json.dumps(res, indent=1)
    if "--out" in opt:
        open(opt["--out"], "w").write(s + "\n")
    if "--png" in opt:
        render(opt["--png"], R, ser, W, H, res, CR if "--cand" in opt else None, cser if "--cand" in opt else None)
    print(s)


def render(path, R, ser, W, H, res, CR, cser):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig = res["figures"]["central"]
    panels = [("base plan (SerDes-only re-lay: 12 low / 10 central)", R, ser, W, {})]
    if CR is not None:
        panels.append(("option d = Codex B2 phyfit cand %s: 14/14 central" % res["candidate"]["sha256_12"], CR, cser, W,
                       res["candidate"]["moved"]))
    # option b: W strip (synthetic): shift every rect by strip, add rotated macros
    st = res["options"]["b_side_columns"]["fits"]["central"]["one_side_strip_um"]
    RB = {n: (r[0] + st, r[1], r[2] + st, r[3]) for n, r in R.items() if n not in res["options"]["b_side_columns"]["rects_central"]}
    for n, r in res["options"]["b_side_columns"]["rects_central"].items():
        RB[n] = tuple(r)
    panels.append(("option b = W strip +%.0f um (+%.1f mm2), 6 rotated W macros" % (
        st, res["options"]["b_side_columns"]["fits"]["central"]["area_delta_mm2"]), RB, ser, W + st,
        {n: 1 for n in res["options"]["b_side_columns"]["rects_central"]}))
    f, axs = plt.subplots(1, len(panels), figsize=(9 * len(panels), 7.6))
    for ax, (title, RR, ss, ww, moved) in zip(axs, panels):
        ax.add_patch(Rectangle((0, 0), ww, H, fill=False, lw=1.5, ec="k"))
        ax.add_patch(Rectangle((0, 0), 33000, 26000, fill=False, lw=1, ec="r", ls="--"))
        for n, r in RR.items():
            if n in ss:
                fc, ec = "#f4a261", "#9c4a00"
            elif n in ("gunit", "bk_sel", "iqf", "eng", "s_7S_x10", "phy_hbm", "s_4N_x06"):
                fc, ec = "#8ecae6", "#023047"
            elif n.startswith("fW") or n.startswith("fE"):
                fc, ec = "#e9ecef", "#adb5bd"
            else:
                fc, ec = "#f8f9fa", "#ced4da"
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=fc, ec=("m" if n in moved else ec),
                                   lw=(2.0 if n in moved else 0.4)))
            if n in ss or n in ("gunit", "bk_sel", "iqf", "eng", "s_7S_x10", "phy_hbm", "s_4N_x06"):
                ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, n.replace("lk_", ""), ha="center", va="center", fontsize=6)
            if n in ss:   # macro footprint inside the slot (shore x depth at the edge)
                x0, y0, x1, y1 = r
                if y0 < 200:
                    ax.add_patch(Rectangle(((x0 + x1) / 2 - fig["shore_um"] / 2, y0), fig["shore_um"], fig["depth_um"],
                                           fill=False, ec="r", lw=0.8))
                elif y1 > H - 200:
                    ax.add_patch(Rectangle(((x0 + x1) / 2 - fig["shore_um"] / 2, y1 - fig["depth_um"]), fig["shore_um"],
                                           fig["depth_um"], fill=False, ec="r", lw=0.8))
                elif x0 < 200:
                    ax.add_patch(Rectangle((x0, (y0 + y1) / 2 - fig["shore_um"] / 2), fig["depth_um"], fig["shore_um"],
                                           fill=False, ec="r", lw=0.8))
        ax.set_xlim(-500, 33500); ax.set_ylim(-500, 26500); ax.set_aspect("equal")
        ax.set_title(title, fontsize=9)
        ax.tick_params(labelsize=6)
    f.suptitle("S81 N7 SerDes re-lay study (orange = SerDes slot, red box = central 3318x1011 macro at the edge, blue = "
               "shore-row non-SerDes, magenta edge = moved/resized, dashed red = 33x26 mm reticle)", fontsize=9)
    f.tight_layout()
    f.savefig(path, dpi=130)


if __name__ == "__main__":
    main(sys.argv)
