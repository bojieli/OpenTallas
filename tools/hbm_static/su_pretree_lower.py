#!/usr/bin/env python3
"""SU reducer ingress widening: compiler lowering of a reduction onto the per-pgslice pre-tree (HH-6 / HBM-SURED 10-18).

Hardware (rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_su_red_pretree.sv, pgslice PRETREE, qcore_r5
PRETREE): a quarter's 128 lockstep lanes hold one 128-word issue block on their ro_x at edge E; tree_cmd (per slice
{v,max,cntB5,cntA5}, tree_cmd_word) at E turns it into the block's golden csum8 subtree (words >= cnt padding), which the reducer takes as ONE external
operand by a red_cmd {osel=1, lane bit5=1} issued at E + PT_RED.  Fixed edges, no stall, no ready.

Lowering of one reduction of n words (block b = words 128b..128b+127, quarter lane w = word w of the block):
  * pairs (2i, 2i+1) of blocks; in a group of up to DEP pairs the even blocks are emitted on consecutive edges and the odd
    blocks exactly DEP edges after their partners, so the odd block's ADD_EXT / MAX_EXT (a = d = the even block's LOAD
    address) issues exactly DEP after that LOAD (the reducer's same-address distance) when its subtree arrives;
  * pair sums are joined by ADD_TREE / MAX_TREE ops in the reducer's free command slots, left-to-right pairs per level, an
    odd leftover carried up (= the golden's +0 padding to a power of two at the end); EXPORT at the root.
Numerics: equals hdc_golden_v41.csum (chunks of 8 from +0, aligned pairwise tree, +0 padding) bit for bit for ADD, and the
reducer's ordered max with canonical +0 for MAX.  `golden()` is that independent reference; `tree_model()` re-derives
the value along the lowered schedule and must agree.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from hdc_golden_v41 import csum  # noqa: E402
from hdc_golden import add  # noqa: E402

BLOCK = 128
PT_RED = 69          # tree_cmd edge E -> red_cmd edge that takes the subtree (bench-measured, LAT 6)
DEP = 10             # reducer same-address dependent issue distance (ot_hbm_su_reduce_static r1)
OP_LOAD, OP_ADD_EXT, OP_ADD_TREE, OP_MAX_EXT, OP_EXPORT, OP_MAX_TREE = 0, 1, 2, 3, 4, 5


def f32(u):
    return np.uint32(u).view(np.float32)


def u32(x):
    return int(np.float32(x).view(np.uint32))


def fmax(a, b):
    """ot_hbm_su_reduce_static MAX: finite ordered compare, canonical +0 for zeros."""
    fa, fb = f32(a), f32(b)
    r = a if (fa > fb or (fa == fb and not (a >> 31))) else b
    return 0 if (r & 0x7fffffff) == 0 else r


def fadd(a, b):
    return u32(add(f32(a), f32(b)))


def golden(kind, words):
    """independent reference: csum8 (hdc_golden_v41) for 'sum', ordered canonical max for 'max'"""
    w = np.asarray(words, dtype=np.uint32)
    if kind == "sum":
        return u32(csum(w.view(np.float32)))
    r = int(w[0])
    for v in w[1:]:
        r = fmax(r, int(v))
    return fmax(r, r)


def block_subtree(kind, blk, cnt):
    """the pre-tree's value: 16 chunks of 8 (sequential from +0), aligned pairwise tree; words >= cnt padding"""
    if kind == "max":
        return golden("max", blk[:cnt])
    x = [int(v) if i < cnt else 0 for i, v in enumerate(blk)] + [0] * (BLOCK - len(blk))
    ch = []
    for c in range(16):
        acc = 0
        for k in range(8):
            acc = fadd(acc, x[8 * c + k])
        ch.append(acc)
    while len(ch) > 1:
        ch = [fadd(ch[i], ch[i + 1]) for i in range(0, len(ch), 2)]
    return ch[0]


