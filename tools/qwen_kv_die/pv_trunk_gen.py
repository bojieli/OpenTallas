#!/usr/bin/env python3
"""KVPLAN 1815 (2026-10-16; Q-KV approved): the PV16 pair successor qkd_pvw_die_t -- every wire of the pair inside
measured reach, by registered relay-standard stations (closed qkd_rlys_296 / 36 views) in planned lanes / channels.

Why: the per-bit die audit (die_audit_bits.py, kvs13i/j) measured the old pair (qkd_pvw_die_e, 289 closed leaves flattened
by kv_expand) at 6-10.6 mm per bit: each V word landed at one face pin and fanned to 256 slices over 9.3 mm, the command
word broadcast to 288 tiles in one edge, the column flags returned over 9.4 mm.

Structure (canonical R0 frame: control strip at the top, block row r = 0 at the bottom, x: W lane | block column 0 | CT |
block column 1 | E lane):
  * blocks unchanged (2 x 16 blocks of 3 x 3 closed tiles: 8 slices around the join, kv_die.PV_BANK / PV_JOIN);
  * station channels h_0 .. h_16 (CH um) under / between / over the block rows; every slice's input face and the join's
    join_go / rst face one of them;
  * V enters per (port k, GS group g) as its own 128-b die word vc<k>_<g> on the W face (ports 0-3) / E face (ports 4-7)
    at the group's middle channel h_2g+1 (the die relays each chunk there: no in-pair V trunk); a side-lane station takes it
    and two side-lane stages bring it to h_2g / h_2g+2 (two pad stages for h_2g+1); in a channel it reaches its block
    station S1 in three hops (pads for the near column, transits for the far column);
  * the control word {rst_n, cmd[31:0]} and e (512 b, from the strip) run down the CT trunk X_16, M_15, X_15, ..., X_0
    (one stage per ~313 um); group g's channels take it at depth D_g - 3 (taps of X_2g, X_2g+1 + 2 pads, X_2g+2 + 4
    pads) and reach S1 in three hops;
  * S1 (one per block face and group, at the block's channel middle) drives its tiles' input pins (<= ~330 um);
    every tile of group g sees command AND data D_g extra edges after the old pair -> they meet exactly as before;
  * the 31-b V header vh<k> = {epoch, t, valid} goes straight to the control tile in the strip (FIRST_INPUT_AGE as before);
    the chunk words must arrive DELTA_G = D_g - 6 die edges after the header (kv_die pads the chunk relay chains);
  * column flags: F1 over the join -> (2 pads, even rows) -> F2 at CT -> U-shaped return trunk (down CT to h_0, then up to
    the control tile): D_g + R_r is one constant, so the control tile keeps one check slot (ctl_t TRUNK_D / FLAG_D);
  * sf[6] (bank 6 fault -> join: 551 um) takes two stations in the channel below (fault timing only).
Outputs: column s's y / y_valid at its own static age A_s = out_age + COL_D[s] - COL_D[0] (RTL localparam + plan JSON).

    pv_trunk_gen.py --out-sv rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv --out-plan results/arch/qwen_kv_die/pv_trunk_t/plan.json
"""
import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / 'physical/ref_tile'
B, TILE = 561.6, 172.8
PV_BANK = {0: (0.0, 0.0, 'R0'), 1: (194.4, 0.0, 'R0'), 2: (0.0, 194.4, 'MX'), 3: (0.0, 388.8, 'MX'),
           4: (194.4, 388.8, 'MX'), 5: (388.8, 388.8, 'MX'), 6: (388.8, 0.0, 'R0'), 7: (388.8, 194.4, 'R0')}
PV_JOIN = (194.4, 194.4, 'R0')
STD = {1: (12.96, 12.96), 36: (12.96, 12.96), 296: (21.6, 47.52)}
LEAF_LEF = dict(
    ot_qwen_tp8_pv_slice_t=RT / 'qkd_pv_slice_rstpin_r5/views/ot_qwen_tp8_pv_slice_t/ot_qwen_tp8_pv_slice_t.lef',
    ot_qwen_tp8_pv_join_t=RT / 'qkd_pv_join_rstpin_r5/views/ot_qwen_tp8_pv_join_t/ot_qwen_tp8_pv_join_t.lef',
    ot_qwen_tp8_pv_wide_ctl=RT / 'qkd_pv_ctl_rstpin_a72/views/ot_qwen_tp8_pv_wide_ctl/ot_qwen_tp8_pv_wide_ctl.lef',
    **{f'qkd_rlys_{s}': RT / f'qkd_rlys_{s}/views/qkd_rlys_{s}/qkd_rlys_{s}.lef' for s in STD})
FLIP = dict(R0=(0, 0), MX=(0, 1), MY=(1, 0), R180=(1, 1))
TOP_BANKS, BOT_BANKS = (2, 3, 4, 5), (0, 1, 6, 7)


def lef_pins(path):
    t = Path(path).read_text()
    sz = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', t)
    pins = {}
    for m in re.finditer(r'^  PIN (\S+)\s*$(.*?)^  END \1\s*$', t, re.M | re.S):
        r = re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', m.group(2))
        if r:
            x0, y0, x1, y1 = map(float, r.groups())
            pins[m.group(1)] = ((x0 + x1) / 2, (y0 + y1) / 2)
    return (float(sz.group(1)), float(sz.group(2))), pins


def pin_at(x0, y0, w, h, o, p):
    fx, fy = FLIP[o]
    return (x0 + (w - p[0] if fx else p[0]), y0 + (h - p[1] if fy else p[1]))


def col_of(c, r):
    """block (c, r) -> column s = 8 H + GS (kv_die.pv_col_rc inverse: c = H & 1, r = 2 GS + (H >> 1))"""
    return 8 * (c + 2 * (r & 1)) + r // 2


def align_dir(target, al):
    """'v' when the aligned station sits above / below the target (keep x lanes), else 'h' (keep y levels)"""
    cx = sum(x + STD[s][0] / 2 for s, (x, y) in al) / len(al)
    cy = sum(y + STD[s][1] / 2 for s, (x, y) in al) / len(al)
    return 'v' if abs(target[1] - cy) >= abs(target[0] - cx) else 'h'


