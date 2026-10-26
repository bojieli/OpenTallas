#!/usr/bin/env python3
"""B2m = B2l + the 10-24 fixes (HBM lane).  B2l stays untouched; B2m is derived from it deterministically:

    python3 physical/die_plan/hbm_arch/b2m.py [--src B2l] [--out B2m] [--core-insertion JSON]

1. host in-band (OWNER 10-24): the dedicated host UCIe u_host_N (ot_pdie_ucie_col) leaves NW_io; the NW_io SerDes
   window io_NW_io_u_lk_N0 carries the host traffic in-band (host: "in_band", route NW_io -> [L48] -> root, where
   u_host_cp_ingress lives); u_host_ep stays and is fed from the u_ep_N0 host VC (RTL delta, HBM-BIND).
2. clock (BRIEFING decision 5): true balanced binary H-tree (clock_htree.build_balanced) from the die centre, root
   driver in a legal gap (B2l's root sat on core u_tkm_SW_tile19), no leaf drivers over PHY_N / q_sm / io / hard
   cores, NDR reservations re-derived into the per-type M8/M9 ft_budget.
3. SerDes IR (OWNER decision 7): separate PHY supply + dedicated bump rows over every SerDes window
   (die.pg.domains, one per window), checked by check.py rule pg_domain and verified with tools/die_trial/hbm_b2_ir.py.
4. early core taps (decision 5e core-latency contract) from HBM-ELEM's measured core insertion (--core-insertion).
Reset (decision 2) comes from lane RESET's unified die-level planner (not here yet).
"""
import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools/die_plan"))
sys.path.insert(0, str(ROOT / "tools/die_trial"))
import clock_htree as CH  # noqa: E402
import schema as S  # noqa: E402

SIDECARS = ["census_map.json", "core_conns.json", "cores_b2.json", "hbm_rows.json", "cores"]
HOST_LANES = ["L48"]
# PHY supply over each SerDes window (decision 7): own net VDDPHY with VSS, dense M8/M9 straps over the window plus a
# guard ring of one bump pitch, dedicated C4 rows (power/ground only, 45-um array) over the macro; the window's 26
# SerDes signals keep their 150-um signal sites at the shoreline edge of the window.
PHY_GRID = [dict(layer="M8", width_um=1.92, pitch_um=8.64, offset_um=4.32, nets=["VDDPHY", "VSS"]),
            dict(layer="M9", width_um=1.92, pitch_um=8.64, offset_um=4.32, nets=["VDDPHY", "VSS"])]
PHY_BUMP_PITCH = 45.0
PHY_GUARD_UM = 63.64


def host_in_band(plan, log):
    import die_io
    io = plan["die"]["io"]
    host = [w for w in io if w.get("host") is True]
    assert [w["name"] for w in host] == ["io_NW_io_u_host_N"], host
    t = plan["partition_types"]["NW_io"]
    gone = [c for c in t["contents"] if c["inst"] == "u_host_N"]
    t["contents"] = [c for c in t["contents"] if c["inst"] != "u_host_N"]
    t["cells"] = t["cells"] - sum(c.get("cells", 0) for c in gone)
    io[:] = [w for w in io if w["name"] != "io_NW_io_u_host_N"]
    P = S.Plan(plan)
    path, err = die_io.route_path(P, "NW_io", HOST_LANES, set(die_io.host_parts(P)))
    if err:
        raise SystemExit(f"in-band host route: {err}")
    w = next(w for w in io if w["name"] == "io_NW_io_u_lk_N0")
    w["host"] = "in_band"
    w["host_route"] = die_io.fmt_path(path)
    w["note"] += ("; OWNER 10-24: host traffic in-band over this die link (dedicated host UCIe u_host_N dropped); "
                  "u_host_ep fed from the u_ep_N0 host VC; route " + w["host_route"])
    log.append(f"host in-band: dropped u_host_N ({sum(c.get('cells', 0) for c in gone)} cells) + io_NW_io_u_host_N; "
               f"io_NW_io_u_lk_N0 host in_band route {w['host_route']}")


