#!/usr/bin/env python3
"""CORE-PLACE-1 (COORD 11-11): connectivity-driven placement of the hard cores INSIDE a partition type.

    core_place.py PLAN --types T1,T2 --out-plan NEW.json --event EVENT.json [--die NAME] [--repo ROOT]
                  [--ref-dirs d1 d2] [--seed SEED.json] [--gap 34.56] [--sweeps 12] [--lam 4] [--reach 360]
                  [--grt-halving full|none] [--views-dir DIR] [--family] [--no-search]

Die-agnostic successor of DIE-HBM-97 HBM-HUB "B34" (epyc7 die-hbm-97-hubrf/ls_refloor.py + apply_rf.py).
ADVISORY plan event: only hard-core origin_um / orient change (plus the coordinates that ride on a core: clock taps,
clock entry footprints, station end points, contents boxes that equal their cores' bbox), so the logic is unchanged
and EQ holds by construction; the EQ gate below checks that mechanically.

MOVE UNITS: clusters of hard cores closer than 4.32 um (abutted groups move rigidly).  Moves: relocate toward the
bit-weighted median of the partners (4.32 lattice), swap two clusters (centre-aligned), flip a single-core cluster
(R0/MY/MX/R180; pins are never moved: a signed view keeps its pin faces, only its orientation changes).  A --seed
JSON {inst: {origin_um, orient}} (hand design) is legalised first, then improved by the same search.

OBJECTIVE = bit-um + lam_H x OVF_H + lam_V x OVF_V
  bit-um   sum over links of bits x Manhattan between the pin-group centroids: core_conns (core pins -> partner
           core's mate bus / type bus window / face; a link listed at both ends counts half each, as route_supply)
           and internal_stations (from -> to, end points on a core follow it).  ft slots are fixed.
  OVF_d    RUDY overflow (track-um) of direction d on a 21.6 um grid: demand = links + stations + ft hops (RUDY),
           supply = route_supply's per-layer tracks (measured pitch and GRT derate, macro OBS from the view
           route_supply picks, stock GRT transition halving with --grt-halving full), pooled over the 97.2 um detour
           window across the direction (route_supply's anisotropic window); cell-wiring background 0.25 off macro.
  lam_d    lam x (1 + macro-interior shortage of d) = lam x (1 + max(0, p99(base ratio_d over core bins) - 1)):
           the direction a type is short of over its macros (H over M1-M5 cores: only a halved M6) weighs more.
CONSTRAINTS (hard; B34 + CORE-PLACE-1):
  outline: >= 4.32 from the outline, and a pin face toward the outline keeps the pin channel need;
  gap between clusters >= --gap; between FACING faces (overlapping projection) >= max(gap, need(pins on both
           faces)), need = pins x 0.048 / (4 x 0.7) um (slot_channel_event channel model): no pin face abuts a
           blocked face and every channel carries its pins;
  fixed points never under a core (+4.32 halo): ft regs + bit sites, type clock tap, reset tap, edge clocks,
           added / glue clock taps (clock tap free); fixed rects never under a core: reserved channels, landing
           bands (rings);
  die_ft_bands: total core overlap of each band never grows;
  timing: every station keeps its register count (Manhattan from->to <= (regs+1) x reach x 0.95 unless the base was
           already longer) and every direct link stays <= max(base, 405 um) long.
STATIONS: after the search every station with a moved end is re-routed with hub_repack.route_station (registers in
  free street area, hop <= reach, old register count kept); a station that would need more registers is reported
  (latency change -> not EQ) and the move that caused it is undone.
REPORT (event JSON + TSV): per type before/after bit-um, RUDY overflow H/V, route_supply p99 (region worst / core_H /
  core_V / street), worst cut H/V (bits crossing a full cut line / tracks on it), moves, channel deficits left.
  --svg DIR writes the floorplan view (outline, face windows, ft slots, die bands, clock tap, cores with pin
  groups per face, flylines by bits, station reach circles, per-cut bits vs tracks).
"""
import argparse
import ast
import collections
import copy
import gzip
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import route_supply as RS  # noqa: E402

SCHEMA = "opentallas.core_place.v1"
G = 4.32
EPS = 1e-6
FLIP = {"R0": (0, 0), "MY": (1, 0), "MX": (0, 1), "R180": (1, 1)}
INV = {v: k for k, v in FLIP.items()}
OPP = dict(N="S", S="N", E="W", W="E")
PIN_UM = 0.048 / (4 * 0.7)          # channel need per pin (slot_channel_event TS1 model, 4 layers at 0.7)
DIRECT_REACH = 405.0                 # 12.1e plan reach per registered hop


def comp(a, b):
    fa, fb = FLIP[a], FLIP[b]
    return INV[(fa[0] ^ fb[0], fa[1] ^ fb[1])]


def xf(o, w, h, u, v):
    if o in ("MY", "R180"):
        u = w - u
    if o in ("MX", "R180"):
        v = h - v
    return u, v


def snap(v):
    return round(round(v / G) * G, 4)


def read_any(p):
    p = Path(p)
    if p.suffix == ".gz":
        with gzip.open(p, "rt") as f:
            return json.load(f)
    return json.loads(p.read_text())


