#!/usr/bin/env python3
"""LANE ADD (DIE-HBM-16, COORD 10-29 ruling (b)): opt-in die_plan delta that adds plan lanes for as-built crossing
pairs that bind.py reports UNPLANNED.  A plan that is not passed through it is unchanged (new file; no existing tool,
check or default output changes; no new check).

    python3 tools/die_plan/lane_add.py PLANDIR --pairs rows.json --out OUTDIR [--near-um 1200] [--first-id 160]

rows.json = {"rows": [{"src": part, "dst": part, "unplanned_bits": n}, ...]} (HBM-BIND-2 s1_unplanned_lanes.json form).

Per pair (12.13 LOCALITY FIRST: only LOCAL pairs are built; far pairs are listed, never laned):
  ADJ   the two partitions abut: ONE new port on the shared edge (a 2-cycle direct lane: out boundary flop + in
        boundary flop, the same register count bind.py gives an UNPLANNED direct pair today -> no latency change).
  NEAR  not abutting, edge gap <= --near-um: a hop chain through the abutting partitions in between, each crossed
        partition gets a new ft slot.  Template order: (1) an existing lane of the same pair (same partitions, same
        slot station counts and station points, so the new bits have the SAME cycles as the bits of that pair already
        on the plan: one word never splits over two latencies); (2) the reverse lane of the pair, reversed; (3) the
        shortest abutment path (<= --max-hops), stations = ceil(route / ft_station_max_um) per crossed partition.
  FAR   gap > --near-um: not built (report only; 12.13 re-home of the logic instead).
Windows: each hop gets a free interval on the shared edge (off every existing port window of BOTH partitions on that
edge, +guard), sized by schema.window_for at the plan face budget (face_pins_per_um, pin_track_max), on the face's
declared face_layers, nearest the template hop window (else the edge centre).  Type buses / slots are written in each
instance's type frame (orient-aware, die-frame bit order lsb_low on both sides, so the two pin tables coincide).
Latency entries come from schema.Plan.lane_natural (incl. clock_landing), pad 0, param LAT_<ID>.
Writes OUTDIR/die_plan.json + OUTDIR/lane_add_report.json; every other file of PLANDIR is hard-linked.
All numbers are plan arithmetic: UNCHECKED until NUMBER-CHECK (12.9f).
"""
import argparse
import copy
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402

OPP = {"E": "W", "W": "E", "N": "S", "S": "N"}
EPS = 1e-6


def shared_edge(P, a, b, tol=0.5):
    """(die face of a toward b, lo, hi) of the abutting edge, or None."""
    ax0, ay0, ax1, ay1 = P.rect(a)
    bx0, by0, bx1, by1 = P.rect(b)
    lo, hi = max(ay0, by0), min(ay1, by1)
    if hi - lo > tol:
        if abs(ax1 - bx0) < tol:
            return "E", lo, hi
        if abs(bx1 - ax0) < tol:
            return "W", lo, hi
    lo, hi = max(ax0, bx0), min(ax1, bx1)
    if hi - lo > tol:
        if abs(ay1 - by0) < tol:
            return "N", lo, hi
        if abs(by1 - ay0) < tol:
            return "S", lo, hi
    return None


def gap_um(P, a, b):
    ax0, ay0, ax1, ay1 = P.rect(a)
    bx0, by0, bx1, by1 = P.rect(b)
    return max(0.0, bx0 - ax1, ax0 - bx1) + max(0.0, by0 - ay1, ay0 - by1)


def centre(P, a):
    x0, y0, x1, y1 = P.rect(a)
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def face_intervals(P, part, df):
    """die-frame pin intervals of every port of `part` on its die face df."""
    out = []
    for pid, pr in P.ports.items():
        if "face" not in pr or "window_um" not in pr:
            continue
        if pr["src"]["part"] == part and pr["face"] == df:
            pass
        elif pr["dst"]["part"] == part and OPP.get(pr["face"]) == df:
            pass
        else:
            continue
        for _, _, win in S.port_segments(pr):
            out.append(tuple(sorted(win)))
    return out


def free_gaps(lo, hi, occ, guard):
    occ = sorted((a - guard, b + guard) for a, b in occ if b + guard > lo and a - guard < hi)
    gaps, cur = [], lo
    for a, b in occ:
        if a > cur:
            gaps.append((cur, a))
        cur = max(cur, b)
    if hi > cur:
        gaps.append((cur, hi))
    return gaps