class Schedule:
    """per-quarter command image: tree_cmd / block words by emission edge, red_cmd by edge, expected exports"""

    def __init__(self):
        self.tree = {}          # edge -> (max, cnt, words[128])
        self.red = {}           # edge -> dict(op, a, b, d, tag, osel, lane)
        self.exps = []          # (export red_cmd edge, tag, value)
        self.addr = 0

    def _new_addr(self):
        a = self.addr
        self.addr = (self.addr + 1) % 1024
        return a

    def _red(self, e, **kw):
        assert e not in self.red, ("reducer slot busy", e)
        self.red[e] = kw

    def _free_slot(self, e):
        while e in self.red:
            e += 1
        return e

    def lower(self, kind, words, tag, t0):
        """lower one reduction; blocks emitted from edge >= t0; returns the next free emission edge"""
        words = [int(v) for v in words]
        n = len(words)
        nb = -(-n // BLOCK)
        blocks = [(words[BLOCK * b:BLOCK * (b + 1)], min(BLOCK, n - BLOCK * b)) for b in range(nb)]
        mx = 1 if kind == "max" else 0
        ext = OP_MAX_EXT if mx else OP_ADD_EXT
        tre = OP_MAX_TREE if mx else OP_ADD_TREE
        level = []              # (addr, ready edge, value)
        t = t0
        npairs = -(-nb // 2)
        for g0 in range(0, npairs, DEP):
            P = min(DEP, npairs - g0)
            for i in range(P):
                pi = g0 + i
                be, bo = 2 * pi, 2 * pi + 1
                # even block at t + i, odd at t + i + DEP; skip emission edges already used / reducer slots taken
                ee, eo = t + i, t + i + DEP
                assert ee not in self.tree and (bo >= nb or eo not in self.tree)
                blk, cnt = blocks[be]
                self.tree[ee] = (mx, cnt, blk)
                v = block_subtree(kind, blk, cnt)
                d = self._new_addr()
                self._red(ee + PT_RED, op=OP_LOAD, a=0, b=0, d=d, tag=0, osel=1, lane=0x20)
                ready = ee + PT_RED + DEP
                if bo < nb:
                    blk, cnt = blocks[bo]
                    self.tree[eo] = (mx, cnt, blk)
                    vo = block_subtree(kind, blk, cnt)
                    self._red(eo + PT_RED, op=ext, a=d, b=0, d=d, tag=0, osel=1, lane=0x20)
                    v = fmax(v, vo) if mx else fadd(v, vo)
                    ready = eo + PT_RED + DEP
                level.append((d, ready, v))
            t += DEP + P
        # tree over pair sums in free reducer slots (left-to-right, odd leftover carried up)
        last = 0
        while len(level) > 1:
            nl = []
            for i in range(0, len(level) - 1, 2):
                (xa, ra, va), (xb, rb, vb) = level[i], level[i + 1]
                e = self._free_slot(max(ra, rb, last + 1))
                last = e
                d = self._new_addr()
                self._red(e, op=tre, a=xa, b=xb, d=d, tag=0, osel=0, lane=0)
                nl.append((d, e + DEP, fmax(va, vb) if mx else fadd(va, vb)))
            if len(level) % 2:
                nl.append(level[-1])
            level = nl
        root, rr, val = level[0]
        e = self._free_slot(max(rr, last + 1))
        self._red(e, op=OP_EXPORT, a=root, b=0, d=0, tag=tag, osel=0, lane=0)
        g = golden(kind, words)
        assert val == g, ("lowered tree != golden", kind, n, hex(val), hex(g))
        self.exps.append((e, tag, val))
        return t


def tree_cmd_word(mx, cnt):
    """the four slices' tree_cmd {v, max, cntB5, cntA5} (slice G at bits 12G): half A = words 16G..16G+15, B = 64+16G.."""
    v = 0
    for g in range(4):
        ca = min(16, max(0, cnt - 16 * g))
        cb = min(16, max(0, cnt - 64 - 16 * g))
        v |= ((1 << 11) | (mx << 10) | (cb << 5) | ca) << (12 * g)
    return v


def red_cmd_word(c):
    return ((1 << 73) | (c["op"] << 70) | (c["a"] << 60) | (c["b"] << 50) | (c["d"] << 40) | (c["tag"] << 8)
            | (c["osel"] << 7) | c["lane"])
