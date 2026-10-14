#!/usr/bin/env python3
"""VM leaf plan v2 (claude/qwen-tp8-vm PLAN, 2026-10-13): the bit-plane VM as die-assembled hard leaves, every seam short.

  python3 tools/qwen_tp8/vm_leaf_plan.py NET_DUMP OUT.json [--strip-cols 2|3] [--band-relays 0|1]

What changed against the first plan (REJECT with real leaf sizes, el1013-qwen-vm.log 08:35):
  region   one control leaf (gctl_t) and one row-read leaf (rowrd_t) per region are dissolved (RTL: ot_qfd_vm_region_leaf):
           8 x bctl_t beside the bank's bx relay, 6 x sctl_t beside the SU write relay, 2 x rr4_t + 1 x rr2_t in the
           strips (rr4[h] beside the bx relays of unit column h, rr2 beside rr4[1]).  The bank ring is no longer folded
           (the rotation lives in the plane leaves): bank b sits at unit column b // 4, row b % 4, so banks 4h .. 4h + 3
           are ONE column and their bx reaches the 4:1 rung vertically (no 512-b bus crosses a bank: a 2 x 2 quad
           put 1,024 b across every lane window of the region).  The SU answer leaves sit between their two SU banks.
  band     ONE row of 32 bit-plane column leaves (ot_qfd_vm_xcol_t = plane + line of one bit position in one leaf: as
           two leaves the 1,008-b bv plane between them took a third of every band window): the lower region row's
           lanes land on its S face (d_lo), the upper row's on its N face (d_hi), the x_q plane leaves on W / E.
  strips   full-height relay strips of --strip-cols tile columns (2 = the 04:20 slot, 3 = the slot growth option),
           inner gap 4.32 um so that every pin face has a channel.
Per region (= one ot_qfd_vm_region_leaf, wires only): 8 bank_t, 6 su_t, 16 xfifo8_t, 3 su1024_t (closed views, R0) +
8 delay1 (bx) + 14 delay2 (wd / swd) + 8 bctl_t + 6 sctl_t + 2 rr4_t + 1 rr2_t.  Every leaf is its own clock root.
The region is NOT a hardened cluster: the die assembles the leaves, so over the M5-capped leaves the die owns M6 - M9
(contract v3); the region's own seams are die nets and are booked as demand by vm_plane_lanes.py ('seam_segments').
PLAN ONLY for a leaf without a view: sizes come from its ref_tile kit when one exists, else from PLANNED."""
import argparse, json, sys, hashlib, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vm_lef_pins as L
ROOT = Path(__file__).resolve().parents[2]
VIEW = {'ot_qfd_vm_bank_t': 'physical/ref_tile/qfd_vm_bank_t/views/ot_qfd_vm_bank_t/ot_qfd_vm_bank_t.lef',
        'ot_qfd_vm_su_t': 'physical/ref_tile/qfd_vm_su_t/views/ot_qfd_vm_su_t/ot_qfd_vm_su_t.lef',
        'ot_qfd_vm_xfifo8_t': 'physical/ref_tile/qfd_vm_xfifo8_codex/views/ot_qfd_vm_xfifo8_t/ot_qfd_vm_xfifo8_t.lef',
        'ot_qfd_vm_su1024_t': 'physical/ref_tile/qfd_vm_su1024_codex/views/ot_qfd_vm_su1024_t/ot_qfd_vm_su1024_t.lef'}
SINKS = {'ot_qfd_vm_bank_t': 1600, 'ot_qfd_vm_su_t': 1600, 'ot_qfd_vm_xfifo8_t': 3523, 'ot_qfd_vm_su1024_t': 1100,
         'ot_qwen_tree_delay1_t': 512, 'ot_qwen_tree_delay2_t': 1024, 'ot_qfd_vm_bctl_t': 78, 'ot_qfd_vm_sctl_t': 82,
         'ot_qfd_vm_rr4_t': 603, 'ot_qfd_vm_rr2_t': 609, 'ot_qfd_vm_xcol_t': 4163 + 5568, 'ot_qfd_vm_xrelay_t': 516,
         'ot_qfd_vm_fan_t': 2}
KIT = {'ot_qwen_tree_delay1_t': 'qfd_tree_delay1_t', 'ot_qwen_tree_delay2_t': 'qfd_tree_delay2_t', 'ot_qfd_vm_bctl_t': 'qfd_vm_bctl_t',
       'ot_qfd_vm_sctl_t': 'qfd_vm_sctl_t', 'ot_qfd_vm_rr4_t': 'qfd_vm_rr4_t', 'ot_qfd_vm_rr2_t': 'qfd_vm_rr2_t',
       'ot_qfd_vm_xcol_t': 'qfd_vm_xcol_t', 'ot_qfd_vm_xrelay_t': 'qfd_vm_xrelay_t',
       'ot_qfd_vm_fan_t': 'qfd_vm_fan_me'}
PLANNED = {'ot_qfd_vm_bctl_t': (12.96, 38.88), 'ot_qfd_vm_sctl_t': (12.96, 38.88), 'ot_qfd_vm_rr4_t': (17.28, 216.0),
           'ot_qfd_vm_rr2_t': (116.64, 25.92), 'ot_qfd_vm_xcol_t': (142.56, 179.28), 'ot_qfd_vm_fan_t': (4.32, 6.48)}
