#!/usr/bin/env python3
"""LINK-SITES (FABLE-FIX-QC-CB 11-20): plan rows for the register banks of a bound type that sit between hard-core pins.

Why (FABLE-PD-QC-1840 class A, QC cb family, 11 held rows at -1.3 to -8.6 ns): the tile-link delay lines (u_d<N>_u_t_*, the
R8 strap pads u_r8b_*), the core-pin pipe registers (u_pc_nk_*) and the fabric stations have no plan site or a 405-um one;
placement keeps the stages of a line at one end and the last hop crosses a 458-um tile macro that takes no buffer.

Method: the bank graph is read from the bound wrapper RTL (ot_dp_dly / ot_dp_dly_cnt / ot_dp_st / ot_dp_lk instances, the
fabric stations, the hard cores of the plan with their pins files); every movable bank is put on a rectilinear route around the
hard cores so that the worst register-to-register leg of the type is minimal (even spacing along each chain, then a min-max
relaxation for the branch points).  Legs are L1 lengths of routes that stay outside every hard core.

Rows written to OUT_PLAN (the type only):
  relay_sites        one site per bit for every delay-line stage, strap bank, fabric station register and ring read bank
                     (0 cycles); the core-pin pipe register u_pc_* sits AT its core pin, bit by bit (core-pin register form).
  internal_stations  regs_um of every bus row re-spaced on the route; a row that cannot hold --cap with its stations gets
                     more (report.cycles: bus, before, after) -- the lane fixed_cycles are NOT edited here.
  budgets.r_dly_lockup.<type>.seg = --seg when given (kit_dly_lockup: hop lockup latch on every segment boundary; the sites
                     written here use the <inst>_sg<j> names of that split).
Report: every leg (from, to, um), legs over --cap, chains whose depth cannot hold the cap (cycles needed), keys written.

  link_sites.py PLAN TYPE BOUND.sv OUT_PLAN REPORT.json --pins-root DIR [--flops NAMES.txt] [--cap 300] [--seg 1] [--no-grow]
Estimator + row writer: it edits no live plan and holds nothing.
"""
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
SEL_RE = re.compile(r"u_(?:pd\d+|d\d+|lpad)_\w+")       # kit_dly_lockup.DEFAULT_RE
ANCH_PITCH, ANCH_BITS = 4.32, 55


# ------------------------------------------------------------------------------------------------ RTL
def strip_comments(t):
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", t, flags=re.S))


INST = re.compile(r"\b([A-Za-z_]\w*)\s*(?:#\s*\(((?:[^()]|\([^()]*\))*)\))?\s+([A-Za-z_]\w*)\s*\(((?:[^();]|\((?:[^()]|\([^()]*\))*\))*)\)\s*;", re.S)
PORT = re.compile(r"\.(\w+)\s*\(((?:[^()]|\([^()]*\))*)\)")
KW = {"module", "assign", "input", "output", "wire", "logic", "reg", "inout", "always", "if", "else", "begin", "end"}


def instances(sv):
    body = strip_comments(sv)
    out = []
    for m in INST.finditer(body):
        mod, par, nm, ports = m.groups()
        if mod in KW:
            continue
        P = {k: v for k, v in PORT.findall(ports)}
        prm = {k: int(v) for k, v in re.findall(r"\.(\w+)\(\s*(\d+)\s*\)", par or "")}
        out.append((mod, prm, nm, P))
    return out


def ids(expr):
    expr = re.sub(r"\d+'[bhdo][0-9a-fA-F_xz]+", "", expr or "")
    return [x for x in re.findall(r"[A-Za-z_]\w*", expr)]