# ------------------------------------------------------------------------------------------------ type model
class TypeModel:
    def __init__(self, name, t, die_dir, repo, conns, cfg):
        self.name, self.t, self.cfg = name, t, cfg
        self.W, self.H = map(float, t["outline_um"])
        HC = t.get("hard_cores") or []
        self.C = HC
        n = self.n = len(HC)
        self.dim = np.array([h["outline_um"] for h in HC], float).reshape(n, 2)
        self.org0 = np.array([h["origin_um"] for h in HC], float).reshape(n, 2)
        self.ori0 = [h.get("orient", "R0") for h in HC]
        self.fixed = [o not in FLIP for o in self.ori0]
        self.inst = [h["inst"] for h in HC]
        self.idx = {k: i for i, k in enumerate(self.inst)}
        # ---- views -> per-core supply (tracks per bin when the bin is fully covered)
        self.obs = []
        self.kind = []
        for h in HC:
            o, kind, src, _ = RS.macro_view(h, die_dir, repo, cfg["rs"])
            self.obs.append(o)
            self.kind.append(kind)
        # ---- local pins: bus -> [count, sum u, sum v]; face counts in the local frame
        self.lpins = []
        self.lface = []
        for i, h in enumerate(HC):
            pl = RS.core_pins(h, die_dir, repo)        # type frame, orient applied
            acc = collections.defaultdict(lambda: [0, 0.0, 0.0])
            fc = collections.Counter()
            w, hh = self.dim[i]
            for bus, x, y in pl:
                u, v = xf(self.ori0[i], w, hh, x - self.org0[i, 0], y - self.org0[i, 1])
                a = acc[bus]
                a[0] += 1
                a[1] += u
                a[2] += v
                if "clk" in bus or bus.startswith("strap_"):
                    continue
                f = min([(u, "W"), (w - u, "E"), (v, "S"), (hh - v, "N")])[1]
                fc[f] += 1
            self.lpins.append({b: (c, su / c, sv / c) for b, (c, su, sv) in acc.items()})
            self.lface.append(fc)
        self._links(conns)
        self._fixed_geometry()
        self._clusters()

    # ---------------------------------------------------------------- links
    def owner(self, p, tol=0.6):
        for i in range(self.n):
            x0, y0 = self.org0[i]
            w, h = self.dim[i]
            if x0 - tol <= p[0] <= x0 + w + tol and y0 - tol <= p[1] <= y0 + h + tol:
                return i
        return None

    def to_local(self, i, p):
        u, v = p[0] - self.org0[i, 0], p[1] - self.org0[i, 1]
        return xf(self.ori0[i], self.dim[i, 0], self.dim[i, 1], u, v)

    def end(self, p):
        i = self.owner(p)
        return (i, self.to_local(i, p)) if i is not None else (None, (float(p[0]), float(p[1])))

    def _links(self, conns):
        t, W, H = self.t, self.W, self.H
        bus_pt = {}
        for bu in t.get("buses", []) or []:
            if bu.get("face"):
                bus_pt[bu["name"]] = RS.face_point(W, H, bu["face"], bu.get("window_um"))
        name = self.name
        cc_key = next((k for k in (name, re.sub(r"__cl[0-9a-f]{8}.*$", "", name), re.sub(r"__.*$", "", name))
                       if conns.get(k)), None)
        cc = conns.get(cc_key) if cc_key else None
        self.model = "core_conns" if cc else "none"
        st_pairs = set()
        for s_ in t.get("internal_stations", []) or []:
            la = str(s_.get("launch", ""))
            if la.startswith("core:"):
                A, _, bus_ = la[5:].rpartition(".")
                st_pairs.add((A, bus_, str(s_.get("capture", ""))))
                st_pairs.add((A, bus_, str(s_.get("capture", "")).rsplit(".", 1)[0]))
        L = []   # (endA, endB, bits, kind, max_len)
        if cc:
            for inst, ports in cc.items():
                if inst not in self.idx:
                    continue
                i = self.idx[inst]
                for bus, dl in (ports or {}).items():
                    pg = self.lpins[i].get(bus)
                    if not pg or not dl:
                        continue
                    bits, u, v = pg
                    for d in dl:
                        k, _, val = str(d).partition(":")
                        if k == "core":
                            if val not in self.idx and val.rpartition(".")[0] in self.idx:
                                val = val.rpartition(".")[0]
                            if val not in self.idx or (inst, bus, val) in st_pairs:
                                continue
                            j = self.idx[val]
                            mate = [bb for bb, dd in (cc.get(val, {}) or {}).items() if RS._names_core(dd, inst)]
                            if mate and mate[0] in self.lpins[j]:
                                _, mu, mv = self.lpins[j][mate[0]]
                            else:
                                mu, mv = self.dim[j, 0] / 2, self.dim[j, 1] / 2
                            w_ = 0.5 if mate else 1.0
                            L.append(((i, (u, v)), (j, (mu, mv)), bits * w_, "core"))
                        elif k == "bus" and val in bus_pt:
                            L.append(((i, (u, v)), (None, bus_pt[val]), bits, "bus"))
                        elif k == "face" and val in "NSEW":
                            L.append(((i, (u, v)), (None, RS.face_point(W, H, val)), bits, "face"))
        self.stations = []
        for si, s in enumerate(t.get("internal_stations", []) or []):
            a, b = self.end(s["from_um"]), self.end(s["to_um"])
            nreg = len(s.get("regs_um") or [])
            L.append((a, b, float(s.get("bits", 1)), "station"))
            self.stations.append((si, len(L) - 1, nreg))
        self.L = L
        self.inc = collections.defaultdict(list)
        for q, (a, b, w, kind) in enumerate(L):
            for e in (a, b):
                if e[0] is not None:
                    self.inc[e[0]].append(q)
        # static demand nets: ft slot hops (fixed)
        self.static = []
        for f in t.get("ft_slots", []) or []:
            wbits = int(f.get("width", 1))
            regs = [tuple(r[:2]) for r in (f.get("regs_um") or [])]
            sites = f.get("bit_sites_um") or []
            pts = []
            if sites and isinstance(sites[0], list) and sites[0] and isinstance(sites[0][0], list):
                for s in sites:
                    pts.append((sum(p[0] for p in s) / len(s), sum(p[1] for p in s) / len(s)))
            elif regs:
                pts = regs
            a = RS.face_point(W, H, f.get("in_face", "W"), f.get("in_window_um"))
            b = RS.face_point(W, H, f.get("out_face", "E"), f.get("out_window_um"))
            chain = [a] + pts + [b]
            for p, q in zip(chain, chain[1:]):
                self.static.append((p, q, wbits))

    # ---------------------------------------------------------------- fixed geometry / constraints
    def _fixed_geometry(self):
        t = self.t
        fp = []
        for f in t.get("ft_slots", []) or []:
            for r in f.get("regs_um") or []:
                fp.append(r[:2])
            for s in f.get("bit_sites_um") or []:
                if s and isinstance(s[0], list):
                    fp.extend(p[:2] for p in s)
                elif s and isinstance(s[0], (int, float)):
                    fp.append(s[:2])
        nft = len(fp)
        ck = t.get("clock") or {}
        for key in ("tap_um",):
            if isinstance(ck.get(key), list) and len(ck[key]) >= 2:
                fp.append(ck[key][:2])
        for e in ck.get("edge_clocks") or []:
            if isinstance(e, dict) and isinstance(e.get("tap_um"), list):
                fp.append(e["tap_um"][:2])
        for tp in (ck.get("taps") or []) + (ck.get("added_taps") or []):
            if isinstance(tp, dict) and tp.get("xy") and tp.get("kind") != "core":
                if self.owner(tp["xy"]) is None:
                    fp.append(tp["xy"][:2])
        rs = t.get("reset") or {}
        if isinstance(rs.get("tap_um"), list):
            fp.append(rs["tap_um"][:2])
        # a point already inside a core rides on it; clock / reset points keep schema.TAP_CLEAR_UM (8.64) off cores
        hal = [G if k < nft else 8.65 for k in range(len(fp))]
        keep = [k for k, p in enumerate(fp) if self.owner(p, tol=-0.01) is None]
        self.FP = np.array([fp[k][:2] for k in keep], float).reshape(-1, 2)
        self.FPH = np.array([hal[k] for k in keep], float)
        rects = [c["rect_um"] for c in t.get("channels") or [] if c.get("rect_um")]
        for bn, bd in (((ck.get("landing_contract") or {}).get("bands")) or {}).items():
            if isinstance(bd, dict) and bd.get("rect_um"):
                rects.append(bd["rect_um"])
        self.FR = rects
        self.bands = []
        for b in t.get("die_ft_bands") or []:
            sp = b.get("span_um")
            if sp and b.get("dir") in ("EW", "NS"):
                self.bands.append((b["dir"], float(sp[0]), float(sp[1])))

    def band_overlap(self, x, y, w, h):
        out = []
        for d, lo, hi in self.bands:
            if d == "EW":
                out.append(max(0.0, min(y + h, hi) - max(y, lo)) * w)
            else:
                out.append(max(0.0, min(x + w, hi) - max(x, lo)) * h)
        return np.array(out)

    def _clusters(self):
        n = self.n
        par = list(range(n))

        def f(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a
        R = [(self.org0[i, 0], self.org0[i, 1], self.org0[i, 0] + self.dim[i, 0], self.org0[i, 1] + self.dim[i, 1])
             for i in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                a, b = R[i], R[j]
                if max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3]) < G - EPS:
                    par[f(i)] = f(j)
        cl = collections.defaultdict(list)
        for i in range(n):
            cl[f(i)].append(i)
        self.CL = list(cl.values())
        m = self.m = len(self.CL)
        self.cid = {i: k for k, g in enumerate(self.CL) for i in g}
        cbb = []
        for g in self.CL:
            x0 = min(R[i][0] for i in g); y0 = min(R[i][1] for i in g)
            x1 = max(R[i][2] for i in g); y1 = max(R[i][3] for i in g)
            cbb.append([x0, y0, x1 - x0, y1 - y0])
        self.cbb = np.array(cbb).reshape(m, 4)
        self.coff = {i: (self.org0[i, 0] - self.cbb[self.cid[i], 0], self.org0[i, 1] - self.cbb[self.cid[i], 1])
                     for i in range(n)}
        self.cfix = [any(self.fixed[i] for i in g) or self.cfg["fixed_re"] and
                     any(re.search(self.cfg["fixed_re"], self.inst[i]) for i in g) for g in self.CL]
        # pin counts per cluster face (member faces on the cluster bbox boundary), per flip state
        self.cface = []
        for k, g in enumerate(self.CL):
            st = {}
            for fl in FLIP:
                c = collections.Counter()
                for i in g:
                    o = comp(self.ori0[i], fl)
                    for lf, cnt in self.lface[i].items():
                        f = lf
                        if o in ("MX", "R180") and f in "NS":
                            f = OPP[f]
                        if o in ("MY", "R180") and f in "EW":
                            f = OPP[f]
                        ox, oy = self.moff(i, fl)
                        w, h = self.dim[i]
                        cw, ch = self.cbb[k, 2], self.cbb[k, 3]
                        on = {"W": ox < G, "E": ox + w > cw - G, "S": oy < G, "N": oy + h > ch - G}[f]
                        if on:
                            c[f] += cnt
                st[fl] = c
            self.cface.append(st)
        # face clearance rules (--face-clear FACE:UM:REGEX on inst or module): cluster -> {face: um}
        self.cclr = []
        for g in self.CL:
            d = {}
            for face, um, rx in self.cfg.get("face_clear") or []:
                if any(re.search(rx, self.inst[i]) or re.search(rx, self.C[i].get("module", "")) for i in g):
                    d[face] = max(d.get(face, 0.0), um)
            self.cclr.append(d)
        self.reset_state()

    def reset_state(self):
        self.cpos = self.cbb[:, :2].copy()
        self.cflip = ["R0"] * self.m

    # ---------------------------------------------------------------- geometry of the current state
    def core_orient(self, i):
        k = self.cid[i]
        return comp(self.ori0[i], self.cflip[k])

    def moff(self, i, fl):
        """member offset inside its cluster bbox after mirroring the whole cluster by fl."""
        k = self.cid[i]
        ox, oy = self.coff[i]
        if fl in ("MY", "R180"):
            ox = self.cbb[k, 2] - ox - self.dim[i, 0]
        if fl in ("MX", "R180"):
            oy = self.cbb[k, 3] - oy - self.dim[i, 1]
        return ox, oy

    def core_origin(self, i):
        k = self.cid[i]
        ox, oy = self.moff(i, self.cflip[k])
        return (self.cpos[k, 0] + ox, self.cpos[k, 1] + oy)

    def pt(self, e):
        i, d = e
        if i is None:
            return d
        o = self.core_orient(i)
        w, h = self.dim[i]
        u, v = xf(o, w, h, d[0], d[1])
        x0, y0 = self.core_origin(i)
        return (x0 + u, y0 + v)

    def llen(self, q):
        a, b, w, kind = self.L[q]
        pa, pb = self.pt(a), self.pt(b)
        return abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])

    def cost(self, Q):
        return sum(self.L[q][2] * self.llen(q) for q in Q)

    def faces(self, k):
        st = self.cface[k]
        return st[self.cflip[k]] if self.cflip[k] in st else st["R0"]

    def need(self, pins):
        return pins * PIN_UM

    def req_gap(self, gap, pa, pb):
        """facing-face gap: --gap-pinface HI:LO:PINS (R3, COORD 11-11: no side pins facing a neighbour within 40 um)
        = HI when either facing face carries more than PINS pins, else LO; without it the uniform --gap."""
        pf = self.cfg.get("gap_pinface")
        if pf:
            return max(pf[0] if max(pa, pb) > pf[2] else pf[1], self.need(pa + pb))
        return max(gap, self.need(pa + pb))

    def diag_gap(self, gap):
        pf = self.cfg.get("gap_pinface")
        return pf[1] if pf else gap

    def legal(self, k, x, y, ignore=(), fl=None):
        if self.cfix[k]:
            return False
        W, H = self.W, self.H
        w, h = self.cbb[k, 2], self.cbb[k, 3]
        fc = self.cface[k].get(fl or self.cflip[k], self.cface[k]["R0"])
        if x < max(G, self.need(fc["W"])) - EPS or y < max(G, self.need(fc["S"])) - EPS or \
                x + w > W - max(G, self.need(fc["E"])) + EPS or y + h > H - max(G, self.need(fc["N"])) + EPS:
            return False
        cl = self.cclr[k]
        if cl and (x < cl.get("W", 0) - EPS or y < cl.get("S", 0) - EPS or x + w > W - cl.get("E", 0) + EPS or
                   y + h > H - cl.get("N", 0) + EPS):
            return False
        gap = self.cfg["gap"]
        for j in range(self.m):
            if j == k or j in ignore:
                continue
            X0, Y0 = self.cpos[j]
            X1, Y1 = X0 + self.cbb[j, 2], Y0 + self.cbb[j, 3]
            gx = max(X0 - (x + w), x - X1)
            gy = max(Y0 - (y + h), y - Y1)
            fj = self.faces(j)
            # facing pairs: projections overlap on the other axis
            if gy < -EPS:      # side by side in x
                if X0 >= x + w - EPS:
                    req = self.req_gap(gap, fc["E"], fj["W"])
                else:
                    req = self.req_gap(gap, fc["W"], fj["E"])
                if gx < req - EPS:
                    return False
            elif gx < -EPS:    # stacked in y
                if Y0 >= y + h - EPS:
                    req = self.req_gap(gap, fc["N"], fj["S"])
                else:
                    req = self.req_gap(gap, fc["S"], fj["N"])
                if gy < req - EPS:
                    return False
            elif max(gx, gy) < self.diag_gap(gap) - EPS:
                return False
        if len(self.FP):
            F, Hh = self.FP, self.FPH
            if ((F[:, 0] > x - Hh) & (F[:, 0] < x + w + Hh) & (F[:, 1] > y - Hh) & (F[:, 1] < y + h + Hh)).any():
                return False
        for r in self.FR:
            if not (r[2] <= x or r[0] >= x + w or r[3] <= y or r[1] >= y + h):
                return False
        if self.bands:
            cur = self.band_now - self._band_k(k) + self._band_at(k, x, y)
            if (cur > self.band_base + 1.0).any():
                return False
        return True

    def why(self, k, x, y, ignore=(), fl=None):
        """legal() with the first broken rule as text ('' = legal)."""
        if self.cfix[k]:
            return 'rule1 %s' % (locals().get('j', ''),)
        W, H = self.W, self.H
        w, h = self.cbb[k, 2], self.cbb[k, 3]
        fc = self.cface[k].get(fl or self.cflip[k], self.cface[k]["R0"])
        if x < max(G, self.need(fc["W"])) - EPS or y < max(G, self.need(fc["S"])) - EPS or \
                x + w > W - max(G, self.need(fc["E"])) + EPS or y + h > H - max(G, self.need(fc["N"])) + EPS:
            return 'rule2 %s' % (locals().get('j', ''),)
        cl = self.cclr[k]
        if cl and (x < cl.get("W", 0) - EPS or y < cl.get("S", 0) - EPS or x + w > W - cl.get("E", 0) + EPS or
                   y + h > H - cl.get("N", 0) + EPS):
            return 'rule3 %s' % (locals().get('j', ''),)
        gap = self.cfg["gap"]
        for j in range(self.m):
            if j == k or j in ignore:
                continue
            X0, Y0 = self.cpos[j]
            X1, Y1 = X0 + self.cbb[j, 2], Y0 + self.cbb[j, 3]
            gx = max(X0 - (x + w), x - X1)
            gy = max(Y0 - (y + h), y - Y1)
            fj = self.faces(j)
            # facing pairs: projections overlap on the other axis
            if gy < -EPS:      # side by side in x
                if X0 >= x + w - EPS:
                    req = self.req_gap(gap, fc["E"], fj["W"])
                else:
                    req = self.req_gap(gap, fc["W"], fj["E"])
                if gx < req - EPS:
                    return 'rule4 %s' % (locals().get('j', ''),)
            elif gx < -EPS:    # stacked in y
                if Y0 >= y + h - EPS:
                    req = self.req_gap(gap, fc["N"], fj["S"])
                else:
                    req = self.req_gap(gap, fc["S"], fj["N"])
                if gy < req - EPS:
                    return 'rule5 %s' % (locals().get('j', ''),)
            elif max(gx, gy) < self.diag_gap(gap) - EPS:
                return 'rule6 %s' % (locals().get('j', ''),)
        if len(self.FP):
            F, Hh = self.FP, self.FPH
            if ((F[:, 0] > x - Hh) & (F[:, 0] < x + w + Hh) & (F[:, 1] > y - Hh) & (F[:, 1] < y + h + Hh)).any():
                return 'rule7 %s' % (locals().get('j', ''),)
        for r in self.FR:
            if not (r[2] <= x or r[0] >= x + w or r[3] <= y or r[1] >= y + h):
                return 'rule8 %s' % (locals().get('j', ''),)
        if self.bands:
            cur = self.band_now - self._band_k(k) + self._band_at(k, x, y)
            if (cur > self.band_base + 1.0).any():
                return 'rule9 %s' % (locals().get('j', ''),)
        return ''

    def _band_k(self, k):
        return self._band_at(k, self.cpos[k, 0], self.cpos[k, 1])

    def _band_at(self, k, x, y):
        s = np.zeros(len(self.bands))
        for i in self.CL[k]:
            ox, oy = self.moff(i, self.cflip[k])
            s += self.band_overlap(x + ox, y + oy, self.dim[i, 0], self.dim[i, 1])
        return s

    def timing_ok(self, Q):
        for q in Q:
            a, b, w, kind = self.L[q]
            ln = self.llen(q)
            lim = self.maxlen[q]
            if ln > lim + EPS:
                return False
        return True

    def tviol(self, Q):
        return sum(1 for q in Q if self.llen(q) > self.maxlen[q] + EPS)

    def init_limits(self):
        reach = self.cfg["reach"]
        self.maxlen = []
        st = {q: nreg for (_, q, nreg) in self.stations}
        for q in range(len(self.L)):
            b0 = self.llen(q)
            if q in st:
                lim = (st[q] + 1) * reach * 0.8
            else:
                lim = DIRECT_REACH
            self.maxlen.append(max(lim, b0))
        self.band_base = np.zeros(len(self.bands))
        for k in range(self.m):
            self.band_base += self._band_k(k)
        self.band_now = self.band_base.copy()

    def clear_viol(self):
        """clusters breaking their --face-clear rule (inst of the first member)."""
        out = []
        for k in range(self.m):
            cl = self.cclr[k]
            if not cl:
                continue
            (x, y), w, h = self.cpos[k], self.cbb[k, 2], self.cbb[k, 3]
            if x < cl.get("W", 0) - EPS or y < cl.get("S", 0) - EPS or x + w > self.W - cl.get("E", 0) + EPS or \
                    y + h > self.H - cl.get("N", 0) + EPS:
                out.append(self.inst[self.CL[k][0]])
        return out

    def violations(self):
        """per cluster, the hard rules the current state breaks (for a seed / the base)."""
        out = {}
        for k in range(self.m):
            if self.cfix[k]:
                continue
            x, y = self.cpos[k]
            if not self.legal(k, x, y):
                out[k] = "geometry"
        if not self.timing_ok(range(len(self.L))):
            out[-1] = "timing"
        return out