def _d(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


class Free:
    """occupancy bitmap (STEP um) of the frame; nearest-free-spot search in a local window"""
    STEP = 2.16

    def __init__(self, W, H):
        self.nx, self.ny = int(W / self.STEP) + 1, int(H / self.STEP) + 1
        self.occ = np.zeros((self.nx, self.ny), dtype=np.int8)
        self.W, self.H = W, H

    def block(self, x0, y0, x1, y1):
        e = 1e-6
        ax, ay = max(0, int(math.floor(x0 / self.STEP + e))), max(0, int(math.floor(y0 / self.STEP + e)))
        bx, by = min(self.nx, int(math.ceil(x1 / self.STEP - e))), min(self.ny, int(math.ceil(y1 / self.STEP - e)))
        if ax < bx and ay < by:
            self.occ[ax:bx, ay:by] = 1

    def nearest(self, tx, ty, w, h, halo, region=None, rad=700.0):
        S = self.STEP
        x0r, y0r, x1r, y1r = region or (0.0, 0.0, self.W, self.H)
        wx0, wy0 = max(x0r, tx - rad, 0.0), max(y0r, ty - rad, 0.0)
        wx1, wy1 = min(x1r, tx + rad, self.W), min(y1r, ty + rad, self.H)
        ix0, iy0 = int(math.ceil(wx0 / S - 1e-6)), int(math.ceil(wy0 / S - 1e-6))
        ix1, iy1 = int(math.floor(wx1 / S + 1e-6)), int(math.floor(wy1 / S + 1e-6))
        kx, ky = int(math.ceil((w + 2 * halo) / S - 1e-6)), int(math.ceil((h + 2 * halo) / S - 1e-6))
        if ix1 - ix0 < kx or iy1 - iy0 < ky:
            return None
        sub = self.occ[ix0:ix1, iy0:iy1].astype(np.int32)
        c = np.pad(sub, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        s = c[kx:, ky:] - c[:-kx, ky:] - c[kx:, :-ky] + c[:-kx, :-ky]
        ix, iy = np.nonzero(s == 0)
        if not len(ix):
            return None
        ox = (ix0 + ix) * S + halo
        oy = (iy0 + iy) * S + halo
        d = np.abs(ox + w / 2 - tx) + np.abs(oy + h / 2 - ty)
        j = int(np.argmin(d))
        return float(ox[j]), float(oy[j])


class Gen:
    def __init__(self, a):
        self.a = a
        self.CH, self.CT, self.SW, self.STRIP = a.ch, a.ct, a.sw, a.strip
        self.FW = 2 * self.SW + 2 * B + self.CT
        # channel heights: the double-group channels h_2g (two faces of two groups) get CH_EVEN (two 296 rows), the
        # group-middle channels h_2g+1 CH (one 296 row + the 36 rows); both on the 43.2-um lattice (Q-KV 10-16 decision:
        # pay the area, >= 20-um macro clearances, no stations inside the blocks' 21.6-um gaps)
        self.CHs = [a.ch_even if h % 2 == 0 else a.ch for h in range(17)]
        self.ylo = [sum(self.CHs[:h]) + h * B for h in range(17)]
        self.FH = self.ylo[16] + self.CHs[16] + self.STRIP
        self.views = {m: lef_pins(p) for m, p in LEAF_LEF.items()}
        self.cells = {}
        self.free = Free(self.FW, self.FH)
        self.wires = []
        self.inst = []
        self.st = {}
        self.root = {}
        self.rootpin = {}            # root key -> (x, y) of its pin (face / tile pin) for the hop check

    # ---- geometry ---------------------------------------------------------------------------------------------------
    def bx(self, c):
        return self.SW + c * (B + self.CT)

    def by(self, r):
        return self.ylo[r] + self.CHs[r]

    def hy(self, r):
        return self.ylo[r] + self.CHs[r] / 2

    def chan(self, r):
        y0 = self.ylo[r]
        return (0.0, y0, self.FW, y0 + self.CHs[r])

    def ct_x(self):
        return self.SW + B + self.CT / 2

    def ct(self):
        return (self.SW + B, 0.0, self.SW + B + self.CT, self.FH - self.STRIP)

    def lane(self, side):
        return (0.0, 0.0, self.SW, self.FH - self.STRIP) if side == 'W' else (self.FW - self.SW, 0.0, self.FW, self.FH - self.STRIP)

    def s1_x(self, c):
        return self.bx(c) + B / 2

    def place_tiles(self):
        for r in range(16):
            for c in range(2):
                s = col_of(c, r)
                for l_, (x, y, o) in PV_BANK.items():
                    self.cells[f'u_s{s}_b{l_}'] = ('ot_qwen_tp8_pv_slice_t', self.bx(c) + x, self.by(r) + y, TILE, TILE, o)
                self.cells[f'u_s{s}_j'] = ('ot_qwen_tp8_pv_join_t', self.bx(c) + PV_JOIN[0], self.by(r) + PV_JOIN[1], TILE, TILE, 'R0')
        # control tile in the strip over CT, MX: its N-face cmd / col pins face the trunk below
        self.cells['u_ctl'] = ('ot_qwen_tp8_pv_wide_ctl', self.ct_x() - 21.6, self.FH - self.STRIP + (self.STRIP - 43.2) / 2,
                               43.2, 43.2, 'MX')
        h = self.a.halo_tile - 4.32          # + the replica's own 4.32-um halo = halo_tile to every tile
        for n, (m, x, y, w, hh, o) in self.cells.items():
            self.free.block(x - h, y - h, x + w + h, y + hh + h)
        # the strip is reserved for the control tile and the face pins
        self.free.block(0, self.FH - self.STRIP, self.FW, self.FH)

    def tpin(self, cell, pin):
        m, x, y, w, h, o = self.cells[cell]
        return pin_at(x, y, w, h, o, self.views[m][1][pin])

    # ---- stations --------------------------------------------------------------------------------------------------
    @staticmethod
    def replicas(n):
        if n == 1:
            return [1]
        out = []
        while n > 296:
            out.append(296)
            n -= 296
        if n > 0:
            out += [296] if n > 3 * 36 else [36] * math.ceil(n / 36)
        return out

    def station(self, name, keys, src, target, ck, region, depth_check=True, align=None, lanes=None, prio=5):
        """one registered stage of keys; src: parent station name / None (root) or dict key -> parent.  Placement is
        deferred (place_all, by prio then creation order): lanes = CT lane indices for replica j (vertical chains),
        align = station whose replica j this one's replica j lines up with, else nearest free spot to target in region"""
        if name in self.st:
            raise ValueError(f'duplicate station {name}')
        par = (lambda k: src.get(k)) if isinstance(src, dict) else (lambda k: src)
        reps = self.replicas(len(keys))
        depths = set()
        for k in keys:
            p = par(k)
            depths.add(0 if p is None else self.st[p]['depth'])
        if depth_check and len(depths) != 1:
            raise ValueError(f'{name}: inputs at different depths {sorted(depths)}')
        self.wires.append((f'w_{name}', sum(reps)))
        self.st[name] = dict(keys=list(keys), idx={k: i for i, k in enumerate(keys)}, wire=f'w_{name}', reps=None,
                             sizes=reps, depth=max(depths) + 1, par={k: par(k) for k in keys}, ck=ck, target=target,
                             region=region, align=align, lanes=lanes, prio=prio, order=len(self.st))
        return name

    def place_all(self):
        if self.a.no_place:       # structure only (RTL / bench): the netlist does not depend on the station positions
            for d in self.st.values():
                d['reps'] = [(s_, (0.0, 0.0)) for s_ in d['sizes']]
            return
        for name in sorted(self.st, key=lambda n: (self.st[n]['prio'], self.st[n]['order'])):
            d = self.st[name]
            placed = []
            tx, ty = d['target']
            al = self.st[d['align']]['reps'] if d['align'] else None
            if d['align'] and al is None:
                raise ValueError(f'{name}: aligned to unplaced {d["align"]}')
            for j, s in enumerate(d['sizes']):
                w, h = STD[s]
                region = d['region']
                tx_, ty_ = tx, ty
                if d.get('rep_targets'):
                    tx_, ty_ = d['rep_targets'][j]
                elif d['lanes'] is not None:
                    lx = self.lane_x(d['lanes'][j % len(d['lanes'])])
                    region = (lx - 4.32, region[1], lx + w + 4.32, region[3])
                    tx_ = lx + w / 2
                    ty_ = ty + (j // len(d['lanes'])) * (h + 4.32)
                elif al and j < len(al):
                    ax_, ay_ = al[j][1]
                    if align_dir(d['target'], al) == 'v':
                        tx_ = ax_ + STD[al[j][0]][0] / 2
                    else:
                        ty_ = ay_ + STD[al[j][0]][1] / 2
                elif d.get('xstep'):
                    tx_ = tx + j * d['xstep']
                if region is not None and d['lanes'] is None and d.get('row') and region[3] - region[1] < 300:
                    # a station channel: 296s on the row facing the tiles they feed ('lo' = next to the block below,
                    # 'hi' = next to the block above), 36s on the middle row
                    lo = region[1] + self.a.halo_tile
                    hi = region[3] - self.a.halo_tile
                    if s == 296 or d.get('same_row'):
                        ty_ = lo + h / 2 if d['row'] == 'lo' else hi - h / 2
                        if s != 296 and placed:
                            tx_ = placed[-1][1][0] + (25.92 if d.get('dir', 1) > 0 else -17.28)
                    else:
                        ty_ = (lo + hi) / 2
                if d.get('rep_targets'):
                    got = self.free.nearest(tx_, ty_, w, h, 4.32, region, rad=60.0) or self.free.nearest(tx_, ty_, w, h, 4.32, region)
                else:
                    got = self.free.nearest(tx_, ty_, w, h, 4.32, region)
                if got is None:
                    raise ValueError(f'{name}: no spot for replica {j} ({s}) near ({tx_:.0f}, {ty_:.0f}) in {region}')
                self.free.block(got[0], got[1], got[0] + w, got[1] + h)
                placed.append((s, got))
            d['reps'] = placed

    def emit_insts(self):
        self.inst = []
        for name, d in sorted(self.st.items(), key=lambda kv: kv[1]['order']):
            off = 0
            for j, (s, (x, y)) in enumerate(d['reps']):
                rn = f'u_{name}_r{j}'
                self.cells[rn] = (f'qkd_rlys_{s}', x, y, STD[s][0], STD[s][1], 'R0')
                ins = []
                for i in range(s):
                    k = off + i
                    ins.append(self.expr(d['keys'][k], d['par'][d['keys'][k]]) if k < len(d['keys']) else "1'b0")
                self.inst.append(f'  qkd_rlys_{s} {rn} (.ck({d["ck"]}), .a({{{", ".join(reversed(ins))}}}), .b({d["wire"]}[{off + s - 1}:{off}]));')
                off += s

    def lane_x(self, l_):
        """origin x of a CT lane: V lanes 0-3 (block column 0) at the CT's column-0 side, then the flag lane f0, control
        lanes 4-5, flag lane f1, V lanes 6-9 (column 1) at its column-1 side"""
        x = self.SW + B + self.a.halo_tile
        order = ['k0', 0, 1, 2, 3, 'f0', 'f1', 6, 7, 8, 9, 'k1']
        for o in order:
            if o == l_:
                return x
            x += (12.96 if o in ('f0', 'f1') else 21.6) + 4.32
        raise KeyError(l_)

    def expr(self, key, parent):
        if parent is None:
            return self.root[key]
        p = self.st[parent]
        return f'{p["wire"]}[{p["idx"][key]}]'

    # ---- sources -----------------------------------------------------------------------------------------------------
    def build_root(self):
        for g in range(8):
            for k in range(8):
                for b in range(128):
                    self.root[('V', g, k, b)] = f'vc{k}_{g}[{b}]'
        for k in range(8):
            for H in range(4):
                for b in range(16):
                    self.root[('E', k, H, b)] = f'in_e[{64 * k + 16 * H + b}]'
        for b in range(32):
            self.root[('C', b)] = f'cmd_w[{b}]'
        self.root[('R',)] = 'rst_n'

    @staticmethod
    def tile_srcs(H, GS, l_):
        PA, PB = l_, l_ ^ 4
        pv2 = [('V', GS, PA, b) for b in range(128)] + [('V', GS, PB, b) for b in range(128)]
        pe2 = [('E', PA, H, b) for b in range(16)] + [('E', PB, H, b) for b in range(16)]
        bc = [('C', 0), ('C', 1 + l_), ('C', 9 if l_ < 4 else 10)] + [('C', b) for b in range(11, 31)]
        return pv2, pe2, bc

    def face_tiles(self, h, c):
        """tiles of block column c facing channel h, per group: {g: [(s, bank or 'j')]}"""
        out = defaultdict(list)
        if h >= 1:                       # row h-1: top tiles + join
            s = col_of(c, h - 1)
            out[(h - 1) // 2] += [(s, l_) for l_ in TOP_BANKS] + [(s, 'j')]
        if h <= 15:                      # row h: bottom tiles
            s = col_of(c, h)
            out[h // 2] += [(s, l_) for l_ in BOT_BANKS]
        return out

    def tile_keys(self, s, t):
        H, GS = s // 8, s % 8
        if t == 'j':
            return [('C', 31), ('R',)]
        pv2, pe2, bc = self.tile_srcs(H, GS, t)
        return pv2 + pe2 + bc + [('R',)]

    # ---- build --------------------------------------------------------------------------------------------------------
    def build(self):
        self.build_root()
        self.place_tiles()
        CTR, ctx = self.ct(), self.ct_x()
        rowclk = lambda r: f'col_clk[{col_of(0, max(0, min(r, 15)))}]'   # noqa: E731
        NS = self.a.ns                  # registered stages per block-row pitch along CT (pitch / NS <= reach)
        midy = lambda r, i: self.hy(r + 1) + (self.hy(r) - self.hy(r + 1)) * i / NS   # noqa: E731  i-th node between h_r+1, h_r
        VL = {(0, 'W'): [0, 1], (0, 'E'): [2, 3], (1, 'W'): [6, 7], (1, 'E'): [8, 9]}
        # 1. CT control trunks, one per block column (its lane next to the column): {rst_n, cmd[31:0]} + the e words of the
        #    column's heads H = c, c + 2 (289 b); X_r at the crossings, NS - 1 mid nodes per row pitch
        ckc = {c: [('R',)] + [('C', b) for b in range(32)] + [('E', k, H, b) for k in range(8) for H in (c, c + 2) for b in range(16)]
               for c in range(2)}
        X = {}
        for c in range(2):
            prev = None
            for r in range(16, -1, -1):
                if r < 16:
                    for i in range(1, NS):
                        prev = self.station(f'M{r}_{i}c{c}', ckc[c], prev, (ctx, midy(r, i)), rowclk(r), CTR, lanes=[f'k{c}'], prio=0)
                X[(r, c)] = prev = self.station(f'X{r}c{c}', ckc[c], prev, (ctx, self.hy(r)), rowclk(r), CTR, lanes=[f'k{c}'], prio=0)
        dX = {r: self.st[X[(r, 0)]]['depth'] for r in range(17)}
        # group g's control word leaves its 3 channel crossings at depth dX[2g]: X_2g directly, X_2g+1 + NS, X_2g+2 + 2 NS
        # pads (a U around the crossing in the column's control lane, ending next to it)
        offs = {0: [], NS: [1, 2, -1][:NS] if NS == 3 else list(range(1, NS + 1)),
                2 * NS: [1, 2, 3, -3, -2, -1] if NS == 3 else list(range(1, 2 * NS + 1))}
        cross = {}
        for c in range(2):
            for g in range(8):
                for h, npad in ((2 * g, 0), (2 * g + 1, NS), (2 * g + 2, 2 * NS)):
                    p = X[(h, c)]
                    for i in range(npad):
                        o_ = offs[npad][i]
                        if h == 16:     # the top crossing: the strip is above it -> its pads sit in channel h_16
                            p = self.station(f'CP{h}g{g}c{c}_{i}', ckc[c], p, (self.lane_x(f'k{c}'), self.hy(h)), rowclk(h),
                                             self.chan(h), prio=0)
                        else:
                            p = self.station(f'CP{h}g{g}c{c}_{i}', ckc[c], p, (ctx, self.hy(h) + o_ * 56.16), rowclk(h), CTR,
                                             lanes=[f'k{c}'], prio=0)
                    cross[(h, g, c)] = p
                    assert self.st[p]['depth'] == dX[2 * g], (h, g)
        ctl_keys = ckc[0] + [k for k in ckc[1] if k not in set(ckc[0])]
        # 2. V side entry: e0 at the face end of channel h_2g+1, two hops across the near column, then one copy per block
        #    column into its CT lanes (t2), and NS stages up / down / pad to the group's 3 crossings
        vt = {}
        self.v_entry_stages = 4 + NS
        for g in range(8):
            hm = 2 * g + 1
            for side, ports in (('W', range(4)), ('E', range(4, 8))):
                keys = [('V', g, k, b) for k in ports for b in range(128)]
                ck = f'col_clk[{col_of(0 if side == "W" else 1, hm)}]'
                fx = 0.0 if side == 'W' else self.FW
                sg = 1.0 if side == 'W' else -1.0
                for i in ports:
                    self.rootpin.update({('V', g, i, b): (fx, self.hy(hm)) for b in range(128)})
                e0 = self.station(f'V{side}{g}e', keys, None, (fx + (40.0 if side == 'W' else -100.0), self.hy(hm)), ck, self.chan(hm), prio=3)
                self.st[e0]['xstep'] = 25.92
                a1 = self.station(f'V{side}{g}a', keys, e0, (fx + sg * 270.0 - (50 if side == 'E' else 0), self.hy(hm)), ck, self.chan(hm), prio=3)
                self.st[a1]['xstep'] = 25.92
                b1 = self.station(f'V{side}{g}b', keys, a1, (fx + sg * 530.0 - (50 if side == 'E' else 0), self.hy(hm)), ck, self.chan(hm), prio=3)
                self.st[b1]['xstep'] = 25.92
                for c in range(2):
                    lanes = VL[(c, side)]
                    t2 = self.station(f'V{side}{g}c{c}t', keys, b1, (ctx, self.hy(hm) + 56.16), ck, CTR, lanes=lanes, prio=0)
                    p, q, w = t2, t2, t2
                    for i in range(1, NS + 1):
                        # chain ends sit at their crossing (u below it, d above it: the even crossing holds both groups')
                        p = self.station(f'V{side}{g}c{c}u{i}', keys, p, (ctx, midy(hm, NS - i) if i < NS else self.hy(hm + 1) - 28.08), ck, CTR, lanes=lanes, prio=0)
                        q = self.station(f'V{side}{g}c{c}d{i}', keys, q, (ctx, midy(hm - 1, i) if i < NS else self.hy(hm - 1) + 28.08), ck, CTR, lanes=lanes, prio=0)
                        po = {1: 2, 2: -1}.get(i, 0) if i < NS else 0.0
                        w = self.station(f'V{side}{g}c{c}p{i}', keys, w, (ctx, self.hy(hm) + po * 56.16), ck, CTR, lanes=lanes, prio=0)
                    vt[(hm + 1, g, side, c)], vt[(hm - 1, g, side, c)], vt[(hm, g, side, c)] = p, q, w
        # 3. per channel h, block column c, group g: W1 (V) and Ka (control) at the block's CT side, then one station per
        #    tile under / over its input face (bank 4's also carries the join's join_go / rst_n)
        self.S1, self.s1_of = {}, {}
        self.pending_rst, self.rst_of, self.kac_of = [], {}, {}
        self.row_of = {col_of(c, r): r for c in range(2) for r in range(16)}
        for h in range(17):
            for c in range(2):
                for g, tiles in sorted(self.face_tiles(h, c).items()):
                    s0 = tiles[0][0]
                    ck = f'col_clk[{s0}]'
                    keys = list(dict.fromkeys(k for s, t in tiles for k in self.tile_keys(s, t)))
                    ckeys = [k for k in keys if k[0] in ('C', 'R', 'E')]
                    vkeys = [k for k in keys if k[0] == 'V']
                    vkeys = [k for k in vkeys if k[2] < 4] + [k for k in vkeys if k[2] >= 4]
                    # A: the face word (V from this column's CT lanes + the control word) at the block's CT side
                    ax = self.bx(c) + B - 230.0 if c == 0 else self.bx(c) + 230.0 - 5 * 25.92
                    # keys ordered by the x of the tiles that use them (far tiles' keys on the far replicas)
                    kx = {}
                    for s_, t_ in tiles:
                        tx0 = PV_BANK[t_][0] if t_ != 'j' else PV_JOIN[0]
                        for k in self.tile_keys(s_, t_):
                            kx[k] = min(kx.get(k, 1e9), tx0) if c == 0 else max(kx.get(k, -1e9), tx0)
                    # far tiles' keys first (column 0: far = small x; column 1: far = large x); replica 0 at the far edge
                    # of the window that keeps every replica within reach of this column's CT lanes
                    both = any(t in TOP_BANKS for _, t in tiles) and any(t in BOT_BANKS for _, t in tiles)
                    # the face row; a channel serving both rows of one group puts A on the row of its far tiles
                    # (column 0: left tiles 2 / 3 on the lower row; column 1: right tiles 6 / 7 on the upper row)
                    arow = ('lo' if c == 0 else 'hi') if both else ('lo' if any(t in TOP_BANKS for _, t in tiles) else 'hi')
                    lo_, hi_ = self.chan(h)[1] + self.a.halo_tile, self.chan(h)[3] - self.a.halo_tile
                    ay = lo_ + 23.76 if arow == 'lo' else hi_ - 23.76
                    # A_v: the face's V, one station per port side (W ports from this column's W lanes, E from its E lanes),
                    # each as far from CT as its lanes' reach allows (the far tiles' stations need it there)
                    aw = {}
                    for side, lanes in (('W', VL[(c, 'W')]), ('E', VL[(c, 'E')])):
                        sk = sorted([k for k in vkeys if (k[2] < 4) == (side == 'W')], key=lambda k: ((kx[k] if c == 0 else -kx[k]), str(k)))
                        if c == 0:
                            x0_ = max(self.lane_x(l_) for l_ in lanes) + 21.6 - (self.a.hop - 90.0)
                        else:
                            x0_ = min(self.lane_x(l_) for l_ in lanes) + (self.a.hop - 90.0) - 21.6
                        st_ = self.station(f'W{h}c{c}g{g}{side}', sk, vt[(h, g, side, c)], (x0_, ay), ck, self.chan(h), prio=1)
                        nr = len(self.replicas(len(sk)))
                        self.st[st_]['rep_targets'] = [((x0_ + 10.8 + j_ * 25.92) if c == 0 else (x0_ + 10.8 - j_ * 25.92), ay) for j_ in range(nr)]
                        aw[side] = st_
                    w1 = aw['W']
                    # A_c: the face's control word, from the column's control lane at the CT edge: closer to the far tiles
                    kl = self.lane_x(f'k{c}')
                    acx = kl + 21.6 - self.a.hop + 90.0 if c == 0 else kl + self.a.hop - 90.0 - 21.6
                    kac = self.station(f'K{h}c{c}g{g}', ckeys, cross[(h, g, c)], (acx + 10.8, ay), ck, self.chan(h), prio=1)
                    self.st[kac]['rep_targets'] = [(acx + 10.8, ay)]
                    for s_, t_ in tiles:
                        self.kac_of[(s_, t_)] = kac
                    # one station per tile, on the channel row facing it, as far toward CT as its pins allow (bank 4's also
                    # carries the join's join_go / rst_n)
                    for s, t in tiles:
                        if t == 'j':
                            continue
                        tk = list(dict.fromkeys(self.tile_keys(s, t) + ([('C', 31), ('R',)] if (s, 'j') in tiles and t == 4 else [])))
                        row = 'lo' if t in TOP_BANKS else 'hi'
                        sy = lo_ + 23.76 if row == 'lo' else hi_ - 23.76
                        pins = [self.tpin(f'u_s{s}_b{t}', f'{pn}[{i_}]') for pn, n_ in (('pv2', 256), ('pe2', 32), ('bc', 23)) for i_ in (0, n_ - 1)]
                        if (s, 'j') in tiles and t == 4:
                            pins += [self.tpin(f'u_s{s}_j', 'join_go'), self.tpin(f'u_s{s}_j', 'rst_n')]
                        # feasible origins x: every pin within hop of the station's b pins (x + 21.6) and every A replica's
                        # b pin within hop of the station's a pins (x); the 36 part sits on the middle row (worst dy)
                        H_ = self.a.hop
                        my = (lo_ + hi_) / 2
                        lo_b, hi_b = -1e9, 1e9
                        for px, py in pins:
                            dy_ = max(abs(py - sy), abs(py - my))
                            lo_b = max(lo_b, px - (H_ - dy_) - 21.6)
                            hi_b = min(hi_b, px + (H_ - dy_) - 21.6)
                        for ax_, ay_ in self.st[aw['W']]['rep_targets'] + self.st[aw['E']]['rep_targets'] + self.st[kac]['rep_targets']:
                            abx = ax_ - 10.8 + 21.6
                            dy_ = max(abs(ay_ - sy), abs(ay_ - my))
                            lo_b = max(lo_b, abx - (H_ - dy_))
                            hi_b = min(hi_b, abx + (H_ - dy_))
                        x_lo, x_hi = self.bx(c) + 4.32, self.bx(c) + B - 21.6 - 4.32
                        sx = min(max((lo_b + hi_b) / 2, x_lo), x_hi) if lo_b <= hi_b else min(max(hi_b, x_lo), x_hi)
                        name = self.station(f'S{s}b{t}', tk, {k: ((aw['W'] if k[2] < 4 else aw['E']) if k[0] == 'V' else kac) for k in tk}, (sx + 10.8, sy), ck,
                                            self.chan(h), prio=2, depth_check=False)
                        self.st[name]['row'] = row
                        self.st[name]['same_row'] = True
                        self.st[name]['dir'] = 1 if c == 0 else -1
                        self.s1_of[(s, t)] = name
                        # the slice's reset pin is on its W face, mid height: its own 1-b station in the nearer channel
                        rp = self.tpin(f'u_s{s}_b{t}', 'rst_n')
                        up = rp[1] > self.by(h if t in BOT_BANKS else h - 1) + B / 2      # pin in the block's upper half?
                        rh = (h + 1 if t in BOT_BANKS else h) if up else (h if t in BOT_BANKS else h - 1)
                        rsrc = kac if rh == h else None
                        self.pending_rst.append((s, t, rh, rp, ck))
                        if t == 4 and (s, 'j') in tiles:
                            self.s1_of[(s, 'j')] = name
                    self.S1[(h, c, g)] = w1
        # 3b. the slices' reset stations (1 b each), fed by the control station of the same row's face in that channel
        for s, t, rh, rp, ck in self.pending_rst:
            below = rh == self.row_of[s]            # channel h_r under the tile's row r
            kac = self.kac_of[(s, 0 if below else 3)]
            lo_, hi_ = self.chan(rh)[1] + self.a.halo_tile, self.chan(rh)[3] - self.a.halo_tile
            ry = hi_ - 6.48 if below else lo_ + 6.48     # the face row next to the tile's block
            # x: between the reset pin and its control station, both within the hop
            kx_ = self.st[kac]['rep_targets'][0][0] - 10.8 + 21.6
            dyp = abs(rp[1] - ry)
            lo_b = max(rp[0] - (self.a.hop - dyp) - 12.96, kx_ - (self.a.hop - abs(self.st[kac]['rep_targets'][0][1] - ry)))
            hi_b = min(rp[0] + (self.a.hop - dyp) - 12.96, kx_ + (self.a.hop - abs(self.st[kac]['rep_targets'][0][1] - ry)))
            rx = (lo_b + hi_b) / 2 if lo_b <= hi_b else (rp[0] + kx_) / 2
            nm = self.station(f'R{s}b{t}', [('R',)], kac, (rx + 6.48, ry), ck, self.chan(rh), prio=3)
            self.st[nm]['rep_targets'] = [(rx + 6.48, ry)]
            self.rst_of[(s, t)] = nm
        # 4. flags: F1 over the join, 2 pads for even rows, F2 at CT, U-shaped return trunk in the CT flag lanes
        fl = {}
        for r in range(16):
            for c in range(2):
                s = col_of(c, r)
                jx, _ = self.tpin(f'u_s{s}_j', 'y_valid')
                self.root[('FV', s)] = f'yv_w[{s}]'
                self.root[('FF', s)] = f'jf_w[{s}]'
                self.rootpin[('FV', s)] = self.tpin(f'u_s{s}_j', 'y_valid')
                self.rootpin[('FF', s)] = self.tpin(f'u_s{s}_j', 'fault')
                ck = f'col_clk[{s}]'
                kk = [('FV', s), ('FF', s)]
                p = self.station(f'F{s}a', kk, None, (jx, self.hy(r + 1)), ck, self.chan(r + 1), prio=4)
                if r % 2 == 0:
                    for i in range(NS):
                        p = self.station(f'F{s}p{i}', kk, p, ((jx + ctx) / 2 + 30 * i, self.hy(r + 1)), ck, self.chan(r + 1), prio=4)
                fl[s] = self.station(f'F{s}b', kk, p, (self.lane_x('f0') - (40 if c == 0 else -260), self.hy(r + 1)), ck,
                                     self.chan(r + 1), prio=4)
        prev, keys = None, []
        self.flag_chain = []
        for r in range(16, -1, -1):
            ent = [col_of(c, r - 1) for c in range(2)] if r >= 1 else []
            ek = [k for s in ent for k in (('FV', s), ('FF', s))]
            src = {k: prev for k in keys}
            src.update({k: fl[k[1]] for k in ek})
            keys = keys + ek
            prev = self.station(f'FD{r}', keys, src, (ctx, self.hy(r)), rowclk(r), CTR, depth_check=False, lanes=['f0'], prio=0)
            self.flag_chain.append(prev)
            if r > 0:
                for i in range(1, NS):
                    prev = self.station(f'FDm{r - 1}_{i}', keys, prev, (ctx, midy(r - 1, i)), rowclk(r - 1), CTR, lanes=['f0'], prio=0)
                    self.flag_chain.append(prev)
        for r in range(0, 17):
            if r > 0:
                for i in range(NS - 1, 0, -1):
                    prev = self.station(f'FUm{r - 1}_{i}', keys, prev, (ctx, midy(r - 1, i)), rowclk(r - 1), CTR, lanes=['f1'], prio=0)
                    self.flag_chain.append(prev)
            prev = self.station(f'FU{r}', keys, prev, (ctx, self.hy(r)), rowclk(r), CTR, lanes=['f1'], prio=0)
            self.flag_chain.append(prev)
        self.flag_top = prev
        # 5. sf[6]: bank 6 fault -> 2 stations in the channel below -> join sf[6]
        self.sf6 = {}
        for r in range(16):
            for c in range(2):
                s = col_of(c, r)
                fx, _ = self.tpin(f'u_s{s}_b6', 'fault')
                jx, _ = self.tpin(f'u_s{s}_j', 'sf[6]')
                self.root[('SF', s)] = f'sf_{s}[6]'
                self.rootpin[('SF', s)] = self.tpin(f'u_s{s}_b6', 'fault')
                a1 = self.station(f'Q{s}a', [('SF', s)], None, (fx, self.hy(r)), f'col_clk[{s}]', self.chan(r), prio=4)
                self.sf6[s] = self.station(f'Q{s}b', [('SF', s)], a1, (jx, self.hy(r)), f'col_clk[{s}]', self.chan(r), prio=4)
        for k in ctl_keys:
            self.rootpin[k] = self.tpin('u_ctl', f'cmd[{k[1]}]') if k[0] == 'C' else (ctx, self.FH)
        self.place_all()
        self.emit_insts()

    def rst_src(self, s, t):
        """the station driving tile (s, t)'s rst_n: the middle-row slices' W-face reset pins sit deep in the block, so bank 2
        takes it from bank 0's station (channel below) and bank 7 from bank 5's (channel above) -- same row, same depth"""
        return self.rst_of[(s, t)]

    # ---- timing ---------------------------------------------------------------------------------------------------------
    def timing(self):
        Dcol, Rcol = {}, {}
        for r in range(16):
            for c in range(2):
                s = col_of(c, r)
                ds = {self.st[self.s1_of[(s, t)]]['depth'] for t in list(range(8)) + ['j']}
                if len(ds) != 1:
                    raise ValueError(f'column {s}: tiles at depths {ds}')
                Dcol[s] = ds.pop()
                # return: F1 .. F2 (+ pads) + flag chain from its FD entry to the top, inclusive
                chain = self.flag_chain
                ent = chain.index(f'FD{r + 1}')
                Rcol[s] = (self.st[f'F{s}b']['depth']) + (len(chain) - ent)
        # data side: chunk (k, g) needs DELTA_g die edges after the header so that face -> S1 (6 stages) meets D
        vdep = {}
        for g in range(8):
            vd = {self.st[self.S1[key]]['depth'] for key in self.S1 if key[2] == g}
            vdep[g] = vd
        return Dcol, Rcol

    # ---- hop check ----------------------------------------------------------------------------------------------------
    def verify(self):
        pin = {s: self.views[f'qkd_rlys_{s}'][1] for s in STD}
        ain, bout = {}, {}
        for name, d in self.st.items():
            off = 0
            for s, (x, y) in d['reps']:
                for i in range(s):
                    k = off + i
                    if k < len(d['keys']):
                        key = d['keys'][k]
                        pa, pb = pin[s][f'a[{i}]'], pin[s][f'b[{i}]']
                        ain[(name, key)] = (x + pa[0], y + pa[1])
                        bout[(name, key)] = (x + pb[0], y + pb[1])
                off += s
        hops = []
        for name, d in self.st.items():
            for key in d['keys']:
                p = d['par'][key]
                q = self.rootpin.get(key) if p is None else bout[(p, key)]
                if q is None:
                    continue
                hops.append((_d(q, ain[(name, key)]), f'{p}->{name}', str(key)))
        for (s, t), S1 in self.s1_of.items():
            if t == 'j':
                for pn, k in (('join_go', ('C', 31)), ('rst_n', ('R',))):
                    hops.append((_d(bout[(S1, k)], self.tpin(f'u_s{s}_j', pn)), f'{S1}->s{s}j', pn))
                continue
            H, GS = s // 8, s % 8
            pv2, pe2, bc = self.tile_srcs(H, GS, t)
            for pn, grp in (('pv2', pv2), ('pe2', pe2), ('bc', bc)):
                for i, k in enumerate(grp):
                    hops.append((_d(bout[(S1, k)], self.tpin(f'u_s{s}_b{t}', f'{pn}[{i}]')), f'{S1}->s{s}b{t}', pn))
            hops.append((_d(bout[(self.rst_src(s, t), ('R',))], self.tpin(f'u_s{s}_b{t}', 'rst_n')), f'{self.rst_src(s, t)}->s{s}b{t}', 'rst_n'))
        for s in range(32):
            hops.append((_d(bout[(self.sf6[s], ('SF', s))], self.tpin(f'u_s{s}_j', 'sf[6]')), f'Q{s}b->j', 'sf6'))
            for l_ in range(8):
                if l_ != 6:
                    hops.append((_d(self.tpin(f'u_s{s}_b{l_}', 'fault'), self.tpin(f'u_s{s}_j', f'sf[{l_}]')), f's{s}b{l_}->j', 'sf'))
                for i in range(0, 512, 37):
                    tsn, base = ['ts0', 'ts1', 'ts2', 'ts3'][l_ // 2], 512 * (l_ % 2)
                    hops.append((_d(self.tpin(f'u_s{s}_b{l_}', f'ts[{i}]'), self.tpin(f'u_s{s}_j', f'{tsn}[{base + i}]')),
                                 f's{s}b{l_}->j', 'ts'))
            for key, pn in ((('FV', s), 'col_valid'), (('FF', s), 'col_fault')):
                hops.append((_d(bout[(self.flag_top, key)], self.tpin('u_ctl', f'{pn}[{s}]')), f'{self.flag_top}->ctl', pn))
        hops.sort(reverse=True)
        return hops

    # ---- emit -------------------------------------------------------------------------------------------------------------
    def emit(self, out_sv, Dcol, trunk_d, flag_d, delta):
        L = ['`timescale 1ns/1ps',
             '// GENERATED by tools/qwen_kv_die/pv_trunk_gen.py (KVPLAN 1815) -- do not edit; re-run the generator.',
             f'// Frame {self.FW:.3f} x {self.FH:.3f} um (lanes {self.SW}, CT {self.CT}, channels {self.a.ch} / {self.a.ch_even}); '
             f'{sum(len(d["reps"]) for d in self.st.values())} relay-standard replicas, {sum(len(d["keys"]) for d in self.st.values())} station flops.',
             '// Column s: command AND data COL_D[s] extra edges after the old pair -> its y / y_valid at out_age + COL_D[s] - COL_D[0].',
             '// V chunk vc<k>_<g> must arrive DELTA[g] edges after the header vh<k> (the die relay chains are padded to it).',
             'module qkd_pvw_die_t #(',
             ' parameter integer PAIR=0, parameter integer CTL_RESET_PIN=1, parameter integer LEAF_RESET_PIN=1,',
             ' parameter integer FIRST_INPUT_AGE=20, parameter integer MUT=0,',
             ' parameter integer TRUNK_MUT=0,  // bench negative control: 1 = one control station of group 0 is a wire',
             ' parameter integer FLAG_D_ADJ=0  // bench negative control: control-tile flag slot moved by this many edges',
             ')(',
             ' input wire rst_n,start,input wire[32:0] col_clk,input wire[13:0] context_len,input wire[15:0] epoch,',
             ' input wire[30:0] vh0,vh1,vh2,vh3,vh4,vh5,vh6,vh7,',
             ' input wire[127:0] ' + ','.join(f'vc{k}_{g}' for k in range(8) for g in range(8)) + ',',
             ' input wire[511:0] in_e,',
             ' output wire[14:0] vrq0,vrq1,vrq2,vrq3,vrq4,vrq5,vrq6,vrq7,',
             ' output wire out_valid,output wire[16383:0] out_leaf,output wire[15:0] out_epoch,',
             ' output wire fault,output wire busy,output wire[15:0] out_age',
             ');',
             f' localparam integer TRUNK_D={trunk_d}, FLAG_D={flag_d};',
             ' localparam [255:0] COL_D={' + ', '.join(f"8'd{Dcol[s]}" for s in range(31, -1, -1)) + '};   // column s: COL_D[8s+:8]',
             ' localparam [63:0] DELTA={' + ', '.join(f"8'd{delta[g]}" for g in range(7, -1, -1)) + '};   // group g: DELTA[8g+:8]',
             ' wire[7:0] in_valid,req_valid; wire[111:0] in_t,req_t; wire[127:0] in_epoch; wire[59:0] cmd_w;',
             ' wire[31:0] yv_w,jf_w,cv_w,cf_w;']
        for k in range(8):
            L.append(f' assign in_valid[{k}]=vh{k}[0]; assign in_t[{14 * k + 13}:{14 * k}]=vh{k}[14:1]; '
                     f'assign in_epoch[{16 * k + 15}:{16 * k}]=vh{k}[30:15]; assign vrq{k}={{req_t[{14 * k + 13}:{14 * k}],req_valid[{k}]}};')
        for s in range(32):
            L.append(f' wire[4095:0] ts_{s}; wire[7:0] sf_{s};')
        for name, w in self.wires:
            L.append(f' wire[{w - 1}:0] {name};')
        L += [' ot_qwen_tp8_pv_wide_ctl_t #(.FIRST_INPUT_AGE(FIRST_INPUT_AGE),.RESET_PIN(CTL_RESET_PIN),.TRUNK_D(TRUNK_D),.FLAG_D(FLAG_D+FLAG_D_ADJ)) u_ctl(',
              '  .clk(col_clk[32]),.rst_n(rst_n),.pair_id(PAIR[0]),.start(start),.context_len(context_len),.epoch(epoch),',
              '  .in_valid(in_valid),.in_t(in_t),.in_epoch(in_epoch),.req_valid(req_valid),.req_t(req_t),.cmd(cmd_w),',
              '  .col_valid(cv_w),.col_fault(cf_w),.out_epoch(out_epoch),.fault(fault),.busy(busy),.out_age(out_age));']
        top = self.st[self.flag_top]
        L.append(' assign cv_w={' + ', '.join(f'{top["wire"]}[{top["idx"][("FV", s)]}]' for s in range(31, -1, -1)) + '};')
        L.append(' assign cf_w={' + ', '.join(f'{top["wire"]}[{top["idx"][("FF", s)]}]' for s in range(31, -1, -1)) + '};')
        L.append(' assign out_valid=yv_w[0];')
        ox = lambda S1, k: f'{self.st[S1]["wire"]}[{self.st[S1]["idx"][k]}]'   # noqa: E731
        for s in range(32):
            H, GS = s // 8, s % 8
            for l_ in range(8):
                S1 = self.s1_of[(s, l_)]
                pv2, pe2, bc = self.tile_srcs(H, GS, l_)
                cat = lambda ks: '{' + ', '.join(ox(S1, k) for k in reversed(ks)) + '}'   # noqa: E731
                L.append(f' ot_qwen_tp8_pv_slice_t #(.RESET_PIN(LEAF_RESET_PIN)) u_s{s}_b{l_}(.clk(col_clk[{s}]),'
                         f'.rst_n({ox(self.rst_src(s, l_), ("R",))}),.pv2({cat(pv2)}),.pe2({cat(pe2)}),.bc({cat(bc)}),'
                         f'.ts(ts_{s}[{512 * l_ + 511}:{512 * l_}]),.fault(sf_{s}[{l_}]));')
            Sj = self.s1_of[(s, 'j')]
            sfj = '{' + ', '.join([f'sf_{s}[7]', ox(self.sf6[s], ('SF', s))] + [f'sf_{s}[{i}]' for i in range(5, -1, -1)]) + '}'
            L.append(f' ot_qwen_tp8_pv_join_t #(.MUT(MUT),.RESET_PIN(LEAF_RESET_PIN)) u_s{s}_j(.clk(col_clk[{s}]),'
                     f'.rst_n({ox(Sj, ("R",))}),.ts0(ts_{s}[1023:0]),.ts1(ts_{s}[2047:1024]),'
                     f'.ts2(ts_{s}[3071:2048]),.ts3(ts_{s}[4095:3072]),.join_go({ox(Sj, ("C", 31))}),'
                     f'.sf({sfj}),.y(out_leaf[{512 * s + 511}:{512 * s}]),.y_valid(yv_w[{s}]),.fault(jf_w[{s}]));')
        body = list(self.inst)
        if self.a.mut_station:
            ln = next(i for i, x in enumerate(body) if f' u_{self.a.mut_station}_r0 ' in x)
            m = re.match(r'\s+(qkd_rlys_\d+) (\S+) \(\.ck\((.*?)\), \.a\((.*)\), \.b\((.*)\)\);$', body[ln])
            body[ln] = (f' generate if(TRUNK_MUT==1)begin:g_mut assign {m.group(5)}={m.group(4)}; end else begin:g_ok\n'
                        f'  {m.group(1)} {m.group(2)} (.ck({m.group(3)}), .a({m.group(4)}), .b({m.group(5)}));\n end endgenerate')
        L += body
        L.append('endmodule')
        Path(out_sv).write_text('\n'.join(L) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ch', type=float, default=172.8)
    ap.add_argument('--ch-even', type=float, default=172.8)
    ap.add_argument('--ns', type=int, default=3)
    ap.add_argument('--hop', type=float, default=390.0, help='per-bit hop target used to place stations')
    ap.add_argument('--ct', type=float, default=345.6)
    ap.add_argument('--sw', type=float, default=0.0)
    ap.add_argument('--strip', type=float, default=86.4)
    ap.add_argument('--halo-tile', type=float, default=21.6)
    ap.add_argument('--mut-station', default='K1c0g0', help='the station TRUNK_MUT=1 replaces by a wire (bench negative control)')
    ap.add_argument('--no-place', action='store_true', help='structure only: emit the RTL, skip placement / hop checks')
    ap.add_argument('--out-sv', required=True)
    ap.add_argument('--out-plan', required=True)
    a = ap.parse_args(argv)
    g = Gen(a)
    g.build()
    Dcol, Rcol = g.timing()
    tot = {s: Dcol[s] + Rcol[s] for s in range(32)}
    if len(set(tot.values())) != 1:
        raise ValueError(f'flag return not balanced: D + R per column {tot}')
    # V chunk arrival: face -> e0 -> T1 -> T2 -> CT (2) -> S1 = 6 stages; command: D_g
    delta = {}
    for gg in range(8):
        ds = {Dcol[col_of(c, r)] for c in range(2) for r in (2 * gg, 2 * gg + 1)}
        assert len(ds) == 1
        delta[gg] = ds.pop() - (g.v_entry_stages + 2)   # face -> e0, a, b, t2 -> CT (NS) -> W1 -> tile station
        if delta[gg] < 0:
            raise ValueError(f'group {gg}: DELTA {delta[gg]} < 0 (the chunk would have to arrive before the header)')
    trunk_d, flag_d = Dcol[0], tot[0] - Dcol[0]
    hops = [] if a.no_place else g.verify()
    g.emit(a.out_sv, Dcol, trunk_d, flag_d, delta)
    flops = sum(len(d['keys']) for d in g.st.values())
    reps = defaultdict(int)
    for d in g.st.values():
        for s, _ in d['reps']:
            reps[s] += 1
    spread = max(Dcol.values()) - min(Dcol.values())
    deskew = sum(512 * (max(Dcol.values()) - Dcol[s]) for s in range(32))
    plan = dict(schema='opentallas.qwen_kv_pv_trunk.v2', generator='tools/qwen_kv_die/pv_trunk_gen.py',
                frame_um=[round(g.FW, 3), round(g.FH, 3)], ch_um=a.ch, ch_even_um=a.ch_even, ct_um=a.ct, lane_um=a.sw, strip_um=a.strip,
                cells={n: [m, round(x, 3), round(y, 3), w, h, o] for n, (m, x, y, w, h, o) in sorted(g.cells.items())},
                col_extra_edges=Dcol, col_flag_return=Rcol, trunk_d=trunk_d, flag_d=flag_d, chunk_delta_vs_header=delta,
                col_age_delta_vs_col0={s: Dcol[s] - Dcol[0] for s in range(32)}, age_spread_edges=spread,
                station_flops=flops, replicas=dict(reps),
                replica_area_mm2=round(sum(n * STD[s][0] * STD[s][1] for s, n in reps.items()) / 1e6, 4),
                deskew_alternative=dict(output_pad_flops=deskew, note='balancing all 32 column outputs at one face instead '
                                        'of per-column static ages: every 512-b y padded to the deepest group'),
                face_pins=dict(vc={f'vc{k}_{gg}': ['W' if k < 4 else 'E', round(g.hy(2 * gg + 1), 3)] for k in range(8) for gg in range(8)},
                               strip=dict(x=round(g.ct_x(), 3), y=round(g.FH, 3), ports=['vh*', 'vrq*', 'in_e', 'rst_n', 'start',
                                                                                           'context_len', 'epoch'])),
                worst_hops=[dict(um=round(h[0], 1), hop=h[1], key=h[2]) for h in hops[:40]],
                hops_over_400=sum(h[0] > 400 for h in hops), hops_total=len(hops))
    Path(a.out_plan).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out_plan).write_text(json.dumps(plan, indent=1) + '\n')
    print(json.dumps({k: plan[k] for k in ('frame_um', 'trunk_d', 'flag_d', 'chunk_delta_vs_header', 'age_spread_edges',
                                           'station_flops', 'replicas', 'replica_area_mm2', 'hops_over_400', 'deskew_alternative')}))
    print('worst', plan['worst_hops'][:15])


if __name__ == '__main__':
    sys.exit(main())