def core_taps(plan, ins, log):
    """decision 5e core-latency contract: a hard core whose measured internal insertion I exceeds the common latency
    gets its own die-tree tap (kind core) beside its clock pin, in a channel (schema.tap_clear), early by I - 250
    (HBM-ELEM physical/die_plan/hbm_arch_cores/results/core_insertion_b2l.json, `ins` = {(type, inst): view row}).
    Every hard core of a q_sm tile (32 SM halves) gets one too (I = 250 until measured): without it the die tree
    reached 32 core pins through one tile-centre tap and ~2.9 mm of tile glue (DIE-STA 10-24: NW_sm2 tap +440 ps)."""
    n = nm = 0
    for tn, t in plan["partition_types"].items():
        sm = bool(t.get("hard") and t.get("channels") and t.get("hard_cores"))
        taps = []
        for c in t.get("hard_cores", []) or []:
            r = ins.get((tn, c["inst"]))
            if not sm and not (r and r.get("early_tap_ps", 0) > 0):
                continue
            pins = json.loads((HERE / "B2l" / c["pins_file"]).read_text())
            ports = list((r or {}).get("ports", {}).keys()) or ["ck", "clk", "clock"]
            ck = [p for p in pins if p["name"] in ports or (not r and p["name"].startswith("ck"))]
            if not ck:
                raise SystemExit(f"core tap: no clock pin {ports} on {tn}.{c['inst']}")
            for p in ck:
                (ox, oy) = c["origin_um"]
                x, y = S.tap_clear(t, ox + p["x"], oy + p["y"], [tuple(a["xy"]) for a in taps], clear=4.32)
                I = float(r["insertion_mean_ps"]) if r else 250.0
                taps.append(dict(name=c["inst"] if len(ck) == 1 else f"{c['inst']}.{p['name']}", kind="core",
                                 xy=[round(x, 4), round(y, 4)], insertion_ps=round(max(I, 250.0), 3),
                                 budget_owner=c["module"],
                                 note=(f"HBM-ELEM measured I {I:g} ps (max {r.get('insertion_max_ps')}), view {r['view']}"
                                       if r else "SM half: insertion NOT MEASURED (250 = common latency, not early)")))
                nm += 1 if r else 0
        if taps:
            t["clock"].update(core_taps="early", taps=taps)
            n += len(taps)
    # PHY_N (hard HBM PHY, no channels): its clock pin on the S face (toward the die), not the tile centre: the die
    # tree may not place a driver over the PHY, so a centre pin hung 1.2 mm of unbuffered wire off the nearest leaf
    tp = plan["partition_types"]["PHY_N"]
    w, h = tp["outline_um"]
    tp["clock"]["tap_um"] = [round(w / 2, 4), 4.32]
    tp["reset"]["tap_um"] = [round(w / 2 + 8.64, 4), 4.32]
    log.append(f"core taps: {n} early core taps ({nm} from measured insertion > 250 ps, the rest SM halves at 250)")


def forbid_rects(P):
    out = []
    for pn, p in P.parts.items():
        t = P.ptype(pn)
        if t.get("hard") and not t.get("channels"):
            out.append(P.rect(pn))
            continue
        for c in t.get("hard_cores", []) or []:
            (ox, oy), (w, h) = c["origin_um"], c["outline_um"]
            a, b = P.to_die(pn, (ox, oy)), P.to_die(pn, (ox + w, oy + h))
            out.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])))
    for w in P.die.get("io", []) or []:
        out.append(tuple(w["rect_um"]))
    return out


def seam_lengths(P):
    out = {}
    names = sorted(P.parts)
    R = {n: P.rect(n) for n in names}
    for ai, a in enumerate(names):
        ra = R[a]
        for b in names[ai + 1:]:
            rb = R[b]
            if abs(ra[2] - rb[0]) < 0.5 or abs(rb[2] - ra[0]) < 0.5:
                ov = min(ra[3], rb[3]) - max(ra[1], rb[1])
            elif abs(ra[3] - rb[1]) < 0.5 or abs(rb[3] - ra[1]) < 0.5:
                ov = min(ra[2], rb[2]) - max(ra[0], rb[0])
            else:
                continue
            if ov > 1.0:
                out[(a, b)] = ov
                out[(b, a)] = ov
    return out