# ------------------------------------------------------------------------------------------------ geometry
class Geo:
    def __init__(self, die, rects, halo=1.0, lane=8.0):
        self.die = die
        self.rects = [(r[0] - halo, r[1] - halo, r[2] + halo, r[3] + halo) for r in rects]
        self.corners = []
        for r in self.rects:
            for x in (r[0] - lane, r[2] + lane):
                for y in (r[1] - lane, r[3] + lane):
                    if self.free((x, y)):
                        self.corners.append((x, y))
        n = len(self.corners)
        INF = float("inf")
        self.D = [[INF] * n for _ in range(n)]
        self.N = [[None] * n for _ in range(n)]
        for i in range(n):
            self.D[i][i] = 0.0
            for j in range(n):
                if i != j and self.lclear(self.corners[i], self.corners[j]):
                    self.D[i][j] = L1(self.corners[i], self.corners[j])
                    self.N[i][j] = j
        for k in range(n):
            Dk = self.D[k]
            for i in range(n):
                dik = self.D[i][k]
                if dik == INF:
                    continue
                Di, Ni = self.D[i], self.N[i]
                for j in range(n):
                    v = dik + Dk[j]
                    if v < Di[j] - 1e-9:
                        Di[j] = v
                        Ni[j] = Ni[k]
        self._vis = {}
        self._dist = {}

    def free(self, p, m=2.0):
        d = self.die
        if not (d[0] + m <= p[0] <= d[2] - m and d[1] + m <= p[1] <= d[3] - m):
            return False
        return not any(r[0] < p[0] < r[2] and r[1] < p[1] < r[3] for r in self.rects)

    def seg_clear(self, a, b):
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        for r in self.rects:
            if x0 < r[2] and x1 > r[0] and y0 < r[3] and y1 > r[1]:
                return False
        return True

    def bend(self, a, b):
        """a clear L from a to b: the bend point, or None"""
        for c in ((b[0], a[1]), (a[0], b[1])):
            if self.seg_clear(a, c) and self.seg_clear(c, b):
                return c
        return None

    def lclear(self, a, b):
        return self.bend(a, b) is not None

    def vis(self, p):
        k = (round(p[0], 1), round(p[1], 1))
        v = self._vis.get(k)
        if v is None:
            v = [(i, L1(p, c)) for i, c in enumerate(self.corners) if self.lclear(p, c)]
            self._vis[k] = v
        return v

    def dist(self, a, b):
        k = (round(a[0], 1), round(a[1], 1), round(b[0], 1), round(b[1], 1))
        v = self._dist.get(k)
        if v is not None:
            return v
        if self.lclear(a, b):
            v = L1(a, b)
        else:
            v = float("inf")
            vb = self.vis(b)
            for i, da in self.vis(a):
                Di = self.D[i]
                for j, db in vb:
                    w = da + Di[j] + db
                    if w < v:
                        v = w
        self._dist[k] = v
        return v

    def route(self, a, b):
        """polyline a -> b (axis-parallel pieces) outside every rect"""
        if self.lclear(a, b):
            pts = [a, b]
        else:
            best = None
            vb = self.vis(b)
            for i, da in self.vis(a):
                for j, db in vb:
                    w = da + self.D[i][j] + db
                    if best is None or w < best[0]:
                        best = (w, i, j)
            if best is None or best[0] == float("inf"):
                return [a, b]
            _w, i, j = best
            pts = [a, self.corners[i]]
            while i != j:
                i = self.N[i][j]
                pts.append(self.corners[i])
            pts.append(b)
        out = [pts[0]]
        for p, q in zip(pts, pts[1:]):
            c = self.bend(p, q)
            if c is not None and c != p and c != q:
                out.append(c)
            out.append(q)
        return out

    @staticmethod
    def along(poly, fr):
        seg = [L1(p, q) for p, q in zip(poly, poly[1:])]
        tot = sum(seg)
        t = fr * tot
        for (p, q), s in zip(zip(poly, poly[1:]), seg):
            if t <= s or (p, q) == (poly[-2], poly[-1]):
                f = 0.0 if s == 0 else min(1.0, t / s)
                return (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)
            t -= s
        return poly[-1]

    def push_free(self, p, step=2.0):
        if self.free(p):
            return p
        for r in range(1, 200):
            for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r), (r, r), (-r, r), (r, -r), (-r, -r)):
                q = (p[0] + dx * step, p[1] + dy * step)
                if self.free(q):
                    return q
        return p


def pin_abs(c, x, y):
    o, (w, h) = c.get("origin_um") or [0, 0], (c.get("outline_um") or [0, 0])[:2]
    ori = str(c.get("orient", "R0"))
    if ori in ("MX", "FS"):
        return (o[0] + x, o[1] + h - y)
    if ori in ("MY", "FN"):
        return (o[0] + w - x, o[1] + y)
    if ori in ("R180", "S"):
        return (o[0] + w - x, o[1] + h - y)
    return (o[0] + x, o[1] + y)


def core_pins(c, roots):
    f = c.get("pins_file")
    if not f:
        return {}
    for r in roots:
        p = Path(r) / f
        if p.is_file():
            d = json.loads(p.read_text())
            out = collections.defaultdict(dict)
            for q in d.get("pins", d) if isinstance(d, dict) else d:
                nm = str(q["name"])
                m = re.match(r"(\w+)\[(\d+)\]$", nm)
                out[m.group(1) if m else nm][int(m.group(2)) if m else 0] = pin_abs(c, float(q["x"]), float(q["y"]))
            return out
    raise SystemExit(f"link_sites: pins file {f} not found under {roots}")


def out_of(c, p, d=4.0):
    """a core pin pushed d um out of the nearest core edge"""
    o, (w, h) = c["origin_um"], c["outline_um"][:2]
    e = [(p[0] - o[0], (-d, 0)), (o[0] + w - p[0], (d, 0)), (p[1] - o[1], (0, -d)), (o[1] + h - p[1], (0, d))]
    k = min(e, key=lambda x: abs(x[0]))
    x = o[0] if k[1][0] < 0 else o[0] + w if k[1][0] > 0 else p[0]
    y = o[1] if k[1][1] < 0 else o[1] + h if k[1][1] > 0 else p[1]
    return (x + k[1][0], y + k[1][1])


# ------------------------------------------------------------------------------------------------ model
class Node:
    __slots__ = ("key", "fixed", "pos", "half", "kind", "meta")

    def __init__(self, key, fixed, pos=None, half=0.0, kind="", meta=None):
        self.key, self.fixed, self.pos, self.half, self.kind, self.meta = key, fixed, pos, half, kind, meta or {}


