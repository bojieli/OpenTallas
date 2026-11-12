#!/usr/bin/env python3
"""PATH-RESPACE (SEAM-HOP-1, COORD P0 11-12): one pass that re-spaces the relay stations of every lane whose end-to-end
path has a hop over the 405-um signal reach, instead of fixing seam hops one at a time.

    python3 tools/die_plan/path_respace.py PLAN[.json|.gz] OUTDIR [--limit 405] [--no-add] [--name NAME]

Model (settled by kit_istations.py / face_flops.tcl): every bound bus has a boundary flop (u_bin / u_bout) pinned at the
face pin, so a lane is  source face flop -> [slot stations of partition 1] -> seam pin -> [slot stations of partition 2]
-> ... -> sink face flop, and a type's internal_stations[] chain runs behind the face flop (R3-INTERNAL judges it).
Per lane with a hop > limit (path measured through every seam pin, as seam_hop.py / check.lane_pin_hops):
  1. the slot stations of all crossed partitions are re-sited on the lane's route polyline (the same Z/L routes as
     check.lane_geometry), SAME station count per slot, minimising the largest hop first (binary search on the gap
     with the per-slot arc interval as the only constraint), then pulled to the even spacing D/(n+1) inside the
     feasible band.  0 cycles.
  2. if even the best placement leaves a hop > limit - 1, one station is added at a time to the slot that holds the
     binding gap (+1 cycle on every lane through that slot; latency table re-derived with gen.latency_table, the
     lanes whose row changed are listed with their latency-group membership for TOK).  --no-add reports instead.
  3. a station site must clear the type's hard cores / content macros (landing_place._clear_of_hard_cores margin);
     it slides along the route inside its slot interval to the nearest clear site, else the lane is reported blocked.
  4. type internal_stations[] entries whose own chain has a hop > limit are re-spaced evenly along their own route
     (same count); exact-site entries (bit_sites_um, face_bit_sites_um, bit_route, leaf_um) are reported, not moved.
Slots shared by several instances of one type take ONE position list: the first lane decides, later lanes through the
same (type, slot) are kept if they stay within the limit, else reported as replica conflicts.
Pins, windows, faces and partition geometry are never touched.  Slots with a full-stage placement file or exact bit
sites are reported, not moved.
Output OUTDIR: path_respace_delta.json (ladder-delta: name/source/base/files.die_plan.json.ops), die_plan.json (the delta
applied, for G0 / seam_hop before-after), path_respace_report.json.  Plan arithmetic only: UNCHECKED until G0 / bind.
"""
import argparse
import copy
import gzip
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import schema as S  # noqa: E402

EPS = 1e-6
MARGIN = 4.32          # landing_place._clear_of_hard_cores margin
GRID_X, GRID_Y = 0.054, 0.27
SLACK = 1.0            # a placement must leave every hop <= limit - SLACK


def _load(path):
    return json.loads(gzip.open(path, "rt").read()) if str(path).endswith(".gz") else json.loads(Path(path).read_text())


def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _blockers(P, tn, cache={}):
    key = (id(P), tn)
    if key not in cache:
        t = P.types[tn]
        r = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
              h["origin_um"][1] + h["outline_um"][1]) for h in t.get("hard_cores") or []]
        cache[key] = r
    return cache[key]


def _clear(P, tn, pt):
    return not any(a - MARGIN < pt[0] < c + MARGIN and b - MARGIN < pt[1] < d + MARGIN for a, b, c, d in _blockers(P, tn))