def clock(plan, out, log, reach=400.0, cap=8):
    """BRIEFING decision 5 (a)-(c): symmetric binary H-tree (clock_htree.build_balanced, 64 x 64 leaf cells) to a
    pruned tap-driver grid (no driver over PHY_N / io windows / hard cores; q_sm tiles keep their channels), then
    sink -> tap-driver assignment by distance + load (<= `cap` partition taps per driver, <= `reach` um Manhattan),
    with partition coherence: a partition's taps go to drivers under the same high subtree when one is in reach, so
    pairs inside a partition diverge as deep as the geometry allows (decision 5f)."""
    import htree_clock as HC
    P = S.Plan(plan)
    W, H = plan["die"]["outline_um"]
    rects = {n: P.rect(n) for n in P.parts}
    forbid = forbid_rects(P)
    taps = HC.plan_taps(P)
    segs, leaves, res, rd = CH.build_balanced(W, H, rects, forbid, taps)
    nx, ny = CH.NXL, CH.NYL
    cw, ch = W / nx, H / ny

    def path(i, j):
        i0, i1, j0, j1, seq = 0, nx, 0, ny, []
        while (i1 - i0) > 1 or (j1 - j0) > 1:
            ni, nj = i1 - i0, j1 - j0
            if ni >= nj and ni > 1:
                h = ni // 2
                b = i >= i0 + h
                seq.append(b)
                i0, i1 = (i0 + h, i1) if b else (i0, i0 + h)
            else:
                h = nj // 2
                b = j >= j0 + h
                seq.append(b)
                j0, j1 = (j0 + h, j1) if b else (j0, j0 + h)
        return tuple(seq)
    seglen, i0, i1, j0, j1 = [], 0, nx, 0, ny
    while (i1 - i0) > 1 or (j1 - j0) > 1:
        ni, nj = i1 - i0, j1 - j0
        if ni >= nj and ni > 1:
            seglen.append(ni * cw / 4)
            i1 = i0 + ni // 2
        else:
            seglen.append(nj * ch / 4)
            j1 = j0 + nj // 2
    for l in leaves:
        l["path"] = path(*l["cell"])

    def shared(a, b):
        k = 0
        while k < len(a) and a[k] == b[k]:
            k += 1
        return k
    # (c) assignment: nearest driver in reach, load-capped; then partition coherence
    drv = leaves
    load = [0] * len(drv)
    assign = {}
    bypart = {}
    for ti, (pn, nm, x, y) in enumerate(taps):
        bypart.setdefault(pn, []).append(ti)
    for ti, (pn, nm, x, y) in sorted(enumerate(taps), key=lambda e: e[1][0]):
        cand = sorted(range(len(drv)), key=lambda k: abs(drv[k]["driver_um"][0] - x) + abs(drv[k]["driver_um"][1] - y))
        ok = [k for k in cand[:24] if load[k] < cap and abs(drv[k]["driver_um"][0] - x) + abs(drv[k]["driver_um"][1] - y) <= reach]
        k = ok[0] if ok else cand[0]
        assign[ti] = k
        load[k] += 1
    moved = 0
    for pn, tis in bypart.items():
        if len(tis) < 2:
            continue
        for it in range(3):
            paths = [drv[assign[t]]["path"] for t in tis]
            best = None
            for depth in range(1, len(paths[0])):
                from collections import Counter
                c = Counter(p[:depth] for p in paths).most_common(1)[0]
                if c[1] == len(paths):
                    continue
                best = (depth, c[0])
                break
            if best is None:
                break
            depth, pref = best
            ch_ = 0
            for t in tis:
                if drv[assign[t]]["path"][:depth] == pref:
                    continue
                pn_, nm, x, y = taps[t]
                cand = [k for k in range(len(drv)) if drv[k]["path"][:depth] == pref and load[k] < cap and
                        abs(drv[k]["driver_um"][0] - x) + abs(drv[k]["driver_um"][1] - y) <= reach]
                if cand:
                    k = min(cand, key=lambda k: abs(drv[k]["driver_um"][0] - x) + abs(drv[k]["driver_um"][1] - y))
                    load[assign[t]] -= 1
                    assign[t] = k
                    load[k] += 1
                    ch_ += 1
            moved += ch_
            if not ch_:
                break
    # divergence (OCV exposure, INFO): non-common wire = 2 x (path below the diverging node)
    def noncommon(k):
        return 2 * sum(seglen[k:])
    intra = []
    for pn, tis in bypart.items():
        ps = {drv[assign[t]]["path"] for t in tis}
        k = min((shared(a, b) for a in ps for b in ps if a != b), default=len(seglen))
        intra.append(dict(part=pn, shared_levels=k, noncommon_ps=round(noncommon(k) * CH.PS_PER_MM / 1000, 1)))
    intra.sort(key=lambda r: -r["noncommon_ps"])
    seams = seam_lengths(P)
    seam_rows, done = [], set()
    for (a, b), ln in seams.items():
        if (b, a) in done:
            continue
        done.add((a, b))
        best = None
        for ta in bypart.get(a, []):
            for tb in bypart.get(b, []):
                if _d(taps[ta][2:], taps[tb][2:]) > 900:
                    continue
                k = shared(drv[assign[ta]]["path"], drv[assign[tb]]["path"])
                if best is None or k < best:
                    best = k
        if best is not None:
            seam_rows.append(dict(a=a, b=b, edge_um=round(ln, 1), shared_levels=best,
                                  noncommon_ps=round(noncommon(best) * CH.PS_PER_MM / 1000, 1)))
    seam_rows.sort(key=lambda r: -r["noncommon_ps"])
    far = max(abs(drv[assign[t]]["driver_um"][0] - taps[t][2]) + abs(drv[assign[t]]["driver_um"][1] - taps[t][3])
              for t in assign)
    over = sum(1 for t in assign if abs(drv[assign[t]]["driver_um"][0] - taps[t][2]) +
               abs(drv[assign[t]]["driver_um"][1] - taps[t][3]) > reach)
    used = sorted({assign[t] for t in assign})
    # NDR reservation -> per-type M8 / M9 ft_budget
    LAY = P.layers
    old = {tn: dict(t.get("ft_budget", {})) for tn, t in plan["partition_types"].items()}
    newb, tracks = {}, {}
    for pt in plan["partitions"]:
        tn = pt["type"]
        w, h = plan["partition_types"][tn]["outline_um"]
        for d, ln, ext_ in (("H", "M8", h), ("V", "M9", w)):
            r = res.get((pt["name"], d), 0)
            ut = S.usable_tracks(LAY[ln], ln, 0.0, ext_)
            newb.setdefault(tn, {})[ln] = min(newb.get(tn, {}).get(ln, 0.6), 0.6 - r / ut)
            if r:
                tracks[f"{pt['name']}.{ln}"] = r
    for tn, t in plan["partition_types"].items():
        fb = t.setdefault("ft_budget", {})
        for ln in ("M8", "M9"):
            fb[ln] = round(newb[tn][ln], 6)
    plan["clock"]["spine"]["root_um"] = [round(W / 2, 3), round(H / 2, 3)]
    plan["clock"]["spine"]["topology"] = "htree"
    path_um = sum(seglen)
    summ = dict(method="symmetric binary H-tree (decision 5a) -> pruned tap-driver grid (5b) -> distance+load "
                       "assignment with partition coherence (5c, 5f)",
                levels=len(seglen), level_um=[round(v, 1) for v in seglen], path_um=round(path_um, 1),
                model_insertion_ps=round(path_um * CH.PS_PER_MM / 1000, 1), ps_per_mm=CH.PS_PER_MM,
                segments=len(segs), drivers=len(used), cells=[nx, ny], taps=len(taps),
                drivers_moved=sum(1 for k in used if drv[k]["moved_um"] > 0),
                driver_moved_max_um=max(drv[k]["moved_um"] for k in used), tap_driver_max_um=round(far, 1),
                taps_over_reach=over, coherence_moves=moved, max_load=max(load),
                root_driver=rd, wire_mm=round(sum(abs(s_[2] - s_[0]) + abs(s_[3] - s_[1]) for s_ in segs) / 1000, 1),
                intra_split_top2=[r["part"] for r in intra if r["shared_levels"] <= 1],
                seams_top2=sum(1 for r in seam_rows if r["shared_levels"] <= 1),
                seams_over_80ps_at_5pct=sum(1 for r in seam_rows if 0.05 * r["noncommon_ps"] > 80),
                intra_over_80ps_at_5pct=sum(1 for r in intra if 0.05 * r["noncommon_ps"] > 80))
    json.dump(dict(rule=clock.__doc__, ndr_tracks=CH.NDR_TRACKS, root_um=[round(W / 2, 3), round(H / 2, 3)],
                   root_driver=rd,
                   segments=[dict(xy=[s_[0], s_[1], s_[2], s_[3]], level=s_[4], layer=s_[5]) for s_ in segs],
                   leaves=[drv[k]["driver_um"] for k in used],
                   drivers=[dict(id=k, cell=drv[k]["cell"], centre_um=drv[k]["xy"], driver_um=drv[k]["driver_um"],
                                 moved_um=drv[k]["moved_um"], load=load[k]) for k in used],
                   tap_assign=[dict(part=taps[t][0], tap=taps[t][1], xy=[round(taps[t][2], 3), round(taps[t][3], 3)],
                                    driver=assign[t]) for t in sorted(assign)],
                   reserved_tracks=tracks,
                   ft_budget_change={tn: dict(old=old[tn], new=plan["partition_types"][tn]["ft_budget"])
                                     for tn in plan["partition_types"]
                                     if old[tn] != plan["partition_types"][tn]["ft_budget"]},
                   intra=intra, seams=seam_rows, summary=summ,
                   hard_core_comp="core-latency contract: core taps (kind core) early by insertion - common latency",
                   gate="related-pair skew with CPPR <= 80 ps at TT and FF; OCV INFO (BRIEFING decisions 3, 5)"),
              open(out / "clock_htree.json", "w"), indent=0)
    CH.render_balanced(plan, segs, [drv[k] for k in used], rd, forbid, str(out / "clock_htree.png"),
                       f"{plan['die']['name']}: symmetric binary H-tree, {len(seglen)} levels, {len(used)} tap drivers "
                       f"({summ['drivers_moved']} moved off PHY/io/cores, max {summ['driver_moved_max_um']} um), "
                       f"tap<-driver max {summ['tap_driver_max_um']} um, root driver {rd['xy']}")
    log.append("clock: " + json.dumps({k: v for k, v in summ.items()}))
    return summ