GEO = None
HINT = {}
PC_SITES = False    # --pc-sites: write relay_sites keys for the u_pc_* core-pin pipe registers (default off: the kit's core-input
                    # hook seats them at the pin and a FIRM relay site makes global_place fail ODB-0359, QC cb proof p1 11-20)
PC_SLACK = 0.0      # --pc-slack: a core-pin pipe register may sit up to this far (L1 um) from its pin (0 = AT the pin)


def row_layout(e, bus, geo, W, H, cap, nmin, shadows):
    """stations of a bus row evenly on its own polyline (window far end / from_um -> regs -> to_um / window far end):
    the row keeps the channel it was planned in; count = what the cap needs (>= nmin)"""
    lo, hi = sorted(bus["window_um"])
    f = bus["face"]
    mk = lambda c: {"N": (c, H), "S": (c, 0.0), "E": (W, c), "W": (0.0, c)}[f]
    regs = [tuple(r) for r in e["regs_um"]]
    ends = sorted((mk(lo), mk(hi)), key=lambda q: -L1(q, regs[0] if bus["dir"] == "in" else regs[-1]))
    ok = lambda q: geo.free(q, 3.0) and not any(r[0] - 4 <= q[0] <= r[2] + 4 and r[1] - 4 <= q[1] <= r[3] + 4 for r in shadows)
    n = max(len(regs), nmin)
    while True:
        for end in [mk((lo + hi) / 2)] + ends:
            pts = [end] + regs + [tuple(e["to_um"])] if bus["dir"] == "in" else [tuple(e["from_um"])] + regs + [end]
            poly = [pts[0]]
            for a, b in zip(pts, pts[1:]):
                poly += geo.route(geo.push_free(a), geo.push_free(b)) + [b]
            tot = sum(L1(a, b) for a, b in zip(poly, poly[1:]))
            if math.ceil(tot / cap) - 1 > n:
                continue
            st = []
            for j in range(1, n + 1):
                best = None
                for off in (0, 6, -6, 12, -12, 20, -20, 30, -30, 45, -45, 60, -60, 80, -80):
                    q = Geo.along(poly, min(1.0, max(0.0, j / (n + 1) + off / tot)))
                    if ok(q):
                        best = q
                        break
                st.append(best or geo.push_free(Geo.along(poly, j / (n + 1))))
            inner = [L1(a, b) for a, b in zip(st, st[1:])]
            if bus["dir"] == "in":
                hops = [max(L1(q, st[0]) for q in ends)] + inner + [L1(st[-1], pts[-1])]
            else:
                hops = [L1(pts[0], st[0])] + inner + [max(L1(st[-1], q) for q in ends)]
            if max(hops) <= cap + 0.9:
                return [(round(q[0], 3), round(q[1], 3)) for q in st], round(max(hops), 1), round(tot, 1)
        if n > len(regs) + 12:
            return [(round(q[0], 3), round(q[1], 3)) for q in st], round(max(hops), 1), round(tot, 1)
        n += 1


