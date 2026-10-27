#!/usr/bin/env python3
"""PATH-HBM-R11 (GEOM-REVIEW-6 R10 verdict + COORD R11 lane): opt-in HBM hub delta on top of hbm_r10_delta.
A plan that is not passed through it is unchanged (new file; no existing tool or default output changes).

  1 Y-DEMAND SEGMENTS  S=2 boundary chosen by per-segment y demand per unit width (not equal lane bits): every
                       candidate boundary on the --search-step lattice is realised at the hub height and scored by the
                       band-clipped plan_cut per-sink y of each segment (y supply = segment width) at the smallest
                       serialisation k that brings whole hub + both segments <= 0.6; the winner = passes, then
                       fewest beats k, then smallest max(seg y).  --bound-um fixes it instead.
  2 COMMON HEIGHT      both hubs of a row get the SAME height --height-um (the row grows once); default = the largest
                       packing minimum of the hubs (no extra height beyond what packing / the x cut needs).
  3 FACE PIN SPREAD    lane pins legalised at a spread density max(--spread-pins-per-um, group need) instead of the
                       budget cap (6/um), so pin fans over one consumer span do not pile at the cap density.
  4 OPTION (a)         --cc-serial-k 2: hub-internal service core-core stations longer than --cc-min-um (Manhattan,
                       1000) are serialised by k: ceil(bits/k) wires, k beats per transfer (+k-1 cycles per traversal,
                       1/k of the parallel bandwidth), registered serialiser at launch + k-deep deserialiser at capture
                       (static schedule, no credits).  The serialised link list goes to the report (TOK-HBM price).
  5 DIE GROWTH         --grow-die: the die grows by dH = H_new - H_old at one insertion line Y* inside the hub row
                       (chosen where no root hard core / content straddles it); every partition / io / PG domain / port
                       window / clock root / root-internal object at y >= Y* moves up by dH; the hubs take their new
                       outline in place; the other hub-row partitions keep origin and size (the dH strip above them is
                       reported as hub_row_gap_rects_um); --grow-row-types also grows those row types by dH (their
                       N-face station ends follow the N edge) so no die-level empty strip lies on their links.
Writes <out>/die_plan.json (+ r11_delta_report.json); everything else hard-linked.
All numbers are plan arithmetic: UNCHECKED until NUMBER-CHECK (12.9f).
"""
import argparse
import copy
import hashlib
import json
import math
import os
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_r10_delta as R10  # noqa: E402
import hbm_r9_delta as R9  # noqa: E402
import hub_repack as HR  # noqa: E402

r3 = HR.r3


def _face(p, W, H, tol=0.5):
    return p[1] <= tol or p[1] >= H - tol or p[0] <= tol or p[0] >= W - tol


def serialise_cc(stations, W, H, k, min_um=1000.0):
    """option (a): hub-internal core-core stations longer than min_um -> ceil(bits/k); returns the link list."""
    out = []
    if k <= 1:
        return out
    for s in stations:
        if _face(s["from_um"], W, H) or _face(s["to_um"], W, H) or s.get("serial_k"):
            continue
        L = abs(s["from_um"][0] - s["to_um"][0]) + abs(s["from_um"][1] - s["to_um"][1])
        if L > min_um:
            par = s["bits"]
            s["bits_parallel"] = par
            s["bits"] = int(math.ceil(par / k))
            s["serial_k"] = k
            s["r11_cc_serial"] = True
            out.append(dict(conn=s.get("conn"), launch=s.get("launch"), capture=s.get("capture"), bits=par,
                            wires=s["bits"], length_um=r3(L), k=k))
    return out


def spread_place(stations, W, H, cap, spread):
    """place_pins with the spread density: legalise each group at max(spread, need) pins/um (<= cap)."""
    if spread is None or spread >= cap:
        return R10.place_pins(stations, W, H, cap)
    orig = R10.legalise

    def leg(items, lo, hi, c):
        need = sum(b for _, _, b in items) / max(hi - lo, 1e-9)
        return orig(items, lo, hi, min(c, max(spread, need)))
    R10.legalise = leg
    try:
        return R10.place_pins(stations, W, H, cap)
    finally:
        R10.legalise = orig