def to_type_window(P, part, df, win):
    """die-frame window on die face df -> (type face, type window, flipped)."""
    p = P.parts[part]
    w, h = P.ptype(part)["outline_um"]
    o = p.get("orient", "R0")
    tf = P.type_face(part, df)
    a, b = sorted(win)
    if df in "EW":
        base, ext, flip = p["origin_um"][1], h, o in ("MX", "R180")
    else:
        base, ext, flip = p["origin_um"][0], w, o in ("MY", "R180")
    a, b = a - base, b - base
    if flip:
        a, b = ext - b, ext - a
    return tf, [round(a, 4), round(b, 4)], flip


def face_layers(P, part, df):
    tf = P.type_face(part, df)
    fl = P.ptype(part).get("face_layers", {}).get(tf)
    return list(fl) if fl else (["M6", "M4"] if df in "EW" else ["M7", "M5"])


class Builder:
    def __init__(self, raw, near_um=1200.0, max_hops=4, guard_um=2.0, first_id=160, reject_macro_hits=True,
                 require_cycle_match=True):
        self.raw = raw
        self.near_um, self.max_hops, self.guard = near_um, max_hops, guard_um
        self.next_id = first_id
        self.P = S.Plan(raw)
        self.taken = defaultdict(list)          # (part, die face) -> windows added by this run
        self.report = dict(built=[], far=[], failed=[])
        self.ids = {}
        import reach as R
        layer_reach, _ = R.hop_reach(self.P)
        self.reach = min(float(getattr(self.P, "reach", S.SIGNAL_REACH_UM)),
                         float(self.P.budgets.get("reach_margin", R.MARGIN)) * layer_reach)
        self.smax = min(float(self.P.budgets.get("ft_station_max_um", S.SIGNAL_REACH_UM)), self.reach)
        self.adj = {}
        self._why = None
        self.reject_macro_hits, self.require_cycle_match = reject_macro_hits, require_cycle_match
        cnt = {}
        for p in raw["partitions"]:
            cnt[p["type"]] = cnt.get(p["type"], 0) + 1
        self.shared = {p["name"] for p in raw["partitions"] if cnt[p["type"]] > 1}   # new buses would be unbound
        self.orig_lanes = set(self.P.lanes)      # templates and pair cycles come from the input plan only

    # ---------------------------------------------------------------- geometry helpers
    def neighbours(self, a):
        if a not in self.adj:
            self.adj[a] = [b for b in self.P.parts if b != a and shared_edge(self.P, a, b)]
        return self.adj[a]

    def path(self, a, b):
        """shortest abutment path a..b by centre distance (Dijkstra), <= max_hops ports."""
        import heapq
        dist = {a: 0.0}
        prev = {}
        hq = [(0.0, a, 0)]
        while hq:
            d, u, n = heapq.heappop(hq)
            if u == b:
                break
            if d > dist.get(u, 1e18) + EPS or n >= self.max_hops:
                continue
            for v in self.neighbours(u):
                if v.startswith("PHY") or v == "root" and b != "root":
                    continue
                cu, cv = centre(self.P, u), centre(self.P, v)
                nd = d + abs(cu[0] - cv[0]) + abs(cu[1] - cv[1])
                if nd < dist.get(v, 1e18) - EPS:
                    dist[v], prev[v] = nd, u
                    heapq.heappush(hq, (nd, v, n + 1))
        if b not in prev:
            return None
        out = [b]
        while out[-1] != a:
            out.append(prev[out[-1]])
        return out[::-1]

    def pins_need(self, width, layers):
        per = float(self.P.budgets.get("face_pins_per_um", 6.0)) * len(layers) / float(
            self.P.budgets.get("face_pin_layers", 2))
        return width + 1, per            # + the in-band epoch bit (schema.has_epoch)

    def alloc(self, a, b, width, prefer=None):
        """free die-frame window on the a|b edge for width bits; returns (die face of a, window, layers)."""
        e = shared_edge(self.P, a, b)
        df, lo, hi = e
        layers = face_layers(self.P, a, df)
        if face_layers(self.P, b, OPP[df]) != layers and sorted(face_layers(self.P, b, OPP[df])) == sorted(layers):
            pass
        pins, per = self.pins_need(width, layers)
        occ = face_intervals(self.P, a, df) + face_intervals(self.P, b, OPP[df]) + self.taken[(a, df)]
        tgt = prefer if prefer is not None else (lo + hi) / 2
        best = None
        for g0, g1 in free_gaps(lo + 1.0, hi - 1.0, occ, self.guard):
            L = S.window_for(0.0, pins, layers, self.P.layers, per_um=per,
                             track_max=float(self.P.budgets.get("pin_track_max", 0.6)))
            if g1 - g0 < L + 0.1:
                continue
            # slide the window inside the gap toward the target, on the 0.016 lattice; recheck tracks at the spot
            x = min(max(tgt - L / 2, g0), g1 - L)
            x = round(math.floor(x / 0.016) * 0.016, 4)
            x = max(x, g0)
            hi_w = S.window_for(x, pins, layers, self.P.layers, per_um=per,
                                track_max=float(self.P.budgets.get("pin_track_max", 0.6)))
            if hi_w > g1:
                x = max(g0, round(g1 - (hi_w - x) - 0.016, 4))
                hi_w = S.window_for(x, pins, layers, self.P.layers, per_um=per,
                                    track_max=float(self.P.budgets.get("pin_track_max", 0.6)))
                if hi_w > g1:
                    continue
            cost = abs((x + hi_w) / 2 - tgt)
            if best is None or cost < best[0]:
                best = (cost, [x, hi_w])
        if best is None:
            return None
        win = best[1]
        self.taken[(a, df)].append(tuple(win))
        self.taken[(b, OPP[df])].append(tuple(win))
        return df, win, layers

    # ---------------------------------------------------------------- plan writers
    def add_bus(self, part, name, direction, width, df, win, layers, kind="data"):
        tf, tw, flip = to_type_window(self.P, part, df, win)
        t = self.P.ptype(part)
        if any(b["name"] == name for b in t.get("buses", [])):
            raise ValueError(f"{part}: bus {name} exists")
        t.setdefault("buses", []).append(dict(name=name, dir=direction, width=width, kind=kind, face=tf,
                                              window_um=tw, layers=list(layers),
                                              order="lsb_high" if flip else "lsb_low"))

    def add_slot(self, part, name, width, din, win_in, lay_in, dout, win_out, lay_out, stations, regs_die=None):
        tfi, twi, fi = to_type_window(self.P, part, din, win_in)
        tfo, two, fo = to_type_window(self.P, part, dout, win_out)
        s = dict(name=name, in_face=tfi, out_face=tfo, width=width, stations=int(stations),
                 in_window_um=twi, in_layers=list(lay_in), in_order="lsb_high" if fi else "lsb_low",
                 out_window_um=two, out_layers=list(lay_out), out_order="lsb_high" if fo else "lsb_low")
        if regs_die:
            s["regs_um"] = [[round(v, 4) for v in self.P.to_type(part, r)] for r in regs_die]
        self.P.ptype(part).setdefault("ft_slots", []).append(s)
        return s

    @staticmethod
    def face_pt(P, part, df, win):
        x0, y0, x1, y1 = P.rect(part)
        c = (win[0] + win[1]) / 2
        return {"E": (x1, c), "W": (x0, c), "N": (c, y1), "S": (c, y0)}[df]

    def stations_for(self, part, din, win_in, dout, win_out):
        import check as C
        a = self.face_pt(self.P, part, din, win_in)
        b = self.face_pt(self.P, part, dout, win_out)
        seg = C.zroute(a, b, din, dout)
        L = C.plen(seg)
        k = max(1, math.ceil(L / self.smax - 1e-9))
        return k, seg, L

    def resite(self, chain, slots, start, end):
        """[[die-frame regs] per slot] or None: K = sum(slot stations) FF homes on the 4.32 lattice inside the crossed
        partitions (not in any core/macro + 4.32 halo), every hop <= reach, each partition >= 1 FF and its
        route length / FF count <= ft_station_max (check R3)."""
        import numpy as np
        import station_resite as SR
        P, G, H = self.P, SR.G, SR.HALO
        mids = [sl[0] for sl in slots]
        rects = {p: P.rect(p) for p in mids}
        X0 = min(r[0] for r in rects.values()); Y0 = min(r[1] for r in rects.values())
        X1 = max(r[2] for r in rects.values()); Y1 = max(r[3] for r in rects.values())
        nx, ny = int((X1 - X0) / G) + 2, int((Y1 - Y0) / G) + 2
        xs = X0 + np.arange(nx) * G
        ys = Y0 + np.arange(ny) * G
        free = np.zeros((nx, ny), bool)
        owner = np.full((nx, ny), -1, int)
        for k, p in enumerate(mids):
            x0, y0, x1, y1 = rects[p]
            m = ((xs[:, None] > x0 + H) & (xs[:, None] < x1 - H) & (ys[None, :] > y0 + H) & (ys[None, :] < y1 - H))
            for bx0, by0, bx1, by1 in S.placed_macro_boxes(P.ptype(p), halo=H).values():
                c0, c1 = P.to_die(p, (bx0, by0)), P.to_die(p, (bx1, by1))
                ux0, ux1 = sorted((c0[0], c1[0])); uy0, uy1 = sorted((c0[1], c1[1]))
                m &= ~((xs[:, None] > ux0 - EPS) & (xs[:, None] < ux1 + EPS) & (ys[None, :] > uy0 - EPS)
                       & (ys[None, :] < uy1 + EPS))
            free |= m
            owner[m] = k
        a = (start[0] - X0, start[1] - Y0)
        b = (end[0] - X0, end[1] - Y0)
        K = sum(sl[8] for sl in slots)
        SR.G = G
        regs = SR.route(free, a, b, K, self.reach)
        if regs is None:
            return None
        out = [[] for _ in slots]
        last = 0
        for rx, ry in regs:
            k = int(owner[int(round(rx / G)), int(round(ry / G))])
            if k < last:          # chain order must be monotone through the crossed partitions
                return None
            last = k
            out[k].append((round(rx + X0, 4), round(ry + Y0, 4)))
        for sl, r in zip(slots, out):
            if not r or sl[10] / len(r) > self.smax + EPS:
                return None
        return out

    def macro_hits(self, part, regs_die):
        boxes = S.placed_macro_boxes(self.P.ptype(part))
        n = 0
        for r in regs_die:
            x, y = self.P.to_type(part, r)
            n += any(x0 + EPS < x < x1 - EPS and y0 + EPS < y < y1 - EPS for (x0, y0, x1, y1) in boxes.values())
        return n

    # ---------------------------------------------------------------- templates
    def template(self, a, b):
        """candidate (kind, template lane, partition chain) list, best first: same-pair lanes (fewest ports first),
        reverse lanes reversed, then the shortest abutment path."""
        same, rev = [], []
        for lid in sorted(self.orig_lanes):
            ln = self.P.lanes[lid]
            hp = [self.P.ports[q] for q in ln["ports"]]
            s, d = hp[0]["src"]["part"], hp[-1]["dst"]["part"]
            chain = [hp[0]["src"]["part"]] + [x["dst"]["part"] for x in hp]
            if S.DIE_PART in chain:
                continue
            if (s, d) == (a, b) and len(hp) > 1:
                same.append((len(hp), lid, chain))
            elif (s, d) == (b, a) and len(hp) > 1:
                rev.append((len(hp), lid, chain[::-1]))
        out, seen = [], set()
        for kind, lst in (("same", sorted(same)), ("reverse", sorted(rev))):
            for _, lid, chain in lst:
                if tuple(chain) not in seen:
                    seen.add(tuple(chain))
                    out.append((kind, lid, chain))
        p = self.path(a, b)
        if p and tuple(p) not in seen:
            out.append(("path", None, p))
        return out

    # ---------------------------------------------------------------- build
    def new_id(self, a, b, part=0):
        """NW pairs take L<n>; the NE mirror of an NW pair (same split part) takes the same L<n> + 'm' (plan convention)."""
        ne = a.startswith("NE_") or b.startswith("NE_")
        key = (a.replace("NE_", "NW_"), b.replace("NE_", "NW_"), part)
        if ne and key in self.ids:
            return self.ids.pop(key) + "m"
        lid = f"L{self.next_id}"
        self.next_id += 1
        if not ne:
            self.ids[key] = lid
        return lid

    def build(self, rows):
        P = self.P
        # NW before NE so mirror ids pair up; biggest first inside each half (best windows to the widest lanes)
        rows = sorted(rows, key=lambda r: (r["src"].startswith("NE_") or r["dst"].startswith("NE_"),
                                           -int(r["unplanned_bits"]), r["src"], r["dst"]))
        for r in rows:
            a, b, bits = r["src"], r["dst"], int(r["unplanned_bits"])
            if a not in P.parts or b not in P.parts:
                self.report["failed"].append(dict(r, why="missing partition"))
                continue
            e = shared_edge(P, a, b)
            g = gap_um(P, a, b)
            if e is None and g > self.near_um:
                self.report["far"].append(dict(src=a, dst=b, bits=bits, gap_um=round(g, 1)))
                continue
            cands = [("adj", None, [a, b])] if e is not None else self.template(a, b)
            if not cands:
                self.report["failed"].append(dict(src=a, dst=b, bits=bits, why="no abutment path"))
                continue
            # one lane on the first candidate with room; else split the width over k parallel lanes of the same
            # cycle count (bind.py packs a pair's lanes by width), each on the first candidate with room
            done = None
            saved_raw = copy.deepcopy(self.raw)
            saved_taken = copy.deepcopy(self.taken)
            saved_ids, saved_next = dict(self.ids), self.next_id

            def restore_pair():
                self.raw.clear()
                self.raw.update(copy.deepcopy(saved_raw))
                self.P = S.Plan(self.raw)
                self.taken = copy.deepcopy(saved_taken)
                self.ids, self.next_id = dict(saved_ids), saved_next

            for k in (1, 2, 3, 4):
                restore_pair()
                parts = [bits // k + (1 if i < bits % k else 0) for i in range(k)]
                got = []
                for w in parts:
                    r1 = None
                    for kind, tl, chain in cands:
                        if got and k > 1:
                            # keep the cycles equal over the split: same candidate chain as the first part
                            if chain != got[0]["chain"]:
                                continue
                        r1 = self.build_one(a, b, w, chain, kind, tl, record=False, part=len(got))
                        if r1:
                            break
                    if r1 is None:
                        break
                    got.append(r1)
                if got and len(got) == k:
                    done = got
                    break
            if done is None:
                restore_pair()
                self.report["failed"].append(dict(src=a, dst=b, bits=bits, why=self._why, chains=[c[2] for c in cands]))
                continue
            for r1 in done:
                r1["split"] = len(done)
            self.report["built"].extend(done)

    def build_one(self, a, b, bits, chain, kind, tl, record=True, part=0):
        P = self.P
        # template hop windows / slots (die frame) to stay close to the existing lane
        tw, tslots = {}, {}
        if tl:
            ln = P.lanes[tl]
            hp = [P.ports[q] for q in ln["ports"]]
            if kind == "reverse":
                hp = hp[::-1]
            for x in hp:
                u, v = (x["src"]["part"], x["dst"]["part"])
                if kind == "reverse":
                    u, v = v, u
                tw[(u, v)] = (x["window_um"][0] + x["window_um"][1]) / 2
            for part, slot, _, _ in P.lane_crossings(tl):
                tslots[part] = P.slot(part, slot) if slot else None
        hops = []
        if set(chain) & self.shared:
            self._why = f"type shared by several partitions on the chain {sorted(set(chain) & self.shared)}"
            if record:
                self.report["failed"].append(dict(src=a, dst=b, bits=bits, why=self._why, chain=chain))
            return None

        def rollback(why):
            self._why = why
            if record:
                self.report["failed"].append(dict(src=a, dst=b, bits=bits, why=why, chain=chain))
            for (uu, vv, (df, win, _)) in hops:
                self.taken[(uu, df)].remove(tuple(win))
                self.taken[(vv, OPP[df])].remove(tuple(win))
            return None
        prev = None
        for u, v in zip(chain, chain[1:]):
            # straight-through chains keep the previous hop's coordinate (no Z jog inside the crossed partition)
            pref = tw.get((u, v))
            if pref is None and prev is not None and (prev[0] in "EW") == (shared_edge(P, u, v)[0] in "EW"):
                pref = (prev[1][0] + prev[1][1]) / 2
            got = self.alloc(u, v, bits, prefer=pref)
            if got is None:
                return rollback(f"no free window {u}|{v}")
            hops.append((u, v, got))
            prev = got
        n = len(hops)
        slots, hits = [], 0
        import check as C
        for i in range(1, n):
            part = chain[i]
            _, _, (dfi, wi, li) = hops[i - 1]
            _, _, (dfo, wo, lo_) = hops[i]
            k, seg, L = self.stations_for(part, OPP[dfi], wi, dfo, wo)
            regs = None
            ts = tslots.get(part)
            if ts:
                k = max(k, int(ts.get("stations", 1)))
                if ts.get("regs_um") and int(ts.get("stations", 1)) == k:
                    regs = [P.to_die(part, tuple(r)) for r in ts["regs_um"]]
                    if kind == "reverse":
                        regs = regs[::-1]
            even = [C.point_at(seg, L * j / k) for j in range(k)]
            slots.append([part, i, dfi, wi, li, dfo, wo, lo_, k, regs if regs is not None else even, L, 0, even])
        # check.check_hops: Manhattan register-to-register hops (src face, stations..., dst face) <= reach.  Template
        # stations sit on the template's own windows; if they break reach on ours, re-site them evenly on our route.
        start = self.face_pt(P, a, hops[0][2][0], hops[0][2][1])
        end = self.face_pt(P, b, OPP[hops[-1][2][0]], hops[-1][2][1])

        def worst_hop():
            pts = [start] + [r for sl in slots for r in sl[9]] + [end]
            return max([abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])] or [0.0])
        if worst_hop() > self.reach + EPS:
            for sl in slots:
                sl[9] = sl[12]
        if slots and (worst_hop() > self.reach + EPS or any(self.macro_hits(sl[0], sl[9]) for sl in slots)):
            # exact-count Manhattan solver over the chain's crossed partitions, FF homes off every core/macro + halo
            # (station_resite.route); the lane's TOTAL station count is kept, per-partition counts follow the solve
            got = self.resite(chain, slots, start, end)
            if got is None:
                return rollback(f"no macro-free station chain with {sum(sl[8] for sl in slots)} stations "
                                f"(hop<= {self.reach:.0f})")
            for sl, regs in zip(slots, got):
                sl[8], sl[9] = len(regs), regs
        if worst_hop() > self.reach + EPS:
            return rollback(f"hop {worst_hop():.0f} um > reach {self.reach:.0f} with template station counts")
        for sl in slots:
            sl[11] = self.macro_hits(sl[0], sl[9])
            hits += sl[11]
        if hits and self.reject_macro_hits:
            return rollback(f"{hits} station points inside macros")
        st = sum(x[8] for x in slots)
        cyc = 2 + st
        pair_cyc = sorted({int(self.raw["latency"]["lanes"].get(l2, {}).get("cycles", -1))
                           for l2 in self.orig_lanes
                           if P.ports[P.lanes[l2]["ports"][0]]["src"]["part"] == a
                           and P.ports[P.lanes[l2]["ports"][-1]]["dst"]["part"] == b})
        if self.require_cycle_match and pair_cyc and cyc not in pair_cyc:
            return rollback(f"cycles {cyc} not in the pair's existing lane cycles {pair_cyc}")
        lid = self.new_id(a, b, part)
        ports, xs = [], []
        for i, (u, v, (df, win, layers)) in enumerate(hops):
            ob = f"{lid}_o" if i == 0 else f"{lid}x{i}_o"
            ib = f"{lid}_i" if i == n - 1 else f"{lid}x{i + 1}_i"
            ports.append(dict(id=f"{lid}_{i}", src=dict(part=u, bus=ob), dst=dict(part=v, bus=ib), width=bits,
                              kind="data"))
        self.add_bus(a, f"{lid}_o", "out", bits, hops[0][2][0], hops[0][2][1], hops[0][2][2])
        self.add_bus(b, f"{lid}_i", "in", bits, OPP[hops[-1][2][0]], hops[-1][2][1], hops[-1][2][2])
        for part, i, dfi, wi, li, dfo, wo, lo_, k, regs, L, h, _ in slots:
            self.add_slot(part, f"{lid}x{i}", bits, OPP[dfi], wi, li, dfo, wo, lo_, k, regs_die=regs)
            xs.append(dict(part=part, slot=f"{lid}x{i}", stations=k, route_um=round(L, 1), macro_hits=h))
        self.raw["ports"].extend(ports)
        self.raw["lanes"].append(dict(id=lid, ports=[p["id"] for p in ports],
                                      note=f"DIE-HBM-16 lane_add {kind}"
                                           + (f" (template {tl})" if tl else "") + f": {a}->{b} {bits} b S1"))
        # refresh the Plan view so later lanes see these ports
        self.P = S.Plan(self.raw)
        P = self.P
        nat = P.lane_natural(lid)
        ent = dict(nat, natural=nat["cycles"], pad=0, param="LAT_" + lid.upper())
        self.raw.setdefault("latency", {}).setdefault("lanes", {})[lid] = ent
        return dict(lane=lid, src=a, dst=b, bits=bits, kind=kind, template=tl, chain=chain,
                    windows=[dict(edge=f"{u}|{v}", face=df, window_um=win, layers=lay) for u, v, (df, win, lay) in hops],
                    crossings=xs, cycles=nat["cycles"], stations=nat["stations"],
                    clock_landing=nat.get("clock_landing", 0), existing_pair_cycles=pair_cyc,
                    cycles_match_pair=(not pair_cyc) or nat["cycles"] in pair_cyc, macro_hits=hits)