def clock_zst(plan, out, log):
    """INFO comparison: partition-aware zero-skew tree (clock_htree.build_zst) to every partition tap (grid + early core taps)."""
    import htree_clock as HC
    P = S.Plan(plan)
    W, H = plan["die"]["outline_um"]
    rects = {n: P.rect(n) for n in P.parts}
    forbid = forbid_rects(P)
    raw = HC.plan_taps(P)
    early = {}
    for pn, p in P.parts.items():
        for port, x, y, tp in S.core_taps(P, p["type"]):
            early[(pn, round(P.to_die(pn, (x, y))[0], 2), round(P.to_die(pn, (x, y))[1], 2))] = S.core_tap_early_ps(P, tp)
    taps = []
    for pn, nm, x, y in raw:
        e = early.get((pn, round(x, 2), round(y, 2)), 0.0)
        taps.append((pn, nm, x, y, e * 1000.0 / CH.PS_PER_MM))
    seams = seam_lengths(P)
    nodes, root = CH.build_zst(taps, rects, forbid, seams, (W, H))
    segs = CH.zst_segments(nodes, root)
    res = {}
    for (x0, y0, x1, y1, lev, ln) in segs:
        a0, a1 = sorted((x0, x1)); b0, b1 = sorted((y0, y1))
        for n, (rx0, ry0, rx1, ry1) in rects.items():
            if ln == "M8" and ry0 <= b0 < ry1 and a0 < rx1 and a1 > rx0:
                res[(n, "H")] = res.get((n, "H"), 0) + CH.NDR_TRACKS
            if ln == "M9" and rx0 <= a0 < rx1 and b0 < ry1 and b1 > ry0:
                res[(n, "V")] = res.get((n, "V"), 0) + CH.NDR_TRACKS
    LAY = P.layers
    old = {tn: dict(t.get("ft_budget", {})) for tn, t in plan["partition_types"].items()}
    newb, tracks = {}, {}
    for pt in plan["partitions"]:
        tn = pt["type"]
        w, h = plan["partition_types"][tn]["outline_um"]
        for d, ln, ext_ in (("H", "M8", h), ("V", "M9", w)):
            r = res.get((pt["name"], d), 0)
            ut = S.usable_tracks(LAY[ln], ln, 0.0, ext_)
            newb.setdefault(tn, {})[ln] = min(newb.get(tn, {}).get(ln, 0.6), 0.6 - r / ut)
            if r:
                tracks[f"{pt['name']}.{ln}"] = r
    rp = nodes[root]["xy"]
    # pair divergence (OCV exposure, INFO): intra-partition = shallowest node splitting a partition's own taps;
    # seam = shallowest node splitting the nearest taps (<= 900 um) of two abutted partitions
    intra = CH.zst_lca_report(nodes, root)
    leaf_of = {}
    for i, nd in enumerate(nodes):
        if not nd["kids"]:
            leaf_of.setdefault(nd["parts"][0], []).append(i)
    par = {}
    for i, nd in enumerate(nodes):
        for k, _, _ in nd["kids"]:
            par[k] = i

    def anc(i):
        a = [i]
        while a[-1] in par:
            a.append(par[a[-1]])
        return a
    seam_rows = []
    done = set()
    for (a, b), ln in seams.items():
        if (b, a) in done:
            continue
        done.add((a, b))
        best = None
        for i in leaf_of.get(a, []):
            ai = set(anc(i))
            for j in leaf_of.get(b, []):
                if _d(nodes[i]["xy"], nodes[j]["xy"]) > 900:
                    continue
                k = next(x for x in anc(j) if x in ai)
                if best is None or nodes[k]["d"] > best[0]:
                    pass
                if best is None or nodes[k]["level"] < best[1]:
                    best = (nodes[k]["d"], nodes[k]["level"])
        if best:
            seam_rows.append(dict(a=a, b=b, edge_um=round(ln, 1), level=best[1], noncommon_ps=round(2 * best[0] * CH.PS_PER_MM / 1000, 1)))
    seam_rows.sort(key=lambda r: -r["noncommon_ps"])
    intra_rows = sorted(({"part": p, "level": v[0], "noncommon_ps": round(2 * v[1] * CH.PS_PER_MM / 1000, 1)}
                         for p, v in intra.items()), key=lambda r: -r["noncommon_ps"])
    snake = sum(s_ for nd in nodes for _, _, s_ in nd["kids"])
    wire = sum(w_ for nd in nodes for _, w_, _ in nd["kids"])
    summ = dict(method="partition-aware zero-skew tree (guillotine bisection + linear-delay merge)", taps=len(taps),
                early_taps=sum(1 for t in taps if t[4] > 0), nodes=len(nodes),
                depth=max(nd["level"] for nd in nodes), root_um=list(rp),
                insertion_wire_um=round(nodes[root]["d"], 1),
                insertion_ps_model=round(nodes[root]["d"] * CH.PS_PER_MM / 1000, 1),
                wire_mm=round(wire / 1000, 1), snake_mm=round(snake / 1000, 1),
                worst_intra=intra_rows[:8], worst_seams=seam_rows[:8],
                seams_over_80ps_5pct_ocv=sum(1 for r in seam_rows if 0.05 * r["noncommon_ps"] > 80))
    edges = [dict(parent=i, child=k, wire_um=round(w_, 3), snake_um=s_) for i, nd in enumerate(nodes) for k, w_, s_ in nd["kids"]]
    json.dump(dict(rule=CH.build_zst.__doc__, design="B2m partition-aware zero-skew clock tree (clock_htree.build_zst); "
                   "B2l fishbone + geometric H-tree superseded", ndr_tracks=CH.NDR_TRACKS, ps_per_mm=CH.PS_PER_MM,
                   root_um=[round(rp[0], 3), round(rp[1], 3)],
                   nodes=[dict(id=i, xy=list(nd["xy"]), d_um=round(nd["d"], 3), level=nd["level"], cut=nd["cut"],
                               name=nd.get("name")) for i, nd in enumerate(nodes)],
                   edges=edges,
                   segments=[dict(xy=[s_[0], s_[1], s_[2], s_[3]], level=s_[4], layer=s_[5]) for s_ in segs],
                   leaves=[list(nd["xy"]) for nd in nodes if not nd["kids"]],
                   reserved_tracks=tracks,
                   ft_budget_change={tn: dict(old=old[tn], new=plan["partition_types"][tn]["ft_budget"])
                                     for tn in plan["partition_types"]
                                     if old[tn] != plan["partition_types"][tn]["ft_budget"]},
                   intra=intra_rows, seams=seam_rows, summary=summ,
                   hard_core_comp="core-latency contract: core taps enter with delay credit = early_ps",
                   gate="related-pair skew with CPPR <= 80 ps at TT and FF; OCV INFO (BRIEFING decisions 3, 5)"),
              open(out / "clock_zst_info.json", "w"), indent=0)
    CH.render_balanced(plan, segs, [dict(xy=list(nd["xy"]), driver_um=list(nd["xy"]), moved_um=0) for nd in nodes
                                    if not nd["kids"]], dict(xy=list(rp), stub_um=0), forbid,
                       str(out / "clock_zst_info.png"),
                       f"{plan['die']['name']} (INFO alternative): partition-aware zero-skew tree, {len(taps)} taps, depth {summ['depth']}, "
                       f"model insertion {summ['insertion_ps_model']} ps @ {CH.PS_PER_MM:g} ps/mm, snake "
                       f"{summ['snake_mm']} mm")
    log.append("clock INFO alternative (zero-skew, not adopted): " + json.dumps({k: v for k, v in summ.items() if k not in ("worst_intra", "worst_seams")}))
    return summ


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def pg_domains(plan, log):
    doms = []
    for w in plan["die"]["io"]:
        if w.get("iface") != "serdes":
            continue
        x0, y0, x1, y1 = w["rect_um"]
        W, H = plan["die"]["outline_um"]
        g = PHY_GUARD_UM
        r = [round(max(0.0, x0 - g), 4), round(max(0.0, y0 - g), 4), round(min(W, x1 + g), 4), round(min(H, y1 + g), 4)]
        doms.append(dict(name=f"phy_{w['name'][3:]}", nets=["VDDPHY", "VSS"], io=[w["name"]], rect_um=r,
                         grid=copy.deepcopy(PHY_GRID),
                         bumps=dict(rect_um=[x0, y0, x1, y1], pitch_um=PHY_BUMP_PITCH, use="power_ground",
                                    note="dedicated VDDPHY/VSS C4 rows over the SerDes macro (checkerboard on the 45-um "
                                         "array); no signal bumps inside except the window's own 26 SerDes sites"),
                         note="OWNER decision 7 (10-24): separate PHY supply + dedicated bump rows over the SerDes "
                              "window; core VDD grid unchanged around it"))
    plan["die"]["pg"]["domains"] = doms
    log.append(f"pg domains: {len(doms)} SerDes PHY supplies ({', '.join(d['name'] for d in doms)})")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=str(HERE / "B2l"))
    ap.add_argument("--out", default=str(HERE / "B2m"))
    ap.add_argument("--core-insertion")
    a = ap.parse_args(argv)
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in SIDECARS:
        s, d = src / f, out / f
        if s.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(s, d)
        elif s.exists():
            shutil.copy2(s, d)
    plan = json.loads((src / "die_plan.json").read_text())
    log = []
    plan["die"]["name"] = "hbm_arch_B2m"
    plan["die"]["label"] = ("B2m = B2l (accepted 10-24, ~22% DS-AR loss vs d4g) + in-band host, balanced binary H-tree, "
                            "SerDes PHY supplies")
    host_in_band(plan, log)
    pg_domains(plan, log)
    ins = {}
    if a.core_insertion:
        for r in json.loads(Path(a.core_insertion).read_text()).get("views", []):
            if r.get("status") == "MEASURED":
                for ti in r["instances"]:
                    tn_, inst = ti.split(".", 1)
                    ins[(tn_, inst)] = r
    core_taps(plan, ins, log)
    clock(plan, out, log)
    clock_zst(json.loads(json.dumps(plan)), out, log)
    plan.setdefault("note", "")
    plan["note"] = (plan["note"] + " | " if plan["note"] else "") + "B2m derived by physical/die_plan/hbm_arch/b2m.py: " + "; ".join(log)
    (out / "die_plan.json").write_text(json.dumps(plan, indent=0) + "\n")
    io = [w for w in plan["die"]["io"]]
    (out / "die_io.json").write_text(json.dumps(io) + "\n")
    print("\n".join(log))


if __name__ == "__main__":
    main()