class Lane:
    """arc-length model of one lane: per crossing the route polyline, arc interval, current/new stations (die frame)."""

    def __init__(self, P, lid):
        self.P, self.lid = P, lid
        ln = P.lanes[lid]
        self.ports = ln["ports"]
        self.start = P.port_point(self.ports[0])
        self.end = P.port_point(self.ports[-1])
        self.cross = []          # dicts: part, slot, tn, pa, pb, seg, lo, hi, key
        s = 0.0
        for part, slot, a, b in P.lane_crossings(lid):
            pa, pb = P.port_point(a), P.port_point(b)
            sl = P.slot(part, slot) or {}
            fin, fout = P.die_face(part, sl.get("in_face", "W")), P.die_face(part, sl.get("out_face", "E"))
            seg = check.zroute(pa, pb, fin, fout)
            L = check.plen(seg)
            self.cross.append(dict(part=part, slot=slot, tn=P.parts[part]["type"], pa=pa, pb=pb, seg=seg, lo=s,
                                   hi=s + L, k=int(sl.get("stations", 1))))
            s += L
        self.D = s

    def stations_now(self):
        """current station points (die frame) per crossing, as lane_geometry places them."""
        _pts, regs, xs = check.lane_geometry(self.P, self.lid)
        out, i = [], 1
        for x in xs:
            out.append(regs[i:i + x["stations"]])
            i += x["stations"]
        return out

    @staticmethod
    def hops(start, end, cross, st):
        h, prev, length = [], start, 0.0
        for c, pts in zip(cross, st):
            length += _man(prev, c["pa"])
            prev = c["pa"]
            for p in pts:
                length += _man(prev, p)
                h.append(length)
                prev, length = p, 0.0
            length += _man(prev, c["pb"])
            prev = c["pb"]
        length += _man(prev, end)
        h.append(length)
        return h


def _clear_arcs(P, cross, c, step=2.16):
    """sorted arc positions on crossing c's route whose site clears the type's hard cores (grid step um)."""
    import bisect  # noqa: F401
    cr = cross[c]
    n = int((cr["hi"] - cr["lo"]) / step)
    out = []
    for i in range(n + 1):
        v = min(cr["hi"], cr["lo"] + i * step)
        if _clear(P, cr["tn"], P.to_type(cr["part"], _point_at(cross, c, v))):
            out.append(v)
    return out


def _solve(cross, ks, D, g_cap, clear):
    """arc positions s_m for the stations in order (S0 of every slot pinned at its input pin, the others on clear arcs
    of their own crossing); returns (g*, positions at the even-ish solution) or (inf, None) when a slot has no clear arc."""
    import bisect
    iv = []
    for c in range(len(cross)):
        for j in range(ks[c]):
            iv.append((c, [cross[c]["lo"]] if j == 0 else clear.get((c, j), clear[c])))
    n = len(iv)
    if n == 0:
        return D, []
    if any(not arcs for _, arcs in iv):
        return float("inf"), None

    def le(arcs, x):          # largest arc <= x
        i = bisect.bisect_right(arcs, x + EPS)
        return arcs[i - 1] if i else None

    def ge(arcs, x):          # smallest arc >= x
        i = bisect.bisect_left(arcs, x - EPS)
        return arcs[i] if i < len(arcs) else None

    # monotone order: ub_m = largest arc of station m not beyond what later stations can still reach
    ub, nx = [None] * n, float("inf")
    for m in range(n - 1, -1, -1):
        v = le(iv[m][1], nx)
        if v is None:
            return float("inf"), None
        ub[m] = nx = v
    lb, pv = [None] * n, 0.0
    for m in range(n):
        v = ge(iv[m][1], pv)
        if v is None:
            return float("inf"), None
        lb[m] = pv = v

    def fwd(g):
        s, prev = [], 0.0
        for m, (_, arcs) in enumerate(iv):
            v = le(arcs, min(prev + g, ub[m]))
            if v is None or v < max(prev, lb[m]) - EPS:
                return None
            s.append(v)
            prev = v
        return s if D - s[-1] <= g + EPS else None

    lo_g, hi_g = 0.0, D
    for _ in range(60):
        mid = (lo_g + hi_g) / 2
        if fwd(mid) is None:
            lo_g = mid
        else:
            hi_g = mid
    gstar = hi_g
    if gstar > g_cap:
        return gstar, fwd(gstar)
    g = min(g_cap, max(gstar, 1.15 * D / (n + 1)))
    ff = fwd(g)
    bt, nxt = [None] * n, D
    for m in range(n - 1, -1, -1):
        v = ge(iv[m][1], max(nxt - g, lb[m]))
        bt[m] = v if v is not None and v <= nxt + EPS else ff[m]
        nxt = bt[m]
    s, prev = [], 0.0
    for m in range(n):
        arcs = iv[m][1]
        e = D * (m + 1) / (n + 1)
        a, b = max(bt[m], prev), min(ff[m], prev + g)
        if a > b + EPS:
            v = ff[m]
        else:
            v = e if a <= e <= b else (a if e < a else b)
            lo_i = bisect.bisect_left(arcs, a - EPS)
            hi_i = bisect.bisect_right(arcs, b + EPS)
            cand = arcs[lo_i:hi_i]
            v = min(cand, key=lambda x: abs(x - e)) if cand else ff[m]
        s.append(v)
        prev = v
    return gstar, s