# ------------------------------------------------------------------------------------------------ congestion grid
class Grid:
    def __init__(self, M, cfg):
        self.M, self.cfg = M, cfg
        b = self.b = cfg["grid_um"]
        self.nx, self.ny = max(1, int(math.ceil(M.W / b))), max(1, int(math.ceil(M.H / b)))
        der = cfg["rs"]["derate"]
        tr = {L: b / RS.PITCH[L] * (1 - der[L]) for L in RS.LAYERS}
        fill = cfg["rs"]["cell_fill"]
        self.sH0 = (tr["M2"] + tr["M4"]) * (1 - fill) + tr["M6"]
        self.sV0 = (tr["M3"] + tr["M5"]) * (1 - fill) + tr["M7"]
        halve = 1.0 if cfg["grt_halving"] == "full" else 0.0
        self.sH, self.sV = [], []
        for o in M.obs:
            ob = {L: min(1.0, float(o.get(L, 0.0))) for L in RS.LAYERS}
            ob["M1"] = min(1.0, float(o.get("M1", 0.0)))
            RS.grt_macro_rules(ob)
            s = {}
            for L in RS.LAYERS:
                s[L] = tr[L] * (1 - ob[L])
                if L in RS.GRT_TRANSITION:
                    below = RS.LAYERS[RS.LAYERS.index(L) - 1]
                    s[L] *= (1 - 0.5 * ob[below] * halve)
            self.sH.append(s["M2"] + s["M4"] + s["M6"])
            self.sV.append(s["M3"] + s["M5"] + s["M7"])
        self.kd = max(1, int(round(97.2 / b)) | 1)
        self.k = max(1, int(round(32.4 / b)) | 1)

    def cov_rect(self, A, x0, y0, x1, y1, val):
        b = self.b
        i0, i1 = max(0, int(x0 // b)), min(self.nx - 1, int(x1 // b))
        j0, j1 = max(0, int(y0 // b)), min(self.ny - 1, int(y1 // b))
        if i1 < i0 or j1 < j0:
            return
        xs = np.arange(i0, i1 + 1) * b
        ys = np.arange(j0, j1 + 1) * b
        cx = np.clip(np.minimum(xs + b, x1) - np.maximum(xs, x0), 0, None) / b
        cy = np.clip(np.minimum(ys + b, y1) - np.maximum(ys, y0), 0, None) / b
        A[j0:j1 + 1, i0:i1 + 1] += val * np.outer(cy, cx)

    def supply(self):
        M = self.M
        SH = np.full((self.ny, self.nx), self.sH0)
        SV = np.full((self.ny, self.nx), self.sV0)
        for i in range(M.n):
            x0, y0 = M.core_origin(i)
            w, h = M.dim[i]
            self.cov_rect(SH, x0, y0, x0 + w, y0 + h, self.sH[i] - self.sH0)
            self.cov_rect(SV, x0, y0, x0 + w, y0 + h, self.sV[i] - self.sV0)
        return np.maximum(SH, 1e-3), np.maximum(SV, 1e-3)

    def net(self, DH, DV, p, q, n, sign=1.0):
        b = self.b
        x0, x1 = sorted((p[0], q[0]))
        y0, y1 = sorted((p[1], q[1]))
        aw, ah = x1 - x0, y1 - y0
        w, h = max(aw, b), max(ah, b)
        i0, i1 = int(np.clip(x0 // b, 0, self.nx - 1)), int(np.clip((x0 + w - 1e-9) // b, 0, self.nx - 1))
        j0, j1 = int(np.clip(y0 // b, 0, self.ny - 1)), int(np.clip((y0 + h - 1e-9) // b, 0, self.ny - 1))
        # tracks per bin: H wires n x aw spread over the bbox -> per bin n x aw / (w h) x b^2 / b
        if aw > 0:
            DH[j0:j1 + 1, i0:i1 + 1] += sign * n * aw / (w * h) * b
        if ah > 0:
            DV[j0:j1 + 1, i0:i1 + 1] += sign * n * ah / (w * h) * b

    def demand(self):
        M = self.M
        DH = np.zeros((self.ny, self.nx))
        DV = np.zeros((self.ny, self.nx))
        for (p, q, n) in M.static:
            self.net(DH, DV, p, q, n)
        for q in range(len(M.L)):
            a, bb, w, kind = M.L[q]
            self.net(DH, DV, M.pt(a), M.pt(bb), w)
        fill = self.cfg["rs"]["cell_fill"]
        return DH, DV

    def ovf(self, DH, DV, SH, SV):
        bH = RS.box(DH, self.k, self.kd)
        sH = RS.box(SH, self.k, self.kd)
        bV = RS.box(DV, self.kd, self.k)
        sV = RS.box(SV, self.kd, self.k)
        oH = float(np.clip(bH - sH, 0, None).sum() * self.b)
        oV = float(np.clip(bV - sV, 0, None).sum() * self.b)
        return oH, oV, bH / sH, bV / sV

    def core_mask(self):
        A = np.zeros((self.ny, self.nx))
        M = self.M
        for i in range(M.n):
            x0, y0 = M.core_origin(i)
            self.cov_rect(A, x0, y0, x0 + M.dim[i, 0], y0 + M.dim[i, 1], 1.0)
        return A > 0.5


def cut_table(M, Gd):
    """worst full-length cut per direction: bits of links/stations/ft crossing the cut line vs tracks on it."""
    SH, SV = Gd.supply()
    b = Gd.b
    segs = [(M.pt(a), M.pt(bb), w) for (a, bb, w, kind) in M.L] + [(p, q, n) for (p, q, n) in M.static]
    out = {}
    for d, S, ax in (("H", SH, 0), ("V", SV, 1)):
        nc = Gd.nx if ax == 0 else Gd.ny
        cuts = (np.arange(1, nc) * b)
        dem = np.zeros(len(cuts))
        for p, q, n in segs:
            lo, hi = sorted((p[ax], q[ax]))
            dem[(cuts > lo) & (cuts < hi)] += n
        sup = S.sum(axis=0)[1:] if ax == 0 else S.sum(axis=1)[1:]
        r = dem / np.maximum(sup, 1e-6)
        i = int(np.argmax(r)) if len(r) else 0
        out[d] = dict(worst_ratio=round(float(r[i]), 3) if len(r) else 0.0, at_um=round(float(cuts[i]), 1) if len(r) else 0,
                      bits=int(dem[i]) if len(r) else 0, tracks=int(sup[i]) if len(r) else 0,
                      cuts_over_1=int((r > 1).sum()), profile=[(round(float(c), 1), int(x), int(s))
                                                               for c, x, s in zip(cuts, dem, sup)])
    return out


def intrinsic_cuts(M, Gd, fracs=(0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8), util=0.7, passes=8):
    """ARRANGEMENT-INDEPENDENT verdict (OWNER 11-11 00:5x "congested by design"): for every full cut line at a
    fraction f of the outline (vertical lines -> H demand, horizontal -> V), the smallest number of bits that any
    placement must carry across it: min-cut 2-way partition of the core clusters (FM passes, area of each side <=
    util x its side area, terminals = type face/bus points fixed by side), plus the ft hops that cross the line
    (fixed).  Supply = the tracks on that line if NO macro sat on it (upper bound).  ratio > ~0.8 on any cut =
    congested by design: no arrangement inside this outline fits (die-plan slot change)."""
    W, H = M.W, M.H
    b = Gd.b
    out = {}
    area = np.array([M.cbb[k, 2] * M.cbb[k, 3] for k in range(M.m)])
    # cluster graph
    E = collections.defaultdict(float)
    T = collections.defaultdict(list)     # cluster -> [(fixed point, bits)]
    for (a, bb, w, kind) in M.L:
        ka = M.cid[a[0]] if a[0] is not None else None
        kb = M.cid[bb[0]] if bb[0] is not None else None
        if ka is not None and kb is not None:
            if ka != kb:
                E[(min(ka, kb), max(ka, kb))] += w
        elif ka is not None:
            T[ka].append((bb[1], w))
        elif kb is not None:
            T[kb].append((a[1], w))
    adj = collections.defaultdict(list)
    for (i, j), w in E.items():
        adj[i].append((j, w))
        adj[j].append((i, w))
    for d, ax, L, other in (("H", 0, W, H), ("V", 1, H, W)):
        sup_full = Gd.sH0 * (other / b) if d == "H" else Gd.sV0 * (other / b)
        rows = []
        for f in fracs:
            c = f * L
            capL, capR = util * c * other, util * (L - c) * other
            # init: by current centre
            side = np.array([1 if (M.cpos[k, ax] + M.cbb[k, 2 + ax] / 2) > c else 0 for k in range(M.m)])

            def term_cost(k, s):
                return sum(w for (p, w) in T[k] if (p[ax] > c) != bool(s))

            def cut_bits(side):
                x = sum(w for (i, j), w in E.items() if side[i] != side[j])
                return x + sum(term_cost(k, side[k]) for k in range(M.m))

            def feasible(side):
                aR = float(area[side == 1].sum())
                aL = float(area.sum()) - aR
                return aL <= capL + EPS and aR <= capR + EPS
            # greedy repair to feasibility (move smallest-gain clusters)
            for _ in range(M.m):
                if feasible(side):
                    break
                aR = float(area[side == 1].sum()); aL = float(area.sum()) - aR
                src = 0 if aL > capL else 1
                cand = [k for k in range(M.m) if side[k] == src]
                if not cand:
                    break
                k = min(cand, key=lambda k: (term_cost(k, 1 - src) - term_cost(k, src)
                                             + sum(w if side[j] == src else -w for j, w in adj[k])))
                side[k] = 1 - src
            best = cut_bits(side) if feasible(side) else None
            for _ in range(passes):
                imp = False
                for k in range(M.m):
                    g = (term_cost(k, side[k]) - term_cost(k, 1 - side[k]) +
                         sum((w if side[j] != side[k] else -w) for j, w in adj[k]))
                    if g > EPS:
                        side[k] ^= 1
                        if feasible(side):
                            imp = True
                        else:
                            side[k] ^= 1
                if not imp:
                    break
            fb = cut_bits(side) if feasible(side) else None
            ft = sum(n for (p, q, n) in M.static if min(p[ax], q[ax]) < c < max(p[ax], q[ax]))
            dem = (fb if fb is not None else float("nan")) + ft
            rows.append(dict(at_um=round(c, 1), min_bits=None if fb is None else int(dem), ft_bits=int(ft),
                             tracks_no_macro=int(sup_full),
                             ratio=None if fb is None else round(dem / sup_full, 3)))
        rr = [r["ratio"] for r in rows if r["ratio"] is not None]
        out[d] = dict(worst=max(rr) if rr else None, rows=rows)
    w = max([v["worst"] for v in out.values() if v["worst"] is not None] or [0])
    out["verdict"] = "CONGESTED_BY_DESIGN" if w > 0.8 else "fits"
    out["worst_ratio"] = w
    return out


# ------------------------------------------------------------------------------------------------ search
def search(M, Gd, cfg, log):
    SH, SV = Gd.supply()
    DH, DV = Gd.demand()
    oH, oV, rH, rV = Gd.ovf(DH, DV, SH, SV)
    TP = 1e7    # per link over its timing limit (a seed may start with some; moves never add one)
    cm = Gd.core_mask()
    shH = max(0.0, float(np.percentile(rH[cm], 99)) - 1) if cm.any() else 0.0
    shV = max(0.0, float(np.percentile(rV[cm], 99)) - 1) if cm.any() else 0.0
    lamH, lamV = cfg["lam"] * (1 + shH), cfg["lam"] * (1 + shV)
    st = dict(lamH=round(lamH, 3), lamV=round(lamV, 3), shortage_H=round(shH, 3), shortage_V=round(shV, 3))

    def total():
        S_H, S_V = Gd.supply()
        D_H, D_V = Gd.demand()
        a, b_, _, _ = Gd.ovf(D_H, D_V, S_H, S_V)
        return M.cost(range(len(M.L))) + lamH * a + lamV * b_, a, b_
    base_obj, _, _ = total()
    acc = collections.Counter()
    t0 = time.time()
    for sw in range(cfg["sweeps"]):
        imp = 0
        for k in range(M.m):
            if M.cfix[k]:
                continue
            K = sorted(set(q for i in M.CL[k] for q in M.inc[i]))
            if not K:
                continue
            c0 = M.cost(K)
            tv0 = M.tviol(K)
            ox, oy = M.cpos[k].copy()
            of = M.cflip[k]
            cands = []      # (dbitmm, move)
            # relocate toward the bit-weighted median of the partners
            xs, ys, ws = [], [], []
            for q in K:
                a, b, w, kind = M.L[q]
                me, ot = (a, b) if (a[0] is not None and M.cid[a[0]] == k) else (b, a)
                if ot[0] is not None and M.cid[ot[0]] == k:
                    continue
                pm, po = M.pt(me), M.pt(ot)
                xs.append(po[0] - (pm[0] - ox)); ys.append(po[1] - (pm[1] - oy)); ws.append(w)
            if ws and not cfg.get("flips_only"):
                def wmed(v):
                    z = sorted(zip(v, ws)); hh = sum(ws) / 2; c = 0
                    for val, w in z:
                        c += w
                        if c >= hh:
                            return val
                tx, ty = wmed(xs), wmed(ys)
                seen = set()
                for fr in (1.0, 0.75, 0.5, 0.25, 0.1):
                    cx, cy = ox + fr * (tx - ox), oy + fr * (ty - oy)
                    for dx in range(-6, 7, 2):
                        for dy in range(-6, 7, 2):
                            p = (snap(cx + dx * 4 * G), snap(cy + dy * 4 * G))
                            if p in seen:
                                continue
                            seen.add(p)
                            if M.legal(k, *p):
                                M.cpos[k] = p
                                tv = M.tviol(K)
                                if tv <= tv0:
                                    cands.append((M.cost(K) - c0 + TP * (tv - tv0), ("mv", p)))
                                M.cpos[k] = (ox, oy)
            for j in range(M.m):
                if j == k or M.cfix[j] or cfg.get("flips_only"):
                    continue
                oj = M.cpos[j].copy()
                xk = snap(oj[0] + (M.cbb[j, 2] - M.cbb[k, 2]) / 2); yk = snap(oj[1] + (M.cbb[j, 3] - M.cbb[k, 3]) / 2)
                xj = snap(ox + (M.cbb[k, 2] - M.cbb[j, 2]) / 2); yj = snap(oy + (M.cbb[k, 3] - M.cbb[j, 3]) / 2)
                KK = sorted(set(K) | set(q for i in M.CL[j] for q in M.inc[i]))
                c0j = M.cost(KK)
                tvj = M.tviol(KK)
                M.cpos[k] = (xk, yk); M.cpos[j] = (xj, yj)
                okk = M.legal(k, xk, yk, ignore=(j,)) and M.legal(j, xj, yj)
                tv = M.tviol(KK) if okk else 0
                if okk and tv <= tvj:
                    cands.append((M.cost(KK) - c0j + TP * (tv - tvj), ("sw", j, (xk, yk), (xj, yj), (float(oj[0]), float(oj[1])))))
                M.cpos[k] = (ox, oy); M.cpos[j] = oj
            if True:     # whole-cluster mirror (an abutted group mirrors as one block)
                for fo in ("MY", "MX", "R180"):
                    nf = comp(of, fo)
                    if not M.legal(k, ox, oy, fl=nf):
                        continue
                    M.cflip[k] = nf
                    tv = M.tviol(K)
                    if tv <= tv0:
                        cands.append((M.cost(K) - c0 + TP * (tv - tv0), ("fl", nf)))
                    M.cflip[k] = of
            if not cands:
                continue
            cands.sort(key=lambda c: c[0])
            top = cands[:cfg["topk"]]
            # full objective on the top candidates (congestion is non-local)
            S_H, S_V = Gd.supply(); D_H, D_V = Gd.demand()
            aH, aV, _, _ = Gd.ovf(D_H, D_V, S_H, S_V)
            cur = lamH * aH + lamV * aV
            best = (-1e-6, None)
            for dbm, mv in top:
                apply_move(M, k, mv)
                S_H, S_V = Gd.supply(); D_H, D_V = Gd.demand()
                bH, bV, _, _ = Gd.ovf(D_H, D_V, S_H, S_V)
                d = dbm + lamH * bH + lamV * bV - cur
                undo_move(M, k, mv, (ox, oy), of)
                if d < best[0]:
                    best = (d, mv)
            if best[1] is not None:
                apply_move(M, k, best[1])
                imp += 1
                acc[best[1][0]] += 1
        obj, a, b_ = total()
        log("  sweep %d moves %d obj %.0f (%.1f%%) bit-mm %.0f ovfH %.0f ovfV %.0f tv %d %.0fs" % (
            sw, imp, obj / 1e3, 100 * (obj / max(base_obj, 1) - 1), M.cost(range(len(M.L))) / 1e3, a, b_,
            M.tviol(range(len(M.L))), time.time() - t0))
        if not imp:
            break
    st["moves"] = dict(acc)
    return st


def apply_move(M, k, mv):
    old = M._band_k(k) if M.bands else None
    if mv[0] == "mv":
        M.cpos[k] = mv[1]
    elif mv[0] == "fl":
        M.cflip[k] = mv[1]
    else:
        j = mv[1]
        oldj = M._band_k(j) if M.bands else None
        M.cpos[k] = mv[2]; M.cpos[j] = mv[3]
        if M.bands:
            M.band_now += M._band_k(j) - oldj
    if M.bands:
        M.band_now += M._band_k(k) - old


def undo_move(M, k, mv, pos, fl):
    old = M._band_k(k) if M.bands else None
    if mv[0] == "sw":
        j = mv[1]
        oldj = M._band_k(j) if M.bands else None
        M.cpos[j] = mv[4]
        if M.bands:
            M.band_now += M._band_k(j) - oldj
    M.cpos[k] = pos
    M.cflip[k] = fl
    if M.bands:
        M.band_now += M._band_k(k) - old


def base_ok(M, k, ignore=()):
    """the cluster back at its own base spot (base orient) is feasible when no other cluster, at its CURRENT spot,
    comes nearer than the base did (the base plan is the signed-off reference geometry)."""
    x, y, w, h = M.cbb[k]
    for j in range(M.m):
        if j == k or j in ignore:
            continue
        X, Y = M.cpos[j]; Wj, Hj = M.cbb[j, 2], M.cbb[j, 3]
        g = max(X - (x + w), x - (X + Wj), Y - (y + h), y - (Y + Hj))
        X0, Y0 = M.cbb[j, 0], M.cbb[j, 1]
        g0 = max(X0 - (x + w), x - (X0 + Wj), Y0 - (y + h), y - (Y0 + Hj))
        if g < min(g0, M.cfg["gap"]) - EPS:
            return False
    return True


def face_clear_legalise(M, log):
    """--face-clear: every rule cluster nearer its face than the rule is set onto the clearance line, then a
    sweep away from that face (Tetris) puts each cluster that is no longer legal against the ones already swept
    to the nearest legal lattice spot, moving away from the face first (dx up to +-4 steps).  Clusters that were
    already off-rule in the base and are untouched keep their base spot (base_ok).  Returns (moved, failed)."""
    failed = []
    start = [tuple(M.cpos[k]) for k in range(M.m)]
    for face, um, rx in M.cfg.get("face_clear") or []:
        ax = 1 if face in "SN" else 0
        sg = 1 if face in "SW" else -1           # direction away from the face
        L = M.H if ax else M.W
        hit = []
        for k in range(M.m):
            if face not in M.cclr[k] or M.cfix[k]:
                continue
            p, d = M.cpos[k][ax], M.cbb[k, 2 + ax]
            if sg > 0 and p < um - EPS:
                q = list(M.cpos[k]); q[ax] = snap(um + G / 2); M.cpos[k] = tuple(q); hit.append(k)
            elif sg < 0 and p + d > L - um + EPS:
                q = list(M.cpos[k]); q[ax] = snap(L - um - d - G / 2); M.cpos[k] = tuple(q); hit.append(k)
        if not hit:
            continue
        key = (lambda k: M.cpos[k][ax]) if sg > 0 else (lambda k: -(M.cpos[k][ax] + M.cbb[k, 2 + ax]))
        order = sorted((k for k in range(M.m) if not M.cfix[k]), key=key)
        pending = set(order)
        bad = []
        for k in order:
            pending.discard(k)
            x, y = M.cpos[k]
            untouched = tuple(M.cpos[k]) == start[k] and M.cflip[k] == "R0"
            if M.legal(k, x, y, ignore=pending) or (untouched and base_ok(M, k, ignore=pending)):
                continue
            best = None
            first = None       # nearest legal spot; best = nearest one that adds no link over its timing limit
            K = sorted(set(q for i in M.CL[k] for q in M.inc[i]))
            tv0 = M.tviol(K)
            for st in range(0, int(L / G) + 1):
                if first is not None and st > first[0] + 24:
                    break
                for dx in (0, 1, -1, 2, -2, 3, -3, 4, -4, 6, -6, 8, -8):
                    d = [0.0, 0.0]; d[ax] = sg * st * G; d[1 - ax] = dx * G
                    c = (snap(x + d[0]), snap(y + d[1]))
                    if M.legal(k, *c, ignore=pending):
                        if first is None:
                            first = (st, c)
                        M.cpos[k] = c
                        okt = M.tviol(K) <= tv0
                        M.cpos[k] = (x, y)
                        if okt:
                            best = c
                            break
                if best:
                    break
            if best is None:      # no spot keeps every incident link within its timing limit: the rule fails here
                bad.append(M.inst[M.CL[k][0]])
                continue
            M.cpos[k] = best
        if M.bands:
            M.band_now = np.zeros(len(M.bands))
            for kk in range(M.m):
                M.band_now += M._band_k(kk)
        if bad:
            failed.append(dict(face=face, um=um, no_legal_spot=bad))
            log("  face-clear %s %.1f: no legal, timing-clean spot for %s (an outline/die-plan change is needed)" % (
                face, um, bad))
        moved = [M.inst[M.CL[k][0]] for k in range(M.m) if tuple(M.cpos[k]) != start[k]]
        log("  face-clear %s %.1f: %d rule clusters set on the line, %d clusters moved: %s" % (
            face, um, len(hit), len(moved), [m_.split(".")[-2] + "." + m_.split(".")[-1] for m_ in moved]))
    if failed:
        def restore():
            for k in range(M.m):
                M.cpos[k] = start[k]
            if M.bands:
                M.band_now = np.zeros(len(M.bands))
                for kk in range(M.m):
                    M.band_now += M._band_k(kk)
        restore()
        # how much outline growth (on the rule's axis, at the far face) would make it fit: the die-plan ask
        if not M.cfg.get("_growing"):
            ax = 1 if failed[0]["face"] in "SN" else 0
            W0, H0 = M.W, M.H
            M.cfg["_growing"] = True
            try:
                for ext in np.arange(G * 2, 260.0, G * 2):
                    if ax:
                        M.H = H0 + ext
                    else:
                        M.W = W0 + ext
                    _, f2 = face_clear_legalise(M, lambda s_: None)
                    if not f2:
                        failed[0]["outline_growth_um"] = round(float(ext), 2)
                        log("  face-clear: fits with the outline grown by %.2f um on the %s axis" % (ext, "SN" if ax else "WE"))
                        break
            finally:
                M.W, M.H = W0, H0
                M.cfg.pop("_growing", None)
                restore()
    return sum(1 for k in range(M.m) if tuple(M.cpos[k]) != start[k]), failed


def apply_seed(M, seed, log):
    """hand design: set each listed core's origin/orient (clusters move by their first listed member), then
    legalise illegal clusters to the nearest legal lattice spot."""
    done = set()
    for inst, v in seed.items():
        if inst not in M.idx:
            continue
        i = M.idx[inst]
        k = M.cid[i]
        if k in done:
            continue
        done.add(k)
        if "orient" in v:
            M.cflip[k] = comp(M.ori0[i], v["orient"])
        if "origin_um" in v:
            ox, oy = M.coff[i]
            M.cpos[k] = (snap(v["origin_um"][0] - ox), snap(v["origin_um"][1] - oy))
    M.band_now = np.zeros(len(M.bands))
    for k in range(M.m):
        M.band_now += M._band_k(k)
    fixed = 0
    for k in range(M.m):
        x, y = M.cpos[k]
        if M.cfix[k] or M.legal(k, x, y):
            continue
        best = None
        for r in range(1, 60):
            for dx in range(-r, r + 1):
                for dy in (-r, r) if abs(dx) != r else range(-r, r + 1):
                    p = (snap(x + dx * G * 2), snap(y + dy * G * 2))
                    if M.legal(k, *p):
                        d = abs(dx) + abs(dy)
                        if best is None or d < best[0]:
                            best = (d, p)
            if best:
                break
        if best:
            old = M._band_k(k) if M.bands else None
            M.cpos[k] = best[1]
            if M.bands:
                M.band_now += M._band_k(k) - old
            fixed += 1
        else:
            log("  seed: cluster %d (%s) has no legal spot near its seed" % (k, M.inst[M.CL[k][0]]))
    return fixed


# ------------------------------------------------------------------------------------------------ apply to plan
def follow_fn(M):
    def f(p):
        i = M.owner(p)
        if i is None:
            return None
        u, v = M.to_local(i, p)
        o = M.core_orient(i)
        u, v = xf(o, M.dim[i, 0], M.dim[i, 1], u, v)
        x0, y0 = M.core_origin(i)
        return [round(x0 + u, 4), round(y0 + v, 4)]
    return f


SKIP_KEYS = {"buses", "ft_slots", "die_ft_bands", "internal_stations", "hard_cores", "outline_um", "contents",
             "face_layers", "track_offset_um", "window_um", "in_window_um", "out_window_um"}


def walk_follow(x, fol, key=None):
    if isinstance(x, dict):
        for k, v in x.items():
            if k in SKIP_KEYS:
                continue
            x[k] = walk_follow(v, fol, k)
        return x
    if isinstance(x, list):
        if x and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in x):
            if key and ("rect" in key) and len(x) == 4:
                a, b = fol(x[:2]), fol(x[2:4])
                if a and b:
                    return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]
                return x
            if len(x) >= 2 and key and (key.endswith("_um") or key in ("xy", "root", "outs")):
                q = fol(x[:2])
                return (q + list(x[2:])) if q else x
            return x
        return [walk_follow(v, fol, key) for v in x]
    return x


def write_type(M, t_new, cfg, log):
    """t_new: deepcopy of the base type; returns station report."""
    import hub_repack as HR
    fol = follow_fn(M)
    W, H = M.W, M.H
    rep = dict(stations=0, moved=0, regs_old=0, regs_new=0, rerouted=0, kept_old_regs=0, need_more_regs=0, failed=0,
               need_more_idx=[])
    # stations (base geometry ownership)
    st = t_new.get("internal_stations") or []
    ends = []
    for s in st:
        a, b = fol(s["from_um"]), fol(s["to_um"])
        ends.append((a or list(s["from_um"]), b or list(s["to_um"]), bool(a and a != list(s["from_um"])) or
                     bool(b and b != list(s["to_um"]))))
    for i, h in enumerate(t_new["hard_cores"]):
        if M.fixed[i]:
            continue
        x0, y0 = M.core_origin(i)
        h["origin_um"] = [round(x0, 4), round(y0, 4)]
        if "orient" in h or M.core_orient(i) != "R0":
            h["orient"] = M.core_orient(i)
        cea = h.get("clock_entry_access")
        if isinstance(cea, (str, dict)):
            d = ast.literal_eval(cea) if isinstance(cea, str) else cea
            d = walk_follow(d, fol, "clock_entry_access")
            fp = d.get("footprints_um") if isinstance(d, dict) else None
            if isinstance(fp, dict):
                for L, rs in fp.items():
                    nr = []
                    for r in rs:
                        a, b = fol(r[:2]), fol(r[2:4])
                        nr.append([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])] if a and b else r)
                    fp[L] = nr
            h["clock_entry_access"] = repr(d) if isinstance(cea, str) else d
    # contents boxes that equal their cores' bbox follow
    par = collections.defaultdict(list)
    for i, h in enumerate(M.C):
        par[h["inst"].split("__")[0]].append(i)
        par[h["inst"].rsplit(".", 1)[0]].append(i)
    for c in t_new.get("contents") or []:
        hs = par.get(c.get("inst"))
        if not hs or "origin_um" not in c or "outline_um" not in c:
            continue
        bx0 = min(M.org0[i, 0] for i in hs); by0 = min(M.org0[i, 1] for i in hs)
        bx1 = max(M.org0[i, 0] + M.dim[i, 0] for i in hs); by1 = max(M.org0[i, 1] + M.dim[i, 1] for i in hs)
        if abs(c["origin_um"][0] - bx0) > 0.6 or abs(c["origin_um"][1] - by0) > 0.6 or \
                abs(c["outline_um"][0] - (bx1 - bx0)) > 0.6 or abs(c["outline_um"][1] - (by1 - by0)) > 0.6:
            continue
        nx0 = min(M.core_origin(i)[0] for i in hs); ny0 = min(M.core_origin(i)[1] for i in hs)
        nx1 = max(M.core_origin(i)[0] + M.dim[i, 0] for i in hs); ny1 = max(M.core_origin(i)[1] + M.dim[i, 1] for i in hs)
        c["origin_um"] = [round(nx0, 4), round(ny0, 4)]
        c["outline_um"] = [round(nx1 - nx0, 4), round(ny1 - ny0, 4)]
    # every other coordinate that sits on a core (clock taps, reset, landing pins on a core, ...)
    for k in list(t_new.keys()):
        if k in SKIP_KEYS:
            continue
        t_new[k] = walk_follow(t_new[k], fol, k)
    # station registers
    rects = [(M.core_origin(i)[0], M.core_origin(i)[1], M.core_origin(i)[0] + M.dim[i, 0],
              M.core_origin(i)[1] + M.dim[i, 1]) for i in range(M.n)]
    R = HR.Raster(W, H, rects)
    for s, (a, b, mv) in zip(st, ends):
        nold = len(s.get("regs_um") or [])
        rep["stations"] += 1
        rep["regs_old"] += nold
        s["from_um"], s["to_um"] = [round(a[0], 4), round(a[1], 4)], [round(b[0], 4), round(b[1], 4)]
        regs_free = all(R.free(*r[:2]) for r in s.get("regs_um") or [])
        if not mv and regs_free:
            rep["regs_new"] += nold
            continue
        rep["moved"] += 1
        r = HR.route_station(R, tuple(a), tuple(b), nold, cfg["reach"]) if nold else None
        if nold == 0:
            rep["regs_new"] += 0
            continue
        if r is not None and len(r["regs"]) == nold:
            s["regs_um"] = [list(p) for p in r["regs"]]
            rep["rerouted"] += 1
            rep["regs_new"] += nold
            s["note"] = (s.get("note", "") + " | CORE-PLACE-1 re-sited (%s, %s um, %d regs kept)" %
                         (r["kind"], r["length_um"], nold))
        elif r is not None and len(r["regs"]) > nold:
            rep["need_more_regs"] += 1
            rep["need_more_idx"].append(st.index(s))
            rep["regs_new"] += nold
        else:
            rep["failed"] += 1
            rep["regs_new"] += nold
            if regs_free:
                rep["kept_old_regs"] += 1
    return rep


def eq_gate(t0, t1):
    """positions/orients only: every difference is a coordinate list, an orient, a station note or a
    clock_entry_access repr; buses/ft/bands/outline/modules/params/pins/station bits+counts identical."""
    bad = []

    def rec(a, b, path):
        if type(a) is not type(b):
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                return
            bad.append(path)
            return
        if isinstance(a, dict):
            if set(a) != set(b):
                bad.append(path + "{keys}")
                return
            for k in a:
                if path == "" and k in ("buses", "ft_slots", "die_ft_bands", "outline_um", "module", "params",
                                        "rtl", "face_layers"):
                    if json.dumps(a[k], sort_keys=True) != json.dumps(b[k], sort_keys=True):
                        bad.append(k)
                    continue
                if k in ("note",) and "internal_stations" in path:
                    continue
                if k == "orient":
                    continue
                if k == "clock_entry_access":
                    continue
                rec(a[k], b[k], path + "/" + k)
        elif isinstance(a, list):
            if len(a) != len(b):
                bad.append(path + "[len]")
                return
            if a and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in a):
                return
            for i, (x, y) in enumerate(zip(a, b)):
                rec(x, y, path + "[%d]" % i)
        elif a != b:
            bad.append(path)
    rec(t0, t1, "")
    for i, (h0, h1) in enumerate(zip(t0.get("hard_cores", []), t1.get("hard_cores", []))):
        for k in h0:
            if k in ("origin_um", "orient", "clock_entry_access"):
                continue
            if json.dumps(h0[k], sort_keys=True) != json.dumps(h1.get(k), sort_keys=True):
                bad.append("hard_cores[%d].%s" % (i, k))
    for i, (s0, s1) in enumerate(zip(t0.get("internal_stations") or [], t1.get("internal_stations") or [])):
        if len(s0.get("regs_um") or []) != len(s1.get("regs_um") or []) or s0.get("bits") != s1.get("bits"):
            bad.append("internal_stations[%d] regs/bits" % i)
    return sorted(set(bad))


def overlaps(M):
    out = 0
    for i in range(M.n):
        xi, yi = M.core_origin(i)
        for j in range(i + 1, M.n):
            xj, yj = M.core_origin(j)
            if xi < xj + M.dim[j, 0] - EPS and xj < xi + M.dim[i, 0] - EPS and \
                    yi < yj + M.dim[j, 1] - EPS and yj < yi + M.dim[i, 1] - EPS:
                out += 1
    return out


# ------------------------------------------------------------------------------------------------ views
def svg_view(M, Gd, title, path, cuts=None, heat=None, top=30):
    """floorplan view: outline, face windows, ft slots, die bands, clock tap, cores with pin groups per face,
    flylines by bits (top links), station reach circles, per-cut bits vs tracks (side bars), ratio heat."""
    W, H = M.W, M.H
    PAD = 150
    s = 900.0 / max(W, H)
    VW, VH = W * s + 2 * PAD, H * s + 2 * PAD

    def X(x):
        return PAD + x * s

    def Y(y):
        return PAD + (H - y) * s
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="sans-serif">'
         % (VW, VH, VW, VH), '<rect width="100%" height="100%" fill="#ffffff"/>']
    o.append('<text x="10" y="20" font-size="14">%s</text>' % title)
    if heat is not None:
        rH, rV = heat
        r = np.maximum(rH, rV)
        b = Gd.b
        for j in range(r.shape[0]):
            for i in range(r.shape[1]):
                v = r[j, i]
                if v < 0.6:
                    continue
                c = "#fde68a" if v < 0.9 else ("#fb923c" if v < 1.2 else ("#ef4444" if v < 2 else "#7f1d1d"))
                o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" fill-opacity="0.55"/>' %
                         (X(i * b), Y((j + 1) * b), b * s + 0.3, b * s + 0.3, c))
    o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="#111" stroke-width="1.5"/>' %
             (X(0), Y(H), W * s, H * s))
    for d, lo, hi in M.bands:
        if d == "EW":
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#6366f1" fill-opacity="0.12"/>' %
                     (X(0), Y(hi), W * s, (hi - lo) * s))
        else:
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#6366f1" fill-opacity="0.12"/>' %
                     (X(lo), Y(H), (hi - lo) * s, H * s))
    for r in M.FR:
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#a855f7" fill-opacity="0.25"/>' %
                 (X(r[0]), Y(r[3]), (r[2] - r[0]) * s, (r[3] - r[1]) * s))
    for bu in M.t.get("buses") or []:
        f, wn = bu.get("face"), bu.get("window_um")
        if not f or not wn:
            continue
        lo, hi = wn[:2]
        if f in "NS":
            y = H if f == "N" else 0
            o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#2563eb" stroke-width="5"/>' %
                     (X(lo), Y(y), X(hi), Y(y)))
        else:
            x = W if f == "E" else 0
            o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#2563eb" stroke-width="5"/>' %
                     (X(x), Y(lo), X(x), Y(hi)))
    if len(M.FP):
        step = max(1, len(M.FP) // 3000)
        for p in M.FP[::step]:
            o.append('<circle cx="%.1f" cy="%.1f" r="0.8" fill="#059669"/>' % (X(p[0]), Y(p[1])))
    for (p, q, n) in M.static:
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#059669" stroke-width="%.1f" '
                 'stroke-opacity="0.5" stroke-dasharray="4 3"/>' % (X(p[0]), Y(p[1]), X(q[0]), Y(q[1]),
                                                                     min(6, 0.5 + math.log10(1 + n))))
    pal = ["#0ea5e9", "#f97316", "#22c55e", "#e11d48", "#8b5cf6", "#eab308", "#14b8a6", "#64748b", "#d946ef",
           "#84cc16", "#f43f5e"]
    mods = sorted(set(h["module"] for h in M.C))
    for i in range(M.n):
        x0, y0 = M.core_origin(i)
        w, h = M.dim[i]
        col = pal[mods.index(M.C[i]["module"]) % len(pal)]
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" fill-opacity="0.35" stroke="%s"/>' %
                 (X(x0), Y(y0 + h), w * s, h * s, col, col))
        o.append('<text x="%.1f" y="%.1f" font-size="8">%s %s</text>' % (X(x0) + 2, Y(y0 + h) + 9,
                                                                          M.inst[i].split(".")[-1][:18], M.core_orient(i)))
        # pin groups per face (bar thickness ~ pins)
        oo = M.core_orient(i)
        fc = collections.Counter()
        for lf, cnt in M.lface[i].items():
            f = lf
            if oo in ("MX", "R180") and f in "NS":
                f = OPP[f]
            if oo in ("MY", "R180") and f in "EW":
                f = OPP[f]
            fc[f] += cnt
        for f, cnt in fc.items():
            th = min(8, 1 + 2 * math.log10(1 + cnt))
            if f == "N":
                seg = (X(x0), Y(y0 + h), X(x0 + w), Y(y0 + h))
            elif f == "S":
                seg = (X(x0), Y(y0), X(x0 + w), Y(y0))
            elif f == "E":
                seg = (X(x0 + w), Y(y0), X(x0 + w), Y(y0 + h))
            else:
                seg = (X(x0), Y(y0), X(x0), Y(y0 + h))
            o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#111" stroke-width="%.1f" '
                     'stroke-opacity="0.7"><title>%s %s pins</title></line>' % (seg + (th, f, cnt)))
    # flylines: top links by bits (aggregated per core pair)
    agg = collections.defaultdict(float)
    for (a, b, w, kind) in M.L:
        ka = ("c", a[0]) if a[0] is not None else ("p", tuple(round(v) for v in a[1]))
        kb = ("c", b[0]) if b[0] is not None else ("p", tuple(round(v) for v in b[1]))
        agg[(ka, kb) if ka <= kb else (kb, ka)] += w
    mx = max(agg.values()) if agg else 1

    def cen(k):
        if k[0] == "c":
            x0, y0 = M.core_origin(k[1])
            return (x0 + M.dim[k[1], 0] / 2, y0 + M.dim[k[1], 1] / 2)
        return k[1]
    for (ka, kb), w in sorted(agg.items(), key=lambda kv: -kv[1])[:top]:
        p, q = cen(ka), cen(kb)
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#be123c" stroke-width="%.1f" '
                 'stroke-opacity="0.6"><title>%d bits</title></line>' % (X(p[0]), Y(p[1]), X(q[0]), Y(q[1]),
                                                                          0.6 + 7 * w / mx, w))
    # station reach circles at the launch end of the 8 widest stations
    sts = sorted(M.stations, key=lambda s: -M.L[s[1]][2])[:8]
    for (_, q, nreg) in sts:
        a = M.pt(M.L[q][0])
        o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="#7c3aed" stroke-dasharray="3 3" '
                 'stroke-opacity="0.5"/>' % (X(a[0]), Y(a[1]), M.cfg["reach"] * s))
    ck = (M.t.get("clock") or {}).get("tap_um")
    if isinstance(ck, list):
        o.append('<path d="M %.1f %.1f l 7 0 l -7 -10 l -7 10 z" fill="#facc15" stroke="#111"/>' % (X(ck[0]), Y(ck[1]) + 5))
    # per-cut bars: bits vs tracks
    if cuts:
        for d, prof in (("H", cuts["H"]["profile"]), ("V", cuts["V"]["profile"])):
            for c, dem, sup in prof:
                r = dem / max(sup, 1)
                col = "#16a34a" if r < 0.8 else ("#f59e0b" if r < 1.0 else "#dc2626")
                L = min(PAD - 30, 60 * r)
                if d == "H":      # vertical cut lines along x: bars above the outline
                    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f"/>' %
                             (X(c), Y(H) - 8, X(c), Y(H) - 8 - L, col, max(1, Gd.b * s * 0.8)))
                else:
                    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f"/>' %
                             (X(W) + 8, Y(c), X(W) + 8 + L, Y(c), col, max(1, Gd.b * s * 0.8)))
        o.append('<text x="%.1f" y="%.1f" font-size="10">cut bits/tracks (H across x, top; V across y, right); '
                 '60 px = 1.0; worst H %.2f @x=%.0f, V %.2f @y=%.0f</text>' %
                 (PAD, VH - 20, cuts["H"]["worst_ratio"], cuts["H"]["at_um"], cuts["V"]["worst_ratio"],
                  cuts["V"]["at_um"]))
    o.append("</svg>")
    Path(path).write_text("\n".join(o))


