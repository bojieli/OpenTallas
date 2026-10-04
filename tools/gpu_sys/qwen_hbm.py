#!/usr/bin/env python3
"""Qwen3 HBM comparator, reduced shape: the decode step lowered to OTG-1 kernels for the GPU-organised system
(2 dies TP2, 2 SMs per die, 16-lane exact tensor core per SM, 128-lane SIMT), its HBM images, and a
functional check against the golden.

Golden: tools/hdc_golden.py, Model(groups=GROUPS, tp=2).decode_token_tp on the reduced Qwen3 vehicle
(build/models/qwen3-reduced-v1), default arithmetic (R-ARITH chunk-8 sums, FP8 E4M3 KV cache).  GROUPS = 256
is the golden's K-split parameter: it gives every weight matvec a split that is a multiple of the 16-lane
tensor core (qkv 128, o 64, gate/up 64, down 64, lm_head 16) and the attention splits (16, 256); the golden
emits the oracle's token 1073 at position 15 at this setting (checked by --check).

    python3 tools/gpu_sys/qwen_hbm.py --check            # functional machine vs golden, every position
    python3 tools/gpu_sys/qwen_hbm.py --emit DIR         # program + HBM images + expected tokens for the RTL
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
from asm import Kernel  # noqa: E402
from machine import Machine  # noqa: E402

F = np.float32
GROUPS = 256
TP = 2
NSM = 2
NL = 128
L = 16
CTX = 32
SIGN = 0x80000000
NEG_BIG = int(np.float32(-3.0e38).view(np.uint32))

# shared-memory map (bytes)
XS = 0x0000          # x staging for the tensor core's x store
TCR = 0x1000         # tensor-core results (<= 1024 rows)


def fbits(x):
    return int(np.asarray(x, dtype=F).view(np.uint32))


# ------------------------------------------------------------------------------------------------ lowering lib
class Lib:
    """Golden primitives as OTG-1 sequences (ordinary GPU instructions; the recipes of
    tools/qwen_hbm_complete_isa.py)."""

    def __init__(self, k: Kernel):
        self.k = k
        self.idx = {}

    def c(self, x):
        return self.k.fconst(x)

    def u(self, bits):
        return self.k.const(bits)

    def lane(self):
        return self.k.laneid()

    def index(self, key, fn):
        """A cached lane-index vector built from LANEID with ordinary integer ops: fn(lib, lane) -> vreg."""
        if key not in self.idx:
            self.idx[key] = fn(self, self.lane())
        return self.idx[key]

    def op(self, name, a, b=None):
        return self.k.op(name, a, b)

    def add(self, a, b):
        return self.op("FADD", a, b)

    def mul(self, a, b):
        return self.op("FMUL", a, b)

    def neg(self, a):
        return self.op("XOR", a, self.u(SIGN))

    def select(self, pred, yes, no):
        mask = self.op("ISUB", self.u(0), pred)
        return self.op("XOR", no, self.op("AND", mask, self.op("XOR", yes, no)))

    def shfl(self, a, idx):
        return self.k.shfl(a, idx)

    def bcast(self, a, lane_no):
        return self.shfl(a, self.u(lane_no))

    # lane-index helpers
    def lane_plus(self, j):
        return self.index(("plus", j), lambda s, ln: s.op("IADD", ln, s.u(j)))

    def lane_xor(self, j):
        return self.index(("xor", j), lambda s, ln: s.op("XOR", ln, s.u(j)))

    def lane_and(self, m):
        return self.index(("and", m), lambda s, ln: s.op("AND", ln, s.u(m)))

    def lane_lt(self, n):
        """0/1 predicate lane < n."""
        return self.index(("lt", n), lambda s, ln: s.op("ULT", ln, s.u(n)))

    # special functions (hdc_golden)
    def rsqrt(self, v):
        half = self.mul(v, self.c(0.5))
        y = self.op("ISUB", self.u(0x5F3759DF), self.op("SHR", v, self.u(1)))
        for _ in range(3):
            y = self.mul(y, self.add(self.c(1.5), self.neg(self.mul(half, self.mul(y, y)))))
        return y

    def reciprocal(self, d):
        seed = self.u(0x7EF311C7)
        over = self.op("AND", self.op("UGT", d, seed), self.op("ULT", d, self.u(0x7F800000)))
        y = self.select(over, self.u(0), self.op("ISUB", seed, d))
        for _ in range(3):
            y = self.mul(y, self.add(self.c(2.0), self.neg(self.mul(d, y))))
        return y

    def exp(self, x):
        x = self.select(self.op("FCMPGT", x, self.c(G.EXP_MIN)), x, self.c(G.EXP_MIN))
        x = self.select(self.op("FCMPGT", x, self.c(G.EXP_MAX)), self.c(G.EXP_MAX), x)
        t = self.mul(x, self.c(G.LOG2E))
        n = self.add(self.add(t, self.c(G.MAGIC)), self.neg(self.c(G.MAGIC)))
        r = self.add(self.add(x, self.neg(self.mul(n, self.c(G.LN2_HI)))), self.neg(self.mul(n, self.c(G.LN2_LO))))
        p = self.c(G.EXP_POLY[0])
        for cc in G.EXP_POLY[1:]:
            p = self.add(self.mul(p, r), self.c(cc))
        return self.op("IADD", p, self.op("SHL", self.op("F2I", n), self.u(23)))

    def silu(self, g):
        return self.mul(g, self.reciprocal(self.add(self.exp(self.mul(g, self.c(-1.0))), self.c(1.0))))

    def seg_sum8(self, v, seg):
        """R-ARITH sum (hdc_golden.reduce_chunked) of every aligned `seg`-lane segment of v (lanes past the
        valid length must already be +0): chunks of 8 sequential from +0 at lanes 8c, then the pairwise tree
        over the segment's chunk sums (zero padding beyond the golden's power of two adds +0, exactly).
        Returns the segment sum broadcast over the segment."""
        acc = self.add(self.u(0), v)
        for j in range(1, 8):
            acc = self.add(acc, self.shfl(v, self.lane_plus(j)))
        w = 8
        while w < seg:
            acc = self.add(acc, self.shfl(acc, self.lane_plus(w)))
            w *= 2
        return self.shfl(acc, self.lane_and(~(seg - 1) & 0xFFFFFFFF))

    def rmsnorm_seg(self, x, gamma, n, seg):
        """rmsnorm over each seg-lane segment (n valid elements per segment = seg)."""
        ss = self.seg_sum8(self.mul(x, x), seg)
        r = self.rsqrt(self.add(self.mul(ss, self.c(1.0 / n)), self.c(1e-6)))
        return self.mul(self.mul(x, r), gamma)


# ------------------------------------------------------------------------------------------------ the program
class Layout:
    """Die-global HBM byte addresses (each die holds its own TP slice; the layout is identical per die)."""

    def __init__(self, cfg):
        self.cur = 0
        self.a = {}
        H, V, nl = cfg["hidden_size"], cfg["vocab_size"], cfg["num_hidden_layers"]
        self.put("EMB", V * H * 4)
        self.put("ROPE_C", CTX * 8 * 4)
        self.put("ROPE_S", CTX * 8 * 4)
        self.put("FNORM", H * 4)
        for L_ in range(nl):
            for n, sz in (("GIN", H * 4), ("GPOST", H * 4), ("QN", 64), ("KN", 64), ("KC", 16 * CTX), ("VC", CTX * 16)):
                self.put(f"L{L_}.{n}", sz)
        for n, sz in (("X", H * 4), ("QKV", 96 * 4), ("ATT", 64 * 4), ("OPART", 128 * 4), ("ORED", 128 * 4),
                      ("GU", 384 * 4), ("DPART", 128 * 4), ("DRED", 128 * 4), ("ARG", 16)):
            self.put(n, sz)

    def put(self, name, size):
        self.cur = (self.cur + 127) // 128 * 128
        self.a[name] = self.cur
        self.cur += size

    def __getitem__(self, k):
        return self.a[k]


def mat_lines(w, split):
    """Bulk-copy weight lines of one SM's row slice, the lockstep (rb, g, t, slot) order of ot_gpu_issue:
    16 BF16 per 32-byte line, lane j of group g = chunk g*16+j at k-step t."""
    R, K = w.shape
    C, c = split, K // split
    Gn = -(-C // L)
    wb = (np.asarray(G.to_bf16(w), dtype=F).view(np.uint32) >> 16).astype(np.uint16)
    out = []
    for rb in range(0, R, 8):
        for g in range(Gn):
            for t in range(c):
                for s in range(8):
                    r = rb + s
                    if r >= R:
                        continue
                    line = np.zeros(L, dtype=np.uint16)
                    for j in range(L):
                        ch = g * L + j
                        if ch < C:
                            line[j] = wb[r, ch * c + t]
                    out.append(line)
    return np.concatenate(out).view(np.uint8), Gn, c


class Program:
    def __init__(self, model: G.Model):
        self.m = model
        self.cfg = model.cfg
        self.lay = Layout(self.cfg)
        self.mats = {}           # name -> (die, sm) -> (addr, g, c, rows)
        self.images = [None, None]

    # ----------------------------------------------------------------- HBM images
    def build_images(self):
        m, cfg, lay = self.m, self.cfg, self.lay
        H, V = cfg["hidden_size"], cfg["vocab_size"]
        imgs = []
        cur_end = lay.cur
        weights_at = (cur_end + 4095) // 4096 * 4096
        for d in range(TP):
            sl = m.die_slices(d)
            mem = {}
            def wr(addr, arr):
                mem[addr] = np.ascontiguousarray(arr).reshape(-1).view(np.uint8).copy()
            wr(lay["EMB"], m.w["model.embed_tokens.weight"].astype(F))
            cs = [G.rope_tables(p, m.hd, m.theta) for p in range(CTX)]
            wr(lay["ROPE_C"], np.stack([c_[0] for c_ in cs]).astype(F))
            wr(lay["ROPE_S"], np.stack([c_[1] for c_ in cs]).astype(F))
            wr(lay["FNORM"], m.w["model.norm.weight"].astype(F))
            wcur = weights_at
            def put_mat(name, w, split, rows_per_sm):
                nonlocal wcur
                for s in range(NSM):
                    blob, gn, c = mat_lines(w[s * rows_per_sm:(s + 1) * rows_per_sm], split)
                    wr(wcur, blob)
                    self.mats.setdefault(name, {})[(d, s)] = (wcur, gn, c, rows_per_sm)
                    wcur = (wcur + len(blob) + 127) // 128 * 128
            for L_ in range(m.layers):
                wr(lay[f"L{L_}.GIN"], m.lw(L_, "input_layernorm.weight").astype(F))
                wr(lay[f"L{L_}.GPOST"], m.lw(L_, "post_attention_layernorm.weight").astype(F))
                wr(lay[f"L{L_}.QN"], m.lw(L_, "self_attn.q_norm.weight").astype(F))
                wr(lay[f"L{L_}.KN"], m.lw(L_, "self_attn.k_norm.weight").astype(F))
                qw, kw, vw = (m.lw(L_, f"self_attn.{n}_proj.weight") for n in "qkv")
                qkv = np.concatenate([qw[sl["q_rows"]], kw[sl["kv_rows"]], vw[sl["kv_rows"]]])
                put_mat(f"L{L_}.qkv", qkv, G.split_for(96, H, GROUPS), 48)
                ow = m.lw(L_, "self_attn.o_proj.weight")[:, sl["q_rows"]]
                put_mat(f"L{L_}.o", ow, G.split_for(128, 64, GROUPS), 64)
                gu = np.concatenate([m.lw(L_, "mlp.gate_proj.weight")[sl["ff"]], m.lw(L_, "mlp.up_proj.weight")[sl["ff"]]])
                put_mat(f"L{L_}.gu", gu, G.split_for(384, H, GROUPS), 192)
                dw = m.lw(L_, "mlp.down_proj.weight")[:, sl["ff"]]
                put_mat(f"L{L_}.down", dw, G.split_for(128, 192, GROUPS), 64)
            lm = m.w["lm_head.weight"][sl["vocab"]]
            put_mat("lm", lm, G.split_for(2048, H, GROUPS), 1024)
            imgs.append((mem, wcur))
        self.mem_bytes = max(e for _, e in imgs)
        self.images = [mem for mem, _ in imgs]
        return self.images

    # ----------------------------------------------------------------- kernels
    def _tc_matvec(self, k, lib, xregs, n_in, name, d, s):
        """x (list of registers covering n_in elements) -> BF16 -> SMEM staging -> x-store words -> MMA ->
        results at SMEM TCR (rows of this SM)."""
        addr, gn, c, rows = self.mats[name][(d, s)]
        for i, xr in enumerate(xregs):
            cnt = min(NL, n_in - i * NL)
            k.sts(lib.op("CVTBF16", xr), 8, XS + i * NL * 4, cnt)
        stride = lib.index(("mul4c", c), lambda s_, ln: s_.op("IMUL", ln, s_.u(4 * c)))
        for g in range(gn):
            for t in range(c):
                k.tcx(k.ldsx(stride, XS + (g * L * c + t) * 4), g * c + t)
        k.umovi(4, addr)
        k.umovi(5, TCR)
        k.tcmma(4, 5, gn, c, rows)
        k.tcwait()
        return rows

    def _store_rows(self, k, rows, gaddr):
        """TC results (SMEM TCR, `rows` FP32) -> die-global gaddr."""
        for i in range(0, rows, NL):
            cnt = min(NL, rows - i)
            v = k.lds(8, TCR + i * 4, cnt)            # UR8 = 0: SMEM absolute
            k.stg(v, 6, gaddr + i * 4, 4, cnt)

    def kernel_embed(self, d, s):
        k = Kernel(f"embed.d{d}.s{s}")
        k.umovi(6, 0)
        k.umovi(8, 0)
        if s == 0:
            k.umuli(7, 0, 128 * 4)
            x = k.ldg(7, self.lay["EMB"], 4, 128)
            k.stg(x, 6, self.lay["X"], 4, 128)
            k.membar()
        k.exit()
        return k

    def kernel_layer(self, L_, d, s):
        lay = self.lay
        k = Kernel(f"L{L_}.d{d}.s{s}")
        lib = Lib(k)
        k.umovi(6, 0)                 # UR6 = 0: absolute addressing base
        k.umovi(8, 0)
        # LDS/STS address = UR[a] + imm: SMEM accesses use UR8 = 0
        x = k.ldg(6, lay["X"], 4, 128)
        gin = k.ldg(6, lay[f"L{L_}.GIN"], 4, 128)
        h = lib.rmsnorm_seg(x, gin, 128, 128)
        rows = self._tc_matvec(k, lib, [h], 128, f"L{L_}.qkv", d, s)
        self._store_rows(k, rows, lay["QKV"] + s * 48 * 4)
        k.membar()
        k.bar()
        qkv = k.ldg(6, lay["QKV"], 4, 96)
        # head norms: q heads at lanes 0..63, the k head at 64..79 (gamma: qn tiled below 64, kn above)
        qn = k.ldg(6, lay[f"L{L_}.QN"], 4, 16)
        kn = k.ldg(6, lay[f"L{L_}.KN"], 4, 16)
        l16 = lib.lane_and(15)
        gam = lib.select(lib.lane_lt(64), lib.shfl(qn, l16), lib.shfl(kn, l16))
        valid80 = lib.op("ISUB", lib.u(0), lib.lane_lt(80))
        qk = lib.op("AND", qkv, valid80)
        qk = lib.rmsnorm_seg(qk, gam, 16, 16)
        # RoPE: lane p = l % 16; partner l ^ 8; C1 = cos[p % 8]; S1 = -sin[p] (p < 8) or sin[p - 8] (p >= 8)
        k.umuli(9, 1, 8 * 4)
        cosr = k.ldg(9, lay["ROPE_C"], 4, 8)
        sinr = k.ldg(9, lay["ROPE_S"], 4, 8)
        l8 = lib.lane_and(7)
        c1 = lib.shfl(cosr, l8)
        sn = lib.shfl(sinr, l8)
        lowhalf = lib.op("ULT", lib.lane_and(8), lib.u(1))           # 1 when (l & 8) == 0
        s1 = lib.op("XOR", sn, lib.op("SHL", lowhalf, lib.u(31)))
        partner = lib.shfl(qk, lib.lane_xor(8))
        qkr = lib.add(lib.mul(qk, c1), lib.mul(partner, s1))
        if s == 0:
            # KV append (this die's KV head): K k-major [16][CTX] E4M3, V [CTX][16] E4M3
            kb = lib.op("CVTE4M3", lib.shfl(qkr, lib.lane_plus(64)))
            vb = lib.op("CVTE4M3", lib.shfl(qkv, lib.lane_plus(80)))
            k.umovi(15, CTX)
            k.stg(kb, 1, lay[f"L{L_}.KC"], 1, 16, strided=True)        # addr = pos + KC + lane * CTX
            k.umuli(10, 1, 16)
            k.stg(vb, 10, lay[f"L{L_}.VC"], 1, 16)
            k.membar()
        k.bar()
        # attention: this SM's two heads hl = 2s, 2s+1; score lanes (h2, t) = h2*32 + t
        qb = lib.op("CVTBF16", qkr)
        kreg = [k.ldg(6, lay[f"L{L_}.KC"] + i * 128, 1, 128) for i in range(4)]
        prods = []
        for cdim in range(16):
            ki = lib.index(("kidx", cdim), lambda s_, ln, cd=cdim: s_.op("IADD", s_.op("AND", ln, s_.u(31)), s_.u((cd % 4) * 32)))
            qi = lib.index(("qidx", s, cdim), lambda s_, ln, cd=cdim: s_.op("IADD", s_.op("SHL", s_.op("SHR", ln, s_.u(5)), s_.u(4)), s_.u((2 * s) * 16 + cd)))
            prods.append(lib.mul(lib.shfl(kreg[cdim // 4], ki), lib.shfl(qb, qi)))
        while len(prods) > 1:
            prods = [lib.add(prods[i], prods[i + 1]) for i in range(0, len(prods), 2)]
        sc = lib.mul(prods[0], lib.c(1.0 / np.sqrt(16)))
        tpos = lib.lane_and(31)
        pos1 = lib.op("IADD", k.movu(1), lib.u(1))
        valid = lib.op("AND", lib.op("ULT", tpos, pos1), lib.lane_lt(64))
        vmask = lib.op("ISUB", lib.u(0), valid)
        scm = lib.select(valid, sc, lib.u(NEG_BIG))
        mx = scm
        for j in (16, 8, 4, 2, 1):
            o = lib.shfl(mx, lib.lane_xor(j))
            mx = lib.select(lib.op("FCMPGT", o, mx), o, mx)
        e = lib.op("AND", lib.exp(lib.add(scm, lib.neg(mx))), vmask)
        z = lib.seg_sum8(e, 32)
        z = lib.select(lib.lane_lt(64), z, lib.c(1.0))     # idle segments: keep every lane finite (fail-closed FP)
        rz = lib.reciprocal(z)
        eb = lib.op("CVTBF16", e)
        vreg = [k.ldg(6, lay[f"L{L_}.VC"] + i * 128, 1, 128) for i in range(4)]
        pv = []
        for t in range(CTX):
            vi = lib.index(("vidx", t), lambda s_, ln, tt=t: s_.op("IADD", s_.op("AND", ln, s_.u(15)), s_.u((tt % 8) * 16)))
            ei = lib.index(("eidx", t), lambda s_, ln, tt=t: s_.op("IADD", s_.op("SHL", s_.op("SHR", ln, s_.u(4)), s_.u(5)), s_.u(tt)))
            pv.append(lib.mul(lib.shfl(vreg[t // 8], vi), lib.shfl(eb, ei)))
        while len(pv) > 1:
            pv = [lib.add(pv[i], pv[i + 1]) for i in range(0, len(pv), 2)]
        ri = lib.index(("ridx",), lambda s_, ln: s_.op("SHL", s_.op("SHR", ln, s_.u(4)), s_.u(5)))
        att = lib.mul(pv[0], lib.shfl(rz, ri))
        k.stg(att, 6, lay["ATT"] + s * 32 * 4, 4, 32)
        k.membar()
        k.bar()
        att = k.ldg(6, lay["ATT"], 4, 64)
        rows = self._tc_matvec(k, lib, [att], 64, f"L{L_}.o", d, s)
        self._store_rows(k, rows, lay["OPART"] + s * 64 * 4)
        k.membar()
        k.bar()
        if s == 0:
            red = k.coll(k.ldg(6, lay["OPART"], 4, 128), 0, 128)
            k.stg(red, 6, lay["ORED"], 4, 128)
            k.membar()
        k.bar()
        x = lib.add(x, k.ldg(6, lay["ORED"], 4, 128))
        gpost = k.ldg(6, lay[f"L{L_}.GPOST"], 4, 128)
        h = lib.rmsnorm_seg(x, gpost, 128, 128)
        rows = self._tc_matvec(k, lib, [h], 128, f"L{L_}.gu", d, s)
        self._store_rows(k, rows, lay["GU"] + s * 192 * 4)
        k.membar()
        k.bar()
        act = []
        for i, cnt in ((0, 128), (128, 64)):
            gate = k.ldg(6, lay["GU"] + i * 4, 4, cnt)
            up = k.ldg(6, lay["GU"] + (192 + i) * 4, 4, cnt)
            act.append(lib.mul(lib.silu(gate), up))
        rows = self._tc_matvec(k, lib, act, 192, f"L{L_}.down", d, s)
        self._store_rows(k, rows, lay["DPART"] + s * 64 * 4)
        k.membar()
        k.bar()
        if s == 0:
            red = k.coll(k.ldg(6, lay["DPART"], 4, 128), 0, 128)
            k.stg(red, 6, lay["DRED"], 4, 128)
            k.membar()
        k.bar()
        x = lib.add(x, k.ldg(6, lay["DRED"], 4, 128))
        if s == 0:
            k.stg(x, 6, lay["X"], 4, 128)
            k.membar()
        k.exit()
        return k

    def kernel_head(self, d, s):
        lay = self.lay
        k = Kernel(f"head.d{d}.s{s}")
        lib = Lib(k)
        k.umovi(6, 0)
        k.umovi(8, 0)
        x = k.ldg(6, lay["X"], 4, 128)
        fn = k.ldg(6, lay["FNORM"], 4, 128)
        xf = lib.rmsnorm_seg(x, fn, 128, 128)
        self._tc_matvec(k, lib, [xf], 128, "lm", d, s)
        lane = lib.lane()
        bv = k.lds(8, TCR, 128)
        bi = lane
        for r in range(1, 8):
            v = k.lds(8, TCR + r * 512, 128)
            gt = lib.op("FCMPGT", v, bv)
            bv = lib.select(gt, v, bv)
            bi = lib.select(gt, lib.op("IADD", lane, lib.u(128 * r)), bi)
        bv, bi = self._argmax_lanes(lib, bv, bi, 128)
        gi = lib.op("IADD", bi, lib.u(d * 2048 + s * 1024))
        pair = lib.select(lib.lane_lt(1), bv, gi)          # lane 0 value, lane 1 global index
        k.stg(pair, 6, lay["ARG"] + s * 8, 4, 2)
        k.membar()
        k.bar()
        if s == 0:
            a4 = k.ldg(6, lay["ARG"], 4, 4)                 # v0 i0 v1 i1 (SM0, SM1)
            best = self._pick_pairs(lib, a4)
            g4 = k.coll(best, 1, 2)                          # die0 (v, i), die1 (v, i)
            tok = self._pick_pairs(lib, g4)
            k.ufromv(7, tok, 1)
            k.result(7)
        k.exit()
        return k

    def _argmax_lanes(self, lib, bv, bi, n):
        """Lane 0 ends with the maximum value and, among equal values, the lowest index."""
        w = n // 2
        while w >= 1:
            ov = lib.shfl(bv, lib.lane_plus(w))
            oi = lib.shfl(bi, lib.lane_plus(w))
            gt = lib.op("FCMPGT", ov, bv)
            lt = lib.op("FCMPGT", bv, ov)
            eq = lib.op("XOR", lib.op("OR", gt, lt), lib.u(1))
            take = lib.op("OR", gt, lib.op("AND", eq, lib.op("ULT", oi, bi)))
            bv = lib.select(take, ov, bv)
            bi = lib.select(take, oi, bi)
            w //= 2
        return bv, bi

    def _pick_pairs(self, lib, a4):
        """(v0, i0, v1, i1) in lanes 0..3, i0 < i1: the second wins only when strictly greater.  Returns
        (v, i) in lanes 0, 1."""
        hi = lib.shfl(a4, lib.lane_plus(2))
        gt = lib.op("FCMPGT", lib.bcast(a4, 2), lib.bcast(a4, 0))
        return lib.select(gt, hi, a4)

    def graph(self):
        """The decode step's kernels in stream order: name -> {(die, sm): Kernel}."""
        ks = [("embed", {(d, s): self.kernel_embed(d, s) for d in range(TP) for s in range(NSM)})]
        for L_ in range(self.m.layers):
            ks.append((f"L{L_}", {(d, s): self.kernel_layer(L_, d, s) for d in range(TP) for s in range(NSM)}))
        ks.append(("head", {(d, s): self.kernel_head(d, s) for d in range(TP) for s in range(NSM)}))
        return ks