def _fail_point(cross, ks, clear, g):
    """first station that cannot be reached within gap g from the previous one (forward walk): (slot, stage, prev, arcs lo-hi)."""
    import bisect
    prev = 0.0
    for c in range(len(cross)):
        for j in range(ks[c]):
            arcs = [cross[c]["lo"]] if j == 0 else clear.get((c, j), clear[c])
            i = bisect.bisect_right(arcs, prev + g + EPS)
            if not i or arcs[i - 1] < prev - EPS:
                return dict(slot=f"{cross[c]['part']}.{cross[c]['slot']}", stage=j, prev_arc=round(prev, 1),
                            reachable=[round(arcs[0], 1), round(arcs[-1], 1)] if arcs else None)
            prev = arcs[i - 1]
    return None


def _point_at(cross, c, s):
    seg = cross[c]["seg"]
    return check.point_at(seg, max(0.0, s - cross[c]["lo"]))


def _slide(P, cross, c, s, lo_s, hi_s):
    """nearest arc position to s inside [lo_s, hi_s] (within the crossing) whose site clears the blockers."""
    tn = cross[c]["tn"]
    part = cross[c]["part"]
    lo, hi = max(lo_s, cross[c]["lo"]), min(hi_s, cross[c]["hi"])
    for d in [0.0] + [x * 4.32 * sgn for x in range(1, 400) for sgn in (1, -1)]:
        v = s + d
        if lo - EPS <= v <= hi + EPS:
            pt = _point_at(cross, c, v)
            if _clear(P, tn, P.to_type(part, pt)):
                return v, pt
    return None, None