def sha12(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()[:12]


def run(plan_dir, pairs, out, near_um=1200.0, first_id=160, max_hops=4, guard_um=2.0, select=None):
    plan_dir, out = Path(plan_dir), Path(out)
    raw = json.loads((plan_dir / "die_plan.json").read_text())
    rows = json.loads(Path(pairs).read_text())
    rows = rows["rows"] if isinstance(rows, dict) else rows
    if select:
        rows = [r for r in rows if select(r)]
    B = Builder(raw, near_um=near_um, max_hops=max_hops, guard_um=guard_um, first_id=first_id)
    B.build(rows)
    out.mkdir(parents=True, exist_ok=True)
    for f in plan_dir.iterdir():
        dst = out / f.name
        if f.name in ("die_plan.json", "lane_add_report.json") or dst.exists():
            continue
        try:
            os.link(f, dst) if f.is_file() else os.symlink(f.resolve(), dst)
        except OSError:
            if f.is_file():
                import shutil
                shutil.copy2(f, dst)
    raw.setdefault("die", {})["label"] = ("C25c_lanes = + DIE-HBM-16 lane_add (" +
                                         f"{len(B.report['built'])} S1 lanes) | " + raw["die"].get("label", ""))
    (out / "die_plan.json").write_text(json.dumps(raw, indent=1))
    rep = dict(schema="die_plan.lane_add.v1", base=str(plan_dir), base_sha=sha12(plan_dir / "die_plan.json"),
               out_sha=sha12(out / "die_plan.json"), near_um=near_um,
               totals=dict(built=len(B.report["built"]), built_bits=sum(x["bits"] for x in B.report["built"]),
                           far=len(B.report["far"]), far_bits=sum(x["bits"] for x in B.report["far"]),
                           failed=len(B.report["failed"]),
                           by_kind={k: sum(1 for x in B.report["built"] if x["kind"] == k)
                                    for k in ("adj", "same", "reverse", "path")},
                           cycle_mismatch=sum(1 for x in B.report["built"] if not x["cycles_match_pair"]),
                           macro_hits=sum(x["macro_hits"] for x in B.report["built"])),
               **B.report)
    (out / "lane_add_report.json").write_text(json.dumps(rep, indent=1))
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--near-um", type=float, default=1200.0)
    ap.add_argument("--first-id", type=int, default=160)
    ap.add_argument("--max-hops", type=int, default=4)
    ap.add_argument("--guard-um", type=float, default=2.0)
    a = ap.parse_args(argv)
    rep = run(a.plan, a.pairs, a.out, a.near_um, a.first_id, a.max_hops, a.guard_um)
    print(json.dumps(rep["totals"]))
    for x in rep["failed"]:
        print("FAILED", json.dumps(x))
    return 0


if __name__ == "__main__":
    sys.exit(main())