def load_images(mach, prog):
    for d, mem in enumerate(prog.images):
        for addr, blob in mem.items():
            mach.dies[d].mem[addr:addr + len(blob)] = blob


def golden_run(model, tokens):
    cache = [[] for _ in range(model.layers)]
    out = []
    for pos, tok in enumerate(tokens):
        tr = {}
        logits = model.decode_token(tok, pos, cache, tr)
        out.append(dict(token=int(np.argmax(logits)), trace=tr))
    return out


def check(npos=None, out=None):
    model = G.Model(GROUPS, TP)
    prompt, expected = G.prompt_and_expected()
    tokens = prompt if npos is None else prompt[:npos]
    prog = Program(model)
    prog.build_images()
    graph = prog.graph()
    code = [(name, {key: kern.assemble() for key, kern in ks.items()}) for name, ks in graph]
    mach = Machine(nd=TP, nsm=NSM, nl=NL, mem_bytes=(prog.mem_bytes + 4095) // 4096 * 4096, L=L)
    load_images(mach, prog)
    gold = golden_run(model, tokens)
    ok = True
    rows = []
    for pos, tok in enumerate(tokens):
        for name, kc in code:
            mach.launch(kc, tok, pos)
            if name.startswith("L"):
                L_ = int(name[1:])
                xm = mach.dies[0].mem[prog.lay["X"]:prog.lay["X"] + 512].view(np.uint32)
                xg = np.asarray(gold[pos]["trace"][f"layer{L_}"], dtype=F).view(np.uint32)
                if not np.array_equal(xm, xg):
                    nbad = int(np.sum(xm != xg))
                    print(f"pos {pos} layer {L_}: X mismatch in {nbad} lanes")
                    ok = False
        got = mach.dies[0].sms[0].result
        print(f"pos {pos} token {tok}: machine {got} golden {gold[pos]['token']}", "OK" if got == gold[pos]["token"] else "MISMATCH")
        ok &= got == gold[pos]["token"]
        rows.append(dict(pos=pos, input=int(tok), machine=got, golden=gold[pos]["token"]))
    import isa
    print("FP fail-closed lanes:", isa.FP_ERR[0])
    ok &= isa.FP_ERR[0] == 0
    st = {k: sum(sm.stats[k] for sm in mach.sms()) for k in mach.sms()[0].stats}
    peak = max(kern.peak for _, ks in graph for kern in ks.values())
    words = {name: max(len(c) for c in kc.values()) for name, kc in code}
    print("stats", st, "peak vregs", peak, "instructions per step", words)
    if out:
        rec = dict(schema="opentallas.gpu_sys.qwen_functional.v1", tool="tools/gpu_sys/qwen_hbm.py --check",
                   golden=f"tools/hdc_golden.py Model(groups={GROUPS}, tp={TP}) decode_token_tp, default env",
                   scope="OTG-1 kernels on the functional machine (tools/gpu_sys/machine.py); every layer residual of die 0 "
                         "and the token compared bit-exactly at every position", positions=rows,
                   layer_residual_mismatches=0 if ok else None, fp_fail_closed_lanes=isa.FP_ERR[0],
                   machine_totals=st, peak_vector_registers=peak, kernel_words=words, status="pass" if ok else "fail",
                   source_sha256={str(p_.relative_to(ROOT)): hashlib.sha256(p_.read_bytes()).hexdigest()
                                  for p_ in [HERE / "isa.py", HERE / "asm.py", HERE / "machine.py", HERE / "qwen_hbm.py",
                                             ROOT / "tools/hdc_golden.py"]})
        Path(out).write_text(json.dumps(rec, indent=1) + "\n")
    return ok


def link(graph):
    """Place every kernel at one entry PC on every SM (the command processor broadcasts the PC): kernel k
    starts at the sum of the previous kernels' longest per-SM code.  Returns per-SM images and entry PCs."""
    code = [(name, {key: kern.assemble() for key, kern in ks.items()}) for name, ks in graph]
    keys = sorted(code[0][1])
    images = {key: [] for key in keys}
    entries = []
    pc = 0
    for name, kc in code:
        n = max(len(c) for c in kc.values())
        entries.append((name, pc))
        for key in keys:
            images[key] += kc[key] + [0] * (n - len(kc[key]))       # NOP padding (never reached: EXIT ends each)
        pc += n
    return images, entries, code


def emit(out, ngen=3):
    """Write everything the system-top bench needs:
      prog_d{d}_s{s}.hex   SM instruction memory (64-bit words)
      cmd_d{d}.hex         command list (LAUNCH per kernel in stream order, END)
      die{d}.bin           die-global HBM image (bytes from address 0)
      expected.json        prompt, the golden next token of every step (teacher-forced prompt, then greedy),
                           entry PCs, sizes"""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    model = G.Model(GROUPS, TP)
    prompt, oracle = G.prompt_and_expected()
    prog = Program(model)
    prog.build_images()
    images, entries, code = link(prog.graph())
    for (d, s), words in images.items():
        (out / f"prog_d{d}_s{s}.hex").write_text("\n".join(f"{w:016x}" for w in words) + "\n")
    for d in range(TP):
        cmds = [(1 << 60) | (((1 << NSM) - 1) << 44) | pc for _, pc in entries] + [2 << 60]
        (out / f"cmd_d{d}.hex").write_text("\n".join(f"{c:016x}" for c in cmds) + "\n")
        img = np.zeros((prog.mem_bytes + 4095) // 4096 * 4096, dtype=np.uint8)
        for addr, blob in prog.images[d].items():
            img[addr:addr + len(blob)] = blob
        (out / f"die{d}.bin").write_bytes(img.tobytes())
    # golden token stream: prompt teacher-forced, then greedy feedback
    cache = [[] for _ in range(model.layers)]
    steps = []
    tok = None
    for pos in range(len(prompt) + ngen - 1):
        inp = prompt[pos] if pos < len(prompt) else tok
        logits = model.decode_token(inp, pos, cache)
        tok = int(np.argmax(logits))
        steps.append(dict(pos=pos, input=int(inp), next=tok))
    meta = dict(schema="opentallas.gpu_sys.qwen_hbm_emit.v1", golden="tools/hdc_golden.py Model(groups=%d, tp=%d)" % (GROUPS, TP),
                prompt=[int(t) for t in prompt], oracle_generated=[int(t) for t in oracle], steps=steps,
                entries=entries, kernel_words={n: max(len(c) for c in kc.values()) for n, kc in code},
                imem_words=max(len(w) for w in images.values()), mem_bytes=int(img.size), tp=TP, nsm=NSM, nl=NL,
                ctx=CTX, layout=prog.lay.a)
    (out / "expected.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--npos", type=int)
    ap.add_argument("--emit")
    ap.add_argument("--out")
    ap.add_argument("--ngen", type=int, default=3)
    a = ap.parse_args()
    if a.emit:
        m = emit(a.emit, a.ngen)
        print(json.dumps({k: m[k] for k in ("entries", "imem_words", "mem_bytes")}), [st["next"] for st in m["steps"]])
    if a.check:
        sys.exit(0 if check(a.npos, a.out) else 1)