def plan_lane(P, lane, limit, allow_add, decided):
    """-> dict(status, new={crossing idx: [type-frame pts]}, adds={crossing idx: n}) for one lane."""
    cross = lane.cross
    st_now = lane.stations_now()
    h0 = Lane.hops(lane.start, lane.end, cross, st_now)
    if max(h0) <= limit + EPS:
        return dict(status="ok", before=max(h0))
    ks = [c["k"] for c in cross]
    exact = {idx for idx, c in enumerate(cross) if "bit_sites_um" in (P.slot(c["part"], c["slot"]) or {})}
    from ft_full_stage import load
    for c in cross:
        if c["slot"] in load(P, c["tn"]):
            return dict(status="full_stage_slot", before=max(h0), slot=f"{c['part']}.{c['slot']}")
    adds = defaultdict(int)
    clear = {c: _clear_arcs(P, cross, c) for c in range(len(cross))}
    stay = {}
    for c in exact:                  # exact bit banks: stage j may only move where its whole bank stays on the outline
        sl = P.slot(cross[c]["part"], cross[c]["slot"])
        old_c = [tuple(P.to_type(cross[c]["part"], p)) for p in st_now[c]]
        if len(old_c) != len(sl["bit_sites_um"]) + 1:
            return dict(status="exact_slot_bank_shape", before=max(h0), slot=f"{cross[c]['part']}.{cross[c]['slot']}")
        w, h = sl["bit_site_cell_um"]
        W, H = P.types[cross[c]["tn"]]["outline_um"]
        for j in range(1, len(old_c) + 12):
            t = min(j, len(old_c) - 1)             # bank template: stage j itself, clones of the last stage for added ones
            xs = [x for x, _ in sl["bit_sites_um"][t - 1]]
            ys = [y for _, y in sl["bit_sites_um"][t - 1]]
            bb = (min(xs), min(ys), max(xs) + w, max(ys) + h)
            ok = []
            for v in clear[c]:
                tp = P.to_type(cross[c]["part"], _point_at(cross, c, v))
                dx = round((tp[0] - old_c[t][0]) / GRID_X) * GRID_X
                dy = round((tp[1] - old_c[t][1]) / GRID_Y) * GRID_Y
                x0, y0, x1, y1 = bb[0] + dx, bb[1] + dy, bb[2] + dx, bb[3] + dy
                if x0 >= 0 and y0 >= 0 and x1 <= W and y1 <= H and not any(
                        x0 < cc + MARGIN and x1 > a_ - MARGIN and y0 < d_ + MARGIN and y1 > b_ - MARGIN
                        for a_, b_, cc, d_ in _blockers(P, cross[c]["tn"])):
                    ok.append(v)
            if j < len(old_c):
                if ok:
                    pass          # prefer moved-but-fitting sites; the old site stays an option only when nothing fits
                else:
                    near = min(clear[c] or [cross[c]["lo"]], key=lambda v: _man(_point_at(cross, c, v), st_now[c][j]))
                    stay[(c, j)] = (near, st_now[c][j])
                    ok = [near]
            clear[(c, j)] = sorted(set(ok))
    for _ in range(12):
        gstar, s = _solve(cross, ks, lane.D, limit - SLACK, clear)
        if s is None:
            return dict(status="blocked", before=max(h0))
        if gstar <= limit - SLACK + EPS:
            break
        if not allow_add:
            return dict(status="needs_add", before=max(h0), gstar=gstar)
        # add the station that lowers the best achievable max gap most (ties: the crossing with the longest route)
        trial = []
        for c in range(len(cross)):
            ks[c] += 1
            g2, _ = _solve(cross, ks, lane.D, 0.0, clear)
            ks[c] -= 1
            trial.append((g2, -(cross[c]["hi"] - cross[c]["lo"]), c))
        g2, _neg, best = min(trial)
        if g2 >= gstar - EPS and not any(t[0] < gstar - EPS for t in trial):
            # no single add helps (two are needed): add where the route is longest per station
            best = max(range(len(cross)), key=lambda c: (cross[c]["hi"] - cross[c]["lo"]) / ks[c])
        ks[best] += 1
        adds[best] += 1
    else:
        return dict(status="unresolved", before=max(h0), gstar=round(gstar, 1),
                    binding=_fail_point(cross, ks, clear, limit - SLACK))
    out, new_pts, n = {}, [], 0
    for c in range(len(cross)):
        pts_c = []
        for j in range(ks[c]):
            if j == 0:
                pts_c.append(cross[c]["pa"])
            elif (c, j) in stay and abs(stay[(c, j)][0] - s[n]) < 1e-9:
                pts_c.append(stay[(c, j)][1])
            else:
                pts_c.append(_point_at(cross, c, s[n]))
            n += 1
        out[c] = pts_c
        new_pts.append(pts_c)
    h1 = Lane.hops(lane.start, lane.end, cross, new_pts)
    if max(h1) > limit + EPS:
        return dict(status="unresolved", before=max(h0), after=max(h1))
    old = {c: [tuple(P.to_type(cross[c]["part"], p)) for p in st_now[c]] for c in range(len(cross))}
    return dict(status="fixed", before=max(h0), after=max(h1), new=out, adds=dict(adds), ks=ks, old=old, exact=sorted(exact))


def _bank_move(P, lane, res, limit):
    """exact-site slots: translate every bit site of stage j rigidly by the (snapped) displacement of its station
    (added stations clone the last stage's bank).  -> {crossing: (new type pts, new bit_sites_um)} or an error string."""
    out = {}
    for c in res["exact"]:
        cr = lane.cross[c]
        sl = P.slot(cr["part"], cr["slot"])
        old, new = res["old"][c], [P.to_type(cr["part"], p) for p in res["new"][c]]
        if len(sl["bit_sites_um"]) != len(old) - 1:
            return "bank stage count"
        w, h = sl["bit_site_cell_um"]
        W, H = P.types[cr["tn"]]["outline_um"]
        pts, banks = [list(new[0])], []
        for j in range(1, len(new)):
            t = min(j, len(old) - 1)
            if j < len(old) and tuple(round(v, 6) for v in new[j]) == tuple(round(v, 6) for v in old[j]):
                dx = dy = 0.0
            else:
                dx = round((new[j][0] - old[t][0]) / GRID_X) * GRID_X
                dy = round((new[j][1] - old[t][1]) / GRID_Y) * GRID_Y
            bank = [[round(x + dx, 5), round(y + dy, 5)] for x, y in sl["bit_sites_um"][t - 1]]
            for x, y in bank:
                if x < 0 or y < 0 or x + w > W or y + h > H or not _clear(P, cr["tn"], (x + w / 2, y + h / 2)):
                    return f"bank stage {j} site off outline or on a blocker"
            banks.append(bank)
            pts.append([round(old[t][0] + dx, 3), round(old[t][1] + dy, 3)])
        bbs = [(min(x for x, _ in b_), min(y for _, y in b_), max(x for x, _ in b_) + w, max(y for _, y in b_) + h) for b_ in banks]
        for i in range(len(bbs)):
            for k in range(i + 1, len(bbs)):
                a_, b_ = bbs[i], bbs[k]
                if a_[0] < b_[2] and b_[0] < a_[2] and a_[1] < b_[3] and b_[1] < a_[3]:
                    return f"bank stages {i + 1} and {k + 1} overlap"
        out[c] = (pts, banks)
    return out


