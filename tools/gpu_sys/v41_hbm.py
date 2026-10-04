#!/usr/bin/env python3
"""DeepSeek-V4.1 HBM comparator, reduced shape: the decode step lowered to OTG-1 kernels for the GPU-organised system
(2 dies TP2, 2 SMs per die, 128-lane SIMT, a 16-lane exact BF16 tensor core and the block-scaled (MX FP8/FP4)
tensor core of rtl/gpu/ot_gpu_sm_bd.sv per SM), its HBM images, and a functional check against the golden.

Golden: tools/hdc_golden_v41.py Model() on build/models/deepseek-v4.1-flash-reduced-v2 under the arithmetic contract
of the DeepSeek HBM comparator: HDC_V41_ARITH=chunk8 (R-ARITH: every accumulation in contiguous chunks of 8 summed
sequentially from +0, chunk sums by a +0-padded pairwise tree -- the contract tools/w19_hbm_tp96_isa.py executes and
the SM / block-dot RTL (tools/rtl_gpu_sm_exact.py lanes v41_bf16, blockdot) is bit-exact to), HDC_V41_FUSE empty
(two-pass softmax, no norm folding).

Shape: TP = 2 dies x 2 SMs.  Every matrix is split by output rows (w19's TP rule, scaled to 4 SMs); attention heads
16 per SM (head-aligned wq_b, attention, grouped wo_a: the SM's 16 heads are two whole o-groups); index heads 8 per SM
(one golden chunk of the index-head sum each, so the cross-SM sum is the golden tree: SMs within a die, then the
all-reduce across dies); each routed expert's w1/w3 rows 16 per SM and w2 rows 40 per SM, fetched by expert id
(UFROMV -> uniform register -> weight base); hyper-connection mixes 6-7 rows per SM; replicated (every SM): norms,
Sinkhorn, RoPE, routing, hc_pre/hc_post.  Window KV, compressed KV, index keys, the compressor's open slot and the
selection are die-memory state (replicated per die, as w19 replicates the window).  Engram tables are sharded by
row id mod 2 (w19's owner rule) and combined by an all-reduce.

    python3 tools/gpu_sys/v41_hbm.py --check --npos 3     # functional machine vs golden after every layer + token
    python3 tools/gpu_sys/v41_hbm.py --emit DIR           # program + HBM images + expected tokens for the RTL
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ["HDC_V41_ARITH"] = "chunk8"
os.environ["HDC_V41_FUSE"] = ""

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import isa  # noqa: E402
import machine as MC  # noqa: E402
from asm import Kernel, V as VR  # noqa: E402
from isa import enc  # noqa: E402
from machine import Machine  # noqa: E402

F = np.float32
U32 = np.uint32
TP, NSM, NL, L16 = 2, 2, 128, 16
CTX = 16                 # positions the program serves (state sized for them); max_seq_len is 128
TPAD = 32                # attention list lanes per head: window CTX + selected compressed <= 32
SLOT_RING = False        # compressor open slot indexed by position (speculative rollback: tools/gpu_sys/v41_dspark.py)
SIGN = 0x80000000
NEG_BIG = int(np.float32(-3.0e38).view(np.uint32))
BD_FS = {False: 32, True: 16}

# ------------------------------------------------------------------------------------------------ shared memory map
S_ZERO = 0x0000          # 64 zero words (padding target of every gather index)
S_XS = 0x0100            # BF16 tensor-core x staging, 256 words
S_TCR = 0x0800           # tensor-core results, 1024 words
S_FLAT = 0x1800          # hyper-connection flat residual, 640 words
S_TREE = 0x2200          # tree ping, 896 words
S_TREE2 = 0x3000         # tree pong, 448 words
S_NRM = 0x3800           # norm staging, 160 words
S_SEG = 0x4000           # engram segment staging, 1920 words (overlaps the attention area: earlier phase)
S_KVL = 0x4000           # attention KV list [32 rows][32], 1024 words
S_QS = 0x5000            # this SM's q heads [16][32]
S_ES = 0x5800            # exp(scores) FP32 [16][32]
S_EB = 0x6000            # exp(scores) BF16 [16][32]
S_MS = 0x6800            # running max per head lane
S_IKS = 0x5800           # index keys [CTX][32] (indexer phase, before attention)
S_DUMMY = 0x7000         # sink of the compressed-row scatter for unselected rows
S_IQS = 0x7800           # index q [8][32]
S_MISC = 0x7C00          # small staging (slots, latent, weights), 256 words


def fbits(x):
    return int(np.asarray(x, dtype=F).view(np.uint32))


# ================================================================================================ kernel builder
class K2(Kernel):
    """asm.Kernel plus labels, forward/backward branches (BRA, BNZ on a uniform register), scoped constant caches
    and a loop-aware linear-scan allocation (a value live into a loop stays allocated to the loop's end; a value may
    be re-assigned (`into`) to carry it around a loop).  Branch targets are kernel-relative; link() relocates them."""

    def __init__(self, name):
        super().__init__(name)
        self.scopes = [{}]
        self.loops = []
        self.labels = {}
        self.fix = []
        self.nlab = 0
        self.const_loader = None

    # scopes: constants / cached vectors created inside a conditional section or loop die with it
    def push(self):
        self.scopes.append({})

    def pop(self):
        self.scopes.pop()

    def cached(self, key, fn):
        for sc in reversed(self.scopes):
            if key in sc:
                return sc[key]
        v = fn()
        self.scopes[-1][key] = v
        return v

    def const(self, bits):
        bits = int(bits) & 0xFFFFFFFF
        return self.cached(("c", bits), lambda: self._movi(bits))

    def _movi(self, bits):
        d = self._new()
        self.emit("MOVI", d, 0, 0, bits)
        return d

    def laneid(self):
        def mk():
            d = self._new()
            self.emit("LANEID", d)
            return d
        return self.cached("lane", mk)

    def into(self, dst, name, a, b=None):
        """Re-assign an existing value (a loop-carried variable)."""
        self.emit(name, dst, a, a if b is None else b)
        return dst

    # labels and branches
    def newlabel(self, stem="L"):
        self.nlab += 1
        return f"{stem}{self.nlab}"

    def label(self, name):
        self.labels[name] = len(self.ins)

    def bra(self, name):
        self.fix.append((len(self.ins), name))
        self.emit("BRA", 0, 0, 0, 0)

    def bnz(self, ur, name):
        self.fix.append((len(self.ins), name))
        self.emit("BNZ", 0, ur, 0, 0)

    def loop(self, ur, count):
        """for _ in range(count): body  -- usage:  h = k.loop(ur, n); ...; k.endloop(h)"""
        self.umovi(ur, count)
        name = self.newlabel("loop")
        self.label(name)
        self.push()
        return (name, ur, len(self.ins))

    def endloop(self, h):
        name, ur, start = h
        self.uaddi(ur, ur, 0xFFFFFFFF)
        self.bnz(ur, name)
        self.pop()
        self.loops.append((start, len(self.ins) - 1))

    def assemble(self):
        ins = self.ins
        first, last = {}, {}
        for i, (op, d, a, b, imm) in enumerate(ins):
            for x in (d, a, b):
                if isinstance(x, VR):
                    first.setdefault(x.n, i)
                    last[x.n] = i
        changed = True
        while changed:
            changed = False
            for s, e in self.loops:
                for n in first:
                    if first[n] < s <= last[n] < e:
                        last[n] = e
                        changed = True
        ends = {}
        for n, i in last.items():
            ends.setdefault(i, []).append(n)
        free = list(range(self.nv - 1, -1, -1))
        phys = {}
        words = []
        peak = 0
        stores = ("STG", "STS", "STSX")
        for i, (op, d, a, b, imm) in enumerate(ins):
            def p(x, src=True):
                if isinstance(x, VR):
                    if x.n not in phys:
                        if src or first[x.n] != i:
                            raise ValueError(f"{self.name}: v{x.n} read before definition at {i} {op}")
                        if not free:
                            raise ValueError(f"{self.name}: out of vector registers at {i}")
                        phys[x.n] = free.pop()
                    return phys[x.n]
                return x
            pa, pb = p(a), p(b)
            pd = p(d, src=(op in stores))
            peak = max(peak, self.nv - len(free))
            words.append(enc(op, pd, pa, pb, imm))
            for n in ends.get(i, ()):
                if n in phys:
                    free.append(phys.pop(n))
        for i, name in self.fix:
            op, d, a, b, _ = ins[i]
            words[i] = enc(op, d if not isinstance(d, VR) else 0, a, b, self.labels[name])
        self.peak = peak
        return words


# ================================================================================================ lowering library
class Lib:
    """Golden primitives as OTG-1 sequences (ordinary GPU instructions)."""

    def __init__(self, k: K2, prog):
        self.k = k
        self.prog = prog

    def c(self, x):
        return self.k.const(fbits(x))

    def u(self, bits):
        return self.k.const(bits)

    def op(self, name, a, b=None):
        return self.k.op(name, a, b)

    def add(self, a, b):
        return self.op("FADD", a, b)

    def mul(self, a, b):
        return self.op("FMUL", a, b)

    def neg(self, a):
        return self.op("XOR", a, self.u(SIGN))

    def vec(self, vals):
        """A per-lane constant vector (index patterns, masks): one LDG from the constant table."""
        vals = tuple(int(v) & 0xFFFFFFFF for v in vals) + (0,) * (NL - len(vals))
        addr = self.prog.cvec(vals)
        return self.k.cached(("vec", vals), lambda: self.k.ldg(4, addr, 4, NL))

    def lanes(self, fn):
        return self.vec([fn(l) for l in range(NL)])

    def mask(self, pred):
        """All-ones where pred(lane), else 0."""
        return self.lanes(lambda l: 0xFFFFFFFF if pred(l) else 0)

    def select_m(self, m, yes, no):
        """m: all-ones/zero mask vector."""
        return self.op("XOR", no, self.op("AND", m, self.op("XOR", yes, no)))

    def shfl(self, a, idx):
        return self.k.shfl(a, idx)

    def bcast(self, a, lane):
        return self.shfl(a, self.u(lane))

    def lane(self):
        return self.k.laneid()

    def bf(self, a):
        return self.op("CVTBF16", a)

    # special functions (hdc_golden / hdc_golden_v41)
    def rsqrt(self, v):
        nh = self.mul(v, self.c(-0.5))
        y = self.op("ISUB", self.u(0x5F3759DF), self.op("SHR", v, self.u(1)))
        for _ in range(3):
            y = self.mul(y, self.add(self.c(1.5), self.mul(nh, self.mul(y, y))))
        return y

    def exp(self, x):
        x = self.op("FMAX", self.op("FMIN", x, self.c(G.EXP_MAX)), self.c(G.EXP_MIN))
        t = self.mul(x, self.c(G.LOG2E))
        n = self.add(self.add(t, self.c(G.MAGIC)), self.c(-G.MAGIC))
        r = self.add(self.add(x, self.mul(n, self.c(-G.LN2_HI))), self.mul(n, self.c(-G.LN2_LO)))
        p = self.c(G.EXP_POLY[0])
        for cc in G.EXP_POLY[1:]:
            p = self.add(self.mul(p, r), self.c(cc))
        return self.op("IADD", p, self.op("SHL", self.op("F2I", n), self.u(23)))

    def div(self, a, b):
        return self.op("FDIV", a, b)

    def sigmoid(self, x):
        return self.div(self.c(1.0), self.add(self.exp(self.neg(x)), self.c(1.0)))

    def silu(self, x):
        return self.div(x, self.add(self.exp(self.neg(x)), self.c(1.0)))

    def softplus(self, x):
        t = self.exp(self.neg(self.op("AND", x, self.u(0x7FFFFFFF))))
        u = self.div(t, self.add(t, self.c(2.0)))
        u2 = self.mul(u, u)
        p = self.c(V.LOG1P_ODD[0])
        for cc in V.LOG1P_ODD[1:]:
            p = self.add(self.mul(p, u2), self.c(cc))
        lp = self.mul(self.mul(u, p), self.c(2.0))
        return self.add(self.op("FMAX", x, self.u(0)), lp)

    def ceil_log2(self, t):
        """_ceil_log2 of positive normal binary32 lanes (exponent - 127 + any mantissa bit), as int32."""
        ex = self.op("SHR", t, self.u(23))
        nz = self.op("UGT", self.op("AND", t, self.u(0x7FFFFF)), self.u(0))
        return self.op("ISUB", self.op("IADD", ex, nz), self.u(127))

    def pow2(self, e, negate=False):
        """2^e (or 2^-e) as FP32 bits for int32 e in the normal range."""
        if negate:
            return self.op("SHL", self.op("ISUB", self.u(127), e), self.u(23))
        return self.op("SHL", self.op("IADD", e, self.u(127)), self.u(23))

    def seg_max(self, v, seg):
        """max over aligned seg-lane segments, broadcast to every lane of the segment (butterfly)."""
        w = 1
        while w < seg:
            v = self.op("FMAX", v, self.shfl(v, self.lanes(lambda l, w=w: l ^ w)))
            w *= 2
        return v

    def quant_fp8(self, x):
        """act_quant per aligned 32-lane block: (on-grid E4M3 values, block exponent) per lane."""
        amax = self.seg_max(self.op("AND", x, self.u(0x7FFFFFFF)), 32)
        amax = self.op("FMAX", amax, self.c(V.FP8_AMAX_FLOOR))
        e = self.ceil_log2(self.mul(amax, self.c(V.FP8_MAX_INV)))
        q = self.op("CVTE4M3", self.mul(x, self.pow2(e, negate=True)))
        return q, e

    def qdq_fp8(self, x):
        q, e = self.quant_fp8(x)
        return self.bf(self.mul(q, self.pow2(e)))

    def qdq_fp4_e8m0(self, x):
        amax = self.seg_max(self.op("AND", x, self.u(0x7FFFFFFF)), 32)
        amax = self.op("FMAX", amax, self.c(V.FP4_AMAX_FLOOR_E8M0))
        e = self.ceil_log2(self.mul(amax, self.c(V.FP4_MAX_INV)))
        q = self.op("CVTE2M1", self.mul(x, self.pow2(e, negate=True)))
        return self.bf(self.mul(q, self.pow2(e)))

    def qdq_fp4_e4m3(self, x):
        """block 16, E4M3 scale min(e4m3(amax / 6), 448); E2M1 code of x / s (both roundings provably single)."""
        amax = self.seg_max(self.op("AND", x, self.u(0x7FFFFFFF)), 16)
        amax = self.op("FMAX", amax, self.c(V.FP4_AMAX_FLOOR_E4M3))
        s = self.op("CVTE4M3", self.div(amax, self.c(6.0)))
        q = self.op("CVTE2M1", self.div(x, s))
        return self.bf(self.mul(q, s))

    def seq_sum8(self, v):
        """lane L: v[L] + v[L+1] + ... + v[L+7] sequentially (the chunk sum of the chunk starting at L)."""
        acc = v
        for j in range(1, 8):
            acc = self.add(acc, self.shfl(v, self.lanes(lambda l, j=j: (l + j) % NL)))
        return acc

    def tree_up(self, acc, q, step=8):
        """pairwise tree over q chunk sums held at lanes base + step*i: result at lane base."""
        w = step
        while w < step * q:
            acc = self.add(acc, self.shfl(acc, self.lanes(lambda l, w=w: (l + w) % NL)))
            w *= 2
        return acc

    def seg_csum32(self, v):
        """csum over each aligned 32-lane segment (4 chunks of 8, tree), broadcast over the segment."""
        acc = self.tree_up(self.seq_sum8(v), 4)
        return self.shfl(acc, self.lanes(lambda l: l & ~31))

    def rmsnorm32(self, x, gamma, eps):
        """rmsnorm_bf16 over each 32-lane segment of x (n = 32)."""
        ss = self.seg_csum32(self.mul(x, x))
        r = self.rsqrt(self.add(self.div(ss, self.c(32.0)), self.c(eps)))
        return self.bf(self.mul(gamma, self.mul(x, r)))


# ================================================================================================ weight formats
_E4M3_POS = None


def e4m3_codes(vals):
    """exact E4M3 values (float64, signed) -> codes (vectorised)."""
    global _E4M3_POS
    if _E4M3_POS is None:
        _E4M3_POS = MC._e4m3_table()[:127].copy()
    v = np.asarray(vals, dtype=np.float64)
    a = np.abs(v)
    idx = np.searchsorted(_E4M3_POS, a)
    idx = np.minimum(idx, 126)
    assert np.array_equal(_E4M3_POS[idx], a), "value off the E4M3 grid"
    return (idx | (np.signbit(v).astype(np.int64) << 7)).astype(np.uint8)


def e2m1_codes(vals):
    v = np.asarray(vals, dtype=np.float64)
    a = np.abs(v)
    idx = np.searchsorted(V.E2M1_VALUES, a)
    assert np.array_equal(V.E2M1_VALUES[np.minimum(idx, 7)], a), "value off the E2M1 grid"
    return (idx + 8 * np.signbit(v)).astype(np.uint8)


def bd_geometry(K, fp4):
    """(blocks, k-steps c, chunks C, groups g) of a K-wide linear_q on the block-dot core."""
    nb = K // 32
    assert nb * 32 == K
    LA = 8 if fp4 else 4
    if nb <= 8:
        c, C = nb, 1                     # one golden chunk: its nb blocks sequential in lane 0
    else:
        c, C = 8, -(-nb // 8)
    return nb, c, C, -(-C // LA)


def bd_tile(q, e, fp4):
    """TCBMMA weight lines (machine.bd_tcbmma format, 288 B each): q [R, K] exact E4M3 / E2M1 values, e [R, nb]
    block exponents.  Returns (bytes, (rows, g, c))."""
    R, K = q.shape
    nb, c, C, g = bd_geometry(K, fp4)
    LA = 8 if fp4 else 4
    order = MC.bd_issue(R, g, c)
    n = len(order)
    j = np.arange(8)
    b = (order[:, 1:2] * LA + j[None, :]) * c + order[:, 2:3]          # [n, 8] block index
    ok = (j[None, :] < LA) & (b < nb)
    bb = np.where(ok, b, 0)
    blocks = q.reshape(R, nb, 32)[order[:, 0:1], bb]                     # [n, 8, 32]
    blocks = np.where(ok[..., None], blocks, 0.0)
    codes = e2m1_codes(blocks) if fp4 else e4m3_codes(blocks)
    ex = np.where(ok, e[order[:, 0:1], bb], 0).astype(np.int16)
    line = np.zeros((n, MC.BD_LINE), dtype=np.uint8)
    line[:, :256] = codes.reshape(n, 256)
    line[:, 256:272] = ex.view(np.uint8).reshape(n, 16)
    return line.reshape(-1), (R, g, c)


def tc_lines(w):
    """BF16 tensor-core lines (ot_gpu_sm lockstep order rb, g, t, s), chunk-8 csum split (split = K/8)."""
    R, K = w.shape
    c = 8
    C = K // c
    assert C * c == K
    Gn = -(-C // L16)
    wb = (np.asarray(G.to_bf16(w), dtype=F).view(np.uint32) >> 16).astype(np.uint16)
    pad = np.zeros((R, Gn * L16 * c), dtype=np.uint16)
    pad[:, :K] = wb
    t4 = pad.reshape(R, Gn, L16, c)                            # [r, g, lane j, t] = w[r, (g*16 + j)*8 + t]
    out = []
    for rb in range(0, R, 8):
        blk = t4[rb:rb + 8]                                    # [s, g, j, t]
        out.append(np.transpose(blk, (1, 3, 0, 2)).reshape(-1, L16))   # [g, t, s, j]
    return np.concatenate(out).reshape(-1).view(np.uint8), Gn, c


# ================================================================================================ program
ROWS = {0: list(range(0, 7)), 1: list(range(7, 13)), 2: list(range(13, 19)), 3: list(range(19, 25))}   # hc rows
SS_ROW = 24              # the 25th "row" of the hyper-connection projection: the flat sum of squares (w = x)


def ab_perm():
    """AB layout of a [4][160] tensor: A_j = [j, 0:128] (j = 0..3), B lane 32j + e = [j, 128 + e]."""
    p = [160 * j + e for j in range(4) for e in range(128)]
    p += [160 * (l >> 5) + 128 + (l & 31) for l in range(128)]
    return np.array(p)


def to_ab(x4x160):
    return np.asarray(x4x160, dtype=F).reshape(-1)[ab_perm()]


class Program:
    EXTRA = 0                # descriptor rows past the backbone (v41_dspark: the DSpark stages, a globals row)
    EXTRA_LAYERS = ()        # of which these are layers with weights (checkpoint prefix Model.P(L))

    def __init__(self, model: V.Model, dbg=False):
        self.m = m = model
        self.NLD = m.L + self.EXTRA
        self.mem = [dict() for _ in range(TP)]      # die -> {addr: bytes}
        self.cur = 0x1000
        self.a = {}                                 # same address on every die
        self.consts = {}
        self.desc_fields = {}
        self.desc = [[dict() for _ in range(self.NLD)] for _ in range(TP)]
        self.dbg = dbg
        self.CONST = None

    # ----------------------------------------------------------------- addresses
    def put(self, name, size, align=128):
        self.cur = (self.cur + align - 1) // align * align
        self.a[name] = self.cur
        self.cur += size
        return self.a[name]

    def wr(self, d, addr, arr):
        self.mem[d][addr] = np.ascontiguousarray(arr).reshape(-1).view(np.uint8).copy()

    def wr_all(self, addr, arr):
        for d in range(TP):
            self.wr(d, addr, arr)

    def wput(self, name, blobs):
        """A per-die blob (blobs[d]) at one address on every die."""
        blobs = [np.ascontiguousarray(b).reshape(-1).view(np.uint8) for b in blobs]
        addr = self.put(name, max(len(b) for b in blobs))
        for d, b in enumerate(blobs):
            self.wr(d, addr, b)
        return addr

    def cvec(self, vals):
        if vals not in self.consts:
            self.consts[vals] = self.CONST + 512 * len(self.consts)
        return self.consts[vals]

    def fld(self, name):
        if name not in self.desc_fields:
            self.desc_fields[name] = len(self.desc_fields)
            assert len(self.desc_fields) <= NL, "descriptor overflow"
        return self.desc_fields[name]

    def setd(self, d, L, name, val):
        self.desc[d][L][name] = int(val) & 0xFFFFFFFF

    # ----------------------------------------------------------------- images
    def build_images(self):
        m = self.m
        A = self.put
        Vv, H = m.c["vocab_size"], m.dim
        for nm, sz in (("X", 640 * 4), ("PRE", 128), ("CTR", 128), ("CTOK", (CTX + 3) * 4), ("SEL", 128),
                       ("NSEL", 128), ("MIX", 128), ("Z", 1024), ("Y", 640), ("EA", 7 * 256), ("ERW", 768 * 4),
                       ("EKV", 896 * 4), ("IDXP", 256), ("ARG", 64), ("ZROW", 64)):
            A(nm, sz)
        if self.dbg:
            A("DBG", m.L * 4096)
        for L in range(m.L):
            A(f"WIN{L}", CTX * 64)
        for s_ in m.kv_src:
            A(f"CKV{s_}", CTX * 64)
            A(f"IK{s_}", CTX * 64)
            A(f"SLOT{s_}", 256 * (CTX if SLOT_RING else 1))
        A("DESC", self.NLD * 512)
        # tables
        pad = m.engram.pad
        ctok0 = np.zeros(CTX + 3, dtype=np.uint32)
        ctok0[:3] = pad
        self.wr_all(self.a["CTOK"], ctok0)
        self.wr_all(A("TOKMAP", Vv * 4), m.engram.token_map.astype(np.uint32))
        emb = (G.bits(m.w["embed.weight"]) >> 16).astype(np.uint16)
        self.wr_all(A("EMB", Vv * H * 2), emb)
        for nm, fr in (("ROPEP", m.freqs_plain), ("ROPEY", m.freqs_yarn)):
            t = np.zeros((CTX, 4), dtype=F)
            for p_ in range(CTX):
                c_, s_ = V.rope_cs(fr, p_)
                t[p_] = [c_[0], c_[1], s_[0], s_[1]]
            self.wr_all(A(nm, CTX * 16), t)
        # engram tables (row id mod 2 = owner die) and hash constants
        self.etab = {}
        for li, L in enumerate(m.engram.layer_ids):
            codes, sc = m.emb_codes[L]
            blobs = []
            for d in range(TP):
                ids = np.arange(d, codes.shape[0], 2)
                rec = np.zeros((len(ids), 36), dtype=np.uint8)
                rec[:, :32] = codes[ids]
                rec[:, 32:36] = np.exp2(sc[ids, 0].astype(np.float64)).astype(F).view(np.uint8).reshape(-1, 4)
                blobs.append(rec)
            self.etab[L] = self.wput(f"ETAB{L}", blobs)
            et = m.engram
            P_, MAG, R32, OFF = (np.zeros(NL, dtype=np.uint64) for _ in range(4))
            for i in range(24):
                sg, hd = (i >> 3) + 1, i & 7
                p_ = int(et.primes[li, sg - 1, hd])
                P_[i], MAG[i], R32[i], OFF[i] = p_, (1 << 32) // p_, (1 << 32) % p_, int(et.offsets[li, (sg - 1) * 8 + hd])
            vecs = []
            for u in range(4):
                mu = int(et.multipliers[li, u])
                vecs += [np.full(NL, mu & 0xFFFFFFFF), np.full(NL, mu >> 32)]
            vecs += [P_, MAG, R32, OFF]
            for u in range(1, 4):
                vecs.append(np.array([0xFFFFFFFF if (i < 24 and u <= (i >> 3) + 1) else 0 for i in range(NL)]))
            self.wr_all(A(f"EHASH{L}", 15 * 512), np.stack(vecs).astype(np.uint32))
        self.ehash_names = ["MLO0", "MHI0", "MLO1", "MHI1", "MLO2", "MHI2", "MLO3", "MHI3", "P", "MAG", "R32", "OFF",
                            "MASK1", "MASK2", "MASK3"]
        # per-layer weights
        for L in list(range(m.L)) + list(self.EXTRA_LAYERS):
            self._layer_images(L)
        hd = m.w["head.weight"]
        self.head = {}
        for s_ in range(NSM):
            blobs = []
            for d in range(TP):
                g = 2 * d + s_
                blob, gn, c_ = tc_lines(hd[1010 * g:1010 * (g + 1)])
                blobs.append(blob)
            self.head[s_] = self.wput(f"HEAD{s_}", blobs)
        self.wr_all(A("FNORM", 160 * 4), m.w["norm.weight"].astype(F))
        self.CONST = (self.cur + 4095) // 4096 * 4096
        return self

    def _q8rows(self, w, rows):
        return V.Q8(w.q[rows], w.e[rows])

    def _layer_images(self, L):
        m, P = self.m, f"L{L}."
        lw = lambda n: m.lw(L, n)  # noqa: E731
        yarn = L < m.L and m.ratio[L] > 0
        comp = yarn and L == m.kv_of[L]
        idx = yarn and L == m.idx_of[L]
        r = m.ratio[L] if L < m.L else 0
        sd = self.setd
        for d in range(TP):
            sd(d, L, "skip_eng", 0 if L in m.engram.layer_ids else 1)
            sd(d, L, "yarnmask", 0xFFFFFFFF if yarn else 0)
            sd(d, L, "skip_comp2", 0 if (comp and r == 2) else 1)
            sd(d, L, "skip_comp1", 0 if (comp and r == 1) else 1)
            sd(d, L, "skip_idx", 0 if idx else 1)
            sd(d, L, "log2r", 1 if r == 2 else 0)
            sd(d, L, "negr", -r)
            sd(d, L, "rope", self.a["ROPEY"] if yarn else self.a["ROPEP"])
            sd(d, L, "win", self.a.get(f"WIN{L}", 0))
            if yarn:
                src = m.kv_of[L]
                sd(d, L, "ckv", self.a[f"CKV{src}"])
                sd(d, L, "ik", self.a[f"IK{src}"])
                sd(d, L, "slot", self.a[f"SLOT{src}"])
            else:
                sd(d, L, "ckv", self.a["CKV2"])
                sd(d, L, "ik", self.a["IK2"])
                sd(d, L, "slot", self.a["SLOT2"])

        def put(name, per_die, field=None):
            addr = self.wput(P + name, per_die)
            for d in range(TP):
                sd(d, L, field or name, addr)
            return addr

        def put_sm(name, fn):
            """fn(d, s) -> blob; one field per SM (name + s)."""
            for s_ in range(NSM):
                put(f"{name}{s_}", [fn(d, s_) for d in range(TP)])

        # hyper-connections
        for which in ("attn", "ffn"):
            fn = lw(f"hc_{which}_fn")
            def hcfn(d, s_, fn=fn):
                rows = [r_ for r_ in ROWS[2 * d + s_] if r_ != SS_ROW]
                a = np.zeros((max(1, len(rows)), 8, 80), dtype=F)
                for ri, r_ in enumerate(rows):
                    a[ri] = fn[r_].reshape(80, 8).T
                return a
            put_sm(f"hcfn_{which}", hcfn)
            scale, base = lw(f"hc_{which}_scale"), lw(f"hc_{which}_base")
            sb = np.zeros((2, 128), dtype=F)
            sb[0, :24] = np.concatenate([np.full(4, scale[0]), np.full(4, scale[1]), np.full(16, scale[2])])
            sb[1, :24] = base
            put(f"hcsb_{which}", [sb, sb])
        for nm in ("attn_norm", "ffn_norm"):
            put(nm, [lw(f"{nm}.weight").astype(F)] * 2)
        qkvn = np.concatenate([lw("attn.q_norm.weight"), lw("attn.kv_norm.weight")]).astype(F)
        put("qkvn", [qkvn] * 2)
        wqa, wkv = lw("attn.wq_a.weight"), lw("attn.wkv.weight")
        cat = V.Q8(np.concatenate([wqa.q, wkv.q]), np.concatenate([wqa.e, wkv.e]))
        put("wqakv", [bd_tile(cat.q, cat.e, False)[0]] * 2)
        wqb = lw("attn.wq_b.weight")
        put_sm("wqb", lambda d, s_: bd_tile(wqb.q[512 * (2 * d + s_):512 * (2 * d + s_ + 1)],
                                            wqb.e[512 * (2 * d + s_):512 * (2 * d + s_ + 1)], False)[0])
        sink = lw("attn.attn_sink").astype(F)
        put_sm("sink", lambda d, s_: sink[16 * (2 * d + s_):16 * (2 * d + s_ + 1)])
        wa = lw("attn.wo_a.weight").reshape(m.groups, m.o_rank, -1)
        put_sm("woa", lambda d, s_: np.concatenate([tc_lines(wa[2 * (2 * d + s_) + i])[0] for i in range(2)]))
        self.woa_stride = len(tc_lines(wa[0])[0])
        wob = lw("attn.wo_b.weight")
        put_sm("wob", lambda d, s_: bd_tile(wob.q[40 * (2 * d + s_):40 * (2 * d + s_ + 1)],
                                            wob.e[40 * (2 * d + s_):40 * (2 * d + s_ + 1)], False)[0])
        put("gate", [tc_lines(lw("ffn.gate.weight"))[0]] * 2)
        put("gbias", [lw("ffn.gate.bias").astype(F)] * 2)

        def expert_blob(pref, g, fp4):
            w1, w3, w2 = (m.w[pref + f"{n}.weight"] for n in ("w1", "w3", "w2"))
            rr = slice(16 * g, 16 * (g + 1))
            q13 = np.concatenate([w1.q[rr], w3.q[rr]])
            e13 = np.concatenate([w1.e[rr], w3.e[rr]])
            b13 = bd_tile(q13, e13, fp4)[0]
            r2 = slice(40 * g, 40 * (g + 1))
            b2 = bd_tile(w2.q[r2], w2.e[r2], fp4)[0]
            return b13, b2
        def shared(d, s_):
            b13, b2 = expert_blob(f"{m.P(L)}ffn.shared_experts.", 2 * d + s_, False)
            self.sh_w2off = len(b13)
            return np.concatenate([b13, b2])
        put_sm("shexp", shared)
        def routed(d, s_):
            out = []
            for e in range(m.n_exp if L < m.L else m.dspark_n_exp):
                b13, b2 = expert_blob(f"{m.P(L)}ffn.experts.{e}.", 2 * d + s_, True)
                self.ex_w2off = len(b13)
                out.append(np.concatenate([b13, b2]))
            self.ex_stride = len(out[0])
            return np.concatenate(out)
        put_sm("rexp", routed)
        if comp:
            if r == 2:
                wc = np.concatenate([lw("attn.compressor.wkv.weight"), lw("attn.compressor.wgate.weight")])
            else:
                wc = lw("attn.compressor.wkv.weight")
            put("cwkv", [tc_lines(wc)[0]] * 2)
            put("cnorm", [lw("attn.compressor.norm.weight").astype(F)] * 2)
            put("iwk", [tc_lines(lw("attn.indexer.wk.weight"))[0]] * 2)
            put("iknorm", [lw("attn.indexer.k_norm.weight").astype(F)] * 2)
        if idx:
            iq = lw("attn.indexer.wq_b.weight")
            put_sm("iwqb", lambda d, s_: bd_tile(iq.q[256 * (2 * d + s_):256 * (2 * d + s_ + 1)],
                                                 iq.e[256 * (2 * d + s_):256 * (2 * d + s_ + 1)], False)[0])
            wp = lw("attn.indexer.weights_proj.weight")
            put_sm("iwp", lambda d, s_: tc_lines(wp[8 * (2 * d + s_):8 * (2 * d + s_ + 1)])[0])
        if L in m.engram.layer_ids:
            ew = lw("engram.wkv.weight")
            perm = np.concatenate([ab_perm(), np.arange(640, 800)])
            put_sm("ewkv", lambda d, s_: bd_tile(ew.q[perm[200 * (2 * d + s_):200 * (2 * d + s_ + 1)]],
                                                 ew.e[perm[200 * (2 * d + s_):200 * (2 * d + s_ + 1)]], False)[0])
            qk = np.concatenate([to_ab(lw("engram.q_weight")), to_ab(lw("engram.k_weight"))])
            put("eqk", [qk] * 2)
            for d in range(TP):
                sd(d, L, "etab", self.etab[L])
                sd(d, L, "ehash", self.a[f"EHASH{L}"])

    def finish_images(self):
        """Descriptor table and constant table (after every kernel registered its fields and vectors)."""
        for d in range(TP):
            tab = np.zeros((self.NLD, NL), dtype=np.uint32)
            for L in range(self.NLD):
                for nm, lane in self.desc_fields.items():
                    tab[L, lane] = self.desc[d][L].get(nm, 0)
            self.wr(d, self.a["DESC"], tab)
        if self.consts:
            ct = np.zeros((len(self.consts), NL), dtype=np.uint32)
            for vals, addr in self.consts.items():
                ct[(addr - self.CONST) // 512] = vals
            self.wr_all(self.CONST, ct)
        end = max(a + len(b) for mm in self.mem for a, b in mm.items())
        self.mem_bytes = (end + 4095) // 4096 * 4096


# ================================================================================================ kernels
class Gen:
    """Code generator of one SM's kernels (die d, SM s); per-layer variation through the layer descriptor."""

    def __init__(self, prog: Program, d, s, name):
        self.p, self.m, self.d, self.s, self.g = prog, prog.m, d, s, 2 * d + s
        self.k = K2(f"{name}.d{d}.s{s}")
        self.lib = Lib(self.k, prog)
        self.k.umovi(4, 0)                       # UR4 = 0: absolute addressing base (global and shared)
        self.DESC = None

    # ----------------------------------------------------------------- small helpers
    def A(self, n):
        return self.p.a[n]

    def ldg(self, addr, count=NL, esz=4, ur=4):
        return self.k.ldg(ur, addr, esz, count)

    def stg(self, v, addr, count=NL, esz=4, ur=4):
        self.k.stg(v, ur, addr, esz, count)

    def sts(self, v, addr, count=NL):
        self.k.sts(v, 4, addr, count)

    def lds(self, addr, count=NL):
        return self.k.lds(4, addr, count)

    def dfield(self, ur, name):
        self.k.ufromv(ur, self.DESC, self.p.fld(name))

    def ldd(self, name, off=0, count=NL, esz=4, ur=6):
        self.dfield(ur, name)
        return self.k.ldg(ur, off, esz, count)

    def gather(self, words):
        """LDSX of shared-memory words (None -> the zero area): one constant index vector, the base in imm."""
        valid = [w for w in words if w is not None]
        base = min(valid) if valid else S_ZERO // 4
        vec = [((w if w is not None else S_ZERO // 4) - base) * 4 for w in words]
        vec += [(S_ZERO // 4 - base) * 4] * (NL - len(vec))
        return self.k.ldsx(self.lib.vec(vec), base * 4)

    def bar(self):
        self.k.membar()
        self.k.bar()

    def zero(self):
        return self.lib.u(0)

    # ----------------------------------------------------------------- reductions over shared memory
    def tree_smem(self, base_w, S, Q):
        """Pairwise tree over S segments of Q (power of two) leaves at shared words base_w + s*Q: lane s."""
        lib = self.lib
        regions = [S_TREE // 4, S_TREE2 // 4]
        ping = 0
        while S * Q > NL:
            n_out = S * Q // 2
            dst = regions[ping] if regions[ping] != base_w else regions[1 - ping]
            for v in range(-(-n_out // NL)):
                ev = [base_w + 2 * (NL * v + l) if NL * v + l < n_out else None for l in range(NL)]
                od = [w + 1 if w is not None else None for w in ev]
                o = lib.add(self.gather(ev), self.gather(od))
                self.sts(o, dst * 4 + 512 * v, min(NL, n_out - NL * v))
            base_w, Q = dst, Q // 2
            ping = 1 - ping
        acc = self.gather([base_w + l if l < S * Q else None for l in range(NL)])
        return self.tree_reg(acc, S, Q)

    def tree_reg(self, acc, S, Q):
        lib = self.lib
        w = 1
        while w < Q:
            acc = lib.add(acc, lib.shfl(acc, lib.lanes(lambda l, w=w: (l + w) % NL)))
            w *= 2
        if Q > 1:
            acc = lib.shfl(acc, lib.lanes(lambda l: l * Q if l < S else 0))
        return acc

    def csum_segs(self, starts, n):
        """R-ARITH csum of S segments of n (multiple of 8) FP32 words in shared memory: lane s."""
        lib = self.lib
        S, nc = len(starts), n // 8
        assert nc * 8 == n
        Q = 1
        while Q < nc:
            Q *= 2
        tot = S * Q
        vs = []
        for v in range(-(-tot // NL)):
            def words(i, v=v):
                out = []
                for l in range(NL):
                    t = NL * v + l
                    sg, ci = divmod(t, Q)
                    out.append(starts[sg] + 8 * ci + i if (t < tot and ci < nc) else None)
                return out
            acc = self.gather(words(0))
            for i in range(1, 8):
                acc = lib.add(acc, self.gather(words(i)))
            vs.append(acc)
        if tot <= NL:
            return self.tree_reg(vs[0], S, Q)
        for v, acc in enumerate(vs):
            self.sts(acc, S_TREE + 512 * v, min(NL, tot - NL * v))
        return self.tree_smem(S_TREE // 4, S, Q)

    # ----------------------------------------------------------------- residual helpers
    def load_h(self):
        return [self.ldg(self.A("X") + 512 * j) for j in range(5)]

    def hc_pre(self, h, pre, poff):
        """to_bf16(seqsum_j pre[j] * h[j]) as (A, B) with B valid in lanes 0..31."""
        lib = self.lib
        xa = xb = None
        for j in range(4):
            pj = lib.bcast(pre, poff + j)
            ta = lib.mul(pj, h[j])
            tb = lib.mul(pj, lib.shfl(h[4], lib.lanes(lambda l, j=j: (l & 31) + 32 * j)))
            xa = ta if j == 0 else lib.add(xa, ta)
            xb = tb if j == 0 else lib.add(xb, tb)
        return lib.bf(xa), lib.op("AND", lib.bf(xb), lib.mask(lambda l: l < 32))

    def rms160(self, xa, xb, gname, gaddr=None):
        lib = self.lib
        self.sts(lib.mul(xa, xa), S_NRM)
        self.sts(lib.mul(xb, xb), S_NRM + 512, 32)
        ss = self.csum_segs([S_NRM // 4], 160)
        r = lib.rsqrt(lib.add(lib.div(ss, lib.c(160.0)), lib.c(self.m.eps)))
        r = lib.bcast(r, 0)
        if gaddr is None:
            ga, gb = self.ldd(gname, 0, NL), self.ldd(gname, 512, 32)
        else:
            ga, gb = self.ldg(gaddr, NL), self.ldg(gaddr + 512, 32)
        return lib.bf(lib.mul(ga, lib.mul(xa, r))), lib.bf(lib.mul(gb, lib.mul(xb, r)))

    # ----------------------------------------------------------------- tensor cores
    def tc_stage(self, regs):
        """BF16 x (registers of 128 elements, zero past K) -> SMEM staging (256 words)."""
        for i, v in enumerate(regs):
            self.sts(self.lib.bf(v), S_XS + 512 * i)
        for i in range(len(regs), 2):
            self.sts(self.zero(), S_XS + 512 * i)

    def tc_words(self, gn):
        lib = self.lib
        idx = lib.lanes(lambda l: 32 * l)
        for g in range(gn):
            for t in range(8):
                self.k.tcx(self.k.ldsx(idx, S_XS + (g * L16 * 8 + t) * 4), g * 8 + t)

    def tc_mma(self, field, rows, gn, off=0, dst=S_TCR, ur=6):
        self.dfield(ur, field)
        if off:
            self.k.uaddi(ur, ur, off)
        self.k.umovi(7, dst)
        self.k.tcmma(ur, 7, gn, 8, rows)
        self.k.tcwait()

    def bd_x(self, regs, K):
        """FP8 activation quantisation of x (registers of 128 elements; zero past K) into the block-dot x store."""
        lib = self.lib
        nb, c, C, g = bd_geometry(K, False)
        codes, exps = [], []
        for v in regs:
            amax = lib.seg_max(lib.op("AND", v, lib.u(0x7FFFFFFF)), 32)
            amax = lib.op("FMAX", amax, lib.c(V.FP8_AMAX_FLOOR))
            e = lib.ceil_log2(lib.mul(amax, lib.c(V.FP8_MAX_INV)))
            codes.append(lib.op("CVTE4M3B", lib.mul(v, lib.pow2(e, negate=True))))
            exps.append(e)
        zero = self.zero()
        if C == 1:
            for t in range(nb):
                cv, ev = codes[t // 4], exps[t // 4]
                if t % 4:
                    ix = lib.lanes(lambda l, t=t: (l + 32 * (t % 4)) % NL)
                    cv, ev = lib.shfl(cv, ix), lib.shfl(ev, ix)
                self.k.emit("TCXB", 0, cv, zero, t)
                self.k.emit("TCXE", 0, ev, 0, t)
        else:
            assert C <= 4
            for i, (cv, ev) in enumerate(zip(codes, exps)):
                self.sts(cv, S_KVL + 512 * i)
                self.sts(ev, S_KVL + 0xC00 + 512 * i)
            for t in range(c):
                cw = [S_KVL // 4 + (8 * (l >> 5) + t) * 32 + (l & 31) if (l >> 5) < C and 8 * (l >> 5) + t < nb
                      else None for l in range(NL)]
                ew = [S_KVL // 4 + 0x300 + (8 * j + t) * 32 if j < C and 8 * j + t < nb else None for j in range(8)]
                self.k.emit("TCXB", 0, self.gather(cw), zero, t)
                self.k.emit("TCXE", 0, self.gather(ew), 0, t)
        return nb, c, C, g

    def bd_mma(self, field, rows, K, fp4=False, off=0, ur=6, uoff=None, dst=S_TCR):
        nb, c, C, g = bd_geometry(K, fp4)
        self.dfield(ur, field)
        if uoff is not None:
            self.k.uadd(ur, ur, uoff)
        if off:
            self.k.uaddi(ur, ur, off)
        self.k.umovi(7, dst)
        self.k.emit("TCBMMA", ur, 7, g, rows | (int(fp4) << 12) | (c << 16))
        self.k.tcwait()

    # ----------------------------------------------------------------- exchange
    def allreduce(self, buf, n, own):
        """After every SM stored its part of buf[0:n]: die SM0s all-reduce 128-element chunks, each die
        contributing the elements own(die, i) and +0 elsewhere (x + 0 = x: an exact gather); every SM then reads."""
        lib = self.lib
        self.bar()
        if self.s == 0:
            for q in range(-(-n // NL)):
                cnt = min(NL, n - NL * q)
                v = self.ldg(self.A(buf) + 512 * q, cnt)
                v = lib.op("AND", v, lib.mask(lambda l, q=q: NL * q + l < n and own(self.d, NL * q + l)))
                r = self.k.coll(v, 0, cnt)
                self.stg(r, self.A(buf) + 512 * q, cnt)
            self.k.membar()
        self.k.bar()

    # ----------------------------------------------------------------- hyper-connections
    def hc_mixes(self, which, h):
        k, lib, g = self.k, self.lib, self.g
        for j in range(4):
            self.sts(h[j], S_FLAT + 640 * j)
        k.stsx(h[4], lib.lanes(lambda l: S_FLAT + (160 * (l >> 5) + 128 + (l & 31)) * 4), 0)
        xs = [self.gather([S_FLAT // 4 + 8 * l + i if l < 80 else None for l in range(NL)]) for i in range(8)]
        rows = ROWS[g]
        self.dfield(6, f"hcfn_{which}{self.s}")
        for ri, r in enumerate(rows):
            acc = None
            for i in range(8):
                w = xs[i] if r == SS_ROW else k.ldg(6, (ri * 8 + i) * 320, 4, 80)
                pr = lib.mul(w, xs[i])
                acc = pr if i == 0 else lib.add(acc, pr)
            self.sts(acc, S_TREE + 512 * ri)
        res = self.tree_smem(S_TREE // 4, len(rows), NL)
        self.stg(res, self.A("MIX") + 4 * rows[0], len(rows))
        self.bar()
        if self.s == 0:
            v = self.ldg(self.A("MIX") + 52 * self.d, 13)
            self.stg(k.coll(v, 1, 13), self.A("MIX"), 26)
            k.membar()
        k.bar()
        mixes = self.ldg(self.A("MIX"), 26)
        # tail (replicated): norm scale, pre / post / comb, Sinkhorn
        ss = lib.bcast(mixes, SS_ROW)
        rr = lib.rsqrt(lib.add(lib.div(ss, lib.c(640.0)), lib.c(self.m.eps)))
        mm = lib.mul(mixes, rr)
        sc = self.ldd(f"hcsb_{which}", 0, 24)
        bs = self.ldd(f"hcsb_{which}", 512, 24)
        v = lib.add(lib.mul(mm, sc), bs)
        sig = lib.sigmoid(v)
        pre = lib.add(sig, lib.c(self.m.hc_eps))                     # lanes 0..3
        post = lib.mul(sig, lib.c(2.0))                               # lanes 4..7
        eps = lib.c(self.m.hc_eps)
        cm = lib.select_m(lib.mask(lambda l: l < 16), lib.shfl(v, lib.lanes(lambda l: (l + 8) % NL)), lib.c(1.0))
        R = [lib.lanes(lambda l, q=q: (l & ~3) + q if l < 16 else l) for q in range(4)]
        C = [lib.lanes(lambda l, q=q: (l & 3) + 4 * q if l < 16 else l) for q in range(4)]
        def ssum(x, I):
            acc = lib.add(lib.shfl(x, I[0]), lib.shfl(x, I[1]))
            return lib.add(lib.add(acc, lib.shfl(x, I[2])), lib.shfl(x, I[3]))
        mx = lib.seg_max(cm, 4)
        e = lib.exp(lib.add(cm, lib.neg(mx)))
        cm = lib.add(lib.div(e, ssum(e, R)), eps)
        cm = lib.div(cm, lib.add(ssum(cm, C), eps))
        cv = k.op("OR", cm, cm)
        h_ = k.loop(14, self.m.sinkhorn_iters - 1)
        t = lib.div(cv, lib.add(ssum(cv, R), eps))
        k.into(cv, "FDIV", t, lib.add(ssum(t, C), eps))
        k.endloop(h_)
        return pre, post, cv

    def hc_post(self, ya, yb, h, post, comb):
        """to_bf16(post[k] * y + seqsum_j comb[j, k] * res[j]) in the AB layout (yb valid in lanes 0..31)."""
        lib = self.lib
        out = []
        for kk in range(4):
            mix = None
            for j in range(4):
                t = lib.mul(lib.bcast(comb, 4 * j + kk), h[j])
                mix = t if j == 0 else lib.add(mix, t)
            out.append(lib.bf(lib.add(lib.mul(lib.bcast(post, 4 + kk), ya), mix)))
        mix = None
        for j in range(4):
            bj = lib.shfl(h[4], lib.lanes(lambda l, j=j: (l & 31) + 32 * j))
            cj = lib.shfl(comb, lib.lanes(lambda l, j=j: 4 * j + (l >> 5)))
            t = lib.mul(cj, bj)
            mix = t if j == 0 else lib.add(mix, t)
        pb = lib.shfl(post, lib.lanes(lambda l: 4 + (l >> 5)))
        y4 = lib.shfl(yb, lib.lanes(lambda l: l & 31))
        out.append(lib.bf(lib.add(lib.mul(pb, y4), mix)))
        return out

    def dbg(self, regs, slot, counts=None):
        """debug dump (die 0 SM 0): DBG + layer*4096 + slot*640 (--debug only)."""
        if not self.p.dbg or self.d or self.s:
            return
        for i, v in enumerate(regs):
            self.k.stg(v, 13, slot * 640 + 512 * i, 4, counts[i] if counts else NL)
        self.k.membar()

    # ----------------------------------------------------------------- RoPE
    def rope_cs(self, field=None, absaddr=None, ur=8):
        """(c0, c1, s0, s1) of the position in lanes 0..3: table row at UR1 (pos) of the layer's table."""
        k = self.k
        k.umuli(ur, 1, 16)
        if field is not None:
            self.dfield(6, field)
            k.uadd(ur, ur, 6)
            return k.ldg(ur, 0, 4, 4)
        return k.ldg(ur, absaddr, 4, 4)

    def rope(self, x, cs, inverse, sel):
        """rope_tail on the last 4 elements of each 32-lane row (adjacent pairs), BF16, where sel(lane)."""
        lib = self.lib
        cv = lib.shfl(cs, lib.lanes(lambda l: 0 if (l & 31) < 30 else 1))
        sv = lib.shfl(cs, lib.lanes(lambda l: 2 if (l & 31) < 30 else 3))
        even_neg = not inverse                                    # forward: re = a c - b s, im = b c + a s
        sv = lib.op("XOR", sv, lib.lanes(lambda l: SIGN if ((l & 1) == 0) == even_neg else 0))
        rot = lib.bf(lib.add(lib.mul(x, cv), lib.mul(lib.shfl(x, lib.lanes(lambda l: l ^ 1)), sv)))
        return lib.select_m(lib.mask(lambda l: (l & 31) >= 28 and sel(l)), rot, x)

    # ----------------------------------------------------------------- attention
    def attention(self, xa, xb):
        k, lib, m, s, g = self.k, self.lib, self.m, self.s, self.g
        cs, qk, kv0 = self.attn_front(xa, xb)
        if s == 0:
            self.dfield(6, "win")
            k.umuli(8, 1, 64)
            k.uadd(6, 6, 8)
            k.stg(kv0, 6, 0, 2, 32)
            k.membar()
        self.attn_q(qk, cs)
        # ---- indexer, part A (index q, head weights) and the compressor
        la = k.newlabel("noidxA")
        self.dfield(10, "skip_idx")
        k.bnz(10, la)
        k.push()
        self.bd_mma(f"iwqb{s}", 256, 32)
        for v_ in range(2):
            q = self.rope(lib.bf(self.lds(S_TCR + 512 * v_)), cs, False, lambda l: True)
            self.sts(lib.qdq_fp4_e8m0(q), S_IQS + 512 * v_)
        self.tc_stage([xa, xb])
        self.tc_words(2)
        self.tc_mma(f"iwp{s}", 8, 2)
        w = lib.bf(lib.mul(lib.bf(self.lds(S_TCR, 8)), lib.c(m.index_w_scale)))
        self.sts(w, S_MISC, 8)
        if s == 1:
            self.compressor()
        k.pop()
        k.label(la)
        self.bar()
        # ---- indexer, part B (scores over the source's keys, head sum, top-k, list slots)
        lb = k.newlabel("noidxB")
        k.bnz(10, lb)
        k.push()
        self.indexer()
        k.pop()
        k.label(lb)
        # ---- the KV list: window rows (oldest first), this position's row, the selected compressed rows
        self.dfield(6, "win")
        for v_ in range(CTX // 4):
            self.sts(k.ldg(6, 256 * v_, 2, NL), S_KVL + 512 * v_)
        for v_ in range(CTX // 4, TPAD // 4):
            self.sts(self.zero(), S_KVL + 512 * v_)
        k.umuli(8, 1, 128)
        k.sts(kv0, 8, S_KVL, 32)
        self.dfield(6, "ckv")
        ck = [k.ldg(6, 256 * v_, 2, NL) for v_ in range(CTX // 4)]
        self.dfield(9, "yarnmask")
        ym = k.movu(9)
        slots = lib.select_m(ym, self.ldg(self.A("SEL"), CTX), lib.u(S_DUMMY))
        dcol = lib.lanes(lambda l: (l & 31) * 4)
        for v_ in range(CTX // 4):
            ad = lib.op("IADD", lib.shfl(slots, lib.lanes(lambda l, v_=v_: 4 * v_ + (l >> 5))), dcol)
            k.stsx(ck[v_], ad, 0)
        nsel = lib.op("AND", self.ldg(self.A("NSEL"), 1), ym)
        T = lib.op("IADD", lib.op("IADD", k.movu(1), lib.u(1)), lib.bcast(nsel, 0))
        return self.attend_core(T, cs)

    def attn_front(self, xa, xb):
        """wq_a | wkv, q_norm / kv_norm, the position's RoPE; returns (cs, qk, kv0): kv0 = this position's FP8
        window row in lanes 0..31."""
        lib, m = self.lib, self.m
        self.bd_x([xa, xb], 160)
        self.bd_mma("wqakv", 64, 160)
        v = lib.bf(self.lds(S_TCR, 64))
        qk = lib.rmsnorm32(v, self.ldd("qkvn", 0, 64), m.eps)
        cs = self.rope_cs("rope")
        kvr = lib.qdq_fp8(self.rope(qk, cs, False, lambda l: 32 <= l < 64))
        kv0 = lib.shfl(kvr, lib.lanes(lambda l: (l + 32) % NL))
        return cs, qk, kv0

    def attn_q(self, qk, cs):
        """wq_b (this SM's 16 heads), RoPE -> S_QS; returns the q registers."""
        lib = self.lib
        qr = lib.op("AND", qk, lib.mask(lambda l: l < 32))
        self.bd_x([qr], 32)
        self.bd_mma(f"wqb{self.s}", 512, 32)
        qs = []
        for v_ in range(4):
            q = self.rope(lib.bf(self.lds(S_TCR + 512 * v_)), cs, False, lambda l: True)
            self.sts(q, S_QS + 512 * v_)
            qs.append(q)
        return qs

    def attend_core(self, T, cs):
        """attend() over the KV list at S_KVL (T valid rows, TPAD lanes per head) for this SM's 16 heads (q at
        S_QS), the sink, inverse RoPE, grouped wo_a, z exchange, wo_b, y exchange."""
        lib, m, s, g = self.lib, self.m, self.s, self.g
        hpv = NL // TPAD                       # heads per score register
        nvs = 16 // hpv
        acc = [[None] * 4 for _ in range(nvs)]
        for kk in range(32):
            kop = self.gather([S_KVL // 4 + (l % TPAD) * 32 + kk for l in range(NL)])
            for v_ in range(nvs):
                qop = self.gather([S_QS // 4 + (hpv * v_ + l // TPAD) * 32 + kk for l in range(NL)])
                pr = lib.mul(qop, kop)
                cc = kk // 8
                acc[v_][cc] = pr if kk % 8 == 0 else lib.add(acc[v_][cc], pr)
        valid = lib.op("ULT", lib.lanes(lambda l: l % TPAD), T)
        vm = lib.op("ISUB", lib.u(0), valid)
        fill = lib.op("AND", lib.op("XOR", vm, lib.u(0xFFFFFFFF)), lib.u(NEG_BIG))
        for v_ in range(nvs):
            sc = lib.mul(lib.add(lib.add(acc[v_][0], acc[v_][1]), lib.add(acc[v_][2], acc[v_][3])),
                         lib.c(m.attn_scale))
            sc = lib.op("OR", lib.op("AND", sc, vm), fill)
            mx = lib.seg_max(sc, TPAD)
            e = lib.op("AND", lib.exp(lib.add(sc, lib.neg(mx))), vm)
            self.sts(e, S_ES + 512 * v_)
            self.sts(lib.bf(e), S_EB + 512 * v_)
            self.sts(mx, S_MS + 512 * v_)
        es = self.csum_segs([S_ES // 4 + TPAD * h for h in range(16)], TPAD)
        mh = self.gather([S_MS // 4 + TPAD * l if l < 16 else None for l in range(NL)])
        sink = self.ldd(f"sink{s}", 0, 16)
        den = lib.add(es, lib.exp(lib.add(sink, lib.neg(mh))))
        nch = TPAD // 8
        acc = [[None] * nch for _ in range(4)]
        for t in range(TPAD):
            vop = self.gather([S_KVL // 4 + t * 32 + (l & 31) for l in range(NL)])
            for v_ in range(4):
                eop = self.gather([S_EB // 4 + (4 * v_ + (l >> 5)) * TPAD + t for l in range(NL)])
                pr = lib.mul(eop, vop)
                cc = t // 8
                acc[v_][cc] = pr if t % 8 == 0 else lib.add(acc[v_][cc], pr)
        o = []
        for v_ in range(4):
            parts = acc[v_]
            while len(parts) > 1:
                parts = [lib.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
            ov = parts[0]
            dv = lib.shfl(den, lib.lanes(lambda l, v_=v_: 4 * v_ + (l >> 5)))
            o.append(self.rope(lib.bf(lib.div(ov, dv)), cs, True, lambda l: True))
        # ---- grouped wo_a (this SM's two o-groups), z exchange, wo_b, y exchange
        for i in range(2):
            self.tc_stage(o[2 * i:2 * i + 2])
            self.tc_words(2)
            self.tc_mma(f"woa{s}", 32, 2, off=i * self.p.woa_stride, dst=S_TCR + 128 * i)
        z = lib.bf(self.lds(S_TCR, 64))
        self.stg(z, self.A("Z") + 256 * g, 64)
        self.allreduce("Z", 256, lambda d, i: i // 128 == d)
        z = [self.ldg(self.A("Z")), self.ldg(self.A("Z") + 512)]
        self.bd_x(z, 256)
        self.bd_mma(f"wob{s}", 40, 256)
        return self.y_exchange(lib.bf(self.lds(S_TCR, 40)))

    def y_exchange(self, y):
        self.stg(y, self.A("Y") + 160 * self.g, 40)
        self.allreduce("Y", 160, lambda d, i: i // 80 == d)
        return self.ldg(self.A("Y")), self.ldg(self.A("Y") + 512, 32)

    def compressor(self):
        """SM 1 of each die: the KV source's compressor (ratio 2: open slot / pooling; ratio 1), then the index key
        and the compressed row of the group that closes at this position (die-memory state)."""
        k, lib, m = self.k, self.lib, self.m
        l_c1, l_com, l_end = k.newlabel("c1"), k.newlabel("ccom"), k.newlabel("cend")
        self.dfield(11, "skip_comp2")
        k.bnz(11, l_c1)
        k.push()
        self.tc_mma("cwkv", 64, 2)
        v = self.lds(S_TCR, 64)
        odd = lib.op("AND", k.movu(1), lib.u(1))
        k.ufromv(11, odd, 0)
        l_pool = k.newlabel("pool")
        k.bnz(11, l_pool)
        self.dfield(6, "slot")
        if SLOT_RING:
            k.umuli(8, 1, 256)
            k.uadd(6, 6, 8)
        k.stg(v, 6, 0, 4, 64)
        k.membar()
        k.bra(l_end)
        k.label(l_pool)
        self.dfield(6, "slot")
        if SLOT_RING:
            k.umuli(8, 1, 256)
            k.uadd(6, 6, 8)
        old = k.ldg(6, -256 if SLOT_RING else 0, 4, 64)
        mx = lib.op("FMAX", old, v)
        e0 = lib.exp(lib.add(old, lib.neg(mx)))
        e1 = lib.exp(lib.add(v, lib.neg(mx)))
        den = lib.add(e0, e1)
        up = lib.lanes(lambda l: (l + 32) % NL)
        p0, p1 = lib.shfl(lib.div(e0, den), up), lib.shfl(lib.div(e1, den), up)
        pooled = lib.add(lib.mul(old, p0), lib.mul(v, p1))
        pooled = lib.op("AND", lib.bf(pooled), lib.mask(lambda l: l < 32))
        lat = lib.rmsnorm32(pooled, self.ldd("cnorm", 0, 32), m.eps)
        self.sts(lat, S_MISC + 256, 32)
        k.pop()
        k.bra(l_com)
        k.label(l_c1)
        self.dfield(11, "skip_comp1")
        k.bnz(11, l_end)
        k.push()
        self.tc_mma("cwkv", 32, 2)
        v = lib.bf(self.lds(S_TCR, 32))
        lat = lib.rmsnorm32(v, self.ldd("cnorm", 0, 32), m.eps)
        self.sts(lat, S_MISC + 256, 32)
        k.pop()
        k.label(l_com)
        k.push()
        lat = self.lds(S_MISC + 256, 32)
        # the group's RoPE position pos + 1 - r (yarn table)
        self.dfield(8, "negr")
        k.uadd(8, 8, 1)
        k.uaddi(8, 8, 1)
        k.umuli(8, 8, 16)
        gcs = k.ldg(8, self.A("ROPEY"), 4, 4)
        self.tc_stage([lat])
        self.tc_words(1)
        self.tc_mma("iwk", 32, 1)
        kk = lib.rmsnorm32(lib.bf(self.lds(S_TCR, 32)), self.ldd("iknorm", 0, 32), m.eps)
        ik = lib.qdq_fp4_e8m0(self.rope(kk, gcs, False, lambda l: l < 32))
        ckv = lib.qdq_fp4_e4m3(self.rope(lat, gcs, False, lambda l: l < 32))
        self.dfield(9, "log2r")
        gi = lib.op("ISUB", lib.op("SHR", lib.op("IADD", k.movu(1), lib.u(1)), k.movu(9)), lib.u(1))
        k.ufromv(8, gi, 0)
        k.umuli(8, 8, 64)
        for fld_, val in (("ik", ik), ("ckv", ckv)):
            self.dfield(6, fld_)
            k.uadd(6, 6, 8)
            k.stg(val, 6, 0, 2, 32)
        k.membar()
        k.pop()
        k.label(l_end)

    def indexer(self):
        k, lib, m, s = self.k, self.lib, self.m, self.s
        self.dfield(6, "ik")
        for v_ in range(CTX // 4):
            self.sts(k.ldg(6, 256 * v_, 2, NL), S_IKS + 512 * v_)
        hpv = NL // CTX                                            # index heads per register (lanes: head, key)
        nv = 8 // hpv
        acc = [None] * nv
        for kk in range(32):
            for v_ in range(nv):
                q = self.gather([S_IQS // 4 + (hpv * v_ + l // CTX) * 32 + kk for l in range(NL)])
                if v_ == 0:
                    key = self.gather([S_IKS // 4 + (l % CTX) * 32 + kk for l in range(NL)])
                pr = lib.mul(q, key)
                acc[v_] = pr if kk == 0 else lib.add(acc[v_], pr)  # exact: FP4 x FP4 block terms
        wv = self.lds(S_MISC, 8)
        wl = [lib.shfl(wv, lib.lanes(lambda l, v_=v_: hpv * v_ + l // CTX)) for v_ in range(nv)]
        terms = [lib.bf(lib.mul(lib.op("FMAX", lib.bf(acc[v_]), lib.u(0)), wl[v_])) for v_ in range(nv)]
        part = None
        for h in range(8):
            t = lib.shfl(terms[h // hpv], lib.lanes(lambda l, h=h: (l % CTX) + CTX * (h % hpv)))
            part = t if h == 0 else lib.add(part, t)
        self.stg(part, self.A("IDXP") + 4 * CTX * s, CTX)
        self.bar()
        if s == 0:
            tot = lib.add(self.ldg(self.A("IDXP"), CTX), self.ldg(self.A("IDXP") + 4 * CTX, CTX))
            sc = lib.bf(k.coll(tot, 0, CTX))
            self.dfield(9, "log2r")
            n = lib.op("SHR", lib.op("IADD", k.movu(1), lib.u(1)), k.movu(9))
            valid = lib.op("ULT", lib.lane(), n)
            if CTX > m.topk:
                bm = lib.select_m(lib.op("ISUB", lib.u(0), valid), sc, lib.u(NEG_BIG))
                cnt = lib.u(0)
                for j in range(CTX):
                    bj = lib.bcast(bm, j)
                    gt = lib.op("FCMPGT", bj, bm)
                    eq = lib.op("XOR", lib.op("OR", gt, lib.op("FCMPGT", bm, bj)), lib.u(1))
                    tie = lib.op("AND", eq, lib.lanes(lambda l, j=j: 1 if l > j else 0))
                    cnt = lib.op("IADD", cnt, lib.op("OR", gt, tie))
                sel = lib.op("AND", valid, lib.op("ULT", cnt, lib.u(m.topk)))
            else:
                sel = valid
            sel = lib.op("AND", sel, lib.lanes(lambda l: 1 if l < CTX else 0))
            inc = self.scan(sel, CTX)
            excl = lib.op("ISUB", inc, sel)
            W = lib.op("IADD", k.movu(1), lib.u(1))
            ad = lib.op("IADD", lib.op("SHL", lib.op("IADD", W, excl), lib.u(7)), lib.u(S_KVL))
            ad = lib.select_m(lib.op("ISUB", lib.u(0), sel), ad, lib.u(S_DUMMY))
            self.stg(ad, self.A("SEL"), CTX)
            self.stg(lib.bcast(inc, CTX - 1), self.A("NSEL"), 1)
            if self.p.dbg and self.d == 0:
                self.dbg([sc, sel], 6, [CTX, CTX])
            k.membar()
        k.bar()

    def scan(self, v, n):
        """inclusive prefix sum (integers) over lanes 0..n-1."""
        lib = self.lib
        w = 1
        while w < n:
            sh = lib.shfl(v, lib.lanes(lambda l, w=w: l - w if l >= w else 0))
            v = lib.op("IADD", v, lib.op("AND", sh, lib.mask(lambda l, w=w: l >= w)))
            w *= 2
        return v

    # ----------------------------------------------------------------- MoE
    def moe(self, xa, xb, ne=None, ke=None):
        k, lib, m, s, g = self.k, self.lib, self.m, self.s, self.g
        ne = ne or m.n_exp
        ke = ke or m.k_exp
        self.tc_stage([xa, xb])
        self.tc_words(2)
        self.tc_mma("gate", ne, 2)
        sc = self.k.op("FSQRT", lib.softplus(self.lds(S_TCR, ne)))
        b = lib.add(sc, self.ldd("gbias", 0, ne))
        v12 = lib.mask(lambda l: l < ne)
        bm = lib.select_m(v12, b, lib.u(NEG_BIG))
        cnt = lib.u(0)
        for j in range(ne):
            bj = lib.bcast(bm, j)
            gt = lib.op("FCMPGT", bj, bm)
            eq = lib.op("XOR", lib.op("OR", gt, lib.op("FCMPGT", bm, bj)), lib.u(1))
            tie = lib.op("AND", eq, lib.lanes(lambda l, j=j: 1 if l > j else 0))
            cnt = lib.op("IADD", cnt, lib.op("OR", gt, tie))
        sel = lib.op("AND", lib.op("ULT", cnt, lib.u(ke)), lib.lanes(lambda l: 1 if l < ne else 0))
        smask = lib.op("ISUB", lib.u(0), sel)
        excl = lib.op("ISUB", self.scan(sel, 16), sel)
        sm_ = lib.op("AND", sc, smask)
        tot = lib.bcast(sm_, 0)
        for i in range(1, ne):
            tot = lib.add(tot, lib.bcast(sm_, i))
        den = lib.add(tot, lib.c(1e-20))
        wgt = lib.mul(lib.div(sc, den), lib.c(m.route_scale))
        ad = lib.select_m(smask, lib.op("IADD", lib.op("SHL", excl, lib.u(2)), lib.u(S_MISC + 128)),
                          lib.u(S_DUMMY))
        k.stsx(lib.lane(), ad, 0, 16)
        k.stsx(wgt, ad, 64, 16)
        ids = self.lds(S_MISC + 128, ke)
        wts = self.lds(S_MISC + 192, ke)
        if self.p.dbg and self.d == 0:
            self.dbg([b, ids], 7, [ne, ke])
        # w1 | w3 rows 16g .. 16g + 15 of every slot (6 routed by id, then the shared expert)
        self.bd_x([xa, xb], 160)
        lim = lib.c(m.limit)
        nlim = lib.c(-m.limit)
        for e in range(ke + 1):
            if e < ke:
                k.ufromv(9, ids, e)
                k.umuli(9, 9, self.p.ex_stride)
                self.bd_mma(f"rexp{s}", 32, 160, fp4=True, uoff=9)
            else:
                self.bd_mma(f"shexp{s}", 32, 160)
            v = lib.bf(self.lds(S_TCR, 32))
            u = lib.op("FMIN", lib.op("FMAX", lib.shfl(v, lib.lanes(lambda l: (l + 16) % NL)), nlim), lim)
            gg = lib.op("FMIN", v, lim)
            a = lib.mul(lib.silu(gg), u)
            if e < ke:
                a = lib.mul(lib.bcast(wts, e), a)
            self.stg(a, self.A("EA") + 4 * (64 * e + 16 * g), 16)
        self.allreduce("EA", 64 * (ke + 1), lambda d, i: (i % 64) // 32 == d)
        y = None
        for e in range(ke + 1):
            a = lib.bf(self.ldg(self.A("EA") + 256 * e, 64))
            self.bd_x([a], 64)
            if e < ke:
                k.ufromv(9, ids, e)
                k.umuli(9, 9, self.p.ex_stride)
                self.bd_mma(f"rexp{s}", 40, 64, fp4=True, uoff=9, off=self.p.ex_w2off)
            else:
                self.bd_mma(f"shexp{s}", 40, 64, off=self.p.sh_w2off)
            ye = lib.bf(self.lds(S_TCR, 40))
            y = ye if e == 0 else lib.add(y, ye)
        return self.y_exchange(lib.bf(y))

    # ----------------------------------------------------------------- Engram
    def engram(self):
        k, lib, m, s, d, g = self.k, self.lib, self.m, self.s, self.d, self.g
        h = self.load_h()
        k.umuli(8, 1, 4)
        ct = k.ldg(8, self.A("CTOK"), 4, 4)                       # compressed ids of positions pos-3 .. pos
        self.dfield(6, "ehash")
        hv = {nm: k.ldg(6, 512 * i, 4, NL) for i, nm in enumerate(self.p.ehash_names)}
        rlo = rhi = None
        for u in range(4):
            tu = lib.bcast(ct, 3 - u)
            lo = lib.op("IMUL", tu, hv[f"MLO{u}"])
            hi = lib.op("IADD", lib.op("IMULHI", tu, hv[f"MLO{u}"]), lib.op("IMUL", tu, hv[f"MHI{u}"]))
            if u == 0:
                rlo, rhi = lo, hi
            else:
                rlo = lib.op("XOR", rlo, lib.op("AND", lo, hv[f"MASK{u}"]))
                rhi = lib.op("XOR", rhi, lib.op("AND", hi, hv[f"MASK{u}"]))
        P_, pm1 = hv["P"], lib.op("ISUB", hv["P"], lib.u(1))

        def mod(x):
            q = lib.op("IMULHI", x, hv["MAG"])
            r = lib.op("ISUB", x, lib.op("IMUL", q, P_))
            ge = lib.op("UGT", r, pm1)
            return lib.op("ISUB", r, lib.op("AND", lib.op("ISUB", lib.u(0), ge), P_))
        t = lib.op("IADD", lib.op("IMUL", mod(rhi), hv["R32"]), mod(rlo))
        ids = lib.op("IADD", mod(t), hv["OFF"])
        own = lib.op("ISUB", lib.op("XOR", lib.op("AND", ids, lib.u(1)), lib.u(d)), lib.u(1))
        self.dfield(9, "etab")
        rowad = lib.op("IADD", lib.op("IMUL", lib.op("SHR", ids, lib.u(1)), lib.u(36)), k.movu(9))
        addr = lib.select_m(own, rowad, lib.u(self.A("ZROW")))
        if self.p.dbg and d == 0 and s == 0:
            self.dbg([ids], 5, [24])
        k.umovi(15, 0)
        for i in range(12 * s, 12 * s + 12):
            k.ufromv(8, addr, i)
            cd = k.ldg(8, 0, 1, 32)
            scl = k.ldg(8, 32, 4, 32, strided=True)
            self.stg(lib.mul(cd, scl), self.A("ERW") + 128 * i, 32)
        self.allreduce("ERW", 768, lambda d_, i: True)
        rows = [lib.bf(self.ldg(self.A("ERW") + 512 * q)) for q in range(6)]
        self.bd_x(rows, 768)
        self.bd_mma(f"ewkv{s}", 200, 768)
        self.stg(lib.bf(self.lds(S_TCR)), self.A("EKV") + 800 * g, NL)
        self.stg(lib.bf(self.lds(S_TCR + 512, 72)), self.A("EKV") + 800 * g + 512, 72)
        self.allreduce("EKV", 800, lambda d_, i: i // 400 == d_)
        E = self.A("EKV")
        ka = [self.ldg(E + 512 * j) for j in range(5)]
        va, vb = self.ldg(E + 2560), self.ldg(E + 3072, 32)
        qk = [self.ldd("eqk", 512 * i) for i in range(10)]
        W = [lib.mul(qk[i], qk[5 + i]) for i in range(5)]
        for qn in range(3):
            for j in range(5):
                if qn == 0:
                    pr = lib.mul(h[j], h[j])
                elif qn == 1:
                    pr = lib.mul(ka[j], ka[j])
                else:
                    pr = lib.mul(lib.mul(h[j], W[j]), ka[j])
                if j < 4:
                    self.sts(pr, S_SEG + 640 * (4 * qn + j))
                else:
                    k.stsx(pr, lib.lanes(lambda l, qn=qn: S_SEG + (160 * (4 * qn + (l >> 5)) + 128 + (l & 31)) * 4), 0)
        res = self.csum_segs([S_SEG // 4 + 160 * sg for sg in range(12)], 160)
        n = lib.c(160.0)
        eps = lib.c(m.eps)
        rh = lib.rsqrt(lib.add(lib.div(res, n), eps))
        kk = lib.shfl(res, lib.lanes(lambda l: (l + 4) % NL))
        rk = lib.rsqrt(lib.add(lib.div(kk, n), eps))
        dot = lib.mul(lib.mul(lib.shfl(res, lib.lanes(lambda l: (l + 8) % NL)), lib.mul(rh, rk)), lib.c(m.engram_scale))
        mag = k.op("FSQRT", lib.op("FMAX", lib.op("AND", dot, lib.u(0x7FFFFFFF)), lib.c(1e-6)))
        gate = lib.sigmoid(lib.op("OR", mag, lib.op("AND", dot, lib.u(SIGN))))
        out = [lib.bf(lib.add(h[j], lib.mul(lib.bcast(gate, j), va))) for j in range(4)]
        gb = lib.shfl(gate, lib.lanes(lambda l: l >> 5))
        out.append(lib.bf(lib.add(h[4], lib.mul(gb, lib.shfl(vb, lib.lanes(lambda l: l & 31))))))
        if s == 0:
            for j in range(5):
                self.stg(out[j], self.A("X") + 512 * j)
        self.bar()

    # ----------------------------------------------------------------- kernels
    def kernel_layer(self):
        k, lib, m, s = self.k, self.lib, self.m, self.s
        ctr = self.ldg(self.A("CTR"), 1)
        k.ufromv(5, ctr, 0)
        k.umuli(5, 5, 512)
        self.DESC = k.ldg(5, self.A("DESC"), 4, NL)
        if self.p.dbg:
            k.umuli(13, 5, 8)
            k.uaddi(13, 13, self.A("DBG"))
        self.sts(self.zero(), S_ZERO, 64)
        le = k.newlabel("noeng")
        self.dfield(10, "skip_eng")
        k.bnz(10, le)
        k.push()
        self.engram()
        k.pop()
        k.label(le)
        h = self.load_h()
        pre0 = self.ldg(self.A("PRE"), 4)
        pre_a, post_a, comb_a = self.hc_mixes("attn", h)
        xa, xb = self.rms160(*self.hc_pre(h, pre0, 0), "attn_norm")
        self.dbg([xa, xb], 0, [NL, 32])
        ya, yb = self.attention(xa, xb)
        self.dbg([ya, yb], 1, [NL, 32])
        h = self.hc_post(ya, yb, h, post_a, comb_a)
        pre_f, post_f, comb_f = self.hc_mixes("ffn", h)
        xa, xb = self.rms160(*self.hc_pre(h, pre_a, 0), "ffn_norm")
        self.dbg([xa, xb], 2, [NL, 32])
        ya, yb = self.moe(xa, xb)
        self.dbg([ya, yb], 3, [NL, 32])
        h = self.hc_post(ya, yb, h, post_f, comb_f)
        if s == 0:
            for j in range(5):
                self.stg(h[j], self.A("X") + 512 * j)
            self.stg(pre_f, self.A("PRE"), 4)
            self.stg(lib.op("IADD", ctr, lib.u(1)), self.A("CTR"), 1)
            k.membar()
        k.exit()
        return k

    def kernel_embed(self):
        k, lib = self.k, self.lib
        if self.s == 0:
            k.umuli(8, 0, 320)
            row = k.ldg(8, self.A("EMB"), 2, NL)
            rb = lib.shfl(k.ldg(8, self.A("EMB") + 256, 2, 32), lib.lanes(lambda l: l & 31))
            for j in range(4):
                self.stg(row, self.A("X") + 512 * j)
            self.stg(rb, self.A("X") + 2048)
            self.stg(lib.select_m(lib.mask(lambda l: l == 0), lib.c(1.0), lib.u(0)), self.A("PRE"), 4)
            k.umuli(9, 0, 4)
            tm = k.ldg(9, self.A("TOKMAP"), 4, 1)
            k.umuli(10, 1, 4)
            k.stg(tm, 10, self.A("CTOK") + 12, 4, 1)
            self.stg(lib.u(0), self.A("CTR"), 1)
            k.membar()
        k.exit()
        return k

    def kernel_head(self):
        k, lib, s, d = self.k, self.lib, self.s, self.d
        h = self.load_h()
        pre = self.ldg(self.A("PRE"), 4)
        xa, xb = self.rms160(*self.hc_pre(h, pre, 0), None, gaddr=self.A("FNORM"))
        self.tc_stage([xa, xb])
        self.tc_words(2)
        k.umovi(6, self.p.head[s])
        k.umovi(7, S_TCR)
        k.tcmma(6, 7, 2, 8, 1010)
        k.tcwait()
        lane = lib.lane()
        bv, bi = None, None
        for r in range(8):
            v = self.lds(S_TCR + 512 * r)
            if r == 7:
                v = lib.select_m(lib.mask(lambda l: l < 1010 - 896), v, lib.u(NEG_BIG))
            if r == 0:
                bv, bi = v, lane
            else:
                gt = lib.op("FCMPGT", v, bv)
                gm = lib.op("ISUB", lib.u(0), gt)
                bv = lib.select_m(gm, v, bv)
                bi = lib.select_m(gm, lib.op("IADD", lane, lib.u(NL * r)), bi)
        w = NL // 2
        while w >= 1:
            sh = lib.lanes(lambda l, w=w: (l + w) % NL)
            ov, oi = lib.shfl(bv, sh), lib.shfl(bi, sh)
            gt = lib.op("FCMPGT", ov, bv)
            lt = lib.op("FCMPGT", bv, ov)
            eq = lib.op("XOR", lib.op("OR", gt, lt), lib.u(1))
            take = lib.op("ISUB", lib.u(0), lib.op("OR", gt, lib.op("AND", eq, lib.op("ULT", oi, bi))))
            bv, bi = lib.select_m(take, ov, bv), lib.select_m(take, oi, bi)
            w //= 2
        gi = lib.op("IADD", bi, lib.u(1010 * self.g))
        pair = lib.select_m(lib.mask(lambda l: l == 0), bv, gi)
        self.stg(pair, self.A("ARG") + 8 * s, 2)
        self.bar()
        if s == 0:
            a4 = self.ldg(self.A("ARG"), 4)
            best = self._pick(a4)
            tok = self._pick(k.coll(best, 1, 2))
            k.ufromv(7, tok, 1)
            k.result(7)
        k.exit()
        return k

    def _pick(self, a4):
        """(v0, i0, v1, i1), i0 < i1: the second wins only when strictly greater -> (v, i) in lanes 0, 1."""
        lib = self.lib
        hi = lib.shfl(a4, lib.lanes(lambda l: (l + 2) % NL))
        gt = lib.op("ISUB", lib.u(0), lib.op("FCMPGT", lib.bcast(a4, 2), lib.bcast(a4, 0)))
        return lib.select_m(gt, hi, a4)


def build(model=None, dbg=False):
    model = model or V.Model()
    prog = Program(model, dbg).build_images()
    graph = [("embed", {(d, s): Gen(prog, d, s, "embed").kernel_embed() for d in range(TP) for s in range(NSM)}),
             ("layer", {(d, s): Gen(prog, d, s, "layer").kernel_layer() for d in range(TP) for s in range(NSM)}),
             ("head", {(d, s): Gen(prog, d, s, "head").kernel_head() for d in range(TP) for s in range(NSM)})]
    code = [(name, {key: kern.assemble() for key, kern in ks.items()}) for name, ks in graph]
    prog.finish_images()
    return model, prog, graph, code


def load_images(mach, prog):
    for d, mem in enumerate(prog.images if hasattr(prog, "images") else prog.mem):
        for addr, blob in mem.items():
            mach.dies[d].mem[addr:addr + len(blob)] = blob


def launches(nl):
    """The decode step's launch sequence: embed, the layer kernel nl times, the head."""
    return ["embed"] + ["layer"] * nl + ["head"]


def _cmp(name, got, want, pos, L, quiet=False):
    got = np.asarray(got, dtype=np.uint32)
    want = G.bits(np.asarray(want, dtype=F)).reshape(-1)
    bad = np.nonzero(got != want)[0]
    if len(bad) and not quiet:
        i = bad[0]
        print(f"  pos {pos} L{L} {name}: {len(bad)}/{len(want)} differ; first [{i}] machine "
              f"{got[i].view(F) if hasattr(got[i], 'view') else got[i]} {np.uint32(got[i]).view(F)} golden {want[i].view(F)}")
    return len(bad) == 0


def check(npos=3, dbg=False, layers=None, stop=True):
    model, prog, graph, code = build(dbg=dbg)
    kc = dict(code)
    prompt, _ = V.prompt_and_expected()
    tokens = prompt[:npos]
    mach = Machine(nd=TP, nsm=NSM, nl=NL, mem_bytes=prog.mem_bytes, L=L16)
    load_images(mach, prog)
    gm = V.Model()
    st = gm.new_state()
    isa.FP_ERR[0] = 0
    ok = True
    perm = ab_perm()
    nidx = [0]
    nl = model.L if layers is None else layers
    for pos, tok in enumerate(tokens):
        tr = {}
        logits = gm.decode_token(tok, pos, st, tr)
        gold_tok = int(np.argmax(logits))
        mach.launch(kc["embed"], tok, pos)
        for L in range(nl):
            mach.launch(kc["layer"], tok, pos)
            good = True
            for d in range(TP):
                mem = mach.dies[d].mem
                x = mem[prog.a["X"]:prog.a["X"] + 2560].view(np.uint32)
                pre = mem[prog.a["PRE"]:prog.a["PRE"] + 16].view(np.uint32)
                good &= _cmp(f"die{d} h", x, np.asarray(tr[f"block{L}"], dtype=F).reshape(-1)[perm], pos, L)
                good &= _cmp(f"die{d} pre", pre, tr[f"pre{L}"], pos, L)
            if dbg and f"L{L}.index_scores" in tr:
                sc_ = np.asarray(tr[f"L{L}.index_scores"], dtype=np.float64).astype(F)
                b_ = prog.a["DBG"] + 4096 * L + 640 * 6
                got_ = mach.dies[0].mem[b_:b_ + 4 * len(sc_)].view(np.uint32)
                ok_i = _cmp("index_scores", got_, sc_, pos, L)
                nidx[0] += len(sc_)
                good &= ok_i
            if dbg and not good:
                dmem = mach.dies[0].mem
                base = prog.a["DBG"] + 4096 * L
                rd = lambda slot, n: dmem[base + 640 * slot:base + 640 * slot + 4 * n].view(np.uint32)  # noqa: E731
                def ab160(slot):
                    v = dmem[base + 640 * slot:base + 640 * slot + 640].view(np.uint32)
                    return np.concatenate([v[:128], v[128:160]])
                _cmp("attn_norm", ab160(0), tr[f"L{L}.attn_norm"], pos, L)
                _cmp("attn", ab160(1), tr[f"L{L}.attn"], pos, L)
                _cmp("ffn_norm", ab160(2), tr[f"L{L}.ffn_norm"], pos, L)
                _cmp("ffn", ab160(3), tr[f"L{L}.ffn"], pos, L)
                print("   router", rd(7, 12).view(F), np.asarray(tr[f"L{L}.router"], F))
                print("   experts", dmem[base + 640 * 7 + 512: base + 640 * 7 + 512 + 24].view(np.uint32), tr[f"L{L}.experts"])
            if not good:
                ok = False
                if stop:
                    print(f"pos {pos} layer {L}: MISMATCH")
                    break
        else:
            if layers is None:
                mach.launch(kc["head"], tok, pos)
                got = mach.dies[0].sms[0].result
                print(f"pos {pos} token {tok}: machine {got} golden {gold_tok}",
                      "OK" if got == gold_tok else "MISMATCH", flush=True)
                ok &= got == gold_tok
            else:
                print(f"pos {pos}: layers 0..{nl - 1} bit-exact" if ok else f"pos {pos}: mismatches", flush=True)
            continue
        break
    print("FP fail-closed lanes:", isa.FP_ERR[0], " index scores compared:", nidx[0])
    ok &= isa.FP_ERR[0] == 0
    st_ = {k_: sum(sm.stats.get(k_, 0) for sm in mach.sms()) for k_ in ("instr", "tc_lines", "bd_lines")}
    print("stats (all SMs, all steps)", st_, "peak vregs", max(kern.peak for _, ks in graph for kern in ks.values()))
    print("kernel words", {name: max(len(c) for c in kc_.values()) for name, kc_ in code})
    return ok


def link(code):
    """Place every kernel at one entry PC on every SM (the command processor broadcasts the PC); relocate the
    kernel-relative branch targets."""
    keys = sorted(code[0][1])
    images = {key: [] for key in keys}
    entries = {}
    pc = 0
    for name, kc in code:
        n = max(len(c) for c in kc.values())
        entries[name] = pc
        for key in keys:
            words = []
            for w in kc[key]:
                op = (w >> 56) & 0xFF
                if op in (isa.OPS["BRA"], isa.OPS["BNZ"]):
                    w = (w & ~0xFFFFFFFF) | ((w & 0xFFFFFFFF) + pc)
                words.append(w)
            images[key] += words + [0] * (n - len(words))
        pc += n
    return images, entries


def emit(out, ngen=3, nprompt=None):
    """prog_d{d}_s{s}.hex, cmd_d{d}.hex (LAUNCH embed, 40 x LAUNCH layer, LAUNCH head, END), die{d}.bin,
    expected.json -- the file set of qwen_hbm.emit."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    model, prog, graph, code = build()
    prompt, oracle = V.prompt_and_expected()
    if nprompt:
        prompt = prompt[:nprompt]                 # a shorter teacher-forced prefix (RTL simulation time)
    images, entries = link(code)
    for (d, s), words in images.items():
        (out / f"prog_d{d}_s{s}.hex").write_text("\n".join(f"{w:016x}" for w in words) + "\n")
    seq = [(nm, entries[nm]) for nm in launches(model.L)]
    for d in range(TP):
        cmds = [(1 << 60) | (((1 << NSM) - 1) << 44) | pc for _, pc in seq] + [2 << 60]
        (out / f"cmd_d{d}.hex").write_text("\n".join(f"{c:016x}" for c in cmds) + "\n")
        img = np.zeros(prog.mem_bytes, dtype=np.uint8)
        for addr, blob in prog.mem[d].items():
            img[addr:addr + len(blob)] = blob
        (out / f"die{d}.bin").write_bytes(img.tobytes())
    gm = V.Model()
    st = gm.new_state()
    steps, tok = [], None
    for pos in range(len(prompt) + ngen - 1):
        inp = prompt[pos] if pos < len(prompt) else tok
        tok = int(np.argmax(gm.decode_token(inp, pos, st)))
        steps.append(dict(pos=pos, input=int(inp), next=tok))
    assert len(steps) <= CTX, f"the program serves {CTX} positions"
    meta = dict(schema="opentallas.gpu_sys.v41_hbm_emit.v1",
                golden="tools/hdc_golden_v41.py Model() HDC_V41_ARITH=chunk8 HDC_V41_FUSE=''",
                prompt=[int(t) for t in prompt], oracle_generated=[int(t) for t in oracle], steps=steps,
                entries=[[nm, pc] for nm, pc in seq], kernel_words={n: max(len(c) for c in kc.values()) for n, kc in code},
                imem_words=max(len(w) for w in images.values()), mem_bytes=int(prog.mem_bytes), tp=TP, nsm=NSM, nl=NL,
                ctx=CTX, layout=prog.a)
    (out / "expected.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--npos", type=int, default=3)
    ap.add_argument("--layers", type=int)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--emit")
    ap.add_argument("--ngen", type=int, default=3)
    a = ap.parse_args()
    if a.emit:
        meta = emit(a.emit, a.ngen)
        print(json.dumps({k_: meta[k_] for k_ in ("kernel_words", "imem_words", "mem_bytes")}),
              [st_["next"] for st_ in meta["steps"]])
    if a.check:
        sys.exit(0 if check(a.npos, a.debug, a.layers) else 1)
