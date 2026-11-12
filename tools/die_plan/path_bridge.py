#!/usr/bin/env python3
"""PATH-BRIDGE (SEAM-HOP-1, ready10): add stations where a hop over 405 um cannot be closed by moving the stations on the
straight route, by letting new stations sit ANYWHERE in the pin-to-pin box (grown by --pad) inside the crossed partition,
cores as obstacles (METHODOLOGY 12.2b: partition-owned repeater bay along the corridor; in-core bay only where a core
blocks the corridor and nothing outside closes the gap).

    python3 tools/die_plan/path_bridge.py IN OUT REPORT --lanes L1,L2,... [--limit 405] [--pad 250]

Per bad hop p -> q (consecutive stations of a lane, through the seam pin when they sit in different crossings), the new
stations go into the crossing that holds p, after p (existing stations never move: 0 change to existing banks):
  * candidate sites = 10.8-um grid in the box of p, q grown by pad, inside the type outline, off hard cores (+4.32 margin) and
    off every existing bank;  BFS over sites (edge = Manhattan <= limit - 10) gives the fewest new stations m;
  * slots with a bit bank get a re-packed bank per new station (path_respace._pack_bank, station = bank centre) and the hops
    are re-checked; slots without a bank just get the point;
  * no chain (a core blocks the whole corridor) -> status needs_bay, with the blocking cores named: that is a plan TYPE change
    (hard core move / outline) in the crossed partition, for escalation.
Replica slots (one type slot used by several partitions): decided once per (type, slot, hop), so all instances change alike.
Declared keys only (ft_slots regs_um/stations/bit_sites_um, latency rows), real normal-input S0->S1 re-checked.  Reports the
latency rows (+m cycles per lane through the slot, with group membership) and the TYPES THAT REBUILD.
"""
import argparse
import copy
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import path_respace as PR  # noqa: E402
import schema as S  # noqa: E402

EPS = 1e-6
GRID = 10.8


def _blockers(raw, tn, avoid):
    cores = [("box", a - PR.MARGIN, b - PR.MARGIN, c + PR.MARGIN, d + PR.MARGIN)
             for a, b, c, d in PR.type_boxes(raw["partition_types"][tn])]
    return cores


def _sites(raw, tn, p, q, pad, avoid):
    W, H = raw["partition_types"][tn]["outline_um"]
    x0, x1 = max(2.0, min(p[0], q[0]) - pad), min(W - 2.0, max(p[0], q[0]) + pad)
    y0, y1 = max(2.0, min(p[1], q[1]) - pad), min(H - 2.0, max(p[1], q[1]) + pad)
    xs = np.arange(round(x0 / GRID) * GRID, x1 + 1e-9, GRID)
    ys = np.arange(round(y0 / GRID) * GRID, y1 + 1e-9, GRID)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    X, Y = X.ravel(), Y.ravel()
    ok = np.ones(len(X), bool)
    for _i, a, b, c, d in _blockers(raw, tn, avoid):
        ok &= ~((X > a) & (X < c) & (Y > b) & (Y < d))
    for a, b, c, d in avoid:
        ok &= ~((X > a) & (X < c) & (Y > b) & (Y < d))
    return np.stack([X[ok], Y[ok]], 1)


def _chain(sites, p, q, reach, reach_last=None):
    """fewest intermediate sites m so that p -> s1 -> ... -> sm -> q has every hop <= reach; -> list of points or None."""
    n = len(sites)
    if n == 0:
        return None
    dp = np.abs(sites[:, 0] - p[0]) + np.abs(sites[:, 1] - p[1])
    dq = np.abs(sites[:, 0] - q[0]) + np.abs(sites[:, 1] - q[1])
    rl = reach if reach_last is None else reach_last
    if abs(p[0] - q[0]) + abs(p[1] - q[1]) <= rl:
        return []
    layer = [np.where(dp <= reach)[0]]
    prev = [np.full(n, -1)]
    seen = np.zeros(n, bool)
    seen[layer[0]] = True
    for m in range(1, 14):
        cur = layer[-1]
        if len(cur) and (dq[cur] <= rl).any():
            k = cur[np.argmax(dq[cur] <= rl)]
            path = [k]
            for lv in range(len(layer) - 1, 0, -1):
                k = prev[lv][k]
                path.append(k)
            return [tuple(sites[i]) for i in reversed(path)]
        if not len(cur):
            return None
        D = np.abs(sites[:, None, 0] - sites[cur][None, :, 0]) + np.abs(sites[:, None, 1] - sites[cur][None, :, 1])
        hit = (D <= reach) & (~seen[:, None])
        nxt = np.where(hit.any(1))[0]
        pr = np.full(n, -1)
        pr[nxt] = cur[np.argmax(hit[nxt], 1)]
        seen[nxt] = True
        layer.append(nxt)
        prev.append(pr)
    return None


