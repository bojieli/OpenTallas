#!/usr/bin/env python3
"""HBM die: the planned die register hops as INSTANCES of the die netlist (coordinator phase 2, 2026-10-07).

The budget prices two kinds of die register hops that the generator never instanced:
  * r22 pin relays (OWNER 2026-10-07 DIE-WIDE INTERFACE RULE): a relay station abutting every hardened-block pin whose
    die segment is > 100 um (relay_ends.json, 500 ends on 365 buses), +1 cycle each;
  * common-clock wire stages: a segment of length L carries 1 + ceil((L - 359) / 412) hops (budget stage plan, r17),
    i.e. ceil((L - 359) / 412) intermediate registers.
Without them die STA times every die wire as one unbuffered, unregistered hop (r23c: -38 ns).  instance_relays()
rewrites the die model in place: every two-ended common-clock bus is cut into direction-homogeneous sub-buses, and each
gets the chain  source pin -> [relay at the source pin] -> wire stages along the Manhattan path -> [relay at the sink
pin] -> sink pin.  Each register is a generated master hfd_rly_<n> (one flop per bit: d in, q out, ck), placed in free
die area (macro halo 2.16 um) nearest its planned point, faces d toward the upstream node and q toward the downstream.
relay_libs() writes the SS / FF interface Liberty of every hfd_rly master (bus-level timing groups), from the relay
station recipe: SS clock insertion 70-90 ps (hfd_stn_r38 calibrate CKINS 80), FF 40-55 ps, ASAP7 DFF + output buffer.

Forwarded-clock segments (m['fclk']) and buses with more than two ends stay as they are (source-synchronous / broadcast;
checked inside the station views); so do clock / reset / PHY dfi nets (RELAY_SKIP_CLS).
"""
from __future__ import annotations

import math
import re
from collections import defaultdict

REACH_INTER_UM, REACH_INTRA_UM = 359.0, 412.0
RELAY_MIN_SEG_UM = 100.0
BIT_UM2 = 0.7               # station recipe: ~0.7 um2 per stage bit
HALO = 2.16


def lef_pins(text):
    """{macro: (w, h, {pin_base: [(x, y) centre per rect]})} of every MACRO in a LEF text"""
    out = {}
    for mm in re.finditer(r'\nMACRO (\S+)\n(.*?)\nEND \1\n', '\n' + text, re.S):
        name, body = mm.group(1), mm.group(2)
        sz = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', body)
        w, h = (float(sz.group(1)), float(sz.group(2))) if sz else (0.0, 0.0)
        pins = defaultdict(list)
        for pm in re.finditer(r'\n\s*PIN (\S+)\n(.*?)\n\s*END \1[ \t]*(?=\n)', body, re.S):
            if 'USE POWER' in pm.group(2) or 'USE GROUND' in pm.group(2):
                continue
            base = re.sub(r'\[\d+\]$', '', pm.group(1))
            r_ = re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', pm.group(2))
            if r_:
                x0, y0, x1, y1 = map(float, r_.groups())
                pins[base].append(((x0 + x1) / 2, (y0 + y1) / 2))
            if r_ and base != pm.group(1):     # the bit name too (real-port bindings name bits)
                pins[pm.group(1)].append(((x0 + x1) / 2, (y0 + y1) / 2))
        out[name] = (w, h, dict(pins))
    return out


def to_die(it, x, y, w, h):
    if it.orient in ('MY', 'R180'):
        x = w - x
    if it.orient in ('MX', 'R180'):
        y = h - y
    return it.x + x, it.y + y