def build(t, sv, pins_roots, seg):
    W, H = t["outline_um"]
    hc = {c["inst"]: c for c in t.get("hard_cores", [])}
    buses = {b["name"]: b for b in t.get("buses", [])}
    rows = {e["conn"][4:]: e for e in t.get("internal_stations", []) if str(e.get("conn", "")).startswith("bus:")}
    nodes, edges, drv, alias = {}, set(), {}, {}
    insts = instances(sv)
    by_name = {i[2]: i for i in insts}
    rtl2core = {}
    for mod, prm, nm, P in insts:
        if nm in hc:
            rtl2core[nm] = nm
        elif nm.startswith("u_cland_") and "cl_" + nm[8:] in hc:
            rtl2core[nm] = "cl_" + nm[8:]

    def add(n):
        nodes[n.key] = n
        return n

    def face_pts(bus):
        b = buses[bus]
        lo, hi = sorted(b["window_um"])
        f = b["face"]
        mk = lambda c: {"N": (c, H), "S": (c, 0.0), "E": (W, c), "W": (0.0, c)}[f]
        return mk(lo), mk(hi), mk((lo + hi) / 2)

    chains = {}                                   # instance -> [stage node keys]
    for mod, prm, nm, P in insts:
        if nm in rtl2core:
            c = hc[rtl2core[nm]]
            pins = core_pins(c, pins_roots)
            for port, expr in P.items():
                if port not in pins or len(pins[port]) < 8:
                    continue
                pts = list(pins[port].values())
                cen = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
                half = max(L1(cen, p) for p in pts)
                an = out_of(c, cen)
                if GEO is not None and (not (GEO.free(an) and any(GEO.free((an[0] + dx, an[1] + dy)) for dx, dy in ((30, 0), (-30, 0), (0, 30), (0, -30))))
                                        or any(not GEO.free(out_of(c, q)) for q in pts)):
                    # the pin edge abuts another core (QC ring under a tile): leave by the nearest free side of the core
                    o, (cw, chh) = c["origin_um"], c["outline_um"][:2]
                    cand = [(o[0] - 8, o[1] + chh / 2), (o[0] + cw + 8, o[1] + chh / 2), (o[0] + cw / 2, o[1] - 8), (o[0] + cw / 2, o[1] + chh + 8)]
                    cand = [q for q in cand if GEO.free(q, 4.0)]
                    hint = HINT.get(nm[8:]) if nm.startswith("u_cland_") else None
                    if cand:
                        an = min(cand, key=lambda q: L1(q, hint) if hint else L1(q, cen))
                n = add(Node(f"{nm}.{port}", True, an, half, "pin", dict(core=rtl2core[nm], port=port, pins=pins[port], rtl=nm)))
                n.meta["expr"] = expr
        elif mod in ("ot_dp_dly", "ot_dp_dly_keep"):
            D = prm.get("D", 1)
            lp = nm.startswith("u_lpad_") and nm[7:] in rows and len(rows[nm[7:]].get("regs_um") or []) == D
            split = seg and SEL_RE.fullmatch(nm) and D > seg and re.fullmatch(r"[A-Za-z_]\w*", P.get("q", "").strip())
            ks = []
            if split:
                n_sg = max(1, math.ceil(D / seg))
                sizes = [D // n_sg + (1 if j < D % n_sg else 0) for j in range(n_sg)]
            for s in range(D):
                if lp:
                    stage = dict(row=nm[7:], idx=s)
                elif split:
                    j, o = 0, s
                    while o >= sizes[j]:
                        o -= sizes[j]
                        j += 1
                    stage = dict(fam=f"{nm}_sg{j}" + (f".r[{o}]" if o < sizes[j] - 1 else ".q"), two=o < sizes[j] - 1)
                else:
                    stage = dict(fam=nm + (f".r[{s}]" if s < D - 1 else ".q"), two=s < D - 1)
                stage.update(W=prm.get("W", 1), inst=nm, stage=s)
                ks.append(add(Node(f"{nm}#{s}", False, None, 12.0, "lpad" if lp else "dly", stage)).key)
            chains[nm] = ks
        elif mod == "ot_dp_dly_cnt":
            chains[nm] = [add(Node(f"{nm}#0", False, None, 12.0, "cnt", dict(W=prm.get("W", 1), inst=nm, dmax=prm.get("DMAX", 1)))).key]
        elif mod == "ot_dp_st":
            if nm.startswith("u_bout_") and nm[7:] in buses:
                lo, hi, _c = face_pts(nm[7:])
                add(Node(nm + "@lo", True, lo, 0.0, "face"))
                add(Node(nm + "@hi", True, hi, 0.0, "face"))
                chains[nm] = [nm + "@lo", nm + "@hi"]
            elif nm.startswith("u_bin_") and nm[6:] in buses:
                ring = "u_cland_" + nm[6:] in rtl2core
                if ring:
                    chains[nm] = [add(Node(nm + "#0", False, None, 12.0, "bin", dict(W=prm.get("W", 1), inst=nm))).key]
                else:
                    _lo, _hi, c = face_pts(nm[6:])
                    chains[nm] = [add(Node(nm + "#0", True, c, abs(buses[nm[6:]]["window_um"][1] - buses[nm[6:]]["window_um"][0]) / 2, "face")).key]
            elif re.fullmatch(r"u_ist_(\w+)_(\d+)", nm):
                m = re.fullmatch(r"u_ist_(\w+)_(\d+)", nm)
                if m.group(1) in rows:
                    chains[nm] = [add(Node(nm + "#0", False, None, 12.0, "ist", dict(row=m.group(1), idx=int(m.group(2)), inst=nm))).key]
        elif mod.startswith("qfd_c_xstn"):
            a = add(Node(nm + "#in", False, None, 12.0, "xin", dict(inst=nm)))
            b = add(Node(nm + "#tap", False, None, 12.0, "xtap", dict(inst=nm)))
            edges.add((a.key, b.key))
            chains[nm] = [a.key, b.key]
    # drivers of signals
    OUTS = {"ot_dp_dly": ("q",), "ot_dp_dly_keep": ("q",), "ot_dp_dly_cnt": ("q",), "ot_dp_st": ("q", "eq")}
    INS = {"ot_dp_dly": ("d",), "ot_dp_dly_keep": ("d",), "ot_dp_dly_cnt": ("d",), "ot_dp_st": ("d", "ea")}
    for mod, prm, nm, P in insts:
        if mod in ("ot_dp_lk", "ot_dp_hd"):
            o, i = ("q", "d") if mod == "ot_dp_lk" else ("y", "a")
            for x in ids(P.get(o, "")):
                alias[x] = ids(P.get(i, ""))
        elif nm in rtl2core:
            for port, expr in P.items():
                k = f"{nm}.{port}"
                if k in nodes and port in ("q", "n_y", "t_out"):
                    for x in ids(expr):
                        drv[x] = k
        elif nm in chains:
            if mod.startswith("qfd_c_xstn"):
                for x in ids(P.get("a_d", "")):
                    drv[x] = nm + "#in"
                for x in ids(P.get("tap_d", "")):
                    drv[x] = nm + "#tap"
            elif mod in OUTS and not nm.startswith("u_bout_"):
                for o in OUTS[mod]:
                    for x in ids(P.get(o, "")):
                        drv[x] = chains[nm][-1]

    def resolve(x, d=0):
        if x in drv:
            return {drv[x]}
        if x in alias and d < 6:
            out = set()
            for y in alias[x]:
                out |= resolve(y, d + 1)
            return out
        return set()
    for mod, prm, nm, P in insts:
        if nm in rtl2core:
            for port, expr in P.items():
                k = f"{nm}.{port}"
                if k in nodes and port not in ("q", "n_y", "t_out"):
                    for x in ids(expr):
                        for s in resolve(x):
                            edges.add((s, k))
        elif nm in chains:
            first = chains[nm][0]
            ins = ("b_d",) if mod.startswith("qfd_c_xstn") else INS.get(mod, ())
            for i in ins:
                for x in ids(P.get(i, "")):
                    for s in resolve(x):
                        if nm.startswith("u_bout_"):
                            bus = nm[7:]
                            # out-bus stations are inserted by the kit generator (kit_istations u_ist_<bus>_<k>): a bound RTL
                            # without them still has the row's stations between the driver and the face register
                            if bus in rows and buses[bus]["dir"] == "out" and not any(re.fullmatch(rf"u_ist_{re.escape(bus)}_\d+", n) for n in by_name):
                                ks = []
                                for j in range(len(rows[bus].get("regs_um") or [])):
                                    k = f"u_ist_{bus}_{j}#0"
                                    if k not in nodes:
                                        add(Node(k, False, None, 12.0, "ist", dict(row=bus, idx=j, inst=f"u_ist_{bus}_{j}", virtual=True)))
                                    ks.append(k)
                                if ks:
                                    edges.add((s, ks[0]))
                                    continue
                            edges.add((s, chains[nm][0]))
                            edges.add((s, chains[nm][1]))
                        else:
                            edges.add((s, first))
            if mod in ("ot_dp_dly", "ot_dp_dly_keep"):
                for a, b in zip(chains[nm], chains[nm][1:]):
                    edges.add((a, b))
    # census ends of the bus rows: window ends -> first station, last station -> to_um (in); from_um -> first (out)
    for bus, e in rows.items():
        st = sorted((n for n in nodes.values() if n.meta.get("row") == bus), key=lambda n: n.meta["idx"])
        if not st or bus not in buses:
            continue
        lo, hi, _c = face_pts(bus)
        if buses[bus]["dir"] == "in":
            for tag, p in (("lo", lo), ("hi", hi)):
                add(Node(f"win:{bus}@{tag}", True, p, 0.0, "win"))
                edges.add((f"win:{bus}@{tag}", st[0].key))
            add(Node(f"to:{bus}", True, tuple(e["to_um"]), 0.0, "rowend"))
            edges.add((st[-1].key, f"to:{bus}"))
        else:
            add(Node(f"from:{bus}", True, tuple(e["from_um"]), 0.0, "rowend"))
            edges.add((f"from:{bus}", st[0].key))
            for tag, p in (("lo", lo), ("hi", hi)):
                add(Node(f"win:{bus}@{tag}", True, p, 0.0, "win"))
                edges.add((st[-1].key, f"win:{bus}@{tag}"))
            for a, b in zip(st, st[1:]):
                edges.add((a.key, b.key))
    # core-pin pipe registers sit at their pin
    for a, b in list(edges):
        na, nb = nodes[a], nodes[b]
        if nb.kind == "pin" and na.kind == "dly" and len(chains.get(na.meta["inst"], [])) == 1 and re.match(r"u_pc_", na.meta["inst"]):
            na.fixed, na.pos, na.kind = PC_SLACK <= 0, nb.pos, "pc"
            na.meta["pin"] = b
            na.meta["pin_xy"] = nb.pos
    used = {k for e in edges for k in e}
    for k in [k for k in nodes if k not in used]:
        del nodes[k]
    return nodes, sorted(edges), chains, rows, buses, hc


def solve(nodes, edges, geo, sweeps=40):
    adj = collections.defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    pos = {k: n.pos for k, n in nodes.items() if n.pos is not None}
    for k in pos:
        pos[k] = geo.push_free(pos[k]) if nodes[k].kind not in ("win", "face", "rowend") else pos[k]
    anchor = lambda p: geo.push_free(p)
    # even spacing along the most stretched unplaced path first
    while True:
        best = None
        for u in list(pos):
            for v0 in adj[u]:
                if v0 in pos:
                    continue
                prev, front, hit = {v0: u}, [v0], None
                while front and hit is None:
                    nf = []
                    for x in front:
                        for y in sorted(adj[x]):
                            if y in prev or y == u:
                                continue
                            prev[y] = x
                            if y in pos:
                                hit = y
                                break
                            nf.append(y)
                        if hit:
                            break
                    front = nf
                if hit is None:
                    continue
                path = [hit]
                while path[-1] != u:
                    path.append(prev[path[-1]])
                path.reverse()
                d = geo.dist(anchor(pos[u]), anchor(pos[hit])) / (len(path) - 1)
                if best is None or d > best[0]:
                    best = (d, path)
        if best is None:
            break
        _d, path = best
        poly = geo.route(anchor(pos[path[0]]), anchor(pos[path[-1]]))
        n = len(path) - 1
        for j, k in enumerate(path[1:-1], 1):
            pos[k] = geo.push_free(geo.along(poly, j / n))
    for k in nodes:                                  # dangling
        if k not in pos:
            nb = [pos[x] for x in adj[k] if x in pos]
            pos[k] = nb[0] if nb else (geo.die[2] / 2, geo.die[3] / 2)

    def cost(k, p):
        if nodes[k].kind == "pc" and L1(p, nodes[k].meta["pin_xy"]) > PC_SLACK:
            return (1e9, 1e9)                     # --pc-slack: never further than PC_SLACK from its pin
        ws = [geo.dist(p, anchor(pos[x])) + nodes[x].half * (nodes[x].kind == "pin" and nodes[k].kind != "pc") for x in adj[k]]
        return (max(ws), sum(ws)) if ws else (0.0, 0.0)
    mov = [k for k, n in nodes.items() if not n.fixed]
    for _s in range(sweeps):
        moved = 0
        for k in mov:
            cur = cost(k, pos[k])
            bestp, bestc = pos[k], cur
            for step in (48.0, 24.0, 12.0, 6.0):
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                    p = (pos[k][0] + dx * step, pos[k][1] + dy * step)
                    if not geo.free(p, 6.0):
                        continue
                    c = cost(k, p)
                    if c[0] < bestc[0] - 0.5 or (abs(c[0] - bestc[0]) <= 0.5 and c[1] < bestc[1] - 0.5 and c[0] <= bestc[0]):
                        bestp, bestc = p, c
            nbs = sorted(adj[k])
            for i_ in range(len(nbs)):                # midpoints of the routes between two neighbours (leaves local pockets)
                for j_ in range(i_ + 1, len(nbs)):
                    p = geo.push_free(geo.along(geo.route(anchor(pos[nbs[i_]]), anchor(pos[nbs[j_]])), 0.5))
                    c = cost(k, p)
                    if c[0] < bestc[0] - 0.5 or (c[0] <= bestc[0] + 0.5 and c[1] < bestc[1] - 5.0):
                        bestp, bestc = p, c
            if bestp != pos[k]:
                pos[k] = bestp
                moved += 1
        if not moved:
            break
    legs = []
    for a, b in edges:
        d = geo.dist(anchor(pos[a]), anchor(pos[b]))
        if nodes[a].meta.get("row") and nodes[b].meta.get("row") == nodes[a].meta.get("row") or "win" in (nodes[a].kind, nodes[b].kind) or "rowend" in (nodes[a].kind, nodes[b].kind):
            d = L1(pos[a], pos[b])                    # a row is measured the way the census does
        d += sum(nodes[x].half for x in (a, b) if nodes[x].kind == "pin" and nodes[a if x == b else b].kind != "pc")
        if nodes[a].kind == "pc" and nodes[b].kind == "pin":
            d = max(8.0, round(L1(pos[a], nodes[a].meta["pin_xy"]), 1))
        legs.append((round(d, 1), a, b))
    return pos, legs


def strip(geo, p, w):
    """anchors for w bits around p: a row of 4.32-um pitch points, 55 bits each, along x where that is free, else along y"""
    n = max(1, math.ceil(w / ANCH_BITS))
    for ax in (0, 1):
        pts = [(p[0] + (i - (n - 1) / 2) * ANCH_PITCH * (ax == 0), p[1] + (i - (n - 1) / 2) * ANCH_PITCH * (ax == 1)) for i in range(n)]
        if all(geo.free(q, 3.0) for q in pts):
            return pts
    return [p]


def main():
    ap = argparse.ArgumentParser()
    for a in "plan type sv out report".split():
        ap.add_argument(a)
    ap.add_argument("--pins-root", action="append", required=True)
    ap.add_argument("--flops", help="flop names of a placed kit of the type (one per line): only bits that exist get a key")
    ap.add_argument("--cap", type=float, default=300.0)
    ap.add_argument("--target", type=float, default=285.0, help="a row grows until its worst leg is within this")
    ap.add_argument("--seg", type=int, default=0, help="budgets.r_dly_lockup seg for the type (0 = leave the plan key alone)")
    ap.add_argument("--no-grow", action="store_true")
    ap.add_argument("--max-add", type=int, default=6)
    ap.add_argument("--min-stations", action="append", default=[], metavar="BUS=N", help="a bus row gets at least N stations (class balance)")
    ap.add_argument("--pc-sites", action="store_true", help="also write relay_sites keys for the u_pc_* core-pin pipe registers "
                    "(off by default: the kit core-input hook places them; a FIRM site there fails global_place ODB-0359)")
    ap.add_argument("--pc-slack", type=float, default=0.0, help="core-pin pipe registers u_pc_* may sit up to this L1 distance (um) "
                    "from their pin instead of AT it (0 cycles; for a tile link whose stages cannot reach the pin within the cap)")
    A = ap.parse_args()
    global PC_SLACK, PC_SITES
    PC_SLACK, PC_SITES = A.pc_slack, A.pc_sites
    if PC_SLACK > 0 and not PC_SITES:
        ap.error("--pc-slack needs --pc-sites (without plan sites the kit hook seats u_pc_* AT the pin)")
    raw = json.loads(Path(A.plan).read_text())
    t = raw["partition_types"][A.type]
    sv = Path(A.sv).read_text()
    Wd, Hd = t["outline_um"]
    seg = A.seg or int(((raw.get("budgets") or {}).get("r_dly_lockup") or {}).get(next((b for b in sorted((raw.get("budgets") or {}).get("r_dly_lockup") or {}, key=len, reverse=True) if A.type.startswith(b)), ""), {}).get("seg", 8) or 8)
    if not any(A.type.startswith(b) for b in ((raw.get("budgets") or {}).get("r_dly_lockup") or {})) and not A.seg:
        seg = 0
    rects = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1]) for c in t.get("hard_cores", [])]
    geo = Geo((0.0, 0.0, Wd, Hd), rects)
    exist = None
    if A.flops:
        exist = collections.defaultdict(set)
        for ln in Path(A.flops).read_text().split("\n"):
            nm = re.sub(r"\$_[A-Za-z0-9_]*$", "", ln.strip().replace("\\", ""))
            nm = re.sub(r"^u_bound[./]", "", nm)
            m = re.match(r"(.*?)(?:_sg\d+)?[./](?:r\[\d+\]\[(\d+)\]|q\[(\d+)\]|r\[(\d+)\]|[a-z_]+\[(\d+)\])$", nm)
            if m:
                exist[m.group(1)].add(int(next(g for g in m.groups()[1:] if g is not None)))
    cycles = collections.OrderedDict()
    global GEO
    GEO = geo
    busd = {b["name"]: b for b in t.get("buses", [])}
    hcs = {c["inst"]: c for c in t.get("hard_cores", [])}
    shadows = []                                   # the strip between a face ring core and its face
    for c in t.get("hard_cores", []):
        if c["inst"].startswith("cl_"):
            x0, y0 = c["origin_um"]
            x1, y1 = x0 + c["outline_um"][0], y0 + c["outline_um"][1]
            if y0 < 80:
                shadows.append((x0, 0.0, x1, y0))
            if Hd - y1 < 80:
                shadows.append((x0, y1, x1, Hd))
            if x0 < 80:
                shadows.append((0.0, y0, x0, y1))
            if Wd - x1 < 80:
                shadows.append((x1, y0, Wd, y1))
    minst = {x.split("=")[0]: int(x.split("=")[1]) for x in A.min_stations}
    layout = {}
    for e in t.get("internal_stations", []):
        bus = str(e.get("conn", ""))[4:]
        if bus in busd and e.get("regs_um") and e.get("from_um") and e.get("to_um"):
            layout[bus] = row_layout(e, busd[bus], geo, Wd, Hd, A.target, minst.get(bus, 0), shadows)
            HINT[bus] = layout[bus][0][0]
    nodes, edges, chains, rows, buses, hc = build(t, sv, A.pins_root, seg)
    for bus, (st_xy, worst, tot) in layout.items():
        st = sorted((n for n in nodes.values() if n.meta.get("row") == bus), key=lambda n: n.meta["idx"])
        if not st:
            continue
        last = st[-1]
        outs = [(a_, b_) for a_, b_ in edges if a_ == last.key]
        extra = len(st_xy) - len(st)
        if extra > 0:
            edges = [x for x in edges if x not in outs]
            prev = last.key
            for j in range(extra):
                nk = f"{last.key}+{j + 1}"
                nodes[nk] = Node(nk, False, None, 12.0, last.kind, dict(row=bus, idx=last.meta["idx"] + j + 1, extra=True))
                edges.append((prev, nk))
                prev = nk
                st.append(nodes[nk])
            edges += [(prev, b_) for _a, b_ in outs]
        for n_, xy in zip(st, st_xy):
            n_.fixed, n_.pos = True, xy
    pos, legs = solve(nodes, edges, geo)
    # ------------------------------------------------------------------ rows
    sites = {}
    old = dict(t.get("relay_sites") or {})
    tapbits = collections.defaultdict(set)          # bits of a fabric tap bank that exist = the plan keys <xstn>.u_st.tap_d[b]
    for key in old:
        m = re.match(r"(\w+)\.u_st\.tap_d\[(\d+)\]$", key)
        if m:
            tapbits[m.group(1)].add(int(m.group(2)))
    pred = collections.defaultdict(set)
    for a, b in edges:
        pred[b].add(a)

    def bits_of(inst, w):
        if exist is not None and inst in exist:
            return sorted(exist[inst])
        for a in pred.get(inst + "#0", ()):
            if nodes[a].kind == "xtap" and tapbits.get(nodes[a].meta["inst"]):
                return sorted(b for b in tapbits[nodes[a].meta["inst"]] if b < w)
        return list(range(w))
    dropped = 0

    def put(fam, two, inst, w, p, sep="."):
        bl = bits_of(inst, w)
        an = strip(geo, p, len(bl))
        for i, b in enumerate(bl):
            q = an[min(len(an) - 1, i // ANCH_BITS)]
            sites[f"{fam}[{b}]"] = [round(q[0], 3), round(q[1], 3)]
    for k, n in nodes.items():
        p = pos[k]
        if n.kind == "dly":
            put(n.meta["fam"], n.meta["two"], n.meta["inst"], n.meta["W"], p)
        elif n.kind == "pc" and PC_SITES:
            pn = nodes[n.meta["pin"]]
            c = hc[pn.meta["core"]]
            for b in bits_of(n.meta["inst"], n.meta["W"]):
                q = pn.meta["pins"].get(b)
                q = out_of(c, q, 3.0) if q else pn.pos
                if PC_SLACK > 0:                      # the bank moved off its pin by (dx, dy): every bit keeps its pin offset
                    dx, dy = p[0] - n.meta["pin_xy"][0], p[1] - n.meta["pin_xy"][1]
                    q = geo.push_free((q[0] + dx, q[1] + dy))
                sites[f"{n.meta['inst']}.q[{b}]"] = [round(q[0], 3), round(q[1], 3)]
        elif n.kind == "cnt":
            for s in range(n.meta["dmax"]):
                put(f"{n.meta['inst']}/r[{s}]", True, n.meta["inst"], n.meta["W"], p)
    # existing plan keys of the fabric stations, ring read banks and fabric delay lines move with their node
    fam_node = {}
    for k, n in nodes.items():
        if n.kind == "xin":
            for f in ("b_d", "cap", "cnt", "run"):
                fam_node[f"{n.meta['inst']}.u_st.{f}"] = k
        elif n.kind == "xtap":
            fam_node[f"{n.meta['inst']}.u_st.tap_d"] = k
        elif n.kind == "bin":
            fam_node[n.meta["inst"] + "/q"] = k
            fam_node[n.meta["inst"] + "/eq"] = k
    grp = collections.defaultdict(list)
    for key in old:
        m = re.match(r"(.*?)(\[\d+\])?$", key)
        base = m.group(1)
        if base in fam_node:
            grp[base].append(key)
        elif re.match(r"u_d\d+_", key) and (key.split(".")[0] in chains or re.sub(r"_sg\d+$", "", key.split(".")[0]) in chains):
            dropped += 1                           # re-keyed above (stage names follow the segment split)
        elif re.match(r"u_pc_", key) and not PC_SITES:
            dropped += 1                           # the kit hook is the single placer of the core-pin pipe registers
        else:
            sites.setdefault(key, old[key])
    for base, keys in grp.items():
        p = pos[fam_node[base]]
        if base.endswith(("u_st.cap", "u_st.cnt", "u_st.run")):
            p = (p[0], p[1] - 8.64) if geo.free((p[0], p[1] - 8.64), 3.0) else p
        an = strip(geo, p, len(keys))
        srt = sorted(keys, key=lambda x: int(re.search(r"\[(\d+)\]$", x).group(1)) if re.search(r"\[(\d+)\]$", x) else -1)
        for i, key in enumerate(srt):
            q = an[min(len(an) - 1, i // ANCH_BITS)]
            sites[key] = [round(q[0], 3), round(q[1], 3)]
    t["relay_sites"] = dict(sorted(sites.items()))
    for bus, e in rows.items():
        st = sorted((n for n in nodes.values() if n.meta.get("row") == bus), key=lambda n: n.meta["idx"])
        if not st:
            continue
        n0 = len(e["regs_um"])
        e["regs_um"] = [[round(pos[n.key][0], 3), round(pos[n.key][1], 3)] for n in st]
        e["bits"] = e.get("bits")
        if len(st) != n0:
            cycles[bus] = dict(before=n0, after=len(st), dir=buses[bus]["dir"])
            e["note"] = (e.get("note") or "") + f" | FABLE-FIX-QC-CB 11-20 LINK-SITES: {n0}->{len(st)} stations (300 um hop cap), lane +{len(st) - n0} cycles"
        else:
            e["note"] = (e.get("note") or "") + " | FABLE-FIX-QC-CB 11-20 LINK-SITES: stations re-spaced on the route around the cores (300 um hop cap), 0 cycles"
    if A.seg:
        raw.setdefault("budgets", {}).setdefault("r_dly_lockup", {})[A.type] = dict(seg=A.seg)
    Path(A.out).write_text(json.dumps(raw, indent=1) + "\n")
    over = sorted((x for x in legs if x[0] > A.cap), reverse=True)
    rep = dict(type=A.type, cap_um=A.cap, seg=seg, nodes=len(nodes), movable=sum(1 for n in nodes.values() if not n.fixed), legs=len(legs),
               worst_leg_um=max(x[0] for x in legs) if legs else 0, legs_over_cap=len(over), over=[dict(um=d, a=a, b=b) for d, a, b in over[:40]],
               cycles=cycles, relay_keys=len(sites), relay_keys_before=len(old), fabric_delay_keys_rekeyed=dropped,
               positions={k: [round(pos[k][0], 1), round(pos[k][1], 1)] for k in sorted(pos)},
               all_legs=[[d, a, b] for d, a, b in sorted(legs, reverse=True)])
    Path(A.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("type", "seg", "nodes", "movable", "legs", "worst_leg_um", "legs_over_cap", "cycles", "relay_keys", "relay_keys_before")}))
    for d, a, b in over[:12]:
        print("  OVER", d, a, "->", b)


if __name__ == "__main__":
    main()