GATE = {}; SIZE_SRC = {}
def _kit(m):
    d = ROOT / 'physical/ref_tile' / KIT[m]
    if not (d / 'floorplan.json').exists(): SIZE_SRC[m] = 'PLANNED (no kit yet)'; return PLANNED[m]
    die = json.loads((d / 'floorplan.json').read_text())['die']; SIZE_SRC[m] = 'kit physical/ref_tile/' + KIT[m]
    g = d / 'gate_result.json'
    if g.exists():
        r = json.loads(g.read_text()); ck = r.get('clock') or {}
        GATE[m] = dict(verdict=r['verdict'], commit=r.get('commit'), clock=ck.get('text'), tt_insertion_ps=ck.get('tt_insertion_ps'), tt_spread_ps=ck.get('tt_spread_ps'),
                       util=[i['message'] for i in r['items'] if i['check'] in ('util', 'textbook.util_channel')][:1])
        if ck.get('max_root_sinks'): SINKS[m] = ck['max_root_sinks']
    return (round(die[2] - die[0], 4), round(die[3] - die[1], 4))
NEW = {m: _kit(m) for m in KIT}
X0, Y0, RH, BAND = 13284.0, 17249.76, 1080.0, 187.92
TW = 17.28; SGAP = 4.32
G = lambda v: round(round(v / 2.16) * 2.16, 6)
ROWY = lambda row: 10.8 + 205.2 * row
SUY = (10.8, 276.48, 516.24, 781.92)      # right SU column: an answer leaf (21.6 um) between su0 / su1 and between su2 / su3