def pin_peak(stations, W, H, gcell=4.32):
    """max face pins per um over one gcell on the N/S faces after placement (plan model): one pin per distinct face
    point (stations sharing a pin -- broadcast / replicated copies -- count it once, at its widest station)."""
    pts = {}
    for s in stations:
        for p in (s["from_um"], s["to_um"]):
            if p[1] <= 0.5 or p[1] >= H - 0.5:
                key = ("S" if p[1] <= 0.5 else "N", round(p[0], 3))
                pts[key] = max(pts.get(key, 0), s.get("bits_parallel", s["bits"]))
    acc = {}
    for (f, x), b in pts.items():
        acc[(f, int(x // gcell))] = acc.get((f, int(x // gcell)), 0) + b
    return {f: r3(max([b for (ff, _), b in acc.items() if ff == f] or [0]) / gcell) for f in "NS"}


def eval_hub(t1, H0, W, H, bound, k, cap, spread, kcc, cc_min, route=False, hop=405.0):
    Q = R9.plan_quadrants(t1, 2, bounds=[bound], dist_by_x=True)
    cores, st, infos, stats = R9.realise(t1, Q, H, kx=k, route=route)
    spread_place(st, W, H, cap, spread)
    nwe = R10.chain_we(st, W, k, hop)
    cc = serialise_cc(st, W, H, kcc, cc_min)
    u = R9.cut(dict(outline_um=[W, H], hard_cores=cores, internal_stations=st))["blocked"]
    segs = []
    for a, b in ((0.0, bound), (bound, W)):
        pr = R10.profile(W, H, dict(hard_cores=cores, internal_stations=st), a, b)
        segs.append(dict(x_um=[r3(a), r3(b)], cut_x=pr["x"].get("max_use"), cut_y=pr["y"].get("max_use"),
                         at_y=pr["y"].get("at_um")))
    return dict(cores=cores, stations=st, infos=infos, stats=stats, we_chain=nwe, cc=cc, cut=u, segs=segs)


def _full(r):
    return max(r["cut"]["x"]["max_use"], r["cut"]["y"]["max_use"],
               *[s["cut_" + axis] or 0 for s in r["segs"] for axis in "xy"]) <= 0.6 + 1e-9


def _cand(args):
    """one boundary: smallest k (1..kmax) at which whole hub AND both segments are <= 0.6; score =
    (tier: 0 whole+segments pass / 1 whole only / 2 fail, k, max segment y) -> passing first, fewest serialised
    beats, then the best y demand per width."""
    t1, H0, W, H, b, kmax, cap, spread, kcc, cc_min = args
    r, kw = None, None
    try:
        for k in range(1, kmax + 1):
            r = eval_hub(t1, H0, W, H, b, k, cap, spread, kcc, cc_min)
            if kw is None and max(r["cut"]["x"]["max_use"], r["cut"]["y"]["max_use"]) <= 0.6 + 1e-9:
                kw = k
            if _full(r):
                break
    except ValueError:
        return b, None
    if not _full(r) and kw is not None:
        k = kw
    wx, wy = r["cut"]["x"]["max_use"], r["cut"]["y"]["max_use"]
    sy = max(s["cut_" + axis] or 0 for s in r["segs"] for axis in "xy")
    ok = _full(r)
    whole = max(wx, wy) <= 0.6 + 1e-9
    tier = 0 if ok else (1 if whole else 2)
    return b, dict(score=[tier, k if tier < 2 else kmax, sy if tier < 2 else max(wx, wy, sy)], k=k, cut_x=wx, cut_y=wy,
                   seg_y=[s["cut_y"] for s in r["segs"]], seg_x=[s["cut_x"] for s in r["segs"]])


def prepare(P, part, tn, cap, spread):
    t = P["partition_types"][tn]
    W, H0 = t["outline_um"]
    bi = R10.bus_intervals(P, part, t)
    st, lrep = R10.resolve_lanes(t, bi, log=lambda *a: None)
    spread_place(st, W, H0, cap, spread)
    return t, W, H0, dict(t, internal_stations=st), lrep


def min_height(t1, W, bound):
    Q = R9.plan_quadrants(t1, 2, bounds=[bound], dist_by_x=True)
    return R9.min_height(t1, Q, t1["outline_um"][1], log=lambda *a: None)


def search_bound(t1, H0, W, H, cap, spread, kcc, cc_min, kmax, lo=0.25, hi=0.6, step=86.4, jobs=36):
    cands = [r3(HR.sn(x)) for x in [W * lo + i * step for i in range(int((hi - lo) * W / step) + 1)]]
    args = [(t1, H0, W, H, b, kmax, cap, spread, kcc, cc_min) for b in cands]
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        res = dict(ex.map(_cand, args))
    table = [dict(bound_um=b, **v) for b, v in sorted(res.items()) if v]
    best = min(table, key=lambda r: tuple(r["score"]))
    return best["bound_um"], table


def run_hub(P, part, tn, H, bound, cap, spread, kcc, cc_min, kmax, route=True, jobs=36, log=print):
    t, W, H0, t1, lrep = prepare(P, part, tn, cap, spread)
    table = None
    if bound is None:
        bound, table = search_bound(t1, H0, W, H, cap, spread, kcc, cc_min, kmax, jobs=jobs)
        log(f"{tn}: y-demand boundary {bound} um ({len(table)} candidates)")
    rows = []
    full = lambda w: max(w["cut_x"], w["cut_y"],
                         *[v or 0 for axis in "xy" for v in w["seg_" + axis]]) <= 0.6 + 1e-9  # noqa: E731
    for k in range(1, kmax + 1):
        r = eval_hub(t1, H0, W, H, bound, k, cap, spread, kcc, cc_min)
        rows.append(dict(k=k, cut_x=r["cut"]["x"]["max_use"], cut_y=r["cut"]["y"]["max_use"],
                         seg_x=[s["cut_x"] for s in r["segs"]],
                         seg_y=[s["cut_y"] for s in r["segs"]]))
        log(f"{tn}: H {H} b {bound} k {k} x {rows[-1]['cut_x']} y {rows[-1]['cut_y']} seg y {rows[-1]['seg_y']}")
        if full(rows[-1]):
            break
    # smallest k passing whole hub + segments, else smallest passing the whole hub, else k_max
    whole = [w for w in rows if max(w["cut_x"], w["cut_y"]) <= 0.6 + 1e-9]
    kch = rows[-1]["k"] if full(rows[-1]) else (whole[0]["k"] if whole else kmax)
    r = eval_hub(t1, H0, W, H, bound, kch, cap, spread, kcc, cc_min, route=route)
    for s in r["stations"]:
        s.pop("r10", None)
    res = dict(S=2, bound_um=bound, height_um=H, hub_growth_y_um=r3(H - H0), k=kch, k_table=rows,
               bound_table=table, lanes=lrep, cut_per_sink_blocked=r["cut"], segments=r["segs"],
               stations=r["stats"], we_chain=r["we_chain"], cc_serialised=len(r["cc"]), cc_links=r["cc"],
               pin_peak_bits_per_um=pin_peak(r["stations"], W, H),
               segment_fill=[r["infos"][i]["fill"] for i in sorted(r["infos"])],
               latency_cycles=dict(inter_segment_and_we=(kch - 1), cc=(kcc - 1) if kcc > 1 else 0,
                                   note="each serialised slice: +k-1 cycles per traversal and 1/k of its parallel "
                                        "bandwidth; route registers in stations.latency_up_hist"))
    return r["cores"], r["stations"], res


# ----------------------------------------------------------------------------------------------------- die growth
def _yshift(v, ys, dH):
    return v + dH if v >= ys - 1e-6 else v


def _shift_pts(lst, ys, dH):
    return [[p[0], _yshift(p[1], ys, dH)] for p in lst]


def grow_die(P, hub_parts, H_old, H_new, grow_row=False):
    """insert dH at Y* inside the hub row; returns report."""
    dH = r3(H_new - H_old)
    pos = {p["name"]: p for p in P["partitions"]}
    T = P["partition_types"]
    y0 = min(pos[h]["origin_um"][1] for h in hub_parts)
    y1 = y0 + H_old
    # rigid objects of straddling partitions (root): no core/content may straddle Y*
    straddle = [p for p in P["partitions"] if p["name"] not in hub_parts and p["origin_um"][1] < y0 - 1e-6
                and p["origin_um"][1] + T[p["type"]]["outline_um"][1] > y1 + 1e-6]
    blocks = []
    for p in straddle:
        oy = p["origin_um"][1]
        for h in T[p["type"]].get("hard_cores", []) + T[p["type"]].get("contents", []):
            if h.get("origin_um") and h.get("outline_um"):
                blocks.append((oy + h["origin_um"][1], oy + h["origin_um"][1] + h["outline_um"][1]))
    best = None
    for i in range(1, int(H_old / 4.32)):
        y = r3(HR.sn(y0 + i * 4.32))
        if any(a + 1e-6 < y < b - 1e-6 for a, b in blocks):
            continue
        d = abs(y - (y0 + H_old / 2))
        if best is None or d < best[0]:
            best = (d, y)
    if best is None:
        raise ValueError("no insertion line inside the hub row avoids the straddling cores")
    ys = best[1]
    row = [p["name"] for p in P["partitions"] if abs(p["origin_um"][1] - y0) < 1e-6 and p["name"] not in hub_parts]
    rowset = set(row)
    gaps = []
    row_grown = []
    if grow_row:
        others = {p["type"] for p in P["partitions"] if p["name"] not in rowset}
        for tn in sorted({pos[n]["type"] for n in row}):
            if tn in others:
                continue        # type also used outside the hub row: keep (its strip is reported as a gap)
            t = T[tn]
            h0 = t["outline_um"][1]
            t["outline_um"] = [t["outline_um"][0], r3(h0 + dH)]
            for s in t.get("internal_stations", []):
                for key in ("from_um", "to_um"):
                    if s[key][1] >= h0 - 0.5:
                        s[key] = [s[key][0], r3(s[key][1] + dH)]
            t["note"] = (t.get("note", "") + f" | PATH-HBM-R11 hub-row growth: outline +{dH} um in y (N-face pins "
                         "follow the N edge; cores unchanged; the strip is in-partition street with bays)").strip(" |")
            row_grown.append(tn)
    for p in P["partitions"]:
        if p["name"] in rowset:
            w, h = T[p["type"]]["outline_um"]
            if h < H_new - 1e-6:
                gaps.append([r3(p["origin_um"][0]), r3(y0 + h), r3(p["origin_um"][0] + w), r3(y0 + H_new)])
        elif p["name"] in hub_parts:
            continue
        elif p["origin_um"][1] >= ys - 1e-6:
            p["origin_um"] = [p["origin_um"][0], r3(p["origin_um"][1] + dH)]
    # straddling types grow and their internals above (Y* - oy) move
    grown = []
    for p in straddle:
        tn = p["type"]
        if tn in grown:
            continue
        grown.append(tn)
        t = T[tn]
        yl = ys - p["origin_um"][1]
        t["outline_um"] = [t["outline_um"][0], r3(t["outline_um"][1] + dH)]
        for h in t.get("hard_cores", []) + t.get("contents", []):
            if h.get("origin_um") and h["origin_um"][1] >= yl - 1e-6:
                h["origin_um"] = [h["origin_um"][0], r3(h["origin_um"][1] + dH)]
        for s in t.get("internal_stations", []):
            s["from_um"] = [s["from_um"][0], _yshift(s["from_um"][1], yl, dH)]
            s["to_um"] = [s["to_um"][0], _yshift(s["to_um"][1], yl, dH)]
            s["regs_um"] = _shift_pts(s.get("regs_um", []), yl, dH)
        for f in t.get("ft_slots", []):
            f["regs_um"] = _shift_pts(f.get("regs_um", []), yl, dH)
        ck = t.get("clock", {})
        if ck.get("tap_um"):
            ck["tap_um"] = [ck["tap_um"][0], _yshift(ck["tap_um"][1], yl, dH)]
        for tp in ck.get("taps", []):
            if tp.get("xy"):
                tp["xy"] = [tp["xy"][0], _yshift(tp["xy"][1], yl, dH)]
        rs = t.get("reset", {})
        if rs.get("tap_um"):
            rs["tap_um"] = [rs["tap_um"][0], _yshift(rs["tap_um"][1], yl, dH)]
        t["note"] = (t.get("note", "") + f" | PATH-HBM-R11 die growth: +{dH} um at local y {r3(yl)}").strip(" |")
    nwin = 0
    for pt in P["ports"]:
        if pt.get("face") in ("W", "E") and pt.get("window_um"):
            parts = {pt["src"]["part"], pt["dst"]["part"]}
            if parts & rowset:
                continue        # partner keeps its geometry
            a, b = pt["window_um"]
            na, nb = _yshift(a, ys, dH), _yshift(b, ys, dH)
            if (na, nb) != (a, b):
                nwin += 1
            pt["window_um"] = [r3(na), r3(nb)]
    die = P["die"]
    die["outline_um"] = [die["outline_um"][0], r3(die["outline_um"][1] + dH)]
    for io in die.get("io", []):
        if io.get("part") in rowset or io.get("part") in hub_parts:
            continue
        if io.get("rect_um") and io["rect_um"][1] >= ys - 1e-6:
            r = io["rect_um"]
            io["rect_um"] = [r[0], r3(r[1] + dH), r[2], r3(r[3] + dH)]
    for dm in die.get("pg", {}).get("domains", []):
        for key in ("rect_um",):
            r = dm.get(key)
            if r and r[1] >= ys - 1e-6:
                dm[key] = [r[0], r3(r[1] + dH), r[2], r3(r[3] + dH)]
        bm = dm.get("bumps", {})
        r = bm.get("rect_um")
        if r and r[1] >= ys - 1e-6:
            bm["rect_um"] = [r[0], r3(r[1] + dH), r[2], r3(r[3] + dH)]
    sp = P.get("clock", {}).get("spine", {})
    if sp.get("root_um"):
        sp["root_um"] = [sp["root_um"][0], _yshift(sp["root_um"][1], ys, dH)]
    return dict(dH_um=dH, insertion_y_um=ys, hub_row_y_um=[r3(y0), r3(y1)], grown_types=grown, row_types_grown=row_grown,
                windows_moved=nwin, hub_row_unchanged=row, hub_row_gap_rects_um=gaps,
                die_outline_um=die["outline_um"])


def run(plan_dir, out_dir, hubs, height=None, bounds=None, cap=6.0, spread=3.0, kcc=1, cc_min=1000.0, kmax=8,
        route=True, grow=False, grow_row=False, jobs=36, log=print):
    plan_dir, out_dir = Path(plan_dir), Path(out_dir)
    P = json.loads((plan_dir / "die_plan.json").read_text())
    rep = dict(schema="opentallas.hbm_r11_delta.v1", source_plan_sha256=hashlib.sha256(
        (plan_dir / "die_plan.json").read_bytes()).hexdigest(), pins_per_um=cap, spread_pins_per_um=spread,
        cc_serial_k=kcc, cc_min_um=cc_min, hubs={},
        note="plan arithmetic, UNCHECKED until NUMBER-CHECK (12.9f); lane transport = hbm_r10 plan MODEL of the "
             "core_conns cross-product (needs the hub glue bit map to confirm 1:1)")
    H_old = P["partition_types"][hubs[0][1]]["outline_um"][1]
    if height is None:
        hs = []
        for part, tn in hubs:
            t, W, H0, t1, _ = prepare(P, part, tn, cap, spread)
            b = (bounds or {}).get(tn) or R10.lane_bounds(t1["internal_stations"], W, 2)[0]
            hs.append(min_height(t1, W, b))
        height = max(hs)
        log(f"common hub height = max packing minimum {hs} -> {height}")
    height = r3(HR.ce(float(height), 8.64)) if abs(float(height) / 8.64 - round(float(height) / 8.64)) > 1e-6 \
        else r3(float(height))
    out = {}
    for part, tn in hubs:
        cores, st, res = run_hub(P, part, tn, height, (bounds or {}).get(tn), cap, spread, kcc, cc_min, kmax,
                                 route=route, jobs=jobs, log=log)
        out[tn] = (cores, st)
        rep["hubs"][tn] = res
    for part, tn in hubs:
        t = P["partition_types"][tn]
        cores, st = out[tn]
        W = t["outline_um"][0]
        t["outline_um"] = [W, height]
        t["hard_cores"] = cores
        t["internal_stations"] = st
        byname = {h["inst"]: h for h in cores}
        t["contents"] = [c for c in t.get("contents", []) if c.get("inst") in byname] + [
            dict(inst=h["inst"], module=h["module"], status="new", cells=None, note=h.get("note", ""),
                 origin_um=list(h["origin_um"]), outline_um=list(h["outline_um"])) for h in cores if "__q" in h["inst"]]
        for c in t["contents"]:
            if c.get("inst") in byname:
                c["origin_um"] = list(byname[c["inst"]]["origin_um"])
        r = rep["hubs"][tn]
        t["note"] = (t.get("note", "") + f" | PATH-HBM-R11 S=2 y-demand boundary {r['bound_um']} H {height} "
                     f"k={r['k']} cc_k={kcc}").strip(" |")
    rep["die_growth_um"] = r3(height - H_old)
    if grow and height > H_old:
        rep["die_growth"] = grow_die(P, [p for p, _ in hubs], H_old, height, grow_row=grow_row)
    P["note"] = (P.get("note", "") + f" | PATH-HBM-R11 delta: hubs {[h for _, h in hubs]} S=2 y-demand, H {height}, "
                 f"cc_k {kcc}, die growth {rep['die_growth_um']} um {'APPLIED' if grow else 'NOT applied'}").strip(" |")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(plan_dir, out_dir, copy_function=os.link, symlinks=True)
    for name in ("die_plan.json", "die_plan.sha256"):
        if (out_dir / name).exists():
            (out_dir / name).unlink()
    (out_dir / "die_plan.json").write_text(json.dumps(P, indent=1) + "\n")
    sha = hashlib.sha256((out_dir / "die_plan.json").read_bytes()).hexdigest()
    (out_dir / "die_plan.sha256").write_text(f"{sha}  die_plan.json\n")
    rep["plan_sha256"] = sha
    (out_dir / "r11_delta_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--hubs", default="NW_hub:q_hub_nw,NE_hub:q_hub_ne")
    ap.add_argument("--height-um", type=float, default=None, help="common hub height (default: max packing minimum)")
    ap.add_argument("--bound-um", action="append", default=[], help="TYPE:x fixes a hub boundary (else y-demand search)")
    ap.add_argument("--pins-per-um", type=float, default=6.0)
    ap.add_argument("--spread-pins-per-um", type=float, default=3.0)
    ap.add_argument("--cc-serial-k", type=int, default=1, help="option (a): 2 = serialise core-core > --cc-min-um by 2")
    ap.add_argument("--cc-min-um", type=float, default=1000.0)
    ap.add_argument("--k-max", type=int, default=8)
    ap.add_argument("--grow-die", action="store_true")
    ap.add_argument("--grow-row-types", action="store_true",
                    help="with --grow-die: the other hub-row partition types (banks/io) grow by dH too, so no empty "
                         "die strip lies on their N links (owner 10-17: no empty regions on link paths)")
    ap.add_argument("--no-route", action="store_true")
    ap.add_argument("--jobs", type=int, default=36)
    a = ap.parse_args(argv)
    hubs = [tuple(x.split(":")) for x in a.hubs.split(",") if x]
    bounds = {b.split(":")[0]: float(b.split(":")[1]) for b in a.bound_um}
    rep = run(a.plan_dir, a.out, hubs, a.height_um, bounds, a.pins_per_um, a.spread_pins_per_um, a.cc_serial_k,
              a.cc_min_um, a.k_max, route=not a.no_route, grow=a.grow_die, grow_row=a.grow_row_types, jobs=a.jobs)
    for tn, r in rep["hubs"].items():
        c = r["cut_per_sink_blocked"]
        print(f"{tn}: b {r['bound_um']} H {r['height_um']} k {r['k']} cut x {c['x']['max_use']} y {c['y']['max_use']} "
              f"segments {[(s['cut_x'], s['cut_y']) for s in r['segments']]} cc_serialised {r['cc_serialised']} "
              f"pin_peak {r['pin_peak_bits_per_um']} fill {r['segment_fill']}")
    print("die_growth_um", rep["die_growth_um"], "plan_sha256", rep["plan_sha256"])
    if rep.get("die_growth"):
        g = rep["die_growth"]
        print("die grown: dH", g["dH_um"], "at y", g["insertion_y_um"], "outline", g["die_outline_um"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