def run(raw, lanes, limit=405.0, pad=250.0):
    import gen
    import die_hop_scan as DHS
    from ft_full_stage import load as full_load
    P = S.Plan(raw)
    raw2 = copy.deepcopy(raw)
    report = dict(lanes={}, types_rebuilt=[], bays=[])
    done = {}                                  # (tn, slot, j after) -> inserted type-frame points
    ops = []
    for lid in lanes:
        lane = PR.Lane(P, lid)
        _snap = {c_["tn"]: copy.deepcopy(raw2["partition_types"][c_["tn"]]["ft_slots"]) for c_ in lane.cross}
        _done = dict(done)
        st = lane.stations_now()
        s0moves = []
        for c, cr in enumerate(lane.cross):                 # S0 = the in-face register: it belongs AT the input pin
            _W, _H = raw2["partition_types"][cr["tn"]]["outline_um"]
            _pt = P.to_type(cr["part"], cr["pa"])
            if PR._man(st[c][0], cr["pa"]) > 20.0 and -1 <= _pt[0] <= _W + 1 and -1 <= _pt[1] <= _H + 1 and (cr["tn"], cr["slot"], "s0") not in done:
                sl0 = next(s_ for s_ in raw2["partition_types"][cr["tn"]]["ft_slots"] if s_["name"] == cr["slot"])
                if "regs_um" not in sl0:
                    sl0["regs_um"] = [[round(v, 3) for v in P.to_type(cr["part"], pt)] for pt in st[c]]
                old0 = list(sl0["regs_um"][0])
                sl0["regs_um"][0] = [round(v, 3) for v in P.to_type(cr["part"], cr["pa"])]
                done[(cr["tn"], cr["slot"], "s0")] = [sl0["regs_um"][0]]
                s0moves.append(dict(slot=f"{cr['part']}.{cr['slot']}", type=cr["tn"], from_um=old0, to_um=sl0["regs_um"][0]))
                st[c] = [cr["pa"]] + list(st[c][1:])
        pins = [c["pb"] for c in lane.cross]
        todo = []
        for c, pts in enumerate(st):
            for j in range(len(pts) - 1):
                if PR._man(pts[j], pts[j + 1]) > limit + EPS:
                    todo.append((c, j, pts[j], pts[j + 1], 0.0))
            nxt = st[c + 1][0] if c + 1 < len(st) else lane.end
            if PR._man(pts[-1], pins[c]) + PR._man(pins[c], nxt) > limit + EPS:
                todo.append((c, len(pts) - 1, pts[-1], pins[c], PR._man(pins[c], nxt)))
        if not todo:
            report["lanes"][lid] = dict(status="s0_moved" if s0moves else "ok", s0_moves=s0moves)
            continue
        info = list(s0moves)
        for c, j, p, q, leg2 in todo:
            via_pin = leg2 > 0
            cr = lane.cross[c]
            tn, slot, part = cr["tn"], cr["slot"], cr["part"]
            key = (tn, slot, j)
            if key in done:
                info.append(dict(slot=f"{part}.{slot}", added=len(done[key]), reused=True))
                continue
            tp, tq = P.to_type(part, p), P.to_type(part, q)
            sl = next(s_ for s_ in raw2["partition_types"][tn]["ft_slots"] if s_["name"] == slot)
            banked = "bit_sites_um" in sl
            avoid = PR._type_site_rects(raw2, tn, skip=None)
            sites = _sites(raw2, tn, tp, tq, pad, avoid)
            ch, pts_t, banks, why = None, None, None, "no chain"
            # minimum first: ONE station (ceil(hop/405)-1 = 1) tried on candidate sites ranked by hop balance, each with its
            # bank packed and the hops re-measured from the packed station centre (no reach ladder, no uneven chain)
            if sites is not None and len(sites) and PR._man(tp, tq) + leg2 > limit + EPS and PR._man(tp, tq) <= 2 * (limit - 10) - leg2:
                dpv = np.abs(sites[:, 0] - tp[0]) + np.abs(sites[:, 1] - tp[1])
                dqv = np.abs(sites[:, 0] - tq[0]) + np.abs(sites[:, 1] - tq[1]) + leg2
                okm = (dpv <= limit - 5) & (dqv <= limit - 5)
                idx = np.where(okm)[0]
                idx = idx[np.argsort(np.abs(dpv[idx] - dqv[idx]))][:60]
                cand = [[round(float(sites[ii][0]), 3), round(float(sites[ii][1]), 3)] for ii in idx]
                if banked and len(idx):         # the packer shifts a bank sideways: retry anchors at the shifted x, y swept
                    w0, h0 = sl["bit_site_cell_um"]
                    nb0 = len(sl["bit_sites_um"][0]) if sl["bit_sites_um"] else sl["width"] + 1
                    pk0 = PR._pack_bank(raw2, tn, nb0, w0, h0, cand[0], list(avoid))
                    if pk0:
                        ys_ = sorted({round(float(sites[ii][1]), 1) for ii in np.where(okm)[0]})
                        ys_ = ys_[:: max(1, len(ys_) // 120)]
                        cand = [[pk0[1][0], y_] for y_ in ys_] + cand
                for c_ in cand:
                    cen = [c_]
                    bk = None
                    if banked:
                        w, h = sl["bit_site_cell_um"]
                        nb = len(sl["bit_sites_um"][0]) if sl["bit_sites_um"] else sl["width"] + 1
                        pk = PR._pack_bank(raw2, tn, nb, w, h, c_, list(avoid))
                        if pk is None:
                            continue
                        bk, cen = [pk[0]], [pk[1]]
                    hh = [PR._man(tp, cen[0]), PR._man(cen[0], tq) + leg2]
                    if max(hh) <= limit - 2:
                        pts_t, banks, ch, why = cen, bk, [tuple(cen[0])], None
                        break
                if why is None:
                    pass
            even_res = None
            if why is not None and banked:          # even chains of m = 1..5 stations, anchors on the packed column, hops measured
                w, h = sl["bit_site_cell_um"]
                nb = len(sl["bit_sites_um"][0]) if sl["bit_sites_um"] else sl["width"] + 1
                p0 = PR._pack_bank(raw2, tn, nb, w, h, [(tp[0] + tq[0]) / 2, (tp[1] + tq[1]) / 2], list(avoid))
                xcol = p0[1][0] if p0 else (tp[0] + tq[0]) / 2
                found = False
                for m_ in range(1, 6):
                    for dxs in (0.0, -40.0, 40.0, -80.0, 80.0):
                        av = list(avoid)
                        cen, bl, ok_ = [], [], True
                        for k_ in range(1, m_ + 1):
                            f_ = k_ / (m_ + 1)
                            anc = [xcol + dxs, tp[1] + (tq[1] - tp[1]) * f_]
                            pk = PR._pack_bank(raw2, tn, nb, w, h, anc, av)
                            if pk is None:
                                ok_ = False
                                break
                            xs = [x for x, _ in pk[0]]
                            ys = [y for _, y in pk[0]]
                            av.append((min(xs), min(ys), max(xs) + w, max(ys) + h))
                            cen.append(pk[1])
                            bl.append(pk[0])
                        if not ok_:
                            continue
                        chain_ = [tp] + [tuple(c_) for c_ in cen] + [tq]
                        hs_ = [PR._man(a_, b_) for a_, b_ in zip(chain_, chain_[1:])]
                        if max(hs_[:-1] + [hs_[-1] + leg2]) <= limit - 2:
                            even_res, found = (cen, bl), True
                            break
                    if found:
                        break
            for reach in (() if why is None and pts_t is not None else (limit - 10.0, limit - 30.0, limit - 60.0, limit - 100.0, limit - 150.0, limit - 200.0, limit - 250.0, limit - 300.0)):
                ch = _chain(sites, tp, tq, reach, reach_last=reach - leg2)
                if ch is None:
                    break
                pts_t = [list(map(lambda v: round(float(v), 3), c_)) for c_ in ch]
                banks = None
                if banked:
                    w, h = sl["bit_site_cell_um"]
                    nb = len(sl["bit_sites_um"][0]) if sl["bit_sites_um"] else sl["width"] + 1
                    av = list(avoid)
                    bl, cen = [], []
                    for c_ in pts_t:
                        pk = PR._pack_bank(raw2, tn, nb, w, h, c_, av)
                        if pk is None:
                            bl = None
                            break
                        xs = [x for x, _ in pk[0]]
                        ys = [y for _, y in pk[0]]
                        av.append((min(xs), min(ys), max(xs) + w, max(ys) + h))
                        bl.append(pk[0])
                        cen.append(pk[1])
                    if bl is None:
                        why = "bank_pack_failed"
                        ch = "x"
                        continue
                    banks, pts_t = bl, cen
                chain = [tp] + [tuple(c_) for c_ in pts_t] + [tq]
                hs = [PR._man(a_, b_) for a_, b_ in zip(chain, chain[1:])]
                if max(hs[:-1] + [hs[-1] + leg2]) <= limit + EPS:
                    why = None
                    break
                why = "pack_moved_over_reach"
            if even_res is not None and (why is not None or pts_t is None or len(pts_t) > len(even_res[0])):
                pts_t, banks, ch, why = even_res[0], even_res[1], [tuple(c_) for c_ in even_res[0]], None
            if ch is None and why == "no chain":
                t = raw2["partition_types"][tn]
                box = (min(tp[0], tq[0]) - pad, min(tp[1], tq[1]) - pad, max(tp[0], tq[0]) + pad, max(tp[1], tq[1]) + pad)
                blk = [h["inst"] for h in t.get("hard_cores") or []
                       if h["origin_um"][0] < box[2] and h["origin_um"][0] + h["outline_um"][0] > box[0]
                       and h["origin_um"][1] < box[3] and h["origin_um"][1] + h["outline_um"][1] > box[1]]
                report["lanes"][lid] = dict(status="needs_bay", slot=f"{part}.{slot}", type=tn, hop_um=round(PR._man(tp, tq), 1),
                                            blocking_cores=blk[:12], n_cores_in_box=len(blk),
                                            p_um=[round(v, 1) for v in tp], q_um=[round(v, 1) for v in tq], n_sites=int(len(sites)),
                                            via_pin=via_pin, station_index=j,
                                            why="no station chain inside the pin-to-pin box: a core blocks the corridor "
                                                f"(12.2b in-core bay = plan type change of {tn}: move/shrink core or outline)")
                break
            if why and ch is not None and ch != []:
                report["lanes"][lid] = dict(status=why, slot=f"{part}.{slot}")
                break
            if ch == []:
                pts_t, banks = [], None
            # splice after station index j (j+1 for the bank stage list = station index)
            if "regs_um" not in sl:          # implicit even spacing: materialise the current station points first
                sl["regs_um"] = [[round(v, 3) for v in P.to_type(part, pt)] for pt in st[c]]
            sl["regs_um"] = sl["regs_um"][:j + 1] + pts_t + sl["regs_um"][j + 1:]
            sl["stations"] = len(sl["regs_um"])
            if banked:
                sl["bit_sites_um"] = sl["bit_sites_um"][:j] + banks + sl["bit_sites_um"][j:]
            done[key] = pts_t
            info.append(dict(slot=f"{part}.{slot}", type=tn, after_station=j, added=len(pts_t), form="bank" if banked else "plain point",
                             new_points_um=pts_t))
        else:
            report["lanes"][lid] = dict(status="bridged", inserted=info)
            import check as _CK                     # verify with G0's own metric (lane_pin_hops through every seam pin)
            _Pt = S.Plan(raw2)
            _g = _CK.lane_geometry(_Pt, lid)
            _h = max(_CK.lane_pin_hops(_Pt, lid, _g[1]) or [0.0])
            if _h > limit + EPS:
                report["lanes"][lid] = dict(status="verify_failed", worst_hop_um=round(_h, 1), inserted=info)
        if report["lanes"][lid]["status"] not in ("bridged", "ok", "s0_moved"):      # failed lane: undo its partial changes
            for tn_, sls in _snap.items():
                raw2["partition_types"][tn_]["ft_slots"] = sls
            done.clear()
            done.update(_done)
    # real normal-input S0->S1 re-check on every touched normal slot, and latency
    P2 = S.Plan(raw2)
    bad = []
    for (tn, slot, _j) in done:
        sl2 = next(s_ for s_ in P2.types[tn]["ft_slots"] if s_["name"] == slot)
        if DHS.normal_slot(P2, tn, slot, full=full_load(P2, tn)):
            rows = DHS.first_internal_hops(P2, tn, sl2, pins=DHS.pin_table(P2, tn))
            w_ = max([d for _b, d in rows] + [0.0])
            if w_ > limit + EPS:
                bad.append(f"{tn}.{slot}: real input S0->S1 {w_:.0f} um")
    report["s0s1_violations"] = bad
    touched = sorted({(tn, slot) for tn, slot, _ in done})
    for tn, slot in touched:
        path = ["partition_types", tn, "ft_slots", {"k": "name", "v": slot}]
        sl = next(s_ for s_ in raw2["partition_types"][tn]["ft_slots"] if s_["name"] == slot)
        ops.append([path + ["regs_um"], "set", sl["regs_um"]])
        ops.append([path + ["stations"], "set", sl["stations"]])
        if "bit_sites_um" in sl:
            ops.append([path + ["bit_sites_um"], "set", sl["bit_sites_um"]])
    lat0 = raw.get("latency", {}).get("lanes", {})
    c0, c1 = gen.latency_table(P), gen.latency_table(P2)
    plus, newlat = {}, {}
    for lid in c1:
        if c0.get(lid) == c1[lid] or lid not in lat0:
            continue
        row = dict(lat0[lid])
        for k, v in c1[lid].items():
            if c0[lid].get(k) != v:
                row[k] = (row.get(k, 0) + v - c0[lid].get(k, 0)) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
        ops.append([["latency", "lanes", lid], "set", row])
        newlat[lid] = row
        plus[lid] = dict(old_cycles=lat0[lid].get("cycles"), new_cycles=row.get("cycles"))
    raw2["latency"] = dict(raw2.get("latency", {}), lanes={**lat0, **newlat})
    groups = defaultdict(list)
    for name, kind, ls in P.latency_groups():
        for l in ls:
            if l in plus:
                groups[l].append(f"{kind}:{name}")
    report["latency_changed"] = {l: dict(v, groups=groups.get(l, []), in_target_list=l in lanes) for l, v in plus.items()}
    report["types_rebuilt"] = sorted({tn for tn, _ in touched})
    report["slots_changed"] = [f"{tn}.{sl}" for tn, sl in touched]
    return raw2, ops, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("report")
    ap.add_argument("--lanes", required=True)
    ap.add_argument("--limit", type=float, default=405.0)
    ap.add_argument("--pad", type=float, default=250.0)
    a = ap.parse_args(argv)
    import path_respace_stage as ST
    import re
    raw = PR._load(a.inp)
    raw2, ops, rep = run(raw, a.lanes.split(","), a.limit, a.pad)
    geo = PR.geo_guard(raw, raw2)
    if geo:
        print("geometry guard FAIL (new station/bank vs macro):", geo[:4], file=sys.stderr)
        rep["geo_guard_failed"] = geo
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
        return 3
    guard = PR.tap_guard(raw, raw2)
    if guard:
        print("tap guard FAIL (added stations break the kit tap rule):", guard, file=sys.stderr)
        rep["tap_guard_failed"] = guard
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
        return 3
    bad = sorted({p for p in ST.diff_paths(raw, raw2) if not any(re.fullmatch(d, p.lstrip("/")) for d in ST.DECLARED)})
    if bad:
        print("stage touched undeclared keys:", bad[:10], file=sys.stderr)
        return 2
    rep["declared_keys"] = ST.DECLARED
    Path(a.out).write_text(json.dumps(raw2) + "\n")
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    st = defaultdict(int)
    for v in rep["lanes"].values():
        st[v["status"]] += 1
    print(json.dumps(dict(by_status=dict(st), types_rebuilt=len(rep["types_rebuilt"]), plus_lanes=len(rep["latency_changed"]),
                          s0s1=rep["s0s1_violations"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