class Plan:
    def __init__(self, sc, band_relays, pad_rows=0):
        self.pad_rows = pad_rows; self.PR = G(pad_rows * (97.2 + 2.16))          # VM3: pad rows between the column row and each region row
        self.scs = list(sc) if isinstance(sc, (list, tuple)) else [sc] * 4; self.band_relays = band_relays     # strip tile columns per REGION COLUMN
        self.geo = []; x = 0.0
        for c in self.scs:
            SW = c * TW + (c - 1) * SGAP                        # strip width (tile columns + inner channels)
            sW = 4.32; U0 = G(sW + SW + 4.32); sA = G(U0 + 380.16 + 4.32); U1 = G(sA + SW + 4.32); sB = G(U1 + 380.16 + 4.32); SI = G(sB + SW + 4.32); SUX = G(SI + 21.6)
            RW = G(SUX + 235.44 + 6.48); self.geo.append(dict(sc=c, SW=SW, sW=sW, U0=U0, sA=sA, U1=U1, sB=sB, SI=SI, SUX=SUX, RW=RW, X=G(x))); x += RW
        self.EW = G(x + 4.32 + self.geo[3]['SW']); self.use(0)
        self.size = {m: L.read(ROOT / p)[0] for m, p in VIEW.items()}; self.size.update(NEW)
        self.BAND = G(max(BAND, G(self.size['ot_qfd_vm_xcol_t'][1] + 8.64)) + 2 * self.PR)       # the band is as tall as the column leaf needs (+ the pad rows)
        self.ch = []; self.bays = []; self.seams = []; self.me = []

    def use(self, c):
        for k, v in self.geo[c].items(): setattr(self, k if k != 'X' else 'XO', v)

    def origin(self, r): return G(X0 + self.geo[r % 4]['X']), G(Y0 + (r // 4) * (RH + self.BAND))

    def add(self, n, m, x, y, **k):
        c = dict(n=n, m=m, x=G(x), y=G(y), w=self.size[m][0], h=self.size[m][1], orient='R0', layer_cap='M5', **k); self.ch.append(c); return c

    def strip(self, n, x, y, r, blocked=()):
        """full-height strip: sc tile columns x 10 nodes (pitch 99.36); blocked = (column, y0, y1) spans held by another leaf
        (the row-read rungs).  A node keeps its free columns when they are contiguous."""
        th = self.size['ot_qfd_vm_xrelay_t'][1]; NP = G(th + 2.16)
        for k in range(int((RH - 4.32) // NP)):
            yy = G(y + 4.32 + NP * k); cols = [c for c in range(self.sc) if not any(c == bc and a < yy - y + th + 2.16 and yy - y - 2.16 < b for bc, a, b in blocked)]
            cols = [c for c in cols if all(m in cols for m in range(cols[0], c))] if cols else cols       # contiguous run from the first free column
            if cols: self.bays.append(dict(n=f'{n}_{k}', x=G(x + cols[0] * (TW + SGAP)), y=yy, w=G(len(cols) * TW + (len(cols) - 1) * SGAP), h=th, tiles=len(cols), region=r))

    def build(self):
        A = self.add; s = self.size
        P = {m: {b: v for b, v in L.groups(ROOT / p)[1].items()} for m, p in VIEW.items()}
        def pin(c, bus):                       # absolute centroid and span of a closed leaf's pin group
            v = P[c['m']][bus]; b = v['bbox']; return (c['x'] + v['centroid'][0], c['y'] + v['centroid'][1], max(b[2] - b[0], b[3] - b[1]))
        def face(c, f, span=None):             # centre of a face of a leaf without a view (pins spread over the face)
            x, y = {'W': (c['x'], c['y'] + c['h'] / 2), 'E': (c['x'] + c['w'], c['y'] + c['h'] / 2), 'S': (c['x'] + c['w'] / 2, c['y']), 'N': (c['x'] + c['w'] / 2, c['y'] + c['h'])}[f]
            return (x, y, (c['h'] if f in 'WE' else c['w']) if span is None else span)
        def seam(kind, a, b, bits):
            L1 = abs(a[0] - b[0]) + abs(a[1] - b[1]); self.seams.append(dict(kind=kind, bits=bits, A=[round(a[0], 3), round(a[1], 3)], Q=[round(b[0], 3), round(b[1], 3)],
                                                                         centroid_um=round(L1, 1), est_um=round(L1 + (a[2] + b[2]) / 4, 1)))
        for r in range(8):
            X, Y = self.origin(r); self.use(r % 4)
            # row read: banks 4h .. 4h + 3 are ONE unit column (4 rows), their 4:1 rung sits beside the column's bx relays in
            # the strip east of it (first tile column), centred on the column; the 2:1 rung in unit column 1 between the two
            rr4 = [A(f'vm_g{r}_rr4_{h}', 'ot_qfd_vm_rr4_t', X + (self.sA, self.sB)[h], Y + 302.4, region=r, half=h) for h in range(2)]
            rr2 = A(f'vm_g{r}_rr2', 'ot_qfd_vm_rr2_t', X + self.U1 + 261.36, Y + 399.6, region=r)   # the free row between the x FIFOs of bank rows 1 and 2, level with both rr4 leaves
            self.me.append((rr2['n'], rr2['x'], rr2['y']))
            seam('rr4[0].t1 -> rr2.ro', face(rr4[0], 'E', 108.0), face(rr2, 'N', 58.32), 512); seam('rr4[1].t1 -> rr2.ro', face(rr4[1], 'E', 108.0), face(rr2, 'S', 58.32), 512)
            for b in range(8):
                ux = X + (self.U0, self.U1)[b // 4]; yb = Y + ROWY(b % 4); bank = 8 * r + b
                i_ = A(f'vm_g{r}_b{b}_in', 'ot_qwen_tree_delay2_t', ux, yb + 60.48, region=r, role='wd pin flop + NRI relay')
                bk = A(f'vm_g{r}_b{b}', 'ot_qfd_vm_bank_t', ux + 21.6, yb, region=r, logical_bank=bank)
                bc = A(f'vm_g{r}_b{b}_ctl', 'ot_qfd_vm_bctl_t', ux + 244.08, yb + 12.96, region=r)
                bx = A(f'vm_g{r}_b{b}_bx', 'ot_qwen_tree_delay1_t', ux + 244.08, yb + 60.48, region=r, role='bx NRX relay')
                self.me.append((bc['n'], bc['x'], bc['y']))
                seam('delay2.q -> bank.wd', face(i_, 'E'), pin(bk, 'wd'), 512); seam('bank.q -> delay1.d', pin(bk, 'q'), face(bx, 'W'), 512)
                seam('bctl.m_* -> bank pin flops', face(bc, 'W'), pin(bk, 'wm'), 34); seam('bctl.rtg -> bank.rst_n', face(bc, 'W'), pin(bk, 'rst_n'), 1)
                q4 = rr4[b // 4]; seam('delay1.q (bx) -> rr4.t1', face(bx, 'E'), (q4['x'], q4['y'] + (b % 4 + 0.5) * q4['h'] / 4, q4['h'] / 4), 512)   # the bank of row k takes quarter k of the W face
                for h in range(2):
                    xf = A(f'vm_g{r}_b{b}_xf{h}', 'ot_qfd_vm_xfifo8_t', ux + 259.2, yb + (12.96, 129.6)[h], region=r, logical_bank=bank, bits=[256 * h, 256 * h + 255])
                    self.me.append((xf['n'], xf['x'] + xf['w'], xf['y'] + 20.0))
                    seam('delay1.q (bx) -> xfifo8.fe', face(bx, 'E'), pin(xf, 'bx'), 256); seam('bctl.pgw/xg -> xfifo8', face(bc, 'E'), pin(xf, 'xg'), 2)
                    seam('bctl.rtg -> xfifo8.rtg', face(bc, 'E'), pin(xf, 'rtg'), 1)
            sus = [(self.SUX, SUY[k]) for k in range(4)] + [(self.U1 + 21.6, 831.6), (self.U0 + 21.6, 831.6)]   # su4 (j = 0, drives the answer leaf's tag) beside ans2
            ans = [A(f'vm_g{r}_ans{k}', 'ot_qfd_vm_su1024_t', X + ax, Y + ay, region=r, operand=k)
                   for k, (ax, ay) in enumerate(((self.SUX + 144.72, 250.56), (self.SUX + 144.72, 756.0), (self.sA + self.SW - 86.4, 1002.24)))]
            for k, (sx, sy) in enumerate(sus):
                su = A(f'vm_g{r}_su{k}', 'ot_qfd_vm_su_t', X + sx, Y + sy, region=r, operand=k // 2, su_bank=k % 2)
                si = A(f'vm_g{r}_su{k}_in', 'ot_qwen_tree_delay2_t', X + sx - 21.6, Y + sy + 86.4, region=r, role='swd pin flop + NRI relay')
                sc = A(f'vm_g{r}_su{k}_ctl', 'ot_qfd_vm_sctl_t', X + sx - 21.6, Y + sy + 155.52, region=r)
                seam('delay2.q -> su.swd', face(si, 'E'), pin(su, 'swd'), 512); seam('sctl.m_* -> su pin flops', face(sc, 'E'), pin(su, 'swm'), 38)
                seam('su.q (sx) -> su1024.so', pin(su, 'q'), pin(ans[k // 2], 'sx'), 512)
                if k % 2 == 0: seam('sctl.svc/rtg -> su1024', face(sc, 'E'), pin(ans[k // 2], 'svc'), 2)
            # the 4:1 rung holds the first tile column(s) of its strip over its own height (51.84 um wide since the second cut =
            # three tile columns: its bank-major bx pins need >= 1,024 vertical crossings inside the leaf)
            nbk = int(-(-(s['ot_qfd_vm_rr4_t'][0] + SGAP) // (TW + SGAP))); blk = tuple((c, 302.4, 518.4) for c in range(nbk))
            self.strip(f'vm_g{r}_sW', X + self.sW, Y, r); self.strip(f'vm_g{r}_sA', X + self.sA, Y, r, blocked=blk)
            self.strip(f'vm_g{r}_sB', X + self.sB, Y, r, blocked=blk)
            if r % 4 == 3: self.strip(f'vm_g{r}_sE', X + self.RW + 4.32, Y, r)
        # ---- band: one row of 32 bit-plane column leaves (d_lo S, d_hi N, x_q plane W / E) ----
        yb = Y0 + RH + self.PR; PW, PH = s['ot_qfd_vm_xcol_t']; pitch = G((self.EW - 8.64 - PW) / 31 // 2.16 * 2.16); CB = max(BAND, G(PH + 8.64)); self.BAND = G(CB + 2 * self.PR)
        # VM3 pad rows: one bay row of pad / relay tiles on each face of the column row (pad_rows per side).  Every lane lands
        # through the bay of its column face, so the equalisation stages sit at the consumer and the strips hold relays only
        th = s['ot_qfd_vm_xrelay_t'][1]; npt = int((pitch - 4.32 + SGAP) // (TW + SGAP)); bw = G(npt * TW + (npt - 1) * SGAP)
        for p in range(32 if self.pad_rows else 0):
            cx = X0 + 4.32 + pitch * p
            for k in range(self.pad_rows):
                self.bays.append(dict(n=f'vm_pad_{p}_S{k}', x=G(cx + (PW - bw) / 2 // 2.16 * 2.16), y=G(yb - (k + 1) * (th + 2.16) + 2.16), w=bw, h=th, tiles=npt, region=-1, padrow=1, plane=p, face=0))
                self.bays.append(dict(n=f'vm_pad_{p}_N{k}', x=G(cx + (PW - bw) / 2 // 2.16 * 2.16), y=G(yb + CB + k * (th + 2.16)), w=bw, h=th, tiles=npt, region=-1, padrow=1, plane=p, face=1))
        for p in range(32):
            pl = A(f'vm_xcol_{p}', 'ot_qfd_vm_xcol_t', X0 + 4.32 + pitch * p, yb + 4.32, plane=p, region=-1)
            self.me.append((pl['n'], pl['x'], pl['y'] + PH / 2))
        self.band = dict(band_um=self.BAND, pad_rows_per_side=self.pad_rows, pad_row_um=self.PR, column_band_um=CB, pad_bay_tiles=npt, request_0420_um=BAND, column_pitch_um=pitch, column_outline_um=[PW, PH], used_um=G(PH + 8.64),
                         fits=PW <= pitch - 4.32 + 1e-6, grows_um=round(self.BAND - BAND, 3))
        return self


def ov(a, b, gap=0.0):
    return a['x'] < b['x'] + b['w'] + gap - 1e-6 and b['x'] < a['x'] + a['w'] + gap - 1e-6 and a['y'] < b['y'] + b['h'] + gap - 1e-6 and b['y'] < a['y'] + a['h'] + gap - 1e-6


def me_tree(sinks, reach=450.0, fan=16):
    """two registered levels inside the slot (the RTL's XMK = 2: fan_t EN 0 -> fan_t EN 0 -> every leaf's me_e): greedy cover,
    a node feeds <= fan sinks within `reach` (L1, node at the centroid of its sinks).  Level-0 inputs are the slot's me pins:
    the die delivers me_en_t (3 edges early) to each of them (its own relay tree; that depth is part of the die's RSD budget)."""
    def cover(pts):
        pts = sorted(pts, key=lambda p: (round(p[2] / 400), p[1])); nodes = []; left = pts[:]
        while left:
            seed = left[0]; grp = [seed]
            for q in left[1:]:
                if len(grp) >= fan: break
                cx = sum(g[1] for g in grp + [q]) / (len(grp) + 1); cy = sum(g[2] for g in grp + [q]) / (len(grp) + 1)
                if all(abs(g[1] - cx) + abs(g[2] - cy) <= reach for g in grp + [q]): grp.append(q)
            ids = {id(g) for g in grp}; left = [p for p in left if id(p) not in ids]
            cx = sum(g[1] for g in grp) / len(grp); cy = sum(g[2] for g in grp) / len(grp)
            nodes.append((f'n{len(nodes)}', round(cx, 2), round(cy, 2), len(grp), round(max(abs(g[1] - cx) + abs(g[2] - cy) for g in grp), 1)))
        return nodes
    l1 = cover(sinks); l0 = cover([(n, x, y) for n, x, y, _, _ in l1])
    return dict(levels=2, sinks=len(sinks), level1_nodes=len(l1), level0_nodes=len(l0), fan_max=fan, reach_um=reach,
                level1_max_wire_um=max(n[4] for n in l1), level0_max_wire_um=max(n[4] for n in l0),
                slot_me_pins=[dict(x=n[1], y=n[2], level1_nodes=n[3]) for n in l0])


def region_spec(pl, seams, r=0):
    """the region as a die-assembled placement cluster: children (region-relative), the strip slots the die fills with
    relay tiles, every module port with its leaf-pin endpoints and the number of die relay endpoints it needs (greedy
    cover, every endpoint register within `reach` of its pins), the seam table and the region's own cut demand."""
    X, Y = pl.origin(r); pl.use(r % 4); by = {c['n']: c for c in pl.ch if c.get('region') == r}; g = f'vm_g{r}_'
    def at(n, f='W'):
        c = by[g + n]; x, y = {'W': (c['x'], c['y'] + c['h'] / 2), 'E': (c['x'] + c['w'], c['y'] + c['h'] / 2), 'S': (c['x'] + c['w'] / 2, c['y']), 'N': (c['x'] + c['w'] / 2, c['y'] + c['h'])}[f]
        return dict(leaf=n, master=c['m'], face=f, x=round(x - X, 2), y=round(y - Y, 2))
    def cover(pts, reach=450.0):
        left = sorted(pts, key=lambda q: (q['y'], q['x'])); n = 0; worst = 0.0
        while left:
            grp = [left[0]]
            for q in left[1:]:
                cx = sum(t['x'] for t in grp + [q]) / (len(grp) + 1); cy = sum(t['y'] for t in grp + [q]) / (len(grp) + 1)
                if all(abs(t['x'] - cx) + abs(t['y'] - cy) <= reach for t in grp + [q]): grp.append(q)
            cx = sum(t['x'] for t in grp) / len(grp); cy = sum(t['y'] for t in grp) / len(grp); worst = max(worst, max(abs(t['x'] - cx) + abs(t['y'] - cy) for t in grp))
            ids = {id(t) for t in grp}; left = [q for q in left if id(q) not in ids]; n += 1
        return n, round(worst, 1)
    B = [at(f'b{b}_ctl', 'S') for b in range(8)]; SC = {k: at(f'su{k}_ctl', 'W') for k in range(6)}; R4 = [at(f'rr4_{h}', 'S') for h in range(2)]; R2 = at('rr2', 'W')
    XF = [at(f'b{b}_xf{h}', 'E') for b in range(8) for h in range(2)]
    ports = {
        're / ra / we / wl / wm [bank g]': dict(dir='in', bits='8 x 34', pins_per_bit=1, endpoints=[[B[b]] for b in range(8)]),
        'xv': dict(dir='in', bits=1, endpoints=[B + [R2]]), 'pop': dict(dir='in', bits=1, endpoints=[B + [R2]]),
        'me_in': dict(dir='in', bits=1, endpoints=[B + XF + [R2]], note='me tree sinks: the die me tree ends at these pins (leaf plan me_tree)'),
        'rst_n': dict(dir='in', bits=1, endpoints=[B + list(SC.values()) + R4 + [R2]], note='asynchronous: reaches only the reset relays of the control leaves'),
        'rq': dict(dir='in', bits=1, endpoints=[[R2]]), 'rqb': dict(dir='in', bits=3, endpoints=[R4 + [R2]], note='rqb[1:0] -> both rr4_t, rqb[2] -> rr2_t'),
        'sre / sra [copy c, bank j]': dict(dir='in', bits='6 x 11', endpoints=[[SC[k]] for k in range(6)]),
        'swe / swl / swm [bank j]': dict(dir='in', bits='2 x 27', endpoints=[[SC[k] for k in range(6) if by[g + f'su{k}']['su_bank'] == j] for j in range(2)]),
        'sv [copy c]': dict(dir='in', bits='3 x 1', endpoints=[[SC[k] for k in range(6) if by[g + f'su{k}']['operand'] == c] for c in range(3)]),
        'wd [bank g]': dict(dir='in', bits='8 x 512', endpoints=[[at(f'b{b}_in', 'W')] for b in range(8)]),
        'swd [bank j]': dict(dir='in', bits='2 x 512', endpoints=[[at(f'su{k}_in', 'W') for k in range(6) if by[g + f'su{k}']['su_bank'] == j] for j in range(2)]),
        'xo': dict(dir='out', bits='16 x 256', endpoints=[[at(f'b{b}_xf{h}', 'N')] for b in range(8) for h in range(2)], note='the x lanes start here (vm_plane_lanes.py)'),
        'ro': dict(dir='out', bits=512, endpoints=[[at('rr2', 'N')]]), 'ovf': dict(dir='out', bits=1, endpoints=[[at('rr2', 'S')]]),
        'so [copy c]': dict(dir='out', bits='3 x 1024', endpoints=[[at(f'ans{c}', 'N')] for c in range(3)])}
    for v in ports.values():
        cov = [cover(e) for e in v['endpoints']]; v['leaf_pins_per_net'] = max(len(e) for e in v['endpoints'])
        if v['dir'] == 'in': v['die_relay_endpoints_per_net'] = max(c[0] for c in cov); v['max_wire_um'] = max(c[1] for c in cov)
    kids = [dict(n=c['n'][len(g):], m=c['m'], x=round(c['x'] - X, 2), y=round(c['y'] - Y, 2), w=c['w'], h=c['h'], **{k: c[k] for k in ('role', 'logical_bank', 'bits', 'operand', 'su_bank', 'half') if k in c}) for c in by.values()]
    slots = [dict(n=b['n'][len(g):], x=round(b['x'] - X, 2), y=round(b['y'] - Y, 2), w=b['w'], h=b['h'], tiles=b['tiles']) for b in pl.bays if b['region'] == r and b['n'].startswith(g) and '_sE_' not in b['n']]
    # the region's own wires across its mid lines (L model, as the lane tool books them)
    sg = [s_ for s_ in pl.seams if X <= s_['A'][0] <= X + pl.RW and Y <= s_['A'][1] <= Y + RH]
    def cut(ax, cp):
        k = 0 if ax == 'x' else 1; bits = 0
        for s_ in sg:
            a0, q0 = s_['A'], s_['Q']; legs = ((a0[0], q0[0]),) if ax == 'x' else ((a0[1], q0[1]),)
            bits += s_['bits'] * any(min(l) < cp < max(l) for l in legs)
        return bits
    cuts = [dict(ax='x', pos_um=round(v, 1), seam_bits=cut('x', X + v), tracks_M6_M8_75pct=round(0.75 * RH * (1 / 0.064 + 1 / 0.080))) for v in (pl.U0 + 250.0, pl.sA - 2.0, pl.U1 + 120.0, pl.U1 + 250.0, pl.sB - 2.0, pl.SUX + 235.0)] + \
           [dict(ax='y', pos_um=v, seam_bits=cut('y', Y + v), tracks_M7_M9_75pct=round(0.75 * pl.RW * (1 / 0.064 + 1 / 0.080))) for v in (113.4, 318.6, 410.4, 523.8, 729.0, 825.0, 1000.0)]
    for c in cuts: c['util'] = round(c['seam_bits'] / (c.get('tracks_M6_M8_75pct') or c.get('tracks_M7_M9_75pct')), 4)
    return dict(name='qfd_vm_region', module='ot_qfd_vm_region_leaf (rtl/qwen_sys/vm_plane_20261013; instances and wires only)', instances=8,
        kind='DIE-ASSEMBLED PLACEMENT CLUSTER (not hardened): one relative placement, stamped 8 times; the die top instantiates the leaves and routes the seams',
        why_not_hardened=['every child is a closed / hardenable leaf with registers at its pins and every seam is leaf register -> wire <= 500 um -> leaf register: the region holds no logic, no flop and no clock tree to harden',
                          'the relay strips inside the outline hold DIE relay tiles whose lanes differ per region: a hard block could not contain them',
                          'the x lanes cross the region on M6 / M7 over its M5-capped leaves (the centre cut needs M6 + M8: 16,384 lane bits + 2.2 k existing against 22.0 k M8 tracks alone = 0.85); a region hardened with the standard cluster cap (signals M7, die M8+ only) would take that away',
                          'if the die lead wants fewer die instances later: harden per UNIT COLUMN (4 banks + 8 FIFOs + relays + control + rr4, 380 x 1,080, between two strips) with signals capped at M5 + M7 and M6 left to the die; the region-crossing nets (t1 of rr4[0], SU answers) stay die nets'],
        outline_um=[pl.RW, RH], origins_um={k: list(pl.origin(k)) for k in range(8)}, orient='R0 (every child R0: mirrored closed leaves would put their M5 clk / rst_n pins half a track off)',
        layers=dict(children='M2-M5 signals and PG (closed views / kits RLAYERS M2 M5)', seams='die nets: M6 / M7 over the leaves, M2-M5 in the channels; booked in the die cut model (vm_plane_lanes.py region_seam_bits)', parent_strap='M6 (cap + 1)'),
        clock='no region clock tree: every leaf is its own root; the die delivers one tap per leaf at phi - R(leaf) (R = the leaf view insertion.json boundary mean; new leaves: measured at their route)',
        reset='rst_n is asynchronous and reaches only the reset relays (rt, r) of bctl_t x 8, sctl_t x 6, rr4_t x 2, rr2_t; every other async clear is driven by a leaf-local r flop',
        children=kids, child_count=dict(collections.Counter(k['m'] for k in kids)), relay_strip_slots=slots, relay_strip_tiles=sum(b['tiles'] for b in slots),
        ports=ports, seams={k: v for k, v in seams.items() if not k.startswith('xplane')}, own_cut_demand=cuts,
        added_edges='0 on every path against ot_qfd_vm_region_quarter (region miter: every clock, xo / ro / so / ovf)',
        bench='results/rtl/qwen_tp8_vm_plane_20261013/region_leaf_miter/record.json (3 PASS, 12 mutants FAIL); system: results/rtl/qwen_tp8_vm_plane_20261013/system/record.json')


def control_trees(pl):
    """the two control fan trees (plane control W 20, line control W 28; RTL ot_qfd_vm_fantree, XTK levels, engine-enabled,
    tapped XTK entries early: + 0 edges) as a CHAIN OF STATIONS along the column row: one station (one fan_pc + one fan_lc
    tile per level it holds) in the free top of every relay strip of the lower regions (y 1,000 .. 1,075 of the region, above
    the last relay node), the root at the station nearest the row centre.  A station at chain distance k from the root
    registers the word at level k + 1 and holds the pad levels up to K, so every column leaf sees it on the same edge."""
    st = sorted({round(b['x'], 2) for b in pl.bays if 0 <= b['region'] < 4 and b['n'].endswith('_0')}); ys = Y0 + RH - 43.2
    xc = X0 + pl.EW / 2; root = min(range(len(st)), key=lambda k: abs(st[k] - xc)); hops = [round(st[k + 1] - st[k], 1) for k in range(len(st) - 1)]
    cols = [c for c in pl.ch if c['m'] == 'ot_qfd_vm_xcol_t']; reach = []
    for c in cols:
        k = min(range(len(st)), key=lambda k: abs(st[k] - c['x'])); reach.append((abs(st[k] - c['x']) + abs(c['y'] + c['h'] / 2 - ys), abs(k - root) + 1))
    K = max(abs(k - root) for k in range(len(st))) + 1
    nodes = sum(K - abs(k - root) for k in range(len(st)))          # registered stages held per tree (level k + 1 .. K at station k)
    return dict(stations=len(st), station_x_um=st, station_y_um=round(ys, 2), root_station=root, levels_K=K, XTK=K, max_station_hop_um=max(hops), max_station_to_column_um=round(max(r[0] for r in reach), 1),
                fan_tiles_per_tree=nodes, fan_tiles=dict(qfd_vm_fan_pc=nodes, qfd_vm_fan_lc=nodes), rule_ok=max(hops) <= 500 and max(r[0] for r in reach) <= 500,
                rtl_limit='XTK <= 6: the line-control word is tapped from a 7-entry pipeline (stg) in ot_qfd_sp_vector_memory_bv',
                root='the parent schedule logic (seam queue) has no physical owner yet: its control words enter at the root station')


def main():
    global Y0
    ap = argparse.ArgumentParser(); ap.add_argument('net'); ap.add_argument('out'); ap.add_argument('--strip-cols', default='2', help='tile columns of the relay strips: one number, or one per region column (e.g. 3,4,4,3)'); ap.add_argument('--band-relays', type=int, default=0); ap.add_argument('--pad-rows', type=int, default=0, help='pad / relay bay rows on each face of the column row'); ap.add_argument('--grow-south', type=float, default=0.0, help='move the envelope origin south by this many um (keeps the N face)')
    ap.add_argument('--region-spec', default='')
    ap.add_argument('--size', action='append', default=[], help='MODULE=WxH: what-if outline of a leaf (recorded in the report)')
    a = ap.parse_args(); d = json.loads(Path(a.net).read_text())
    for o in a.size:
        m, v = o.split('='); NEW[m] = tuple(float(t) for t in v.split('x')); SIZE_SRC[m] = 'WHAT-IF --size ' + o
    a.strip_cols = [int(v) for v in a.strip_cols.split(',')]; a.strip_cols = a.strip_cols * 4 if len(a.strip_cols) == 1 else a.strip_cols
    Y0 = G(Y0 - a.grow_south)                                   # VM3: the envelope grows to the south (its N face and the SU abutment stay)
    pl = Plan(a.strip_cols, a.band_relays, a.pad_rows).build(); ch, bays, size = pl.ch, pl.bays, pl.size
    gone = ('sp_vector_memory', 'sp_su64_sfu'); rly = ('qfd_rly', 'qkd_rly')
    old = [i for i in d['insts'] if i['n'] not in gone and not i['m'].startswith(rly)]
    relays = [i for i in d['insts'] if i['m'].startswith(rly)]
    env = dict(x=X0, y=Y0, w=pl.EW, h=2 * RH + pl.BAND)
    su64 = dict(n='sp_su64_sfu_reservation', m='UNSIZED_SU64_ACTUAL_LEAF_ENVELOPE', x=16424.64, y=19662.72, w=1991.52, h=2829.6)
    objs = ch + [dict(b, m='ot_qfd_vm_xrelay_t_BAY') for b in bays]
    hard = [(a_['n'], o['n']) for a_ in objs for o in old if ov(a_, o)]; near = sum(ov(a_, o, 20.0) for a_ in objs for o in old)
    peer = [(a_['n'], b['n']) for k, a_ in enumerate(objs) for b in objs[k + 1:] if ov(a_, b)]
    tight = [(a_['n'], b['n']) for k, a_ in enumerate(objs) for b in objs[k + 1:] if ov(a_, b, 2.16) and not ov(a_, b)]
    offgrid = sum(abs(v / 2.16 - round(v / 2.16)) > 1e-6 for a_ in objs for v in (a_['x'], a_['y']))
    xs = [a_['x'] for a_ in objs] + [a_['x'] + a_['w'] for a_ in objs]; ys = [a_['y'] for a_ in objs] + [a_['y'] + a_['h'] for a_ in objs]
    inside = min(xs) >= X0 - 1e-6 and max(xs) <= X0 + pl.EW + 1e-6 and min(ys) >= Y0 - 1e-6 and max(ys) <= Y0 + 2 * RH + pl.BAND + 1e-6
    tl = [i for i in d['insts'] if i['m'] == 'qfd_tile_nk']; cols = sorted({i['x'] for i in tl}); j = max(range(len(cols) - 1), key=lambda k: cols[k + 1] - cols[k])
    spine = (cols[j] + tl[0]['w'], cols[j + 1])
    cnt = collections.Counter(c['m'] for c in ch); area = {m: round(n * size[m][0] * size[m][1] / 1e6, 4) for m, n in cnt.items()}
    relay_tiles = sum(b['tiles'] for b in bays)
    me_sinks = pl.me + [(f"{b['n']}_t{k}", b['x'] + k * (TW + SGAP) + TW / 2, b['y']) for b in bays for k in range(b['tiles'])]
    met = me_tree(me_sinks)
    roots = {m: dict(instances=n, sinks_per_root=SINKS.get(m), new_leaf=m in NEW and not m.startswith('ot_qwen_tree'), size_from=SIZE_SRC.get(m, 'closed view LEF')) for m, n in cnt.items()}
    roots['ot_qfd_vm_xrelay_t'] = dict(instances_max=relay_tiles, sinks_per_root=SINKS['ot_qfd_vm_xrelay_t'], new_leaf=True, size_from=SIZE_SRC['ot_qfd_vm_xrelay_t'])
    roots['ot_qfd_vm_fan_t (me tree)'] = dict(instances=met['level1_nodes'] + met['level0_nodes'], sinks_per_root=2, new_leaf=True, size_from=SIZE_SRC['ot_qfd_vm_fan_t'])
    pins = {m: {b: dict(n=v['n'], dir=v['dir'], faces=v['faces'], layers=v['layers'], centroid=v['centroid'], bbox=v['bbox'])
                for b, v in L.groups(ROOT / p)[1].items()} for m, p in VIEW.items()}
    sk = collections.defaultdict(lambda: dict(n=0, bits=0, est_max=0.0, centroid_max=0.0, over_500=0, over_400=0))
    for s_ in pl.seams:
        o = sk[s_['kind']]; o['n'] += 1; o['bits'] = s_['bits']; o['est_max'] = max(o['est_max'], s_['est_um']); o['centroid_max'] = max(o['centroid_max'], s_['centroid_um'])
        o['over_500'] += s_['est_um'] > 500; o['over_400'] += s_['est_um'] > 400
    seam_bad = {k: v['over_500'] for k, v in sk.items() if v['over_500']}
    ok = not hard and near == 0 and not peer and offgrid == 0 and inside and min(xs) > spine[0] + 20 and max(xs) < spine[1] - 20 and not any(ov(a_, su64, 20.0) for a_ in objs) and pl.band['fits']
    rep = dict(status='LEAF_PLAN_V2', owner='claude/qwen-tp8-vm-phys', options=dict(strip_cols=a.strip_cols, band_relays=a.band_relays, pad_rows=a.pad_rows, grow_south=a.grow_south, what_if_sizes=a.size),
        verdict='PASS' if ok and not seam_bad and met['level1_max_wire_um'] <= 500 and met['level0_max_wire_um'] <= 500 else 'REJECT', kit_gates=GATE,
        region_seams=dict(rule='leaf register -> wire <= 500 um -> leaf register.  centroid = L1 between the two pin-group centroids (real LEF pins of the closed views, face centres of the new leaves); est = centroid + a quarter of the two pin spans (the worst bit of a bus whose pins are spread along both faces)',
                          seams=dict(sk), violating=seam_bad),
        me_tree=met, control_trees=control_trees(pl), plane_band=pl.band,
        inputs={str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [a.net, __file__] + [str(ROOT / v) for v in VIEW.values()] + [str(ROOT / 'physical/ref_tile' / k / f) for k in KIT.values() for f in ('floorplan.json', 'gate_result.json') if (ROOT / 'physical/ref_tile' / k / f).exists()]},
        slot=dict(shape=f'4 x 2 regions, widths {[g_["RW"] for g_ in pl.geo]} x {RH} um (relay strips sW / sA / sB of {a.strip_cols} tile columns per region column) + {pl.BAND} um band (one row of 32 bit-plane column leaves) between the rows; region r at column r % 4, row r // 4',
                  origin_um=[X0, Y0], size_um=[pl.EW, round(2 * RH + pl.BAND, 3)], area_mm2=round(pl.EW * (2 * RH + pl.BAND) / 1e6, 4), spine_x_um=[round(spine[0], 3), round(spine[1], 3)],
                  bbox_um=[round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)],
                  region_origins={r: list(pl.origin(r)) for r in range(8)}, region_um=[[g_['RW'], RH] for g_ in pl.geo], region_column_geometry=pl.geo, unit_x_um=[pl.geo[0]['U0'], pl.geo[0]['U1']],
                  old_slot_um=[2332.776, 2073.576], request_0420_um=[4708.8, 2347.92]),
        geometry=dict(verdict='PASS' if ok else 'FAIL', hard_overlaps_it2=hard[:8], within_20um_of_it2_hard=near, peer_overlaps=peer[:8], peer_pairs_closer_than_2p16=len(tight),
                      off_2p16_grid=offgrid, inside_envelope=inside, kept_it2_hard_instances=len(old), removed=list(gone), su64_reservation=su64,
                      it2_relay_objects_inside_envelope=sum(ov(env, i) for i in relays)),
        leaf_count=dict(cnt), leaf_area_mm2=area, placed_leaf_area_mm2=round(sum(area.values()), 4), x_relay_bay_tiles=relay_tiles,
        x_relay_bay_bits=relay_tiles * 512, clock_roots=roots, max_sinks_per_root=max(v['sinks_per_root'] or 0 for v in roots.values()),
        root_rule='<= 15000 sinks per root: every leaf is its own root; no region-level tree',
        sizing={m: dict(source=SIZE_SRC[m], outline_um=list(NEW[m]), sinks_per_root=SINKS.get(m), gate=GATE.get(m)) for m in KIT},
        real_pins=pins, children=ch, x_relay_bays=bays, seam_segments=pl.seams, me_sinks=len(me_sinks))
    rspec = region_spec(pl, dict(sk))
    if a.region_spec: Path(a.region_spec).write_text(json.dumps(dict(status='REGION_CLUSTER_SPEC', owner='claude/qwen-tp8-vm-phys', plan_options=rep['options'], **rspec), indent=1) + '\n')
    Path(a.out).write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: rep[k] for k in ('verdict', 'options', 'plane_band', 'slot', 'geometry', 'leaf_count', 'x_relay_bay_tiles', 'max_sinks_per_root')}, default=str)[:3000])
    print('region_ports', json.dumps({k: {m: v[m] for m in ('leaf_pins_per_net', 'die_relay_endpoints_per_net', 'max_wire_um') if m in v} for k, v in rspec['ports'].items()})); print('region_cuts', json.dumps(rspec['own_cut_demand']))
    print('control_trees', json.dumps({k: v for k, v in rep['control_trees'].items() if k != 'station_x_um'}))
    print('seams', json.dumps(dict(sk))); print('me', json.dumps({k: v for k, v in met.items() if k != 'slot_me_pins'}))

if __name__ == '__main__': main()
