#!/usr/bin/env python3
"""DSpark speculative decoding (DeepSeek-V4.1's built-in MTP, checkpoint mtp.0-2) on the GPU-organised HBM comparator:
OTG-1 kernels serving the commands of the DSpark control plane (rtl/gpu/dshbm/ot_dshbm_dspark_ctl.sv, branch
claude/dshbm-dspark-rtl-20261003), a Python model of the control loop driving the functional machine, and the RTL
emit.  Golden: tools/hdc_golden_v41.py Model.generate_spec / draft / dspark_* (HDC_V41_ARITH=chunk8).

THE COMMANDS -> LAUNCHES (what the ctl -> command-processor bridge issues; every launch is (entry, token, pos), the
16-bit token and position the existing LAUNCH already delivers in UR0 / UR1; nothing else is passed):

  VLAYER(L, ncol, n, toks)  for c in 0 .. ncol-1:  SWAPIN(c, L); [L == 0: EMBED(toks[c], n+c)];
                            LAYER(toks[c], n+c); SWAPOUT(c, n+c)
  VHEAD(ncol, n)            for c:  SWAPIN(c, 63); HEAD(0, n+c)          -> one RESULT (argmax) per HEAD, in order
  SEED(ncol, n)             for c:  SEED(c, n+c)
  DSTAGE(st, B, q, y)       for i in 0 .. B-1:  SWAPIN(8+i, 40+st); [st == 0: DEMB(y if i == 0 else NOISE, 0)];
                                                DSA(i, q+1+i); SWAPOUT(8+i, 0)
                            for i in 0 .. B-1:  SWAPIN(8+i, 40+st); DSB(i, q+1+i); SWAPOUT(8+i, 0)
  DHEAD(B, q)               for i:  SWAPIN(8+i, 63); DHEAD(i, q+1+i)
  MARKOV(i, d_i)            MARKOV(d_i, i)                                -> one RESULT (d_{i+1})
  (NOISE = dspark_noise_token_id mod vocab = 3519.)

A verify pass runs the one-position layer arithmetic per column in position order inside each layer (layer-major,
the golden's own forward_positions order: identical per-position bits).  Column / block-row state (residual, pre mix,
layer counter, index selection, the DSpark main-hidden parts) lives in die memory slots 0..7 (verify columns) and
8..12 (draft rows); SWAPIN / SWAPOUT move a slot to and from the layer kernels' working buffers.  Position-indexed
state (window rows, DSpark rows, compressor slot ring, compressed rows by group, token history) is never rolled back:
commit n <- n + 1 + a is the only action, rejected rows lie at positions >= n and are rewritten before any read.

    python3 tools/gpu_sys/v41_dspark.py --check --drafter forced --ngen 8
    python3 tools/gpu_sys/v41_dspark.py --check --drafter dspark --ngen 8
    python3 tools/gpu_sys/v41_dspark.py --emit DIR [--drafter forced] [--ngen 8]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v41_hbm as H  # noqa: E402

G, V, isa = H.G, H.V, H.isa
F = np.float32
NL, TP, NSM = H.NL, H.TP, H.NSM

# ---- program geometry for speculative serving (set before any kernel is generated) ----
H.CTX = 32               # positions: prompt 8 + 8 generated + a 4-draft verify + the draft block stay below 32
H.TPAD = 64              # attention list lanes per head: window 32 + selected 16 (or DSpark block 5) <= 64
H.SLOT_RING = True       # the ratio-2 compressor's open slot indexed by position (exact rollback)
# shared-memory map for TPAD 64 (the attention phase reuses the hyper-connection / tree area)
H.S_KVL = 0x1800         # [64 rows][32]
H.S_QS = 0x3C00
H.S_ES = 0x4400
H.S_EB = 0x5400
H.S_MS = 0x6400
H.S_IKS = 0x4400         # [32][32], indexer phase
H.S_DUMMY = 0x7400
H.S_SEG = 0x4000
CTX = H.CTX
PMAX, B, NST, GAMMA = 8, 5, 3, 4
NCOLSLOT = PMAX + B
DESC_G = 43              # descriptor row of the DSpark globals
L_NONE = 63


class DProgram(H.Program):
    EXTRA = 4
    EXTRA_LAYERS = (40, 41, 42)

    def build_images(self):
        super().build_images()
        m = self.m
        A = self.put
        self.CSTR = 4608
        A("COL", NCOLSLOT * self.CSTR)                       # per slot: X 2560, PRE 16, CTR 4, SEL 128, NSEL 4, MH 1920
        for st in range(NST):
            A(f"DSK{st}", CTX * 64)
            A(f"DBLK{st}", 512)
        A("ROWQ", B * 4 * 2048)
        A("ROWMIX", B * 1536)
        A("DLOG", B * 4040 * 4)
        A("YS", 640)
        mp = m.w["mtp.0.main_proj.weight"]
        mpa = self.wput("MAINPROJ", [np.concatenate([H.bd_tile(mp.q[40 * (2 * d + s):40 * (2 * d + s + 1)],
                                                               mp.e[40 * (2 * d + s):40 * (2 * d + s + 1)], False)[0]
                                                     for s in range(NSM)]) for d in range(TP)])
        self.mp_stride = len(H.bd_tile(mp.q[:40], mp.e[:40], False)[0])
        self.wr_all(A("MAINNORM", 640), m.w["mtp.0.main_norm.weight"].astype(F))
        self.wr_all(A("DNORM", 640), m.lw(42, "norm.weight").astype(F))
        wk = [m.lw(40 + st, "attn.wkv.weight") for st in range(NST)]
        dwkv = self.wput("DWKV", [H.bd_tile(np.concatenate([w.q for w in wk]), np.concatenate([w.e for w in wk]),
                                            False)[0]] * TP)
        self.wr_all(A("DKVN", 512), np.concatenate([m.lw(40 + st, "attn.kv_norm.weight") for st in range(NST)]).astype(F))
        memb = (G.bits(m.lw(42, "markov_head.embed.weight")) >> 16).astype(np.uint16)
        self.wr_all(A("MEMB", memb.size * 2), memb)
        mh = m.lw(42, "markov_head.head.weight")
        self.mhead = {}
        for s in range(NSM):
            self.mhead[s] = self.wput(f"MHEAD{s}", [H.tc_lines(mh[1010 * (2 * d + s):1010 * (2 * d + s + 1)])[0]
                                                    for d in range(TP)])
        for d in range(TP):
            for s in range(NSM):
                self.setd(d, DESC_G, f"mproj{s}", mpa + s * self.mp_stride)
            self.setd(d, DESC_G, "dwkv", dwkv)
            for st in range(NST):
                self.setd(d, 40 + st, "dsk", self.a[f"DSK{st}"])
                self.setd(d, 40 + st, "dblk", self.a[f"DBLK{st}"])
        self.CONST = (self.cur + 4095) // 4096 * 4096
        return self


# column-slot offsets
O_X, O_PRE, O_CTR, O_SEL, O_NSEL, O_MH = 0, 2560, 2576, 2592, 2720, 2724


class DGen(H.Gen):
    def load_desc(self, row=None):
        k = self.k
        if row is None:
            ctr = self.ldg(self.A("CTR"), 1)
            k.ufromv(5, ctr, 0)
            k.umuli(5, 5, 512)
            self.DESC = k.ldg(5, self.A("DESC"), 4, NL)
            return ctr
        self.DESC = self.ldg(self.A("DESC") + 512 * row)

    # ----------------------------------------------------------------- slot moves
    def kernel_swapin(self):
        """token = slot c, pos = layer L: slot c -> working buffers, CTR = L; at L = 37..39 also the slot's DSpark
        main-hidden part of the layer's input."""
        k, lib = self.k, self.lib
        if self.s == 0:
            k.umuli(5, 0, self.p.CSTR)
            C = self.A("COL")
            for j in range(5):
                self.stg(k.ldg(5, C + O_X + 512 * j, 4, NL), self.A("X") + 512 * j)
            self.stg(k.ldg(5, C + O_PRE, 4, 4), self.A("PRE"), 4)
            self.stg(k.ldg(5, C + O_SEL, 4, CTX), self.A("SEL"), CTX)
            self.stg(k.ldg(5, C + O_NSEL, 4, 1), self.A("NSEL"), 1)
            self.stg(k.movu(1), self.A("CTR"), 1)
            t = lib.op("ISUB", k.movu(1), lib.u(37))
            k.ufromv(6, lib.op("XOR", lib.op("ULT", t, lib.u(3)), lib.u(1)), 0)
            lend = k.newlabel("nomh")
            k.bnz(6, lend)
            k.push()
            h = [k.ldg(5, C + O_X + 512 * j, 4, NL) for j in range(5)]
            a = lib.add(lib.add(lib.add(h[0], h[1]), h[2]), h[3])
            bb = [lib.shfl(h[4], lib.lanes(lambda l, j=j: (l & 31) + 32 * j)) for j in range(4)]
            b = lib.add(lib.add(lib.add(bb[0], bb[1]), bb[2]), bb[3])
            k.ufromv(6, lib.op("IMUL", t, lib.u(640)), 0)
            k.uadd(5, 5, 6)
            self.k.stg(lib.bf(lib.mul(a, lib.c(0.25))), 5, C + O_MH, 4, NL)
            self.k.stg(lib.bf(lib.mul(b, lib.c(0.25))), 5, C + O_MH + 512, 4, 32)
            k.pop()
            k.label(lend)
            k.membar()
        k.exit()
        return k

    def kernel_swapout(self):
        k = self.k
        if self.s == 0:
            k.umuli(5, 0, self.p.CSTR)
            C = self.A("COL")
            for j in range(5):
                k.stg(self.ldg(self.A("X") + 512 * j), 5, C + O_X + 512 * j, 4, NL)
            k.stg(self.ldg(self.A("PRE"), 4), 5, C + O_PRE, 4, 4)
            k.stg(self.ldg(self.A("SEL"), CTX), 5, C + O_SEL, 4, CTX)
            k.stg(self.ldg(self.A("NSEL"), 1), 5, C + O_NSEL, 4, 1)
            k.membar()
        k.exit()
        return k

    def kernel_demb(self):
        """A draft block row's input: the token's embedding in every residual copy, pre = (1, 0, 0, 0)."""
        k, lib = self.k, self.lib
        if self.s == 0:
            k.umuli(8, 0, 320)
            row = k.ldg(8, self.A("EMB"), 2, NL)
            rb = lib.shfl(k.ldg(8, self.A("EMB") + 256, 2, 32), lib.lanes(lambda l: l & 31))
            for j in range(4):
                self.stg(row, self.A("X") + 512 * j)
            self.stg(rb, self.A("X") + 2048)
            self.stg(lib.select_m(lib.mask(lambda l: l == 0), lib.c(1.0), lib.u(0)), self.A("PRE"), 4)
            k.membar()
        k.exit()
        return k

    # ----------------------------------------------------------------- SEED
    def kernel_seed(self):
        """token = slot c, pos = its position: main_x = main_norm(main_proj(mh)), each stage's FP8 window row."""
        k, lib, m = self.k, self.lib, self.m
        self.load_desc(DESC_G)
        k.umuli(5, 0, self.p.CSTR)
        C = self.A("COL") + O_MH
        mh = [k.ldg(5, C + 512 * i, 4, NL if i < 3 else 96) for i in range(4)]
        self.bd_x(mh, 480)
        self.bd_mma(f"mproj{self.s}", 40, 480)
        self.stg(lib.bf(self.lds(H.S_TCR, 40)), self.A("YS") + 160 * self.g, 40)
        self.allreduce("YS", 160, lambda d, i: i // 80 == d)
        xa, xb = self.ldg(self.A("YS")), self.ldg(self.A("YS") + 512, 32)
        xa, xb = self.rms160(xa, xb, None, gaddr=self.A("MAINNORM"))
        self.bd_x([xa, xb], 160)
        self.bd_mma("dwkv", 96, 160)
        v = lib.bf(self.lds(H.S_TCR, 96))
        kv = lib.rmsnorm32(v, self.ldg(self.A("DKVN"), 96), m.eps)
        cs = self.rope_cs(absaddr=self.A("ROPEP"))
        rows = lib.qdq_fp8(self.rope(kv, cs, False, lambda l: l < 96))
        if self.s == 0:
            k.umuli(8, 1, 64)
            for st in range(NST):
                r = rows if st == 0 else lib.shfl(rows, lib.lanes(lambda l, st=st: (l + 32 * st) % NL))
                k.stg(r, 8, self.A(f"DSK{st}"), 2, 32)
            k.membar()
        k.exit()
        return k

    # ----------------------------------------------------------------- DSpark stage, phase A / B
    def kernel_dsa(self):
        """token = block row i, pos = q+1+i (CTR = the stage's layer): hyper-connection mixes, attn_norm, q and the
        block row's FP8 KV row (dspark_attention's per-row front)."""
        k, lib, s = self.k, self.lib, self.s
        self.load_desc()
        self.sts(self.zero(), H.S_ZERO, 64)
        h = self.load_h()
        pre0 = self.ldg(self.A("PRE"), 4)
        pre_a, post_a, comb_a = self.hc_mixes("attn", h)
        xa, xb = self.rms160(*self.hc_pre(h, pre0, 0), "attn_norm")
        cs, qk, kv0 = self.attn_front(xa, xb)
        qs = self.attn_q(qk, cs)
        k.umuli(8, 0, 4 * 2048)
        for v_ in range(4):
            k.stg(qs[v_], 8, self.A("ROWQ") + 2048 * self.g + 512 * v_, 4, NL)
        if s == 0:
            k.umuli(9, 0, 1536)
            for i, v in enumerate((pre_a, post_a, comb_a)):
                k.stg(v, 9, self.A("ROWMIX") + 512 * i, 4, NL)
            self.dfield(6, "dblk")
            k.umuli(9, 0, 64)
            k.uadd(6, 6, 9)
            k.stg(kv0, 6, 0, 2, 32)
        k.membar()
        k.exit()
        return k

    def kernel_dsb(self):
        """token = block row i, pos = q+1+i: attention over the DSpark window (positions 0..q) and the block's rows,
        hc_post, the stage's MoE (4 experts, top 3), hc_post."""
        k, lib, m, s = self.k, self.lib, self.m, self.s
        self.load_desc()
        self.sts(self.zero(), H.S_ZERO, 64)
        h = self.load_h()
        k.umuli(9, 0, 1536)
        pre_a, post_a, comb_a = (k.ldg(9, self.A("ROWMIX") + 512 * i, 4, NL) for i in range(3))
        k.umuli(8, 0, 4 * 2048)
        for v_ in range(4):
            self.sts(k.ldg(8, self.A("ROWQ") + 2048 * self.g + 512 * v_, 4, NL), H.S_QS + 512 * v_)
        cs = self.rope_cs("rope")
        self.dfield(6, "dsk")
        for v_ in range(CTX // 4):
            self.sts(k.ldg(6, 256 * v_, 2, NL), H.S_KVL + 512 * v_)
        for v_ in range(CTX // 4, H.TPAD // 4):
            self.sts(self.zero(), H.S_KVL + 512 * v_)
        self.dfield(6, "dblk")
        b0, b1 = k.ldg(6, 0, 2, NL), k.ldg(6, 256, 2, 32)
        k.umuli(10, 0, 0xFFFFFF80)                          # -128 i
        k.umuli(11, 1, 128)                                 # 128 (q+1+i)
        k.uadd(10, 10, 11)                                  # list slot of block row 0: q + 1
        k.sts(b0, 10, H.S_KVL, NL)
        k.sts(b1, 10, H.S_KVL + 512, 32)
        T = lib.op("IADD", lib.op("ISUB", k.movu(1), k.movu(0)), lib.u(B))
        ya, yb = self.attend_core(T, cs)
        h = self.hc_post(ya, yb, h, post_a, comb_a)
        pre_f, post_f, comb_f = self.hc_mixes("ffn", h)
        xa, xb = self.rms160(*self.hc_pre(h, pre_a, 0), "ffn_norm")
        ya, yb = self.moe(xa, xb, ne=m.dspark_n_exp, ke=m.dspark_k_exp)
        h = self.hc_post(ya, yb, h, post_f, comb_f)
        if s == 0:
            for j in range(5):
                self.stg(h[j], self.A("X") + 512 * j)
            self.stg(pre_f, self.A("PRE"), 4)
            k.membar()
        k.exit()
        return k

    # ----------------------------------------------------------------- heads
    def argmax_rows(self, get):
        """argmax over this SM's 1010 rows (get(r) -> register r), the SM pair, the dies: RESULT (lowest id on ties)."""
        k, lib, s = self.k, self.lib, self.s
        lane = lib.lane()
        bv = bi = None
        for r in range(8):
            v = get(r)
            if r == 7:
                v = lib.select_m(lib.mask(lambda l: l < 1010 - 896), v, lib.u(H.NEG_BIG))
            if r == 0:
                bv, bi = v, lane
            else:
                gm = lib.op("ISUB", lib.u(0), lib.op("FCMPGT", v, bv))
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
        self.stg(lib.select_m(lib.mask(lambda l: l == 0), bv, gi), self.A("ARG") + 8 * s, 2)
        self.bar()
        if s == 0:
            tok = self._pick(k.coll(self._pick(self.ldg(self.A("ARG"), 4)), 1, 2))
            k.ufromv(7, tok, 1)
            k.result(7)
        k.exit()
        return k

    def kernel_dhead(self):
        """token = block row i: the shared LM head on rmsnorm(hc_pre(h), mtp.2.norm); logits -> DLOG[i] (this SM's
        1010 rows)."""
        k, s = self.k, self.s
        h = self.load_h()
        pre = self.ldg(self.A("PRE"), 4)
        xa, xb = self.rms160(*self.hc_pre(h, pre, 0), None, gaddr=self.A("DNORM"))
        self.tc_stage([xa, xb])
        self.tc_words(2)
        k.umovi(6, self.p.head[s])
        k.umovi(7, H.S_TCR)
        k.tcmma(6, 7, 2, 8, 1010)
        k.tcwait()
        k.umuli(8, 0, 4040 * 4)
        for r in range(8):
            cnt = NL if r < 7 else 1010 - 896
            k.stg(self.lds(H.S_TCR + 512 * r, cnt), 8, self.A("DLOG") + 4040 * self.g + 512 * r, 4, cnt)
        k.membar()
        k.exit()
        return k

    def kernel_markov(self):
        """token = d_i, pos = i: logits_i + markov_head(embed(d_i)) -> argmax d_{i+1}."""
        k, lib, s = self.k, self.lib, self.s
        k.umuli(8, 0, 64)
        e = k.ldg(8, self.A("MEMB"), 2, 32)
        self.tc_stage([e])
        self.tc_words(1)
        k.umovi(6, self.p.mhead[s])
        k.umovi(7, H.S_TCR)
        k.tcmma(6, 7, 1, 8, 1010)
        k.tcwait()
        k.umuli(9, 1, 4040 * 4)

        def get(r):
            lg = k.ldg(9, self.A("DLOG") + 4040 * self.g + 512 * r, 4, NL if r < 7 else 1010 - 896)
            return lib.add(lg, self.lds(H.S_TCR + 512 * r))
        return self.argmax_rows(get)


KINDS = ("swapin", "swapout", "embed", "layer", "head", "seed", "demb", "dsa", "dsb", "dhead", "markov")


def build(model=None):
    model = model or V.Model()
    prog = DProgram(model).build_images()
    graph = []
    for kind in KINDS:
        ks = {}
        for d in range(TP):
            for s in range(NSM):
                gen = DGen(prog, d, s, kind)
                ks[(d, s)] = getattr(gen, f"kernel_{kind}")()
        graph.append((kind, ks))
    code = [(name, {key: kern.assemble() for key, kern in ks.items()}) for name, ks in graph]
    prog.finish_images()
    return model, prog, graph, code


# ================================================================================================ the control loop
NOISE = None


def expand(cmd):
    """One control-plane command -> the launch list (kind, token, pos)."""
    op = cmd["op"]
    if op == "VLAYER":
        L, n, toks = cmd["idx"], cmd["pos"], cmd["toks"]
        out = []
        for c in range(cmd["ncol"]):
            out.append(("swapin", c, L))
            if L == 0:
                out.append(("embed", toks[c], n + c))
            out += [("layer", toks[c], n + c), ("swapout", c, n + c)]
        return out
    if op == "VHEAD":
        return [x for c in range(cmd["ncol"]) for x in (("swapin", c, L_NONE), ("head", 0, cmd["pos"] + c))]
    if op == "SEED":
        return [("seed", c, cmd["pos"] + c) for c in range(cmd["ncol"])]
    if op == "DSTAGE":
        st, q, y = cmd["idx"], cmd["pos"], cmd["tok1"]
        out = []
        for i in range(B):
            out.append(("swapin", PMAX + i, 40 + st))
            if st == 0:
                out.append(("demb", y if i == 0 else NOISE, 0))
            out += [("dsa", i, q + 1 + i), ("swapout", PMAX + i, 0)]
        for i in range(B):
            out += [("swapin", PMAX + i, 40 + st), ("dsb", i, q + 1 + i), ("swapout", PMAX + i, 0)]
        return out
    if op == "DHEAD":
        return [x for i in range(B) for x in (("swapin", PMAX + i, L_NONE), ("dhead", i, cmd["pos"] + 1 + i))]
    if op == "MARKOV":
        return [("markov", cmd["tok1"], cmd["idx"])]
    raise ValueError(op)


class Engine:
    """The SM cluster behind the bridge: runs a command's launches on the functional machine, returns RESULTs."""

    def __init__(self, kc, mach, prog, log=None):
        self.kc, self.mach, self.prog = kc, mach, prog
        self.log = log
        self.launches = 0

    def logits(self):
        return np.concatenate([self.mach.dies[d].sms[s].smem[H.S_TCR // 4:H.S_TCR // 4 + 1010]
                               for d in range(TP) for s in range(NSM)]).view(F)

    def run(self, cmd, want_logits=False):
        res, lgs = [], []
        for kind, tok, pos in expand(cmd):
            self.mach.launch(self.kc[kind], tok, pos)
            self.launches += 1
            if self.log is not None:
                self.log.append((kind, tok, pos))
            if kind in ("head", "markov"):
                res.append(self.mach.dies[0].sms[0].result)
                if want_logits and kind == "head":
                    lgs.append(self.logits().copy())
        return res, lgs


def ctl_loop(eng, prompt, ngen, gamma, forced=None, cmdlog=None, maxpos=128):
    """ot_dshbm_dspark_ctl's loop: prefill, then draft / verify / accept / commit (n <- n + 1 + a)."""
    def issue(op, idx=0, ncol=1, pos=0, toks=(), tok1=0, want=False):
        cmd = dict(op=op, idx=idx, ncol=ncol, pos=pos, toks=list(toks), tok1=tok1)
        res, lgs = eng.run(cmd, want)
        if cmdlog is not None:
            cmdlog.append(dict(cmd, results=res))
        return res, lgs
    nl = eng.prog.m.L
    for p, t in enumerate(prompt):
        for L in range(nl):
            issue("VLAYER", L, 1, p, [t])
        r, lgs = issue("VHEAD", 0, 1, p, [t], want=True)
        issue("SEED", 0, 1, p, [t])
    n = len(prompt)
    y = r[0]
    out, rows, steps = [y], [lgs[0]], []
    step = 0
    while len(out) < ngen:
        q = n - 1
        g = min(gamma, maxpos - 2 - q)
        d = []
        dlg = []
        if g > 0:
            if forced is not None:
                d = forced(step, y, q, g)
            else:
                for st in range(NST):
                    issue("DSTAGE", st, B, q, tok1=y)
                issue("DHEAD", 0, B, q, tok1=y)
                prev = y
                for i in range(g):
                    rr, _ = issue("MARKOV", i, 1, q, tok1=prev)
                    prev = rr[0]
                    d.append(prev)
        toks = [y] + d
        for L in range(nl):
            issue("VLAYER", L, g + 1, n, toks)
        t, lgs = issue("VHEAD", 0, g + 1, n, toks, want=True)
        issue("SEED", 0, g + 1, n, toks)
        a = 0
        while a < len(d) and d[a] == t[a]:
            a += 1
        out += t[:a + 1]
        rows += lgs[:a + 1]
        steps.append(dict(anchor=q, drafts=d, targets=t, accepted=a))
        n += 1 + a
        y = t[a]
        step += 1
        print(f"  step {step}: anchor {q} drafts {d} targets {t} accept {a}", flush=True)
    return out[:ngen], rows[:ngen], steps


def forced_drafter(ar_tok, plen, vocab):
    """tools/dshbm_dspark_trace.py's forced drafter: the golden continuation with one draft corrupted per step at
    slot step % (g+1) (g: none), so every accept length 0 .. g occurs."""
    def f(step, y, q, g):
        dr = [int(ar_tok[q + 1 + i - plen]) for i in range(1, g + 1)]
        c = step % (g + 1)
        if c < g:
            dr[c] = (dr[c] + 1) % vocab
        return dr
    return f


def golden(prompt, ngen, gamma, drafter):
    gm = V.Model()
    ar_tok, ar_lg = gm.generate(prompt, ngen + 2 * B + 4, mtp_state=True)
    gm2 = V.Model()
    if drafter == "forced":
        fd = forced_drafter(ar_tok, len(prompt), int(gm2.c["vocab_size"]))
        cnt = [0]

        def drf(y, q, state):
            r = fd(cnt[0], y, q, min(gamma, int(gm2.c["max_seq_len"]) - 2 - q))
            cnt[0] += 1
            return r
        tok, lg, passes = gm2.generate_spec(prompt, ngen, gamma, drafter=drf)
    else:
        tok, lg, passes = gm2.generate_spec(prompt, ngen, gamma)
    assert tok == ar_tok[:ngen] and all(np.array_equal(G.bits(u), G.bits(v)) for u, v in zip(lg, ar_lg[:ngen]))
    return tok, lg, passes, ar_tok


def check(drafter="forced", ngen=8, gamma=GAMMA):
    global NOISE
    model, prog, graph, code = build()
    NOISE = model.noise_id
    kc = dict(code)
    prompt, _ = V.prompt_and_expected()
    prompt = list(prompt)
    t0 = time.time()
    gtok, glg, gpass, ar_tok = golden(prompt, ngen, gamma, drafter)
    print(f"golden generate_spec: {gtok}  accepts {[p['accepted'] for p in gpass]}  ({time.time() - t0:.0f} s)",
          flush=True)
    mach = H.Machine(nd=TP, nsm=NSM, nl=NL, mem_bytes=prog.mem_bytes, L=H.L16)
    H.load_images(mach, prog)
    isa.FP_ERR[0] = 0
    eng = Engine(kc, mach, prog)
    forced = forced_drafter(ar_tok, len(prompt), int(model.c["vocab_size"])) if drafter == "forced" else None
    tok, rows, steps = ctl_loop(eng, prompt, ngen, gamma, forced)
    ok = tok == gtok
    lg_ok = all(np.array_equal(G.bits(u), G.bits(v)) for u, v in zip(rows, glg))
    pass_ok = [(s["drafts"], s["targets"], s["accepted"]) for s in steps] == \
              [(p["drafts"], p["targets"], p["accepted"]) for p in gpass]
    print(f"machine tokens {tok}\ngolden  tokens {gtok}\ntokens {'OK' if ok else 'MISMATCH'}, logits "
          f"{'bit-exact' if lg_ok else 'MISMATCH'}, drafts/targets/accepts per pass {'equal' if pass_ok else 'DIFFER'}")
    print("accept lengths", [s["accepted"] for s in steps], " FP fail-closed lanes:", isa.FP_ERR[0],
          " launches:", eng.launches)
    st = {k_: max(sm.stats.get(k_, 0) for sm in mach.sms()) for k_ in ("instr", "tc_lines", "bd_lines")}
    print("per-SM totals (max SM)", st, " kernel words", {n: max(len(c) for c in kc_.values()) for n, kc_ in code})
    return ok and lg_ok and pass_ok and isa.FP_ERR[0] == 0


def emit(out, drafter="forced", ngen=8, gamma=GAMMA):
    """Kernels (one linked image per SM), HBM images, the entry table, and the command trace of the golden
    speculative run: per ctl command its launches (entry, token, pos) and the RESULTs the bridge must forward."""
    global NOISE
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    model, prog, graph, code = build()
    NOISE = model.noise_id
    images, entries = H.link(code)
    for (d, s), words in images.items():
        (out / f"prog_d{d}_s{s}.hex").write_text("\n".join(f"{w:016x}" for w in words) + "\n")
    for d in range(TP):
        img = np.zeros(prog.mem_bytes, dtype=np.uint8)
        for addr, blob in prog.mem[d].items():
            img[addr:addr + len(blob)] = blob
        (out / f"die{d}.bin").write_bytes(img.tobytes())
    prompt = list(V.prompt_and_expected()[0])
    gtok, glg, gpass, ar_tok = golden(prompt, ngen, gamma, drafter)
    cmds = []
    for p, t in enumerate(prompt):
        cmds += [dict(op="VLAYER", idx=L, ncol=1, pos=p, toks=[t], tok1=0) for L in range(model.L)]
        cmds += [dict(op="VHEAD", idx=0, ncol=1, pos=p, toks=[t], tok1=0, results=[gtok[0]] if p == len(prompt) - 1 else None),
                 dict(op="SEED", idx=0, ncol=1, pos=p, toks=[t], tok1=0)]
    n, y = len(prompt), gtok[0]
    for ps in gpass:
        q, d, tg, a = ps["anchor"], ps["drafts"], ps["targets"], ps["accepted"]
        g = len(d)
        if g and drafter == "dspark":
            cmds += [dict(op="DSTAGE", idx=st, ncol=B, pos=q, toks=[], tok1=y) for st in range(NST)]
            cmds.append(dict(op="DHEAD", idx=0, ncol=B, pos=q, toks=[], tok1=y))
            prev = y
            for i in range(g):
                cmds.append(dict(op="MARKOV", idx=i, ncol=1, pos=q, toks=[], tok1=prev, results=[d[i]]))
                prev = d[i]
        toks = [y] + d
        cmds += [dict(op="VLAYER", idx=L, ncol=g + 1, pos=n, toks=toks, tok1=0) for L in range(model.L)]
        cmds.append(dict(op="VHEAD", idx=0, ncol=g + 1, pos=n, toks=toks, tok1=0, results=tg))
        cmds.append(dict(op="SEED", idx=0, ncol=g + 1, pos=n, toks=toks, tok1=0))
        n += 1 + a
        y = tg[a]
    with open(out / "commands.jsonl", "w") as f:
        for c in cmds:
            c["launches"] = [[k_, entries[k_], t_, p_] for k_, t_, p_ in expand(c)]
            f.write(json.dumps(c) + "\n")
    meta = dict(schema="opentallas.gpu_sys.v41_dspark_emit.v1",
                golden="tools/hdc_golden_v41.py Model.generate_spec HDC_V41_ARITH=chunk8", drafter=drafter,
                gamma=gamma, block=B, pmax=PMAX, noise_token=NOISE, prompt=prompt, tokens=gtok,
                passes=[dict(anchor=p_["anchor"], drafts=p_["drafts"], targets=p_["targets"], accepted=p_["accepted"])
                        for p_ in gpass],
                entries=entries, kernel_words={n_: max(len(c) for c in kc.values()) for n_, kc in code},
                imem_words=max(len(w) for w in images.values()), mem_bytes=int(prog.mem_bytes), tp=TP, nsm=NSM, nl=NL,
                ctx=CTX, tpad=H.TPAD, layout=prog.a,
                launch_rule="see the module docstring of tools/gpu_sys/v41_dspark.py (COMMANDS -> LAUNCHES)")
    (out / "expected.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--emit")
    ap.add_argument("--drafter", choices=("forced", "dspark"), default="forced")
    ap.add_argument("--ngen", type=int, default=8)
    ap.add_argument("--gamma", type=int, default=GAMMA)
    a = ap.parse_args()
    if a.emit:
        meta = emit(a.emit, a.drafter, a.ngen, a.gamma)
        print(json.dumps({k_: meta[k_] for k_ in ("entries", "kernel_words", "imem_words", "mem_bytes")}), meta["tokens"])
    if a.check:
        sys.exit(0 if check(a.drafter, a.ngen, a.gamma) else 1)