def respace_collectors(raw2, ops, limit, P2=None):
    """reverse-collector / reset-relay chains (collector_reach.py rule): for every type whose ACTIVE collector chain has an
    edge over the limit, re-site relays (same count, same tree, same depth) so every edge incident to a moved relay is
    <= limit - SLACK: each pass moves one endpoint of the worst edge to the clear grid site (type frame, step 4.32 um, on
    the outline, off the hard cores) that minimises the largest edge incident to it, then the smaller move.  Sources and
    the tree shape never change; the landing sidecar collector tree must be republished (added_tap_recentre --sidecar)
    and the type re-bound.  -> report rows."""
    import collector_reach as CR
    rows = []
    P2 = P2 or S.Plan(raw2)
    for tn, t in raw2["partition_types"].items():
        bad = CR.type_findings(tn, t, limit)
        if not bad:
            continue
        lc = t["clock"]["landing_contract"]
        tree = lc["collector_tree"]
        W, H = t["outline_um"]
        relays = {r["q"]: r for r in tree["relays"]}
        xy = {"rst_root_n": tuple(tree["root"]), **{q: tuple(r["xy"]) for q, r in relays.items()}}
        nbr = defaultdict(list)
        for q, r in relays.items():
            nbr[q].append(r["d"])
            nbr[r["d"]].append(q)
        srcpts = defaultdict(list)           # fixed source / status-pin points a tap node must stay within reach of
        for sc in list(lc.get("collector_local_sources") or []) + list(lc.get("collector_children") or []):
            nd = sc.get("node", f"rst_n_t{sc.get('tap', 0)}")
            srcpts[nd] += [tuple(p) for p in (sc.get("status_pins_xy_um") or [sc.get("xy_um")]) if p]
        moved = {}
        before = max(b["hop_um"] for b in bad)
        for _ in range(40):
            bad = CR.type_findings(tn, {**t, "clock": {**t["clock"], "landing_contract": {**lc, "collector_tree": dict(tree, relays=[dict(r, xy=list(xy[r["q"]])) for r in tree["relays"]])}}}, limit - SLACK)
            if not bad:
                break
            w = max(bad, key=lambda b: b["hop_um"])
            done = False
            for n in ((w["src"], w["dst"]) if w["kind"] == "edge" else (w["dst"],)):
                if n == "rst_root_n" or n not in relays:
                    continue
                nb = [xy[m] for m in nbr[n]] + srcpts.get(n, [])
                x0, x1 = min(p[0] for p in nb), max(p[0] for p in nb)
                y0, y1 = min(p[1] for p in nb), max(p[1] for p in nb)
                best = None
                gx = [x0 + i * 4.32 for i in range(int((x1 - x0) / 4.32) + 1)] or [x0]
                gy = [y0 + i * 4.32 for i in range(int((y1 - y0) / 4.32) + 1)] or [y0]
                for x in gx[:: max(1, len(gx) // 80)]:
                    for y in gy[:: max(1, len(gy) // 80)]:
                        if not (0 <= x <= W and 0 <= y <= H) or not _clear(P2, tn, (x, y)):
                            continue
                        m = max(abs(x - p[0]) + abs(y - p[1]) for p in nb)
                        key = (m, abs(x - xy[n][0]) + abs(y - xy[n][1]))
                        if best is None or key < best[0]:
                            best = (key, (round(x, 3), round(y, 3)))
                cur = max(abs(xy[n][0] - p[0]) + abs(xy[n][1] - p[1]) for p in nb)
                if best and best[0][0] < cur - EPS:
                    xy[n] = best[1]
                    moved[n] = best[1]
                    done = True
                    break
            if not done:
                break
        after_bad = [b for b in CR.type_findings(tn, {**t, "clock": {**t["clock"], "landing_contract": {**lc, "collector_tree": dict(tree, relays=[dict(r, xy=list(xy[r["q"]])) for r in tree["relays"]])}}}, limit)]
        for n, p in moved.items():
            relays[n]["xy"] = list(p)
            ops.append([["partition_types", tn, "clock", "landing_contract", "collector_tree", "relays", {"k": "q", "v": n}, "xy"],
                        "set", list(p)])
        rows.append(dict(type=tn, worst_before=before, worst_after=max([b["hop_um"] for b in after_bad] or [0.0]),
                         relays_moved=len(moved), status="fixed" if not after_bad else "unresolved",
                         moved={n: list(p) for n, p in list(moved.items())[:8]}))
    return rows


def run(raw, limit=405.0, allow_add=True):
    P = S.Plan(raw)
    raw2 = copy.deepcopy(raw)
    lanes = {lid: Lane(P, lid) for lid in P.lanes}
    report = dict(lanes={}, replica_conflicts=[], skipped=[])
    decided = {}          # (tn, slot) -> [type pts]
    decided_banks = {}    # (tn, slot) -> new bit_sites_um
    ops, changed_slots = [], {}
    order = sorted(lanes, key=lambda l: -max(Lane.hops(lanes[l].start, lanes[l].end, lanes[l].cross, lanes[l].stations_now())))
    for lid in order:
        lane = lanes[lid]
        # a replica slot already decided by an earlier lane: keep it if this lane is fine under it
        res = plan_lane(P, lane, limit, allow_add, decided)
        if res["status"] == "ok":
            continue
        if res["status"] != "fixed":
            report["lanes"][lid] = res
            continue
        mv = _bank_move(P, lane, res, limit) if res.get("exact") else {}
        if isinstance(mv, str):
            res["status"] = "exact_bank_blocked"
            res["why"] = mv
            report["lanes"][lid] = {k: v for k, v in res.items() if k not in ("new", "old")}
            continue
        for c, (tp, _b) in mv.items():
            res["new"][c] = [P.to_die(lane.cross[c]["part"], p) for p in tp]
        st_all = [res["new"][c] for c in range(len(lane.cross))]
        h1 = Lane.hops(lane.start, lane.end, lane.cross, st_all)
        if max(h1) > limit + EPS:
            res["status"], res["after"] = "exact_snap_over", max(h1)
            report["lanes"][lid] = {k: v for k, v in res.items() if k not in ("new", "old")}
            continue
        res["after"] = max(h1)
        banks_of = {(lane.cross[c]["tn"], lane.cross[c]["slot"]): b for c, (_t, b) in mv.items()}
        conflict = False
        for c, pts in res["new"].items():
            cr = lane.cross[c]
            key = (cr["tn"], cr["slot"])
            tpts = [[round(x, 3) for x in P.to_type(cr["part"], p)] for p in pts]
            if key in decided and decided[key] != tpts:
                conflict = True
        if conflict:
            res["status"] = "replica_conflict"
            report["lanes"][lid] = res
            report["replica_conflicts"].append(lid)
            continue
        for c, pts in res["new"].items():
            cr = lane.cross[c]
            decided[(cr["tn"], cr["slot"])] = [[round(x, 3) for x in P.to_type(cr["part"], p)] for p in pts]
            if (cr["tn"], cr["slot"]) in banks_of:
                decided_banks[(cr["tn"], cr["slot"])] = banks_of[(cr["tn"], cr["slot"])]
        report["lanes"][lid] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in res.items()
                                if k not in ("new", "old")}
    # apply
    for (tn, slot), tpts in decided.items():
        t = raw2["partition_types"][tn]
        sl = next(s_ for s_ in t["ft_slots"] if s_["name"] == slot)
        k0 = sl.get("stations", 1)
        sl["regs_um"] = tpts
        sl["stations"] = len(tpts)
        path = ["partition_types", tn, "ft_slots", {"k": "name", "v": slot}]
        ops.append([path + ["regs_um"], "set", tpts])
        if (tn, slot) in decided_banks:
            sl["bit_sites_um"] = decided_banks[(tn, slot)]
            ops.append([path + ["bit_sites_um"], "set", decided_banks[(tn, slot)]])
        if len(tpts) != k0:
            ops.append([path + ["stations"], "set", len(tpts)])
    P2 = S.Plan(raw2)
    import gen
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
    # internal_stations pass
    internal = []
    for tn, t in raw2["partition_types"].items():
        for i, e in enumerate(t.get("internal_stations", []) or []):
            if not e.get("regs_um"):
                continue
            pts = [tuple(e["from_um"])] + [tuple(r) for r in e["regs_um"]] + [tuple(e["to_um"])]
            worst = max(_man(a, b) for a, b in zip(pts, pts[1:]))
            if worst <= limit + EPS:
                continue
            if any(k in e for k in ("bit_sites_um", "face_bit_sites_um", "bit_route", "leaf_um")):
                internal.append(dict(type=tn, index=i, conn=e.get("conn"), worst=round(worst, 1), status="exact_sites"))
                continue
            total = sum(_man(a, b) for a, b in zip(pts, pts[1:]))
            n = len(e["regs_um"])
            if total / (n + 1) > limit - SLACK:
                internal.append(dict(type=tn, index=i, conn=e.get("conn"), worst=round(worst, 1), status="needs_add",
                                     path_um=round(total, 1), stations=n))
                continue
            cum = [0.0]
            for a, b in zip(pts, pts[1:]):
                cum.append(cum[-1] + _man(a, b))
            new = []
            for j in range(1, n + 1):
                new.append([round(x, 3) for x in check.point_at(pts, total * j / (n + 1))])
            if all(_clear(P2, tn, p) for p in new):
                ops.append([["partition_types", tn, "internal_stations", i, "regs_um"], "set", new])
                e["regs_um"] = new
                internal.append(dict(type=tn, index=i, conn=e.get("conn"), worst=round(worst, 1), status="respaced"))
            else:
                internal.append(dict(type=tn, index=i, conn=e.get("conn"), worst=round(worst, 1), status="blocked"))
    report["internal_stations"] = internal
    report["collector_chains"] = respace_collectors(raw2, ops, limit)
    report["latency_changed"] = {l: dict(v, groups=groups.get(l, [])) for l, v in plus.items()}
    st = defaultdict(int)
    for r in report["lanes"].values():
        st[r["status"]] += 1
    report["summary"] = dict(die=P.name, lanes_over=len(report["lanes"]), by_status=dict(st),
                             zero_cycle=sum(1 for r in report["lanes"].values() if r["status"] == "fixed" and not r.get("adds")),
                             plus_cycle_lanes=len(plus), slots_changed=len(decided), internal=len(internal),
                             collector_types=len(report["collector_chains"]),
                             collector_fixed=sum(1 for r in report["collector_chains"] if r["status"] == "fixed"))
    return raw2, ops, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--limit", type=float, default=S.SIGNAL_REACH_UM)
    ap.add_argument("--no-add", action="store_true")
    ap.add_argument("--name")
    a = ap.parse_args(argv)
    raw = _load(a.plan)
    raw2, ops, rep = run(raw, a.limit, not a.no_add)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    base = hashlib.sha256(Path(a.plan).read_bytes()).hexdigest()[:12]
    delta = dict(name=a.name or f"path_respace_{rep['summary']['die']}", source="SEAM-HOP-1 path_respace.py",
                 base=f"{Path(a.plan).name} {base}", files={"die_plan.json": {"kind": "json", "ops": ops}})
    (out / "path_respace_delta.json").write_text(json.dumps(delta) + "\n")
    (out / "die_plan.json").write_text(json.dumps(raw2) + "\n")
    (out / "path_respace_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep["summary"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