class Free:
    """free-area finder over the placed instance boxes (bucketed)"""

    def __init__(self, boxes, W, H, B=200.0):
        self.W, self.H, self.B = W, H, B
        self.g = defaultdict(list)
        self.base = list(boxes)        # the hard blocks (relays added later are small and not path obstacles)
        self._blk = None
        for b in boxes:
            self.add(b)

    def add(self, b):
        x0, y0, x1, y1 = b
        for i in range(int(x0 // self.B), int(x1 // self.B) + 1):
            for j in range(int(y0 // self.B), int(y1 // self.B) + 1):
                self.g[(i, j)].append(b)

    def ok(self, b):
        x0, y0, x1, y1 = b
        if x0 < 1.0 or y0 < 1.0 or x1 > self.W - 1.0 or y1 > self.H - 1.0:
            return False
        for i in range(int(x0 // self.B), int(x1 // self.B) + 1):
            for j in range(int(y0 // self.B), int(y1 // self.B) + 1):
                for c in self.g.get((i, j), ()):
                    if c[0] < x1 + HALO and x0 < c[2] + HALO and c[1] < y1 + HALO and y0 < c[3] + HALO:
                        return False
        return True

    def inside(self, x, y):
        """the obstacle box strictly containing (x, y), or None"""
        for c in self.g.get((int(x // self.B), int(y // self.B)), ()):
            if c[0] < x < c[2] and c[1] < y < c[3]:
                return c
        return None

    def escape(self, cx, cy, w, h):
        """a requested point inside a hard block (an interior / area pin, or a wire-stage point on a straight L path that
        crosses a macro) moves to the nearest point just outside that block, where a register can actually sit; the
        wire from the pin to it runs over the block on the die layers above the block's obstructions"""
        for _ in range(8):
            c = self.inside(cx, cy)
            if c is None:
                return cx, cy
            m_ = HALO + max(w, h) / 2 + 0.5
            opts = [(cx - c[0], c[0] - m_, cy), (c[2] - cx, c[2] + m_, cy), (cy - c[1], cx, c[1] - m_), (c[3] - cy, cx, c[3] + m_)]
            opts = [o for o in opts if 1.0 < o[1] < self.W - 1.0 and 1.0 < o[2] < self.H - 1.0]
            _, cx, cy = min(opts)
        return cx, cy

    CELL = 30.0

    def _blocked(self):
        if getattr(self, '_blk', None) is None:
            import numpy as np
            C = self.CELL
            nx, ny = int(self.W // C) + 1, int(self.H // C) + 1
            blk = np.zeros((nx, ny), dtype=bool)
            for c in self.base:
                i0, i1 = int((c[0] - HALO) // C), int((c[2] + HALO) // C)
                j0, j1 = int((c[1] - HALO) // C), int((c[3] + HALO) // C)
                blk[max(i0, 0):min(i1, nx - 1) + 1, max(j0, 0):min(j1, ny - 1) + 1] = True
            self._blk = blk
        return self._blk

    def grid_path(self, p0, p1):
        """shortest 4-connected path p0 -> p1 through cells free of hard blocks (start / goal cells may be blocked:
        an interior pin leaves its block by the nearest way); polyline of die points, turns only"""
        import heapq
        blk = self._blocked()
        C = self.CELL
        nx, ny = blk.shape
        s = (min(max(int(p0[0] // C), 0), nx - 1), min(max(int(p0[1] // C), 0), ny - 1))
        g = (min(max(int(p1[0] // C), 0), nx - 1), min(max(int(p1[1] // C), 0), ny - 1))
        h = lambda c: abs(c[0] - g[0]) + abs(c[1] - g[1])
        dist = {s: 0}
        prev = {}
        pq = [(h(s), 0, s)]
        while pq:
            f, d, c = heapq.heappop(pq)
            if c == g:
                break
            if d > dist.get(c, 1e18):
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n_ = (c[0] + dx, c[1] + dy)
                if not (0 <= n_[0] < nx and 0 <= n_[1] < ny):
                    continue
                # blocked cells cost 40x: leaving / entering a block (interior pins) stays possible but is the last resort
                nd = d + (40 if blk[n_] and n_ != g else 1)
                if nd < dist.get(n_, 1e18):
                    dist[n_] = nd
                    prev[n_] = c
                    heapq.heappush(pq, (nd + h(n_), nd, n_))
        if g not in prev and g != s:
            return [p0, (p1[0], p0[1]), p1]
        cells = [g]
        while cells[-1] != s:
            cells.append(prev[cells[-1]])
        cells.reverse()
        pts = [p0] + [((c[0] + 0.5) * C, (c[1] + 0.5) * C) for c in cells[1:-1]] + [p1]
        poly = [pts[0]]
        for k in range(1, len(pts) - 1):      # keep turn points only
            a, b, c = poly[-1], pts[k], pts[k + 1]
            if not ((abs(a[0] - b[0]) < 1e-6 and abs(b[0] - c[0]) < 1e-6) or (abs(a[1] - b[1]) < 1e-6 and abs(b[1] - c[1]) < 1e-6)):
                poly.append(b)
        poly.append(pts[-1])
        return poly

    def place(self, cx, cy, w, h, gx, gy, reach=600.0):
        """lower-left of a free w x h box nearest (cx, cy) (ring search, 2.16 um steps), or None"""
        cx, cy = self.escape(cx, cy, w, h)
        step = 2.16
        for r in range(0, int(reach / step) + 1):
            cand = []
            if r == 0:
                cand = [(0, 0)]
            else:
                for k in range(-r, r + 1):
                    cand += [(k, -r), (k, r), (-r, k), (r, k)]
            cand.sort(key=lambda d: abs(d[0]) + abs(d[1]))
            for dx, dy in cand:
                x = math.floor((cx - w / 2 + dx * step) / gx) * gx
                y = math.floor((cy - h / 2 + dy * step) / gy) * gy
                if self.ok((x, y, x + w, y + h)):
                    return x, y
        return None


def _lpath(p0, p1, f, hfirst):
    """point at arc fraction f along the L path p0 -> p1 (horizontal leg first or vertical first); (q, travel_h)"""
    Lx, Ly = abs(p1[0] - p0[0]), abs(p1[1] - p0[1])
    s = f * (Lx + Ly)
    if hfirst:
        if s <= Lx:
            return (p0[0] + math.copysign(s, p1[0] - p0[0]), p0[1]), True
        return (p1[0], p0[1] + math.copysign(s - Lx, p1[1] - p0[1])), False
    if s <= Ly:
        return (p0[0], p0[1] + math.copysign(s, p1[1] - p0[1])), False
    return (p0[0] + math.copysign(s - Ly, p1[0] - p0[0]), p1[1]), True


def stage_points(p0, p1, n_ws, d_, free, rec, pin_s=None, pin_t=None):
    """the wire-stage points of one chain p0 -> p1, channel-following (2026-10-07): the path is a shortest Manhattan
    path on a CELL-um grid that avoids every hard block (Free.grid_path), and the stages sit along it at equal arc
    length, at least the budget's n_ws and as many more as keep every hop within the register reach (pin hop 359 um,
    stage hop 412 um).  A detour around a macro is longer than the straight L the budget priced: those stages are
    extra_wire_stages (cycles to price)."""
    path = free.grid_path(p0, p1)
    seg = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(path, path[1:])]
    L = sum(seg)
    need = 0 if L <= REACH_INTER_UM else math.ceil((L - REACH_INTER_UM) / REACH_INTRA_UM)
    n = max(n_ws, need)
    if n > n_ws:
        rec['extra_wire_stages'] = rec.get('extra_wire_stages', 0) + n - n_ws
    rec['path_um_total'] = rec.get('path_um_total', 0.0) + L
    out = []
    for k in range(n):
        t = L * (k + 1) / (n + 1)
        acc = 0.0
        for k2, ((a, b), sl) in enumerate(zip(zip(path, path[1:]), seg)):
            if acc + sl >= t or k2 == len(seg) - 1:
                f = (t - acc) / sl if sl else 0.0
                q = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
                out.append((q, abs(b[0] - a[0]) >= abs(b[1] - a[1]), d_, 'ws'))
                break
            acc += sl
    return out

def _ranges(idx):
    out, s = [], None
    for i in idx:
        if s is None:
            s = p = i
        elif i == p + 1:
            p = i
        else:
            out.append(f'{s}:{p}')
            s = p = i
    if s is not None:
        out.append(f'{s}:{p}')
    return ','.join(out)


def instance_relays(m, real, lef_text, H, L, wire_stages=True, relay_all=False):
    """rewrite m (insts, buses, stn_faces) with the relay / wire-stage instances; returns the record"""
    by = {it.name: it for it in m['insts']}
    L.CUR_M['_by'] = by
    pins = lef_pins(lef_text)
    rends = {(r[0], r[1]) for r in m.get('relay_ends', [])}
    fclk = m.get('fclk', {})
    dom = {}
    for bid, cls, bits, eps in m['buses']:
        if cls == 'clock_trunk':
            d_ = bid[len('clk_'):] if bid in ('clk_stream', 'clk_serial', 'clk_hbm', 'clk_link') else None
            for inst, port in eps[1:]:
                if d_:
                    dom.setdefault(inst, d_)
    clk_bus = {b[0]: i for i, b in enumerate(m['buses']) if b[0] in ('clk_stream', 'clk_serial', 'clk_hbm', 'clk_link')}
    W, Hh = m['geo']['W'], m['geo']['H']
    # obstacles: every placed instance AND every reserved region (owner / descriptor / escape bays, corridors, stores)
    free = Free([it.box() for it in m['insts']] + [tuple(b) for b in m.get('reserved_regions', [])], W, Hh)
    rp = H.real_ports(m)

    def pin_xy(inst, port, sel):
        """die-frame centroid of the pins of (inst, port) carrying bus bits `sel` (bus-bit order)"""
        it = by[inst]
        base = H.port_base(port)
        idx = H.port_idx(port)
        rec = pins.get(it.master)
        if rec:
            w, h, pp = rec
            names = None
            if it.master in rp and base in rp[it.master]:
                names = rp[it.master][base]
            pts = []
            for i in sel:
                b_ = idx[i] if idx else i
                key = (names[b_] if names and b_ < len(names) else f'{base}[{b_}]')
                pts += pp.get(key, [])[:1]
            if not pts:
                pts = pp.get(base, [])
            if pts:
                x = sum(p[0] for p in pts) / len(pts)
                y = sum(p[1] for p in pts) / len(pts)
                return to_die(it, x, y, w, h), True
        return (it.x + it.w / 2, it.y + it.h / 2), False

    def nreal(e):
        mst_ = by[e[0]].master
        b_ = H.port_base(e[1])
        return len(rp[mst_][b_]) if mst_ in rp and b_ in rp[mst_] else None

    def face_out(it, p):
        """outward unit step of the block face nearest the die point p"""
        d = {'W': p[0] - it.x, 'E': it.x + it.w - p[0], 'S': p[1] - it.y, 'N': it.y + it.h - p[1]}
        f = min(d, key=d.get)
        return f, {'W': (-1, 0), 'E': (1, 0), 'S': (0, -1), 'N': (0, 1)}[f]

    rec = dict(relay_ends_dropped_short=0, buses_cut=0, relays=0, wire_stages=0, unplaced=[], unknown_dir_bits=0, skipped_multi=0, skipped_fclk=0,
               pin_fallback=0, chains=[], instance_metadata={},
               qualification="diagnostic-only: analytic views and unqualified flow control")
    new_buses, new_insts = [], []
    gx, gy = H.GX, H.GY
    n_id = [0]

    def mk(bid, g, bits, at, travel_h, in_face, out_face, d_):
        n_id[0] += 1
        name = f'rl{n_id[0]}_{bid}_{g}'
        mst = f'hfd_rly_{n_id[0]}'
        face_len = max(8.64, bits * 0.048 * 1.15 + 4.0)
        depth = max(4.32, bits * BIT_UM2 / face_len)
        w, h = (depth, face_len) if travel_h else (face_len, depth)
        w = math.ceil(w / gx) * gx
        h = math.ceil(h / gy) * gy
        xy = free.place(at[0], at[1], w, h, gx, gy)
        if xy is None:
            rec['unplaced'].append(name)
            rec.setdefault('unplaced_detail', []).append(dict(name=name, bits=bits, at=[round(at[0], 3), round(at[1], 3)],
                                                              w=round(w, 3), h=round(h, 3), travel_h=travel_h))
            xy = (math.floor((at[0] - w / 2) / gx) * gx, math.floor((at[1] - h / 2) / gy) * gy)
        free.add((xy[0], xy[1], xy[0] + w, xy[1] + h))
        it = H.Inst(name, mst, xy[0], xy[1], w - H.SHAVE, h - H.SHAVE, kind='waypoint', region='channel')
        new_insts.append(it)
        by[name] = it
        m['stn_faces'][mst] = dict(d=in_face, q=out_face)
        new_buses.append((f'clk_{d_}', name))
        m.setdefault('relay_masters', {})[mst] = bits
        return it

    keep = []
    for bus in m['buses']:
        bid, cls, bits, eps = bus
        if cls in L.H.RELAY_SKIP_CLS or cls == 'clock_trunk' or cls == 'reset_tree':
            keep.append(bus)
            continue
        if len(eps) != 2 or any(e[0] not in by or e[0] == 'TOP' for e in eps):
            rec['skipped_multi'] += 1
            keep.append(bus)
            continue
        if bid in fclk:
            rec['skipped_fclk'] += 1
            keep.append(bus)
            continue
        A, B_ = by[eps[0][0]], by[eps[1][0]]

        def near(it, q):
            return (min(max(q[0], it.x), it.x + it.w), min(max(q[1], it.y), it.y + it.h))
        ca, cb = (A.x + A.w / 2, A.y + A.h / 2), (B_.x + B_.w / 2, B_.y + B_.h / 2)
        a, b = near(A, cb), near(B_, ca)
        a, b = near(A, b), near(B_, a)
        Lm = abs(a[0] - b[0]) + abs(a[1] - b[1])
        n_ws = math.ceil(max(0.0, Lm - REACH_INTER_UM) / REACH_INTRA_UM) if wire_stages else 0
        # r22 rule: a relay abuts a pin whose die segment is > 100 um; abutting blocks (r23 vm_cross_aligned seams, L = 0)
        #   have no segment to cut and no room between the faces
        rel = [(bid, e[0]) in rends for e in eps]
        if n_ws == 0 and not any(rel) and not relay_all:
            keep.append(bus)
            continue
        try:
            seg, _ = L.endpoint_dirs('hbm', real, by, bus, 0)
        except Exception:
            seg = None
        flip = False
        if seg is None:
            try:
                seg, _ = L.endpoint_dirs('hbm', real, by, bus, 1)
                flip = True
            except Exception:
                seg = None
        groups = defaultdict(list)
        for lo, hi, d in (seg or []):
            if d in ('out', 'in'):
                fwd = (d == 'out') != flip
                groups['f' if fwd else 'r'] += list(range(lo, hi))
        cov = set(groups['f']) | set(groups['r'])
        unk = [i for i in range(bits) if i not in cov]
        rec['unknown_dir_bits'] += len(unk)
        if unk:     # undirected bits stay a direct (unregistered) connection
            keep.append((bid + '_u', cls, len(unk), [(e[0], _sub(e[1], unk, bits, H, nreal(e))) for e in eps]))
        rec['buses_cut'] += 1
        for g, sel in groups.items():
            if not sel:
                continue
            sel = sorted(sel)
            s_, t_ = (0, 1) if g == 'f' else (1, 0)
            src, dst = eps[s_], eps[t_]
            (ps, oks), (pt, okt) = pin_xy(src[0], src[1], sel), pin_xy(dst[0], dst[1], sel)
            rec['pin_fallback'] += (not oks) + (not okt)
            if relay_all:       # BRIEF 2026-10-07: a relay station at EVERY die-level pin whose segment is > ~100 um
                d_pp = abs(ps[0] - pt[0]) + abs(ps[1] - pt[1])
                rel_ = [d_pp > RELAY_MIN_SEG_UM] * 2
                rec['relay_ends_added_rule'] = rec.get('relay_ends_added_rule', 0) + sum(
                    1 for k_ in (s_, t_) if rel_[k_] and (bid, eps[k_][0]) not in rends)
                rel = rel_
            if abs(ps[0] - pt[0]) + abs(ps[1] - pt[1]) <= RELAY_MIN_SEG_UM and n_ws == 0 and (any(rel) or relay_all):
                rec['relay_ends_dropped_short'] += sum(rel)
                new_buses.append((f'{bid}_{g}0', 'x_leaf', len(sel), [(src[0], _sub(src[1], sel, bits, H, nreal(src))),
                                                                      (dst[0], _sub(dst[1], sel, bits, H, nreal(dst)))]))
                rec['chains'].append(dict(bus=bid, dir=g, bits=len(sel), len_um=round(Lm, 1), relays=0, wire_stages=0,
                                          src=src[0], dst=dst[0], regs=[], note='pin segment <= 100 um: no relay (r22 rule)'))
                continue
            ds_ = dom.get(src[0]) or dom.get(dst[0]) or 'stream'
            dt_ = dom.get(dst[0]) or ds_
            nb = len(sel)
            nodes = [(src[0], _sub(src[1], sel, bits, H, nreal(src)))]
            pts = []
            fs, us = face_out(by[src[0]], ps)
            ft, ut = face_out(by[dst[0]], pt)
            p0 = (ps[0] + us[0] * 8.0, ps[1] + us[1] * 8.0)
            p1 = (pt[0] + ut[0] * 8.0, pt[1] + ut[1] * 8.0)
            if rel[s_]:
                pts.append((p0, fs in 'EW', ds_, 'relay'))
            pts += stage_points(p0, p1, n_ws, ds_, free, rec, ps if rel[s_] else None, pt if rel[t_] else None)
            if rel[t_]:
                pts.append((p1, ft in 'EW', dt_, 'relay'))
            prev = None
            chain = []
            for q, th, d_, kind in pts:
                ref = prev if prev is not None else ps
                nxt_x = (q[0] - ref[0], q[1] - ref[1])
                if th:
                    inf, outf = ('W', 'E') if (nxt_x[0] >= 0 if prev is not None or kind == 'ws' else us[0] >= 0) else ('E', 'W')
                else:
                    inf, outf = ('S', 'N') if (nxt_x[1] >= 0 if prev is not None or kind == 'ws' else us[1] >= 0) else ('N', 'S')
                it = mk(bid, g, nb, q, th, inf, outf, d_)
                rec['instance_metadata'][it.name] = dict(
                    master=it.master, bits=nb, kind=kind, original_bus=bid,
                    original_source=list(src), original_sink=list(dst),
                    original_bit_indices=list(sel),
                    clock_domain_found=(src[0] in dom and dst[0] in dom),
                    source_clock_domain=ds_, sink_clock_domain=dt_,
                    clock_domain=d_, clock_reference_instance=dst[0] if kind == 'relay' and q == p1 else src[0],
                    source_pin_centroid_um=list(ps), sink_pin_centroid_um=list(pt),
                    source_pin_coordinates_found=oks, sink_pin_coordinates_found=okt,
                    cross_domain=ds_ != dt_,
                    box_um=list(it.box()), requested_centre_um=list(q),
                    placed_legal=it.name not in rec['unplaced'],
                    input_face=inf, output_face=outf)
                rec['relays' if kind == 'relay' else 'wire_stages'] += 1
                nodes.append((it.name, None))
                chain.append(it.name)
                prev = q
            nodes.append((dst[0], _sub(dst[1], sel, bits, H, nreal(dst))))
            for j in range(len(nodes) - 1):
                a_, b2 = nodes[j], nodes[j + 1]
                ea = (a_[0], a_[1]) if a_[1] is not None else (a_[0], 'q')
                eb = (b2[0], b2[1]) if b2[1] is not None else (b2[0], 'd')
                new_buses.append((f'{bid}_{g}{j}', 'x_leaf', nb, [ea, eb]))
            xy_ = [ps] + [(by[r_].x + by[r_].w / 2, by[r_].y + by[r_].h / 2) for r_ in chain] + [pt]
            hops = [round(abs(a_[0] - b_[0]) + abs(a_[1] - b_[1]), 1) for a_, b_ in zip(xy_, xy_[1:])]
            rec['chains'].append(dict(bus=bid, dir=g, bits=nb, src=src[0], dst=dst[0], len_um=round(Lm, 1), relays=sum(rel),
                                      wire_stages=sum(1 for q_ in pts if q_[3] == 'ws'), planned_wire_stages=n_ws,
                                      regs=chain, hops_um=hops, max_hop_um=max(hops)))
    m['insts'] += new_insts
    buses = list(keep)
    adds = defaultdict(list)
    for b in new_buses:
        if len(b) == 2:
            adds[b[0]].append((b[1], 'ck'))
        else:
            buses.append(b)
    for i, b in enumerate(buses):
        if b[0] in adds:
            buses[i] = (b[0], b[1], b[2], list(b[3]) + adds.pop(b[0]))
    for d_, e_ in adds.items():      # a domain with no clock net yet: hang it on the stream net
        j = next(i for i, b in enumerate(buses) if b[0] == 'clk_stream')
        buses[j] = (buses[j][0], buses[j][1], buses[j][2], list(buses[j][3]) + e_)
    m['buses'] = buses
    rec['instances'] = len(new_insts)
    rec['unplaced_n'] = len(rec['unplaced'])
    return rec


def _sub(port, sel, bits, H, nreal=None):
    """the endpoint port restricted to bus bits `sel` ('base@ranges' of the port's own bit indices); on a real port of
    nreal pins the bits past its last pin are dropped (as write_netlist truncates a full-width real connection)"""
    if len(sel) == bits and sel == list(range(bits)):
        return port
    idx = H.port_idx(port) or list(range(bits))
    ib = [idx[i] for i in sel]
    if nreal is not None:
        ib = [i for i in ib if i < nreal]
    return H.port_base(port) + '@' + _ranges(ib)


def relay_libs(m, path_ss, path_ff):
    """interface Liberty of every hfd_rly master (SS / FF), bus-level timing groups (ps / fF)"""
    rm = m.get('relay_masters', {})
    C = dict(ss=dict(ins_min=70.0, ins_max=90.0, ckq=60.0, r=0.30, setup=30.0, hold=15.0, tr=12.0, v=0.63, t=100.0),
             ff=dict(ins_min=40.0, ins_max=55.0, ckq=30.0, r=0.15, setup=15.0, hold=10.0, tr=6.0, v=0.77, t=0.0))
    caps = [1.44, 5.76, 23.04, 92.16, 368.64]
    for corner, path in (('ss', path_ss), ('ff', path_ff)):
        c = C[corner]
        L_ = [f'library (hfd_rly_{corner}) {{', '  delay_model : table_lookup;', '  time_unit : "1ps";',
              '  voltage_unit : "1V";', '  current_unit : "1mA";', '  pulling_resistance_unit : "1kohm";',
              '  leakage_power_unit : "1pW";', '  capacitive_load_unit (1,fF);',
              f'  nom_process : 1.0; nom_temperature : {c["t"]}; nom_voltage : {c["v"]};',
              '  input_threshold_pct_rise : 50; input_threshold_pct_fall : 50;',
              '  output_threshold_pct_rise : 50; output_threshold_pct_fall : 50;',
              '  slew_lower_threshold_pct_rise : 10; slew_lower_threshold_pct_fall : 10;',
              '  slew_upper_threshold_pct_rise : 90; slew_upper_threshold_pct_fall : 90;',
              '  lu_table_template (ld) { variable_1 : total_output_net_capacitance; index_1 ("'
              + ', '.join(f'{x:.2f}' for x in caps) + '"); }']
        for w in sorted(set(rm.values()) | {1}):
            L_.append(f'  type (rb{w}) {{ base_type : array; data_type : bit; bit_width : {w}; bit_from : {w - 1}; bit_to : 0; }}')
        dl = ', '.join(f'{c["ins_max"] + c["ckq"] + c["r"] * x:.2f}' for x in caps)
        tr = ', '.join(f'{c["tr"] + 0.25 * c["r"] * x * 2:.2f}' for x in caps)
        for mst, w in sorted(rm.items()):
            L_ += [f'  cell ({mst}) {{', f'    area : {w * BIT_UM2:.1f};', '    is_macro_cell : true;',
                   '    bus (ck) { bus_type : rb1; direction : input; clock : true; capacitance : 5.0; }',
                   f'    bus (d) {{ bus_type : rb{w}; direction : input; capacitance : 0.6;',
                   f'      timing () {{ related_pin : "ck"; timing_type : setup_rising; rise_constraint (scalar) {{ values ("{c["setup"] - c["ins_min"]:.2f}"); }} fall_constraint (scalar) {{ values ("{c["setup"] - c["ins_min"]:.2f}"); }} }}',
                   f'      timing () {{ related_pin : "ck"; timing_type : hold_rising; rise_constraint (scalar) {{ values ("{c["hold"] + c["ins_max"]:.2f}"); }} fall_constraint (scalar) {{ values ("{c["hold"] + c["ins_max"]:.2f}"); }} }}',
                   '    }',
                   f'    bus (q) {{ bus_type : rb{w}; direction : output;',
                   f'      timing () {{ related_pin : "ck"; timing_type : rising_edge; cell_rise (ld) {{ values ("{dl}"); }} cell_fall (ld) {{ values ("{dl}"); }} rise_transition (ld) {{ values ("{tr}"); }} fall_transition (ld) {{ values ("{tr}"); }} }}',
                   '    }', '  }']
        L_.append('}')
        open(path, 'w').write('\n'.join(L_) + '\n')