# ------------------------------------------------------------------------------------------------ driver
def rs_rows(plan_path, die, repo, types, ref_dirs, halving, outdir):
    argv = [str(plan_path), "--die", die, "--repo", str(repo), "--types", ",".join(types), "--out", str(outdir),
            "--grt-halving", halving]
    if ref_dirs:
        argv += ["--ref-dirs"] + list(ref_dirs)
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        RS.main(argv)
    js = json.loads((Path(outdir) / f"route_supply_{die}.json").read_text())
    return {r["type"]: r for r in js["rows"]}


def rs_summary(r):
    if not r:
        return {}
    g = r.get("regions", {})
    return dict(verdict=r.get("verdict"), worst=r["worst"]["region"] + "_" + r["worst"]["dir"],
                p99=r["worst"]["p99"], core_H=g.get("core_H", {}).get("p99"), core_V=g.get("core_V", {}).get("p99"),
                street_H=g.get("street_H", {}).get("p99"), street_V=g.get("street_V", {}).get("p99"),
                hot_bins=r.get("hot_bins"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--types", required=True)
    ap.add_argument("--die")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--ref-dirs", nargs="*", default=[])
    ap.add_argument("--out-plan")
    ap.add_argument("--event")
    ap.add_argument("--seed", help="JSON {type: {inst: {origin_um, orient}}} hand design, legalised then searched")
    ap.add_argument("--no-search", action="store_true", help="score the seed / base only")
    ap.add_argument("--gap", default="auto", help="min cluster gap um; auto = min(34.56, the base's own min "
                    "cluster gap floored to 4.32) so a packed type is not illegal at its own placement")
    ap.add_argument("--gap-pinface", default="", metavar="HI:LO:PINS",
                    help="R3 face rule: facing faces keep >= HI um when either carries > PINS pins, else >= LO um "
                         "(diagonal neighbours LO); overrides --gap for core-core spacing")
    ap.add_argument("--sweeps", type=int, default=12)
    ap.add_argument("--topk", type=int, default=4)
    ap.add_argument("--lam", type=float, default=4.0)
    ap.add_argument("--reach", type=float, default=360.0)
    ap.add_argument("--grid-um", type=float, default=21.6)
    ap.add_argument("--grt-halving", choices=("full", "none"), default="full")
    ap.add_argument("--flips-only", action="store_true", help="orientation flips only (no relocate / swap)")
    ap.add_argument("--fixed", default="", help="regex of hard-core insts that never move")
    ap.add_argument("--face-clear", action="append", default=[], metavar="FACE:UM:REGEX",
                    help="cores whose inst/module match REGEX keep >= UM from FACE (S/N/E/W); a column too near is "
                         "re-packed off the face before the search")
    ap.add_argument("--svg", help="directory for before/after floorplan SVG views")
    ap.add_argument("--rs-out", help="directory for the route_supply before/after runs (default: beside --event)")
    a = ap.parse_args(argv)
    repo = Path(a.repo).resolve()
    plan = Path(a.plan)
    if not plan.is_absolute():
        plan = repo / plan
    raw = plan.read_bytes()
    P = json.loads(gzip.decompress(raw)) if plan.suffix == ".gz" else json.loads(raw)
    RS.REF_DIRS[:] = [str(plan.parent)] + [str(repo / "physical" / "die_plan" / r) for r in a.ref_dirs]
    die = a.die or (P.get("die") or {}).get("name") or plan.parent.name
    die_dir = repo / "physical" / "die_plan" / die
    if not die_dir.is_dir():
        die_dir = plan.parent
    rs_cfg = dict(RS.DEFAULTS, derate=dict(RS.DERATE), core_ceiling=RS.DEFAULTS["core_ceiling"])
    try:
        rs_cfg["views"] = json.loads((HERE / "route_supply_views.json").read_text()).get("views", {})
    except (OSError, ValueError):
        rs_cfg["views"] = {}
    try:
        rs_cfg["kit_views"] = json.loads((HERE / "route_supply_kit_views.json").read_text()).get(die, {})
    except (OSError, ValueError, AttributeError):
        rs_cfg["kit_views"] = {}
    conns = RS.load_conns(die_dir, None, plan.parent, RS.REF_DIRS[1:])
    cfg = dict(gap=a.gap, sweeps=a.sweeps, topk=a.topk, lam=a.lam, reach=a.reach, grid_um=a.grid_um,
               grt_halving=a.grt_halving, fixed_re=a.fixed, rs=rs_cfg,
               flips_only=a.flips_only,
               gap_pinface=tuple(float(v) for v in a.gap_pinface.split(":")) if a.gap_pinface else None,
               face_clear=[(f.split(":")[0], float(f.split(":")[1]), f.split(":", 2)[2]) for f in a.face_clear])
    seeds = json.loads(Path(a.seed).read_text()) if a.seed else {}
    Q = copy.deepcopy(P)
    rows = []
    log = lambda s: print(s, flush=True)   # noqa: E731
    for tn in [t for t in a.types.split(",") if t]:
        t = P["partition_types"][tn]
        log("== %s" % tn)
        cfg["gap"] = 34.56 if a.gap == "auto" else float(a.gap)
        M = TypeModel(tn, t, die_dir, repo, conns, cfg)
        if a.gap == "auto":
            mg = 34.56
            for k in range(M.m):
                for j in range(k + 1, M.m):
                    x, y, w, h = M.cbb[k]
                    X, Y, Wj, Hj = M.cbb[j]
                    g = max(X - (x + w), x - (X + Wj), Y - (y + h), y - (Y + Hj))
                    mg = min(mg, g)
            cfg["gap"] = max(G, math.floor(mg / G + 1e-6) * G)
            log("  gap auto: %.2f um" % cfg["gap"])
        Gd = Grid(M, cfg)
        M.init_limits()
        base_bitum = M.cost(range(len(M.L)))
        SH, SV = Gd.supply(); DH, DV = Gd.demand()
        b_oH, b_oV, b_rH, b_rV = Gd.ovf(DH, DV, SH, SV)
        b_cut = cut_table(M, Gd)
        base_viol = M.violations()
        icut = intrinsic_cuts(M, Gd)
        log("  intrinsic min-cut: %s worst %.3f (H %s, V %s)" % (icut["verdict"], icut["worst_ratio"],
                                                              icut["H"]["worst"], icut["V"]["worst"]))
        if a.svg:
            Path(a.svg).mkdir(parents=True, exist_ok=True)
            svg_view(M, Gd, "%s BEFORE  bit-mm %.0f  ovf H/V %.0f/%.0f" % (tn, base_bitum / 1e3, b_oH, b_oV),
                     Path(a.svg) / f"{tn}__before.svg", b_cut, (b_rH, b_rV))
        pinned = []
        for attempt in range(3):
            # a retry starts from the base with the end clusters of the stations that could not keep their
            # register count pinned at their base spot (a station's count is its latency: EQ keeps it)
            if attempt:
                M.reset_state()
                for k_ in pinned:
                    M.cfix[k_] = True
                if M.bands:
                    M.band_now = np.zeros(len(M.bands))
                    for kk in range(M.m):
                        M.band_now += M._band_k(kk)
            seeded = 0
            if tn in seeds:
                seeded = apply_seed(M, seeds[tn], log)
            fc_moved, fc_failed = face_clear_legalise(M, log) if cfg.get("face_clear") else (0, [])
            st = {"moves": {}}
            if not a.no_search:
                st = search(M, Gd, cfg, log)
                # station repair: a station that hub_repack.route_station cannot re-site with its old register count
                # (length limit, or no free street sites along it) gets its end clusters reverted to the base placement,
                # most-implicated cluster first, while the revert is legal (the base is feasible, so this converges)
                qmap = {si: q for (si, q, _) in M.stations}
                reverted = []
                # first: swap an over-station end with a same-size cluster (identical lanes) when that lowers the count
                swapped = []
                nbad = lambda: len(write_type(M, copy.deepcopy(t), cfg, lambda s_: None)["need_more_idx"])  # noqa: E731
                cur = nbad()
                for rnd in range(8):
                    if not cur:
                        break
                    bad = write_type(M, copy.deepcopy(t), cfg, lambda s_: None)["need_more_idx"]
                    ends = collections.Counter()
                    for si in bad:
                        a_, b_, _, _ = M.L[qmap[si]]
                        for e in (a_, b_):
                            if e[0] is not None:
                                ends[M.cid[e[0]]] += 1
                    best = (cur, None)
                    tv_cur = M.tviol(range(len(M.L)))
                    for k_, _ in ends.most_common(3):
                        for j_ in range(M.m):
                            if j_ == k_ or M.cfix[j_] or M.cfix[k_] or \
                                    abs(M.cbb[j_, 2] - M.cbb[k_, 2]) > EPS or abs(M.cbb[j_, 3] - M.cbb[k_, 3]) > EPS:
                                continue
                            pk, pj = tuple(M.cpos[k_]), tuple(M.cpos[j_])
                            fk, fj = M.cflip[k_], M.cflip[j_]
                            M.cpos[k_], M.cpos[j_] = pj, pk
                            if M.legal(k_, *pj, ignore=(j_,)) and M.legal(j_, *pk) and M.tviol(range(len(M.L))) <= tv_cur:
                                n_ = nbad()
                                if n_ < best[0]:
                                    best = (n_, (k_, j_))
                            M.cpos[k_], M.cpos[j_] = pk, pj
                            M.cflip[k_], M.cflip[j_] = fk, fj
                    if best[1] is None:
                        break
                    k_, j_ = best[1]
                    M.cpos[k_], M.cpos[j_] = tuple(M.cpos[j_]), tuple(M.cpos[k_])
                    if M.bands:
                        M.band_now = np.zeros(len(M.bands))
                        for kk in range(M.m):
                            M.band_now += M._band_k(kk)
                    swapped.append((M.inst[M.CL[k_][0]], M.inst[M.CL[j_][0]]))
                    cur = best[0]
                if swapped:
                    log("  station repair: %d same-size swaps, %d stations still over: %s" % (len(swapped), cur, swapped))
                    st["swapped"] = swapped
                for rnd in range(M.m):
                    bad = write_type(M, copy.deepcopy(t), cfg, lambda s_: None)["need_more_idx"]
                    if not bad:
                        break
                    cnt = collections.Counter()
                    for si in bad:
                        a_, b_, _, _ = M.L[qmap[si]]
                        for e in (a_, b_):
                            if e[0] is not None:
                                k_ = M.cid[e[0]]
                                if tuple(M.cpos[k_]) != tuple(M.cbb[k_, :2]) or M.cflip[k_] != "R0":
                                    cnt[k_] += 1
                    done_ = False
                    # face-rule clusters (--face-clear) revert last: the rule is the point of the move
                    for k_, _ in sorted(cnt.most_common(), key=lambda kv: bool(M.cclr[kv[0]])):
                        old = (tuple(M.cpos[k_]), M.cflip[k_])
                        ob = M._band_k(k_) if M.bands else None
                        tvb = M.tviol(range(len(M.L)))
                        M.cpos[k_] = tuple(M.cbb[k_, :2]); M.cflip[k_] = "R0"
                        if (M.legal(k_, *M.cpos[k_]) or base_ok(M, k_)) and M.tviol(range(len(M.L))) <= tvb:
                            if M.bands:
                                M.band_now += M._band_k(k_) - ob
                            reverted.append(M.inst[M.CL[k_][0]])
                            done_ = True
                            break
                        M.cpos[k_], M.cflip[k_] = old
                    if not done_:
                        log("  station repair: no legal revert left (%d stations over)" % len(bad))
                        break
                if reverted:
                    log("  station repair: reverted %d clusters to base: %s" % (len(reverted), reverted))
                    st["reverted"] = reverted
            if a.no_search:
                break
            bad_end = write_type(M, copy.deepcopy(t), cfg, lambda s_: None)["need_more_idx"]
            if not bad_end:
                break
            add = set()
            S_ = t.get("internal_stations") or []
            for si in bad_end:
                a_, b_, _, _ = M.L[qmap[si]]
                for e in (a_, b_):
                    if e[0] is not None and not M.cfix[M.cid[e[0]]]:
                        add.add(M.cid[e[0]])
                # clusters that moved onto the station's base path (pins -> its registers, bbox per hop + 10 um)
                pts = [tuple(S_[si]["from_um"])] + [tuple(r) for r in S_[si].get("regs_um") or []] + \
                    [tuple(S_[si]["to_um"])]
                for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                    bx0, bx1 = min(x0, x1) - 10, max(x0, x1) + 10
                    by0, by1 = min(y0, y1) - 10, max(y0, y1) + 10
                    for k_ in range(M.m):
                        if M.cfix[k_]:
                            continue
                        def hit(px, py):
                            return px < bx1 and px + M.cbb[k_, 2] > bx0 and py < by1 and py + M.cbb[k_, 3] > by0
                        if hit(*M.cpos[k_]) and not hit(*M.cbb[k_, :2]):
                            add.add(k_)
            if not add or attempt == 2:
                break
            pinned += sorted(add)
            log("  station retry %d: pin %d station-end clusters at base: %s" % (
                attempt + 1, len(add), [M.inst[M.CL[k_][0]] for k_ in sorted(add)]))
        st["pinned_for_stations"] = [M.inst[M.CL[k_][0]] for k_ in pinned]
        new_bitum = M.cost(range(len(M.L)))
        tviol_end = M.tviol(range(len(M.L)))
        SH, SV = Gd.supply(); DH, DV = Gd.demand()
        n_oH, n_oV, n_rH, n_rV = Gd.ovf(DH, DV, SH, SV)
        n_cut = cut_table(M, Gd)
        tnew = copy.deepcopy(t)
        srep = write_type(M, tnew, cfg, log)
        eqbad = eq_gate(t, tnew)
        nov = overlaps(M)
        moved = sum(1 for i in range(M.n) if M.core_origin(i) != tuple(M.org0[i]) or M.core_orient(i) != M.ori0[i])
        if a.svg:
            svg_view(M, Gd, "%s AFTER  bit-mm %.0f  ovf H/V %.0f/%.0f" % (tn, new_bitum / 1e3, n_oH, n_oV),
                     Path(a.svg) / f"{tn}__after.svg", n_cut, (n_rH, n_rV))
            dump = dict(type=tn, W=M.W, H=M.H, grid_um=Gd.b,
                        before=dict(heat=np.maximum(b_rH, b_rV).round(3).tolist()),
                        after=dict(heat=np.maximum(n_rH, n_rV).round(3).tolist()),
                        cores=[dict(inst=M.inst[i], module=M.C[i]["module"], dim=M.dim[i].tolist(),
                                    before=list(M.org0[i]), before_orient=M.ori0[i], after=list(M.core_origin(i)),
                                    after_orient=M.core_orient(i)) for i in range(M.n)])
            Path(Path(a.svg) / f"{tn}__view.json").write_text(json.dumps(dump))
        ok = not eqbad and nov == 0 and srep["need_more_regs"] == 0 and tviol_end == 0
        if ok:
            Q["partition_types"][tn] = tnew
        rows.append(dict(type=tn, cores=M.n, clusters=M.m, links=len(M.L), stations=len(M.stations),
                         model=M.model, intrinsic=icut, seeded=bool(tn in seeds), seed_legalised=seeded, face_clear_moved=fc_moved, face_clear_failed=fc_failed, face_clear_end=M.clear_viol(),
                         timing_over=[dict(a=str(M.L[q][0]), b=str(M.L[q][1]), bits=M.L[q][2], kind=M.L[q][3],
                                           len_um=round(M.llen(q), 1), limit_um=round(M.maxlen[q], 1))
                                      for q in range(len(M.L)) if M.llen(q) > M.maxlen[q] + EPS][:40],
                         base_violations=len(base_viol), moved_cores=moved, moves=st.get("moves"),
                         lam=dict((k, st[k]) for k in ("lamH", "lamV", "shortage_H", "shortage_V") if k in st),
                         bit_mm=[round(base_bitum / 1e3, 1), round(new_bitum / 1e3, 1),
                                 round(100 * (new_bitum / max(base_bitum, 1) - 1), 1)],
                         rudy_ovf_H=[round(b_oH), round(n_oH)], rudy_ovf_V=[round(b_oV), round(n_oV)],
                         cut_H=[{k: v for k, v in b_cut["H"].items() if k != "profile"},
                                {k: v for k, v in n_cut["H"].items() if k != "profile"}],
                         cut_V=[{k: v for k, v in b_cut["V"].items() if k != "profile"},
                                {k: v for k, v in n_cut["V"].items() if k != "profile"}],
                         timing_violations_end=tviol_end, stations_report=srep, eq_violations=eqbad, overlaps=nov, applied=ok,
                         cores_after={M.inst[i]: dict(origin_um=[round(v, 4) for v in M.core_origin(i)],
                                                      orient=M.core_orient(i)) for i in range(M.n)}))
        log("  bit-mm %.0f -> %.0f  ovf H %.0f -> %.0f  V %.0f -> %.0f  cutH %.2f -> %.2f  cutV %.2f -> %.2f  "
            "moved %d  eq %s  stations %s" % (base_bitum / 1e3, new_bitum / 1e3, b_oH, n_oH, b_oV, n_oV,
                                              b_cut["H"]["worst_ratio"], n_cut["H"]["worst_ratio"],
                                              b_cut["V"]["worst_ratio"], n_cut["V"]["worst_ratio"], moved,
                                              "OK" if not eqbad else eqbad[:4], srep))
    for k in P:
        if k != "partition_types" and json.dumps(P[k], sort_keys=True) != json.dumps(Q[k], sort_keys=True):
            raise AssertionError(f"top-level key {k} changed")
    out_sha = None
    if a.out_plan:
        try:
            import schema as S
            base_errs = set(map(str, S.validate(copy.deepcopy(P))))
            errs = [e for e in map(str, S.validate(copy.deepcopy(Q))) if e not in base_errs]
        except Exception as e:     # schema module not importable: recorded
            errs = ["schema check unavailable: %s" % e]
        txt = json.dumps(Q, indent=1) + "\n"
        Path(a.out_plan).write_text(txt)
        out_sha = hashlib.sha256(txt.encode()).hexdigest()
        # route_supply before / after (the plan's own model, same flags)
        rsd = Path(a.rs_out or (Path(a.event).parent if a.event else Path(a.out_plan).parent))
        types = [r["type"] for r in rows]
        for halv in ("full",) + (("none",) if a.grt_halving == "none" else ()):
            rb = rs_rows(plan, die, repo, types, a.ref_dirs, halv, rsd / f"rs_before_{halv}")
            ra = rs_rows(Path(a.out_plan), die, repo, types, a.ref_dirs, halv, rsd / f"rs_after_{halv}")
            for r in rows:
                r[f"route_supply_{halv}"] = [rs_summary(rb.get(r["type"])), rs_summary(ra.get(r["type"]))]
        for r in rows:
            r["schema_new_errors"] = errs[:5]
    rec = dict(schema=SCHEMA, tool="tools/die_plan/core_place.py", lane="CORE-PLACE-1", advisory=True,
               eq_by_construction="positions/orients only; eq_gate per type", base_plan=str(a.plan),
               base_plan_sha256=hashlib.sha256(raw).hexdigest(), plan_output=a.out_plan, plan_output_sha256=out_sha,
               cfg={k: v for k, v in cfg.items() if k != "rs"}, rows=rows)
    if a.event:
        Path(a.event).write_text(json.dumps(rec, indent=1) + "\n")
    hdr = ["type", "applied", "moved", "bit_mm_before", "bit_mm_after", "pct", "ovfH", "ovfH_new", "ovfV", "ovfV_new",
           "cutH", "cutH_new", "cutV", "cutV_new", "rs_p99", "rs_p99_new", "rs_coreH", "rs_coreH_new"]
    print("\t".join(hdr))
    for r in rows:
        rsf = r.get("route_supply_full") or [{}, {}]
        print("\t".join(map(str, [r["type"], r["applied"], r["moved_cores"]] + r["bit_mm"] + [
            r["rudy_ovf_H"][0], r["rudy_ovf_H"][1], r["rudy_ovf_V"][0], r["rudy_ovf_V"][1],
            r["cut_H"][0]["worst_ratio"], r["cut_H"][1]["worst_ratio"], r["cut_V"][0]["worst_ratio"],
            r["cut_V"][1]["worst_ratio"], rsf[0].get("p99"), rsf[1].get("p99"), rsf[0].get("core_H"),
            rsf[1].get("core_H")])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
