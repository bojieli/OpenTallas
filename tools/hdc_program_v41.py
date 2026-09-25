#!/usr/bin/env python3
"""Program, memory images and ISA-level simulator of the V4.1 hardwired decode core.

    python3 tools/hdc_program_v41.py [--out DIR] [--context N] [--multi K]

For the reduced DeepSeek-V4.1-Flash (build/models/deepseek-v4.1-flash-reduced-v2)
this builds

* the BF16 weight ROM (ME: hyper-connection projections as FP32, the router
  gate, compressor, indexer weights_proj/wk, grouped wo_a, lm_head, embedding),
* the quantised weight ROM (QE: every FP8 / FP4 block-scaled matrix, laid out in
  the engine's (round, block, slot) order), the Engram table ROM,
* the constant ROM (norm gains, mix scales and biases, sinks, router bias,
  Engram q*k weights, the two RoPE tables, the compressed token map),
* the static program (tools/hdc_isa_v41.py) that decodes one token,

then runs the program on an ISA-level model whose every operation is the
arithmetic of tools/hdc_golden_v41.py, and checks the logits (and the token)
against hdc_golden_v41.Model.decode_token bit for bit.  The RTL is checked
against the same images and results.
"""
import argparse
import copy
import json
from pathlib import Path

import numpy as np

import hdc_golden as G
import hdc_golden_v41 as V
import hdc_isa_v41 as I

F = np.float32
W, IL, GR, BL = I.W_LANES, I.INTERLEAVE, I.GROUPS, I.BL
TMAX, PMAX = I.T_MAX, I.POS_MAX
DY = I.DYN
HD = 32
STR = TMAX                       # S-region stride per head
# Where a sublayer's own mixes are finished (the mix passes and the Sinkhorn):
# in attention after ATTN_HOOK ("qkv", "scores", "softmax" or "pv"), in the MoE
# before routed expert MOE_HOOK (7: after the shared expert).  Swept with
# tools/hdc_timing_v41.py: late enough that the HE's 5,120-cycle chain has run,
# early enough that the simple Sinkhorn's ~3,700 cycles hide behind the rest.
# (With the one-step-per-cycle Sinkhorn, MOE_HOOK = 6 is best.)
ATTN_HOOK = "softmax"
MOE_HOOK = 1
KT_WORDS = (TMAX // W) * HD      # transposed rows of one layer (words)
KR_WORDS = TMAX * HD // W        # row-major rows of one layer (words)


def f32(x):
    return int(G.bits(F(x)))


def u32f(i):
    return G.from_bits(np.uint32(i))


# E4M3 / E2M1 value -> code (bit-exact on the float64 value, so -0 maps to its code)
_E4 = {float(v).hex(): c for c, v in enumerate(V.E4M3) if not np.isnan(v)}
_E2 = {float(v).hex(): c for c, v in enumerate(V.E2M1)}


def codes_of(q, fp4):
    table = _E2 if fp4 else _E4
    flat = [table[float(v).hex()] for v in np.asarray(q, dtype=np.float64).reshape(-1)]
    return np.array(flat, dtype=np.uint8).reshape(q.shape)


class Alloc:
    def __init__(self, size, align=32):
        self.top, self.size, self.align, self.map = 0, size, align, {}

    def __call__(self, name, n, align=None):
        a = align or self.align
        self.top = -(-self.top // a) * a
        self.map[name] = self.top
        self.top += n
        assert self.top <= self.size, (name, self.top)
        return self.map[name]


class Layout:
    """Weight ROMs, constant ROM, vector-memory and KV maps for the reduced model."""

    def __init__(self, m):
        self.m = m
        c = m.c
        self.L, self.dim, self.hc = m.L, m.dim, m.hc
        self.nh, self.ih = m.heads, m.ih
        assert m.hd == HD and m.ihd == HD and m.rd == 4 and m.window >= PMAX
        # -- vector memory ------------------------------------------------------
        v = self.vm = Alloc(I.VM_ELEMS)
        for name, n in (("H", 640), ("T", 640), ("SSX", 1), ("RF", 1), ("MIX", 32), ("PA", 4), ("POA", 4),
                        ("CA", 16), ("PF", 4), ("POF", 4), ("CF", 16), ("CRAW", 16), ("M4", 4), ("E16", 32),
                        ("X", 160), ("XN", 160), ("SS", 8), ("RS", 8), ("QA", 32), ("QR", 32), ("KVA", 32),
                        ("KVN", 32), ("KVQ", 32), ("Q", 2048), ("S", self.nh * STR), ("M", 64), ("Z", 64),
                        ("DEN", 64), ("ACC", 2048), ("ZA", 256), ("Y", 160),
                        ("CM", 32), ("CE", 64), ("CD", 32), ("CP", 64), ("POOL", 32), ("CKA", 32), ("LAT", 32),
                        ("IKA", 32), ("IKN", 32), ("IKQ", 32), ("IQ", 1024), ("IQQ", 1024), ("WP", 32),
                        ("WTS", 32), ("IS", 128), ("SEL", 16),
                        ("G12", 16), ("SC", 16), ("BI", 16), ("EID", 8), ("TOT", 1), ("DEN1", 1), ("WGT", 8),
                        ("ER", 768), ("EKV", 800), ("ESS", 8), ("ERS", 8), ("ED", 4), ("EDOT", 4), ("EG", 4)):
            v(name, n)
        for k in range(7):
            v(f"GU{k}", 128)
            v(f"ACT{k}", 64)
            v(f"E{k}", 160)
        # persistent: compressor slots and compressed KV rows per source layer
        self.nrows = {s: PMAX // (m.ratio[s]) for s in m.kv_src}
        for s in m.kv_src:
            v(f"SLOT{s}", 128)
            v(f"CKV{s}", self.nrows[s] * HD)
        self.vm_persist = [(self.vm.map[f"SLOT{s}"], 128) for s in m.kv_src] + \
                          [(self.vm.map[f"CKV{s}"], self.nrows[s] * HD) for s in m.kv_src]
        # -- KV SRAM (elements; W per word) ---------------------------------------------
        k = self.kv = Alloc(I.KV_WORDS * W, align=W)
        for L in range(self.L):
            k(f"KT{L}", KT_WORDS * W)
            k(f"KR{L}", KR_WORDS * W)
        for s in m.kv_src:
            k(f"IK{s}", (self.nrows[s] // W) * HD * W)
        # -- constant ROM -------------------------------------------------------------------
        self.crom = []
        self.cb = {}
        lw = m.lw
        for L in range(self.L):
            for nm in ("attn_norm", "ffn_norm"):
                self.cb[(L, nm)] = self.put(lw(L, f"{nm}.weight"))
            for nm in ("q_norm", "kv_norm"):
                self.cb[(L, nm)] = self.put(lw(L, f"attn.{nm}.weight"))
            for wh in ("attn", "ffn"):
                sc = lw(L, f"hc_{wh}_scale")
                self.cb[(L, wh, "scale")] = self.put(np.concatenate([np.full(4, sc[0]), np.full(4, sc[1]),
                                                                     np.full(16, sc[2])]).astype(F))
                self.cb[(L, wh, "base")] = self.put(lw(L, f"hc_{wh}_base"))
            self.cb[(L, "sink")] = self.put(lw(L, "attn.attn_sink"))
            self.cb[(L, "bias")] = self.put(lw(L, "ffn.gate.bias"))
            if L in m.kv_src:
                self.cb[(L, "cnorm")] = self.put(lw(L, "attn.compressor.norm.weight"))
                self.cb[(L, "knorm")] = self.put(lw(L, "attn.indexer.k_norm.weight"))
            if L in m.engram.layer_ids:
                self.cb[(L, "ewgt")] = self.put(G.mul(lw(L, "engram.q_weight"), lw(L, "engram.k_weight")).reshape(-1))
        self.cb["norm"] = self.put(m.w["norm.weight"])
        self.cb["pre0"] = self.put(np.array([1, 0, 0, 0], dtype=F))
        for tname, fr in (("rope_plain", m.freqs_plain), ("rope_yarn", m.freqs_yarn)):
            self.cb[tname] = len(self.crom)
            for p in range(PMAX):
                cs, sn = V.rope_cs(fr, p)
                self.crom.extend((F(a), F(b)) for a, b in zip(cs, sn))
        self.cb["tmap"] = len(self.crom)
        self.crom.extend((u32f(int(x)), F(0)) for x in m.engram.token_map)
        # -- ME weight ROM (W*GR bf16 lanes per word) -----------------------------------
        self.words = []
        self.hwords = []
        self.mat = {}
        # the embedding first: the stream unit addresses it by element (24-bit)
        emb = m.w["embed.weight"]
        self.emb_word = len(self.words)
        flat = (G.bits(emb.reshape(-1)) >> 16).astype(np.uint16)
        for i in range(0, len(flat), W * GR):
            wd = np.zeros(W * GR, dtype=np.uint16)
            wd[:len(flat[i:i + W * GR])] = flat[i:i + W * GR]
            self.words.append(wd)
        for L in range(self.L):
            for wh in ("attn", "ffn"):
                self.mat[(L, wh, "fn")] = self.hplace(lw(L, f"hc_{wh}_fn"))
            self.mat[(L, "gate")] = self.place(lw(L, "ffn.gate.weight"))
            self.mat[(L, "wo_a")] = self.place_wo_a(lw(L, "attn.wo_a.weight"))
            if L in m.kv_src:
                if m.ratio[L] == 2:
                    wkv = np.concatenate([lw(L, "attn.compressor.wkv.weight"), lw(L, "attn.compressor.wgate.weight")])
                else:
                    wkv = lw(L, "attn.compressor.wkv.weight")
                self.mat[(L, "cwkv")] = self.place(wkv)
                self.mat[(L, "iwk")] = self.place(lw(L, "attn.indexer.wk.weight"))
            if L in m.idx_src:
                self.mat[(L, "iwp")] = self.place(lw(L, "attn.indexer.weights_proj.weight"))
        self.mat["head"] = self.place(m.w["head.weight"])
        # -- QE weight ROM: per word BL lanes x (32 codes, exponent) -------------------
        self.qcodes, self.qexp = [], []
        self.qmat = {}
        for L in range(self.L):
            for nm in ("wq_a", "wkv", "wq_b", "wo_b"):
                self.qmat[(L, nm)] = self.qplace(lw(L, f"attn.{nm}.weight"))
            if L in m.idx_src:
                self.qmat[(L, "iwq_b")] = self.qplace(lw(L, "attn.indexer.wq_b.weight"))
            base = len(self.qcodes)
            for e in range(m.n_exp):
                self.qexpert(f"layers.{L}.ffn.experts.{e}.", (L, "exp", e))
            self.qmat[(L, "exp_base")] = base
            self.qmat[(L, "exp_stride")] = self.qmat[(L, "exp", 1, "w13")]["base"] - self.qmat[(L, "exp", 0, "w13")]["base"]
            for e in range(1, m.n_exp):
                assert self.qmat[(L, "exp", e, "w13")]["base"] - base == e * self.qmat[(L, "exp_stride")]
            self.qexpert(f"layers.{L}.ffn.shared_experts.", (L, "shared"))
            if L in m.engram.layer_ids:
                self.qmat[(L, "ewkv")] = self.qplace(lw(L, "engram.wkv.weight"))
        # -- Engram table ROM ------------------------------------------------------------------
        self.ebase = {}
        ecodes, eexp = [], []
        for L in m.engram.layer_ids:
            codes, sc = m.emb_codes[L]
            self.ebase[L] = sum(len(x) for x in ecodes)
            ecodes.append(codes)
            eexp.append(sc)
        self.ecodes = np.concatenate(ecodes)
        self.eexp = np.concatenate(eexp).astype(np.int64)

    def put(self, v):
        base = len(self.crom)
        self.crom.extend((F(x), F(0)) for x in np.asarray(v, dtype=F).reshape(-1))
        return base

    # ME placement: words in (round, k, slot) order; lane g*W+l holds row_of(t, j, l)
    def place_rows(self, w, row_of, tiles_total):
        n, k = w.shape
        rounds = -(-tiles_total // GR)
        base = len(self.words)
        wb = (G.bits(np.asarray(w, dtype=F)) >> 16).astype(np.uint16)
        for r in range(rounds):
            for kk in range(k):
                for j in range(IL):
                    word = np.zeros(W * GR, dtype=np.uint16)
                    for g in range(GR):
                        t = r * GR + g
                        for l in range(W):
                            row = row_of(t, j, l)
                            if 0 <= row < n:
                                word[g * W + l] = wb[row, kk]
                    self.words.append(word)
        return dict(base=base, n=n, k=k, tiles=rounds)

    def place(self, w):
        n = w.shape[0]
        return self.place_rows(w, lambda t, j, l: (t * IL + j) * W + l, -(-n // (W * IL)))

    def place_wo_a(self, w):
        """Grouped wo_a: slot j is group j, tile t its rows t*W .. t*W+15, so every
        slot reads its own group's 256 attention outputs (xjs = 256)."""
        o_rank = self.m.o_rank
        assert w.shape == (self.m.groups * o_rank, 256) and self.m.groups == IL
        return self.place_rows(w, lambda t, j, l: j * o_rank + t * W + l if t * W + l < o_rank else -1,
                               o_rank // W)

    def hplace(self, w):
        """HE placement (FP32 weights): word k*IL + j holds rows j*NL + l, lane l."""
        n, k = w.shape
        assert n <= I.HE_LANES * IL
        base = len(self.hwords)
        wf = np.zeros((I.HE_LANES * IL, k), dtype=F)
        wf[:n] = w
        for kk in range(k):
            for j in range(IL):
                self.hwords.append(wf[j * I.HE_LANES:(j + 1) * I.HE_LANES, kk].copy())
        return dict(base=base, n=n, k=k)

    # QE placement: word (round r, block kb, slot j), lane l: row (r*IL + j)*BL + l
    def qplace(self, q8, fp4=False):
        n, k = q8.q.shape
        nb = k // 32
        assert nb * 32 == k
        codes = codes_of(q8.q, fp4)
        rounds = -(-n // (BL * IL))
        base = len(self.qcodes)
        for r in range(rounds):
            for kb in range(nb):
                for j in range(IL):
                    cw = np.zeros((BL, 32), dtype=np.uint8)
                    ew = np.zeros(BL, dtype=np.int64)
                    for l in range(BL):
                        row = (r * IL + j) * BL + l
                        if row < n:
                            cw[l] = codes[row, kb * 32:(kb + 1) * 32]
                            ew[l] = q8.e[row, kb]
                    self.qcodes.append(cw)
                    self.qexp.append(ew)
        return dict(base=base, n=n, nb=nb, tiles=rounds, fp4=int(fp4))

    def qexpert(self, prefix, key):
        w = self.m.w
        w1, w3 = w[prefix + "w1.weight"], w[prefix + "w3.weight"]
        fp4 = "shared" not in prefix
        w13 = V.Q8(np.concatenate([w1.q, w3.q]), np.concatenate([w1.e, w3.e]))
        self.qmat[key + ("w13",)] = self.qplace(w13, fp4)
        self.qmat[key + ("w2",)] = self.qplace(w[prefix + "w2.weight"], fp4)

    # KV element addresses
    def kt_elem(self, base, t, d):
        return base + (t // W) * HD * W + d * W + t % W

    def kv_image(self, st):
        kv = np.zeros(I.KV_WORDS * W, dtype=F)
        for L in range(self.L):
            for t, row in enumerate(st["win"][L]):
                for d in range(HD):
                    kv[self.kt_elem(self.kv.map[f"KT{L}"], t, d)] = row[d]
                    kv[self.kv.map[f"KR{L}"] + t * HD + d] = row[d]
        for s in self.m.kv_src:
            for t, row in enumerate(st["ik"][s]):
                for d in range(HD):
                    kv[self.kt_elem(self.kv.map[f"IK{s}"], t, d)] = row[d]
        return kv

    def vm_image(self, st, pos):
        """Persistent vector-memory state after positions 0 .. pos-1."""
        vm = np.zeros(I.VM_ELEMS, dtype=F)
        for s in self.m.kv_src:
            for i, (kv, sc) in enumerate(st["slots"][s]):
                slot = (pos - len(st["slots"][s]) + i) & 1
                vm[self.vm.map[f"SLOT{s}"] + slot * 64: self.vm.map[f"SLOT{s}"] + slot * 64 + 64] = \
                    np.concatenate([kv, sc])
            for t, row in enumerate(st["ckv"][s]):
                vm[self.vm.map[f"CKV{s}"] + t * HD: self.vm.map[f"CKV{s}"] + (t + 1) * HD] = row
        return vm


# -- program -------------------------------------------------------------------------
class Builder:
    def __init__(self, lay):
        self.lay, self.m = lay, lay.m
        self.prog = []
        self.V = lay.vm.map
        self.K = lay.kv.map

    def emit(self, f, reads, writes, tag):
        self.prog.append((f, set(reads), set(writes), tag))

    def me(self, mat, x, out, reads, writes, tag, **over):
        f = dict(unit=I.UNIT_ME, me_nout=mat["n"], me_tiles=mat["tiles"], me_k=mat["k"], me_wsrc=0,
                 me_wbase=mat["base"], me_ts=mat["k"] * IL, me_ks=IL, me_js=1, me_xbase=x, me_xks=1,
                 me_round=1, me_obase=out // W, me_ots=IL, me_ojs=1, me_oen=1, me_xcs=mat["k"])
        f.update(over)
        self.emit(f, reads, writes, tag)

    def su(self, reads, writes, tag, **f):
        f = dict(f, unit=I.UNIT_SU)
        self.emit(f, reads, writes, tag)

    def qe(self, reads, writes, tag, **f):
        f = dict(f, unit=I.UNIT_QE)
        self.emit(f, reads, writes, tag)

    def xu(self, reads, writes, tag, **f):
        f = dict(f, unit=I.UNIT_XU)
        self.emit(f, reads, writes, tag)

    # -- composite operations ---------------------------------------------------------
    def rms_r(self, ss, n, dst, tag, pred=0):
        self.su({ss}, {dst}, tag, pred=pred, su_nout=1, su_nin=1, a_base=self.V[ss], m1=I.M1_DIVIMM,
                imm1=f32(n), ad=I.AD_IMM, imm2=f32(self.m.eps), sfu=I.SFU_RSQRT, dst=I.DST_VM,
                o_base=self.V[dst])

    def rms_out(self, src, n, r, w, dst, tag, pred=0, sq=None):
        f = dict(pred=pred, su_nout=1, su_nin=n, a_base=self.V[src], a_si=1, b_base=self.V[r], m1=I.M1_AB,
                 c_src=I.SRC_CLO, c_base=w, c_si=1, e1=I.E1_MULC, rnd=1, dst=I.DST_VM, o_base=self.V[dst], o_si=1)
        wr = {dst}
        if sq:
            f.update(red=I.RED_SUM, red_sq=1, r_base=self.V[sq])
            wr.add(sq)
        self.su({src, r}, wr, tag, **f)

    def sumsq(self, src, n, dst, tag, pred=0):
        self.su({src}, {dst}, tag, pred=pred, su_nout=1, su_nin=n, a_base=self.V[src], a_si=1, red=I.RED_SUM,
                red_sq=1, r_base=self.V[dst])

    def rmsnorm(self, src, n, w, dst, tag, pred=0, have_ss=None):
        ss = have_ss or "SS"
        if not have_ss:
            self.sumsq(src, n, ss, tag, pred)
        self.rms_r(ss, n, "RS", tag, pred)
        self.rms_out(src, n, "RS", w, dst, tag, pred)

    def bf16(self, src, n, dst, tag, pred=0, sq=None):
        f = dict(pred=pred, su_nout=1, su_nin=n, a_base=self.V[src], a_si=1, rnd=1, dst=I.DST_VM,
                 o_base=self.V[dst], o_si=1)
        wr = {dst}
        if sq:
            f.update(red=I.RED_SUM, red_sq=1, r_base=self.V[sq])
            wr.add(sq)
        self.su({src}, wr, tag, **f)

    def rope(self, region, base, nh, hs, table, dynsel, inverse, tag, pred=0):
        """Interleaved-pair RoPE on the last 4 elements of nh rows of hs elements,
        in place, BF16 out."""
        self.su({region}, {region}, tag, pred=pred, su_nout=nh, su_nin=4,
                a_base=base + hs - 4, a_so=hs, a_si=1, c_pair=1,
                b_src=I.SRC_CLO, b_base=self.lay.cb[table], b_d=dynsel, b_si=1, b_half=1,
                d_src=I.SRC_CHI, d_base=self.lay.cb[table], d_d=dynsel, d_si=1,
                m1=I.M1_AB, qm=I.QM_ALT_PN if inverse else I.QM_ALT_NP, ad=I.AD_Q, rnd=1,
                dst=I.DST_VM, o_base=base + hs - 4, o_so=hs, o_si=1)

    def linq(self, mat, x, out, reads, writes, tag, pred=0, **over):
        f = dict(pred=pred, qe_mode=I.QE_LINQ, qe_fp4=mat["fp4"], qe_xbase=self.V[x], qe_nb=mat["nb"],
                 qe_nout=mat["n"], qe_tiles=mat["tiles"], qe_wbase=mat["base"], qe_obase=self.V[out])
        f.update(over)
        self.qe(reads | {x}, writes | {out}, tag, **f)

    def qdq(self, mode, src, nb, dst_base, writes, tag, pred=0, dsel=0):
        self.qe({src}, writes, tag, pred=pred, qe_mode=mode, qe_xbase=self.V[src], qe_nb=nb,
                qe_obase=dst_base, qe_d_obase=dsel)

    # -- model ---------------------------------------------------------------------------
    def hc_mix_issue(self, L, wh):
        """The mixes' projection on the HE and the stream's norm scalar; the rest
        (hc_mix_finish) is placed inside the sublayer, which runs meanwhile."""
        V_ = self.V
        t = f"L{L}.hc_{wh}"
        self.rms_r("SSX", 640, "RF", t)
        mat = self.lay.mat[(L, wh, "fn")]
        self.emit(dict(unit=I.UNIT_HE, he_nout=mat["n"], he_k=mat["k"], he_wbase=mat["base"], he_xbase=V_["H"],
                       he_obase=V_["MIX"]), {"H"}, {"MIX"}, t)

    def hc_mix_finish(self, L, wh):
        m, V_ = self.m, self.V
        P, PO, C = {"attn": ("PA", "POA", "CA"), "ffn": ("PF", "POF", "CF")}[wh]
        t = f"L{L}.hc_{wh}"
        sc, bs = self.lay.cb[(L, wh, "scale")], self.lay.cb[(L, wh, "base")]
        common = dict(a_si=1, b_base=V_["RF"], m1=I.M1_AB, c_src=I.SRC_CLO, c_si=1, m2=I.M2_C,
                      d_src=I.SRC_CLO, d_si=1, ad=I.AD_D, dst=I.DST_VM, o_si=1, su_nout=1)
        self.su({"MIX", "RF"}, {P}, t, su_nin=4, a_base=V_["MIX"], c_base=sc, d_base=bs, sfu=I.SFU_SIGM,
                e1=I.E1_ADDIMM, imm2=f32(m.hc_eps), o_base=V_[P], **common)
        self.su({"MIX", "RF"}, {PO}, t, su_nin=4, a_base=V_["MIX"] + 4, c_base=sc + 4, d_base=bs + 4,
                sfu=I.SFU_SIGM, e1=I.E1_MULIMM, imm2=f32(2.0), o_base=V_[PO], **common)
        common["su_nout"] = 4
        self.su({"MIX", "RF"}, {"CRAW", "M4"}, t, su_nin=4, a_base=V_["MIX"] + 8, a_so=4, c_base=sc + 8, c_so=4,
                d_base=bs + 8, d_so=4, o_base=V_["CRAW"], o_so=4, red=I.RED_MAX, r_base=V_["M4"], r_so=1,
                **common)
        self.su({"CRAW", "M4"}, {"E16"}, t, su_nout=4, su_nin=4, a_base=V_["CRAW"], a_so=4, a_si=1,
                b_base=V_["M4"], b_so=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, dst=I.DST_VM, o_base=V_["E16"], o_so=4,
                o_si=1)
        self.xu({"E16"}, {C}, t, xu_op=I.XU_SINK, xu_src=V_["E16"], xu_dst=V_[C], xu_n=16)

    def hc_pre(self, pre, dst, tag, ss):
        V_ = self.V
        h = V_["H"]
        self.su({"H", pre}, {"T"}, tag, su_nout=1, su_nin=160, a_base=h, a_si=1, b_base=V_[pre], m1=I.M1_AB,
                c_base=h + 160, c_si=1, d_base=V_[pre] + 1, qm=I.QM_POS, ad=I.AD_Q, dst=I.DST_VM, o_base=V_["T"],
                o_si=1)
        self.su({"H", pre, "T"}, {"T"}, tag, su_nout=1, su_nin=160, a_base=h + 320, a_si=1, b_base=V_[pre] + 2,
                m1=I.M1_AB, c_base=V_["T"], c_si=1, ad=I.AD_C, dst=I.DST_VM, o_base=V_["T"], o_si=1)
        self.su({"H", pre, "T"}, {dst, ss}, tag, su_nout=1, su_nin=160, a_base=h + 480, a_si=1,
                b_base=V_[pre] + 3, m1=I.M1_AB, c_base=V_["T"], c_si=1, ad=I.AD_C, rnd=1, dst=I.DST_VM,
                o_base=V_[dst], o_si=1, red=I.RED_SUM, red_sq=1, r_base=V_[ss])

    def hc_post(self, y, post, comb, tag):
        V_ = self.V
        h, T = V_["H"], V_["T"]
        self.su({"H", comb}, {"T"}, tag, su_nout=4, su_nin=160, a_base=h, a_si=1, b_base=V_[comb], b_so=1,
                m1=I.M1_AB, c_base=h + 160, c_si=1, d_base=V_[comb] + 4, d_so=1, qm=I.QM_POS, ad=I.AD_Q,
                dst=I.DST_VM, o_base=T, o_so=160, o_si=1)
        for j in (2, 3):
            self.su({"H", comb, "T"}, {"T"}, tag, su_nout=4, su_nin=160, a_base=h + 160 * j, a_si=1,
                    b_base=V_[comb] + 4 * j, b_so=1, m1=I.M1_AB, c_base=T, c_so=160, c_si=1, ad=I.AD_C,
                    dst=I.DST_VM, o_base=T, o_so=160, o_si=1)
        self.su({y, post, "T"}, {"H", "SSX"}, tag, su_nout=4, su_nin=160, a_base=V_[y], a_si=1,
                b_base=V_[post], b_so=1, m1=I.M1_AB, c_base=T, c_so=160, c_si=1, ad=I.AD_C, rnd=1,
                dst=I.DST_VM, o_base=h, o_so=160, o_si=1, red=I.RED_SUM, red_sq=1, red_whole=1,
                r_base=V_["SSX"])

    def engram(self, L):
        m, V_, lay = self.m, self.V, self.lay
        t = f"L{L}.engram"
        li = m.engram.layer_ids.index(L)
        h = V_["H"]
        self.xu({"EH"}, {"ER"}, t, xu_op=I.XU_EGATHER, xu_src=lay.ebase[L], xu_dst=V_["ER"], xu_layer=li, xu_n=24)
        self.linq(lay.qmat[(L, "ewkv")], "ER", "EKV", set(), set(), t)
        self.su({"H"}, {"ESS"}, t, su_nout=4, su_nin=160, a_base=h, a_so=160, a_si=1, red=I.RED_SUM, red_sq=1,
                r_base=V_["ESS"], r_so=1)
        self.su({"EKV"}, {"ESS"}, t, su_nout=4, su_nin=160, a_base=V_["EKV"], a_so=160, a_si=1, red=I.RED_SUM,
                red_sq=1, r_base=V_["ESS"] + 4, r_so=1)
        self.su({"H", "EKV"}, {"ED"}, t, su_nout=4, su_nin=160, a_base=h, a_so=160, a_si=1, b_src=I.SRC_CLO,
                b_base=lay.cb[(L, "ewgt")], b_so=160, b_si=1, m1=I.M1_AB, c_base=V_["EKV"], c_so=160, c_si=1,
                m2=I.M2_C, red=I.RED_SUM, r_base=V_["ED"], r_so=1)
        self.su({"ESS"}, {"ERS"}, t, su_nout=1, su_nin=8, a_base=V_["ESS"], a_si=1, m1=I.M1_DIVIMM,
                imm1=f32(160), ad=I.AD_IMM, imm2=f32(m.eps), sfu=I.SFU_RSQRT, dst=I.DST_VM, o_base=V_["ERS"],
                o_si=1)
        self.su({"ERS", "ED"}, {"EDOT"}, t, su_nout=1, su_nin=4, a_base=V_["ERS"], a_si=1, b_base=V_["ERS"] + 4,
                b_si=1, m1=I.M1_AB, c_base=V_["ED"], c_si=1, m2=I.M2_C, e1=I.E1_MULIMM,
                imm2=f32(m.engram_scale), dst=I.DST_VM, o_base=V_["EDOT"], o_si=1)
        self.su({"EDOT"}, {"EG"}, t, su_nout=1, su_nin=4, a_base=V_["EDOT"], a_si=1, sfu=I.SFU_EGATE,
                dst=I.DST_VM, o_base=V_["EG"], o_si=1)
        self.su({"EKV", "EG", "H"}, {"H", "SSX"}, t, su_nout=4, su_nin=160, a_base=V_["EKV"] + 640, a_si=1,
                b_base=V_["EG"], b_so=1, m1=I.M1_AB, c_base=h, c_so=160, c_si=1, ad=I.AD_C, rnd=1,
                dst=I.DST_VM, o_base=h, o_so=160, o_si=1, red=I.RED_SUM, red_sq=1, red_whole=1,
                r_base=V_["SSX"])

    def kvt_write(self, src, region, base, rowsel, tag, pred=0, n=1, ind=False):
        f = dict(pred=pred, su_nout=n, su_nin=HD, a_base=self.V[src], a_si=1, dst=I.DST_KVT, o_base=base,
                 o_d=rowsel)
        self.su({src}, {region}, tag, **f)

    def compressor(self, L):
        m, V_, lay = self.m, self.V, self.lay
        t = f"L{L}.compressor"
        r = m.ratio[L]
        mat = lay.mat[(L, "cwkv")]
        pred = I.PRED_ODD if r == 2 else 0
        slot = f"SLOT{L}"
        if r == 2:
            self.me(mat, V_["XN"], V_[slot], {"XN"}, {slot}, t, me_d_obase=DY["SLOTW"])
            s0, s1 = V_[slot], V_[slot] + 64
            self.su({slot}, {"CM"}, t, pred=pred, su_nout=1, su_nin=32, a_base=s0 + 32, a_si=1, b_base=s1 + 32,
                    b_si=1, m1=I.M1_MAXB, dst=I.DST_VM, o_base=V_["CM"], o_si=1)
            self.su({slot, "CM"}, {"CE"}, t, pred=pred, su_nout=2, su_nin=32, a_base=s0 + 32, a_so=64, a_si=1,
                    b_base=V_["CM"], b_si=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, dst=I.DST_VM, o_base=V_["CE"],
                    o_so=32, o_si=1)
            self.su({"CE"}, {"CD"}, t, pred=pred, su_nout=1, su_nin=32, a_base=V_["CE"], a_si=1,
                    c_base=V_["CE"] + 32, c_si=1, ad=I.AD_C, dst=I.DST_VM, o_base=V_["CD"], o_si=1)
            self.su({"CE", "CD"}, {"CP"}, t, pred=pred, su_nout=2, su_nin=32, a_base=V_["CE"], a_so=32, a_si=1,
                    b_base=V_["CD"], b_si=1, m1=I.M1_DIVB, dst=I.DST_VM, o_base=V_["CP"], o_so=32, o_si=1)
            self.su({slot, "CP"}, {"POOL", "SS"}, t, pred=pred, su_nout=1, su_nin=32, a_base=s0, a_si=1,
                    b_base=V_["CP"], b_si=1, m1=I.M1_AB, c_base=s1, c_si=1, d_base=V_["CP"] + 32, d_si=1,
                    qm=I.QM_POS, ad=I.AD_Q, rnd=1, dst=I.DST_VM, o_base=V_["POOL"], o_si=1, red=I.RED_SUM,
                    red_sq=1, r_base=V_["SS"])
            self.rmsnorm("POOL", 32, lay.cb[(L, "cnorm")], "LAT", t, pred, have_ss="SS")
        else:
            self.me(mat, V_["XN"], V_["CKA"], {"XN"}, {"CKA"}, t)
            self.bf16("CKA", 32, "CKA", t, sq="SS")
            self.rmsnorm("CKA", 32, lay.cb[(L, "cnorm")], "LAT", t, have_ss="SS")
        # index key: rmsnorm(wk . latent), RoPE at the group's first position, FP4 QDQ
        t2 = f"L{L}.index_key"
        gsel = DY["ROPE_G2"] if r == 2 else DY["ROPE"]
        self.me(lay.mat[(L, "iwk")], V_["LAT"], V_["IKA"], {"LAT"}, {"IKA"}, t2, pred=pred)
        self.bf16("IKA", 32, "IKA", t2, pred, sq="SS")
        self.rmsnorm("IKA", 32, lay.cb[(L, "knorm")], "IKN", t2, pred, have_ss="SS")
        self.rope("IKN", V_["IKN"], 1, HD, "rope_yarn", gsel, False, t2, pred)
        self.qdq(I.QE_QDQ4, "IKN", 1, V_["IKQ"], {"IKQ"}, t2, pred)
        self.kvt_write("IKQ", f"IK{L}", self.K[f"IK{L}"], DY["N2M1"] if r == 2 else DY["POS"], t2, pred)
        # compressed KV row: RoPE (in place, after the key path read LAT), FP4 (E4M3 scale) QDQ
        self.rope("LAT", V_["LAT"], 1, HD, "rope_yarn", gsel, False, t, pred)
        self.qdq(I.QE_QDQ4E, "LAT", 1, V_[f"CKV{L}"], {f"CKV{L}"}, t, pred,
                 dsel=DY["CKV2"] if r == 2 else DY["ROW"])

    def indexer(self, L):
        m, V_, lay = self.m, self.V, self.lay
        t = f"L{L}.indexer"
        r, src = m.ratio[L], m.kv_of[L]
        pred = I.PRED_NZ if r == 2 else 0
        nsel = DY["N2"] if r == 2 else DY["POS1"]
        rnds = DY["RND_N2"] if r == 2 else DY["RND_POS1"]
        self.linq(lay.qmat[(L, "iwq_b")], "QR", "IQ", set(), set(), t, pred)
        self.rope("IQ", V_["IQ"], self.m.ih, HD, "rope_yarn", DY["ROPE"], False, t, pred)
        self.qdq(I.QE_QDQ4, "IQ", 32, V_["IQQ"], {"IQQ"}, t, pred)
        self.me(lay.mat[(L, "iwp")], V_["XN"], V_["WP"], {"XN"}, {"WP"}, t, pred=pred)
        self.su({"WP"}, {"WTS"}, t, pred=pred, su_nout=1, su_nin=32, a_base=V_["WP"], a_si=1, a_rnd=1,
                m1=I.M1_AIMM, imm1=f32(m.index_w_scale), rnd=1, dst=I.DST_VM, o_base=V_["WTS"], o_si=1)
        for hb in range(0, m.ih, IL):
            self.me(dict(n=0, tiles=0, k=HD, base=self.K[f"IK{src}"] // W), V_["IQQ"] + hb * HD,
                    V_["S"] + hb * STR, {"IQQ", f"IK{src}"}, {"S"}, t, pred=pred, me_xcs=0, me_wsrc=1,
                    me_ts=HD, me_ks=1, me_js=0, me_jsh=3, me_xks=1, me_xjs=HD, me_ots=1, me_ojs=STR // W,
                    me_mmode=1, me_d_nout=nsel, me_d_tiles=rnds)
        self.su({"S", "WTS"}, {"IS"}, t, pred=pred, su_nout=0, su_d_nout=nsel, su_nin=m.ih, a_base=V_["S"], a_so=1,
                a_si=STR, a_rnd=1, a_relu=1, b_base=V_["WTS"], b_si=1, m1=I.M1_AB, rnd=1, red=I.RED_SUM,
                red_rnd=1, r_base=V_["IS"], r_so=1)
        self.xu({"IS"}, {"SEL"}, t, pred=pred, xu_op=I.XU_SEL, xu_src=V_["IS"], xu_dst=V_["SEL"], xu_d_n=nsel,
                xu_d_k=DY["NSEL2"] if r == 2 else DY["NSEL1"])

    def attention(self, L, hook=None):
        m, V_, lay, K = self.m, self.V, self.lay, self.K
        t = f"L{L}.attn"
        r = m.ratio[L]
        table = "rope_yarn" if r > 0 else "rope_plain"
        self.linq(lay.qmat[(L, "wq_a")], "XN", "QA", set(), set(), t)
        self.linq(lay.qmat[(L, "wkv")], "XN", "KVA", set(), set(), t)
        self.rmsnorm("QA", 32, lay.cb[(L, "q_norm")], "QR", t)
        self.linq(lay.qmat[(L, "wq_b")], "QR", "Q", set(), set(), t)
        self.rmsnorm("KVA", 32, lay.cb[(L, "kv_norm")], "KVN", t)
        self.rope("KVN", V_["KVN"], 1, HD, table, DY["ROPE"], False, t)
        self.qdq(I.QE_QDQ8, "KVN", 1, V_["KVQ"], {"KVQ"}, t)
        self.kvt_write("KVQ", f"KT{L}", K[f"KT{L}"], DY["POS"], t)
        self.su({"KVQ"}, {f"KR{L}"}, t, su_nout=1, su_nin=HD, a_base=V_["KVQ"], a_si=1, dst=I.DST_KV,
                o_base=K[f"KR{L}"], o_d=DY["ROW"], o_si=1)
        self.rope("Q", V_["Q"], m.heads, HD, table, DY["ROPE"], False, t)
        if r > 0:
            src = m.kv_of[L]
            if L == src:
                self.compressor(L)
            if L == m.idx_of[L]:
                self.indexer(L)
            if L == m.cand_src or (0 <= m.cand_src < L):
                # candidate-block select: every block is kept at the reduced shapes
                nb = -(-(PMAX // r) // m.cand_b)
                assert nb <= m.cand_k, "candidate select would drop blocks: not provisioned"
            nsel = DY["NSEL2"] if r == 2 else DY["NSEL1"]
            ta = f"L{L}.gather"
            self.su({f"CKV{src}", "SEL"}, {f"KT{L}"}, ta, su_nout=0, su_d_nout=nsel, su_nin=HD,
                    a_base=V_[f"CKV{src}"], a_so=HD, a_si=1, a_ind=I.IND_O, a_ibase=V_["SEL"], dst=I.DST_KVT,
                    o_base=K[f"KT{L}"], o_d=DY["POS1"])
            self.su({f"CKV{src}", "SEL"}, {f"KR{L}"}, ta, su_nout=0, su_d_nout=nsel, su_nin=HD,
                    a_base=V_[f"CKV{src}"], a_so=HD, a_si=1, a_ind=I.IND_O, a_ibase=V_["SEL"], dst=I.DST_KV,
                    o_base=K[f"KR{L}"], o_d=DY["ROW1"], o_so=HD, o_si=1)
        T = {0: DY["POS1"], 1: DY["T1"], 2: DY["T2"]}[r]
        TR = {0: DY["RND_POS1"], 1: DY["RND_T1"], 2: DY["RND_T2"]}[r]
        if hook and ATTN_HOOK == "qkv":
            hook()
        ts = f"L{L}.scores"
        for hb in range(0, m.heads, IL):
            self.me(dict(n=0, tiles=0, k=HD, base=K[f"KT{L}"] // W), V_["Q"] + hb * HD, V_["S"] + hb * STR,
                    {"Q", f"KT{L}"}, {"S"}, ts, me_xcs=0, me_wsrc=1, me_ts=HD, me_ks=1, me_js=0, me_jsh=3,
                    me_xks=1, me_xjs=HD, me_ots=1, me_ojs=STR // W, me_mmode=1, me_d_nout=T, me_d_tiles=TR)
        if hook and ATTN_HOOK == "scores":
            hook()
        sm = dict(su_nout=m.heads, su_nin=0, su_d_nin=T, a_base=V_["S"], a_so=STR, a_si=1, dst=I.DST_VM,
                  o_base=V_["S"], o_so=STR, o_si=1)
        tsm = f"L{L}.softmax"
        self.su({"S"}, {"S", "M"}, tsm, m1=I.M1_AIMM, imm1=f32(m.attn_scale), red=I.RED_MAX, r_base=V_["M"],
                r_so=1, **sm)
        self.su({"S", "M"}, {"S", "Z"}, tsm, b_base=V_["M"], b_so=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, red=I.RED_SUM,
                r_base=V_["Z"], r_so=1, **sm)
        if hook and ATTN_HOOK == "softmax":
            hook()
        tp = f"L{L}.pv"
        for hb in range(0, m.heads, IL):
            self.me(dict(n=HD, tiles=1, k=0, base=K[f"KR{L}"] // W), V_["S"] + hb * STR, V_["ACC"] + hb * HD,
                    {"S", f"KR{L}"}, {"ACC"}, tp, me_xcs=0, me_wsrc=1, me_ts=1, me_ks=HD // W, me_js=0,
                    me_jsh=3, me_xks=1, me_xjs=STR, me_ots=1, me_ojs=HD // W, me_mmode=1, me_d_k=T)
        self.su({"M", "Z"}, {"DEN"}, tsm, su_nout=1, su_nin=m.heads, a_src=I.SRC_CLO, a_base=lay.cb[(L, "sink")],
                a_si=1, b_base=V_["M"], b_si=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, c_base=V_["Z"], c_si=1,
                e1=I.E1_ADDC, dst=I.DST_VM, o_base=V_["DEN"], o_si=1)
        self.su({"ACC", "DEN"}, {"ACC"}, tsm, su_nout=m.heads, su_nin=HD, a_base=V_["ACC"], a_so=HD, a_si=1,
                b_base=V_["DEN"], b_so=1, m1=I.M1_DIVB, rnd=1, dst=I.DST_VM, o_base=V_["ACC"], o_so=HD, o_si=1)
        self.rope("ACC", V_["ACC"], m.heads, HD, table, DY["ROPE"], True, tsm)
        if hook and ATTN_HOOK == "pv":
            hook()
        to = f"L{L}.out"
        mat = lay.mat[(L, "wo_a")]
        self.me(mat, V_["ACC"], V_["ZA"], {"ACC"}, {"ZA"}, to, me_xjs=256, me_ots=1, me_ojs=2)
        self.bf16("ZA", 256, "ZA", to)
        self.linq(lay.qmat[(L, "wo_b")], "ZA", "Y", set(), set(), to)

    def moe(self, L, hook=None):
        m, V_, lay = self.m, self.V, self.lay
        t = f"L{L}.router"
        self.me(lay.mat[(L, "gate")], V_["XN"], V_["G12"], {"XN"}, {"G12"}, t)
        self.su({"G12"}, {"SC"}, t, su_nout=1, su_nin=m.n_exp, a_base=V_["G12"], a_si=1, sfu=I.SFU_SPSQRT,
                dst=I.DST_VM, o_base=V_["SC"], o_si=1)
        self.su({"SC"}, {"BI"}, t, su_nout=1, su_nin=m.n_exp, a_base=V_["SC"], a_si=1, d_src=I.SRC_CLO,
                d_base=lay.cb[(L, "bias")], d_si=1, ad=I.AD_D, dst=I.DST_VM, o_base=V_["BI"], o_si=1)
        self.xu({"BI"}, {"EID"}, t, xu_op=I.XU_SEL, xu_src=V_["BI"], xu_dst=V_["EID"], xu_n=m.n_exp,
                xu_k=m.k_exp)
        self.su({"SC", "EID"}, {"TOT"}, t, su_nout=1, su_nin=m.k_exp, a_base=V_["SC"], a_si=1, a_ind=I.IND_I,
                a_ibase=V_["EID"], red=I.RED_SEQ, r_base=V_["TOT"])
        self.su({"TOT"}, {"DEN1"}, t, su_nout=1, su_nin=1, a_base=V_["TOT"], ad=I.AD_IMM, imm2=f32(1e-20),
                dst=I.DST_VM, o_base=V_["DEN1"])
        self.su({"SC", "EID", "DEN1"}, {"WGT"}, t, su_nout=1, su_nin=m.k_exp, a_base=V_["SC"], a_si=1,
                a_ind=I.IND_I, a_ibase=V_["EID"], b_base=V_["DEN1"], m1=I.M1_DIVB, m2=I.M2_IMM,
                imm1=f32(m.route_scale), dst=I.DST_VM, o_base=V_["WGT"], o_si=1)
        stride = lay.qmat[(L, "exp_stride")]
        for k in range(m.k_exp + 1):
            if hook and k == MOE_HOOK:
                hook()
            shared = k == m.k_exp
            te = f"L{L}.shared" if shared else f"L{L}.experts"
            if shared:
                w13, w2, ind = lay.qmat[(L, "shared", "w13")], lay.qmat[(L, "shared", "w2")], {}
            else:
                w13, w2 = lay.qmat[(L, "exp", 0, "w13")], lay.qmat[(L, "exp", 0, "w2")]
                ind = dict(qe_ind=1, qe_ibase=V_["EID"] + k, qe_istride=stride)
            self.linq(w13, "XN", f"GU{k}", {"EID"}, set(), te, **ind)
            gu = V_[f"GU{k}"]
            f = dict(su_nout=1, su_nin=64, a_base=gu, a_si=1, a_min=1, imm3=f32(m.limit), c_base=gu + 64, c_si=1,
                     c_clip=1, sfu=I.SFU_SILU, e1=I.E1_MULC, rnd=1, dst=I.DST_VM, o_base=V_[f"ACT{k}"], o_si=1)
            if not shared:
                f.update(b_base=V_["WGT"] + k, e2=I.E2_MULB)
            self.su({f"GU{k}", "WGT"}, {f"ACT{k}"}, te, **f)
            self.linq(w2, f"ACT{k}", f"E{k}", {"EID"}, set(), te, **ind)
        if hook and MOE_HOOK > m.k_exp:
            hook()
        ty = f"L{L}.moe_sum"
        for k in range(1, m.k_exp + 1):
            src = V_["E0"] if k == 1 else V_["Y"]
            self.su({"E0" if k == 1 else "Y", f"E{k}"}, {"Y"}, ty, su_nout=1, su_nin=160, a_base=src, a_si=1,
                    c_base=V_[f"E{k}"], c_si=1, ad=I.AD_C, rnd=int(k == m.k_exp), dst=I.DST_VM, o_base=V_["Y"],
                    o_si=1)

    def build(self, layers=None, embed=True, head=True):
        m, V_, lay = self.m, self.V, self.lay
        layers = range(m.L) if layers is None else layers
        if embed:
            self.xu(set(), {"EH"}, "embed", xu_op=I.XU_EHASH, xu_src=lay.cb["tmap"])
            self.su(set(), {"PF"}, "embed", su_nout=1, su_nin=4, a_src=I.SRC_CLO, a_base=lay.cb["pre0"], a_si=1,
                    dst=I.DST_VM, o_base=V_["PF"], o_si=1)
            self.su(set(), {"H", "SSX"}, "embed", su_nout=4, su_nin=160, a_src=I.SRC_WROM,
                    a_base=lay.emb_word * W * GR, a_d=DY["EMBED"], a_si=1, dst=I.DST_VM, o_base=V_["H"], o_so=160,
                    o_si=1, red=I.RED_SUM, red_sq=1, red_whole=1, r_base=V_["SSX"])
        for L in layers:
            if L in m.engram.layer_ids:
                self.engram(L)
            # the mixes accumulate on the HE while the sublayer runs; the sublayer
            # itself reads only the previous mix (hc_pre), its own is needed at hc_post
            self.hc_mix_issue(L, "attn")
            self.hc_pre("PF", "X", f"L{L}.attn_norm", "SS")
            self.rmsnorm("X", 160, lay.cb[(L, "attn_norm")], "XN", f"L{L}.attn_norm", have_ss="SS")
            self.attention(L, hook=lambda: self.hc_mix_finish(L, "attn"))
            self.hc_post("Y", "POA", "CA", f"L{L}.hc_post")
            self.hc_mix_issue(L, "ffn")
            self.hc_pre("PA", "X", f"L{L}.ffn_norm", "SS")
            self.rmsnorm("X", 160, lay.cb[(L, "ffn_norm")], "XN", f"L{L}.ffn_norm", have_ss="SS")
            self.moe(L, hook=lambda: self.hc_mix_finish(L, "ffn"))
            self.hc_post("Y", "POF", "CF", f"L{L}.hc_post")
        if head:
            self.hc_pre("PF", "X", "head", "SS")
            self.rmsnorm("X", 160, lay.cb["norm"], "XN", "head", have_ss="SS")
            self.me(lay.mat["head"], V_["XN"], 0, {"XN"}, set(), "head", me_amax=1, me_oen=0)
        self.emit(dict(unit=I.UNIT_END, wait=31), set(), set(), "end")
        return schedule(self.prog)


def schedule(prog):
    """Wait masks: an instruction waits for every unit holding an in-flight
    instruction it conflicts with (it reads what that unit writes, or writes what
    it reads or writes).  A unit executes in order, so waiting for it to drain
    covers all its older work."""
    out = []
    rd = {u: set() for u in I.UNITS}
    wr = {u: set() for u in I.UNITS}
    for f, reads, writes, tag in prog:
        f = dict(f)
        wait = f.get("wait", 0)
        for u in I.UNITS:
            if (reads & wr[u]) or (writes & (rd[u] | wr[u])):
                wait |= 1 << (u - 1)
        for u in I.UNITS:
            if wait >> (u - 1) & 1:
                rd[u], wr[u] = set(), set()
        f["wait"] = wait
        if f["unit"] in rd:
            rd[f["unit"]] |= reads
            wr[f["unit"]] |= writes
        f["_tag"] = tag
        out.append(f)
    return out


# -- ISA-level simulator ------------------------------------------------------------------
def to_u32(x):
    return np.asarray(x, dtype=F).view(np.uint32)


class Machine:
    def __init__(self, lay, kv, vm):
        self.lay = lay
        self.m = lay.m
        self.vm = vm.copy()
        self.kv = kv.copy()
        self.wrom = np.stack(lay.words).reshape(-1)
        self.crom = np.array(lay.crom, dtype=F)
        self.qcodes = np.stack(lay.qcodes)             # [words, BL, 32]
        self.hrom = np.stack(lay.hwords)               # [words, HE lanes] binary32
        self.qexp = np.stack(lay.qexp)                 # [words, BL]
        self.tokens = []
        self.eh = None
        self.argmax = None
        self.logits = []
        self.trace = {}

    def wrom_f32(self, e):
        return G.from_bits(self.wrom[e].astype(np.uint32) << 16)

    def run(self, prog, token, pos, stop=None):
        self.dyn = I.dyn_values(token, pos)
        self.token, self.pos = token, pos
        self.tokens.append(int(token))
        for n, f in enumerate(prog):
            if stop is not None and n >= stop:
                break
            f = {name: f.get(name, 0) for name, _ in I.FIELDS} | {"_tag": f.get("_tag", "")}
            if f["pred"] == I.PRED_ODD and not (pos & 1):
                continue
            if f["pred"] == I.PRED_NZ and pos == 0:
                continue
            {I.UNIT_ME: self.me, I.UNIT_SU: self.su, I.UNIT_QE: self.qe, I.UNIT_XU: self.xu,
             I.UNIT_HE: self.he}.get(
                f["unit"], lambda f: None)(f)
        return self.argmax

    # -- matrix engine (tools/hdc_program.py semantics, FP32 lane mode) ------------------
    def me(self, f):
        d = self.dyn
        n = f["me_nout"] + d[f["me_d_nout"]]
        tiles = f["me_tiles"] + d[f["me_d_tiles"]]
        K = f["me_k"] + d[f["me_d_k"]]
        if n == 0 or tiles == 0 or K == 0:
            return
        wb = f["me_wbase"] + d[f["me_d_wbase"]]
        xb = f["me_xbase"] + d[f["me_d_xbase"]]
        ob = f["me_obase"] + d[f["me_d_obase"]]
        split = 0 if f["me_wsrc"] else f["me_split"]
        S = 1 << split
        per_round = GR // S
        r, q, j, l = (a.reshape(-1) for a in np.meshgrid(np.arange(tiles), np.arange(per_round), np.arange(IL),
                                                         np.arange(W), indexing="ij"))
        t = r * per_round + q
        nidx = (t * IL + j) * W + l
        keep = (nidx < n) if f["me_mmode"] == 0 else (t * W + l < n)
        r, q, t, j, l, nidx = r[keep], q[keep], t[keep], j[keep], l[keep], nidx[keep]
        parts = []
        for c in range(S):
            g = q * S + c
            acc = np.zeros(len(t), dtype=F)
            for k in range(K):
                if f["me_wsrc"]:
                    word = wb + t * f["me_ts"] + k * f["me_ks"] + (j >> f["me_jsh"]) * f["me_js"]
                    w = self.kv[word * W + l]
                else:
                    word = wb + r * f["me_ts"] + k * f["me_ks"] + (j >> f["me_jsh"]) * f["me_js"]
                    w = self.wrom_f32(word * (W * GR) + g * W + l)
                x = self.vm[xb + c * f["me_xcs"] + k * f["me_xks"] + j * f["me_xjs"]]
                if f["me_round"]:
                    x = G.to_bf16(x)
                acc = G.add(acc, G.mul(w, x))
            parts.append(acc)
        while len(parts) > 1:
            parts = [G.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
        acc = parts[0]
        if f["me_oen"]:
            self.vm[(ob + t * f["me_ots"] + j * f["me_ojs"]) * W + l] = acc
        if f["me_amax"]:
            order = np.argsort(nidx)
            self.logits = acc[order]
            self.argmax = int(nidx[order][np.argmax(acc[order])])

    # -- hyper-connection projection engine ------------------------------------------------
    def he(self, f):
        """out[row] = sum_k w[row, k] * x[k], sequential from +0 (binary32)."""
        n, K = f["he_nout"], f["he_k"]
        acc = np.zeros(I.HE_LANES * IL, dtype=F)
        for k in range(K):
            w = self.hrom[f["he_wbase"] + k * IL: f["he_wbase"] + (k + 1) * IL].reshape(-1)
            acc = G.add(acc, G.mul(w, self.vm[f["he_xbase"] + k]))
        self.vm[f["he_obase"]:f["he_obase"] + n] = acc[:n]

    # -- stream unit -------------------------------------------------------------------------
    def addr(self, f, s, no, ni, idx=None):
        o, i = np.meshgrid(np.arange(no), np.arange(ni), indexing="ij")
        if s in "bd" and f["b_half"]:
            i = i >> 1
        base = f[f"{s}_base"] + self.dyn[f[f"{s}_d"]]
        if s == "a" and f["a_ind"] == I.IND_I:
            i = idx[i]
        if s == "a" and f["a_ind"] == I.IND_O:
            o = idx[o]
        return (base + o * f[f"{s}_so"] + i * f[f"{s}_si"]).reshape(-1)

    def fetch(self, f, s, e):
        src = f[f"{s}_src"]
        if src == I.SRC_VM:
            return self.vm[e]
        if src == I.SRC_CLO:
            return self.crom[e, 0]
        if src == I.SRC_CHI:
            return self.crom[e, 1]
        return self.wrom_f32(e)

    def su(self, f):
        d = self.dyn
        no = f["su_nout"] + d[f["su_d_nout"]]
        ni = f["su_nin"] + d[f["su_d_nin"]]
        if no == 0 or ni == 0:
            return
        idx = None
        if f["a_ind"]:
            cnt = ni if f["a_ind"] == I.IND_I else no
            idx = to_u32(self.vm[f["a_ibase"]:f["a_ibase"] + cnt]).astype(np.int64)
        ea = self.addr(f, "a", no, ni, idx)
        a = self.fetch(f, "a", ea)
        b = self.fetch(f, "b", self.addr(f, "b", no, ni))
        ec = ea ^ 1 if f["c_pair"] else self.addr(f, "c", no, ni)
        c = self.fetch(f, "c", ec)
        dd = self.fetch(f, "d", self.addr(f, "d", no, ni))
        imm1, imm2, imm3 = (u32f(f[k]) for k in ("imm1", "imm2", "imm3"))
        if f["a_rnd"]:
            a = G.to_bf16(a)
        if f["a_relu"]:
            a = np.maximum(a, F(0)).astype(F)
        if f["a_min"]:
            a = np.minimum(a, imm3).astype(F)
        if f["c_clip"]:
            c = np.clip(c, -imm3, imm3).astype(F)
        p = {I.M1_BYP: lambda: a, I.M1_AB: lambda: G.mul(a, b), I.M1_AA: lambda: G.mul(a, a),
             I.M1_AIMM: lambda: G.mul(a, imm1), I.M1_DIVB: lambda: V.div(a, b), I.M1_DIVIMM: lambda: V.div(a, imm1),
             I.M1_MAXB: lambda: np.maximum(a, b).astype(F)}[f["m1"]]()
        p = {I.M2_BYP: lambda: p, I.M2_C: lambda: G.mul(p, c), I.M2_IMM: lambda: G.mul(p, imm1)}[f["m2"]]()
        par = np.tile(np.arange(ni) & 1, no)
        qd = {I.QM_OFF: None, I.QM_POS: dd, I.QM_NEG: G.neg(dd),
              I.QM_ALT_NP: np.where(par == 0, G.neg(dd), dd).astype(F),
              I.QM_ALT_PN: np.where(par == 0, dd, G.neg(dd)).astype(F)}[f["qm"]]
        q = None if qd is None else G.mul(c, qd)
        r = {I.AD_BYP: lambda: p, I.AD_Q: lambda: G.add(p, q), I.AD_C: lambda: G.add(p, c),
             I.AD_NEGB: lambda: G.add(p, G.neg(b)), I.AD_IMM: lambda: G.add(p, imm2),
             I.AD_D: lambda: G.add(p, dd)}[f["ad"]]()

        def egate(x):
            mag = V.sqrt(np.maximum(np.abs(x), F(1e-6)).astype(F))
            return V.sigmoid(np.where(x < 0, G.neg(mag), mag).astype(F))

        s = {I.SFU_NONE: lambda: r, I.SFU_EXP: lambda: G.exp(r), I.SFU_RSQRT: lambda: G.rsqrt(r),
             I.SFU_SQRT: lambda: V.sqrt(r), I.SFU_SIGM: lambda: V.sigmoid(r), I.SFU_SILU: lambda: V.silu(r),
             I.SFU_SPSQRT: lambda: V.sqrt(V.softplus(r)), I.SFU_EGATE: lambda: egate(r)}[f["sfu"]]()
        t = {I.E1_BYP: lambda: s, I.E1_MULC: lambda: G.mul(s, c), I.E1_ADDC: lambda: G.add(s, c),
             I.E1_MULIMM: lambda: G.mul(s, imm2), I.E1_ADDIMM: lambda: G.add(s, imm2)}[f["e1"]]()
        u = {I.E2_BYP: lambda: t, I.E2_MULB: lambda: G.mul(t, b), I.E2_MULIMM: lambda: G.mul(t, imm1)}[f["e2"]]()
        out = np.asarray(u, dtype=F).reshape(-1)
        if f["rnd"]:
            out = G.to_bf16(out)
        if f["red"]:
            v = G.mul(out, out) if f["red_sq"] else out
            segs = v.reshape(1, -1) if f["red_whole"] else v.reshape(no, ni)
            vals = []
            for sg in segs:
                if f["red"] == I.RED_SUM:
                    vals.append(G.reduce_sum(sg))
                elif f["red"] == I.RED_MAX:
                    vals.append(np.max(sg))
                else:
                    acc = F(0)
                    for x in sg:
                        acc = G.add(acc, x)
                    vals.append(acc)
            vals = np.asarray(vals, dtype=F)
            if f["red_rnd"]:
                vals = G.to_bf16(vals)
            for k, x in enumerate(vals):
                self.vm[f["r_base"] + k * f["r_so"]] = x
        if f["dst"]:
            if f["dst"] == I.DST_KVT:
                o, i = np.meshgrid(np.arange(no), np.arange(ni), indexing="ij")
                row = self.dyn[f["o_d"]] + o
                ed = (f["o_base"] + (row >> 4) * (HD * W) + i * W + (row & 15)).reshape(-1)
            else:
                ed = self.addr(f, "o", no, ni)
            if f["dst"] == I.DST_VM:
                self.vm[ed] = out
            else:
                self.kv[ed] = G.to_bf16(out)

    # -- quantised engine ----------------------------------------------------------------------
    def qe(self, f):
        nb = f["qe_nb"]
        x = self.vm[f["qe_xbase"]:f["qe_xbase"] + nb * 32]
        ob = f["qe_obase"] + self.dyn[f["qe_d_obase"]]
        mode = f["qe_mode"]
        if mode == I.QE_QDQ8:
            self.vm[ob:ob + nb * 32] = V.qdq_fp8(x)
            return
        if mode == I.QE_QDQ4:
            self.vm[ob:ob + nb * 32] = V.qdq_fp4_e8m0(x)
            return
        if mode == I.QE_QDQ4E:
            self.vm[ob:ob + nb * 32] = V.qdq_fp4_e4m3(x, 16)
            return
        xq, xe = V.quant_fp8(x)
        wb = f["qe_wbase"]
        if f["qe_ind"]:
            wb += int(to_u32(self.vm[f["qe_ibase"]])) * f["qe_istride"]
        n, rounds = f["qe_nout"], f["qe_tiles"]
        table = V.E2M1 if f["qe_fp4"] else V.E4M3
        for rr in range(rounds):
            for j in range(IL):
                rows = (rr * IL + j) * BL + np.arange(BL)
                acc = np.zeros(BL, dtype=F)
                for kb in range(nb):
                    word = wb + (rr * nb + kb) * IL + j
                    codes = self.qcodes[word]
                    wv = table[codes & (15 if f["qe_fp4"] else 255)]
                    dsum = (wv @ xq[kb * 32:(kb + 1) * 32]).astype(F)
                    acc = G.add(acc, np.ldexp(dsum, self.qexp[word] + xe[kb]).astype(F))
                y = G.to_bf16(acc)
                ok = rows < n
                self.vm[f["qe_obase"] + rows[ok]] = y[ok]

    # -- auxiliary unit ---------------------------------------------------------------------------
    def xu(self, f):
        op = f["xu_op"]
        if op == I.XU_SEL:
            n = f["xu_n"] + self.dyn[f["xu_d_n"]]
            k = min(f["xu_k"] + self.dyn[f["xu_d_k"]], n)
            if n == 0:
                return
            vals = self.vm[f["xu_src"]:f["xu_src"] + n]
            sel = sorted(int(i) for i in V.topk_lowest_index(vals, k))
            self.vm[f["xu_dst"]:f["xu_dst"] + k] = np.array(sel, dtype=np.uint32).view(F)
        elif op == I.XU_SINK:
            e = self.vm[f["xu_src"]:f["xu_src"] + 16].reshape(4, 4)
            self.vm[f["xu_dst"]:f["xu_dst"] + 16] = sinkhorn(e, self.m).reshape(-1)
        elif op == I.XU_EHASH:
            self.eh = [self.m.engram.hashes(self.tokens, li) for li in range(len(self.m.engram.layer_ids))]
        elif op == I.XU_EGATHER:
            li = f["xu_layer"]
            L = self.m.engram.layer_ids[li]
            ids = self.eh[li] + f["xu_src"]          # the layer's table base in the Engram ROM
            rows = G.to_bf16((V.E4M3[self.lay.ecodes[ids]] * np.exp2(self.lay.eexp[ids])[:, None]).astype(F))
            self.vm[f["xu_dst"]:f["xu_dst"] + rows.size] = rows.reshape(-1)


def sinkhorn(e, m):
    """hdc_golden_v41.Model.hc_mixes after the exponential."""
    h = 4
    rs = V.seqsum([e[:, k] for k in range(h)])
    comb = G.add(V.div(e, rs[:, None]), m.hc_eps)

    def cols(cm):
        cs = V.seqsum([cm[j, :] for j in range(h)])
        return V.div(cm, G.add(cs, m.hc_eps)[None, :])

    def rows(cm):
        rs = V.seqsum([cm[:, k] for k in range(h)])
        return V.div(cm, G.add(rs, m.hc_eps)[:, None])

    comb = cols(comb)
    for _ in range(m.sinkhorn_iters - 1):
        comb = cols(rows(comb))
    return comb


# -- golden state, images --------------------------------------------------------------------
def golden_prefill(model, prompt):
    st = model.new_state()
    for p, t in enumerate(prompt):
        model.decode_token(t, p, st)
    return st


def hexwords(values, width_bits):
    digits = width_bits // 4
    return "".join(f"{int(v):0{digits}x}\n" for v in values)


def pack_lanes(lanes, bits_per_lane):
    word = 0
    for i, v in enumerate(lanes):
        word |= int(v) << (bits_per_lane * i)
    return word


QLANE_BITS = 256 + 16          # 32 codes, then the block exponent (signed, 16 bits)
EROW_BITS = 256 + 8


def write_images(out, lay, prog, roms_from=None):
    out.mkdir(parents=True, exist_ok=True)
    words = [I.encode(**{k: v for k, v in f.items() if not k.startswith("_")}) for f in prog]
    (out / "prog.hex").write_text(hexwords(words, I.INSTR_BITS))
    (out / "prog_tags.txt").write_text("".join(f"{n} {f['_tag']}\n" for n, f in enumerate(prog)))
    if roms_from:                       # debug: reuse another image directory's ROMs
        for n in ("wrom.hex", "hrom.hex", "crom.hex", "qrom.hex", "erom.hex"):
            (out / n).unlink(missing_ok=True)
            (out / n).symlink_to(Path(roms_from).resolve() / n)
        return len(words)
    (out / "wrom.hex").write_text(hexwords((pack_lanes(w, 16) for w in lay.words), 16 * W * GR))
    (out / "hrom.hex").write_text(hexwords((pack_lanes(G.bits(w), 32) for w in lay.hwords), 32 * I.HE_LANES))
    (out / "crom.hex").write_text(hexwords(((f32(hi) << 32) | f32(lo) for lo, hi in lay.crom), 64))
    qw = []
    for cw, ew in zip(lay.qcodes, lay.qexp):
        lanes = [pack_lanes(cw[l], 8) | ((int(ew[l]) & 0xFFFF) << 256) for l in range(BL)]
        qw.append(pack_lanes(lanes, QLANE_BITS))
    (out / "qrom.hex").write_text(hexwords(qw, QLANE_BITS * BL))
    with open(out / "erom.hex", "w") as fh:
        for codes, e in zip(lay.ecodes, lay.eexp):
            fh.write(f"{(pack_lanes(codes, 8) | ((int(e) & 0xFF) << 256)):066x}\n")
    words = [I.encode(**{k: v for k, v in f.items() if not k.startswith("_")}) for f in prog]
    (out / "prog.hex").write_text(hexwords(words, I.INSTR_BITS))
    (out / "prog_tags.txt").write_text("".join(f"{n} {f['_tag']}\n" for n, f in enumerate(prog)))
    return len(words)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, help="write RTL images and expectations here")
    ap.add_argument("--context", type=int, help="decode at position N-1 of the oracle prompt cycled to N tokens")
    ap.add_argument("--multi", type=int, default=0,
                    help="also run the ISA model from an empty state over the prompt and K generated tokens")
    ap.add_argument("--stop", type=int, help="debug: run only this many instructions")
    ap.add_argument("--roms-from", type=Path, help="debug: symlink the ROM images from this directory")
    ap.add_argument("--check-layers", action="store_true", help="debug: compare the residual after every layer")
    args = ap.parse_args()
    model = V.Model()
    prompt, expected = V.prompt_and_expected()
    if args.context:
        prompt = (list(prompt) * (-(-args.context // len(prompt))))[:args.context]
    lay = Layout(model)
    prog = Builder(lay).build()
    if args.stop is not None:
        prog = prog[:args.stop] + [dict(unit=I.UNIT_END, wait=31, _tag="end")]
    for f in prog:                                    # every field fits its width
        I.encode(**{k: v for k, v in f.items() if not k.startswith("_")})
    token, pos = prompt[-1], len(prompt) - 1
    st = golden_prefill(model, prompt[:-1])
    kv, vm = lay.kv_image(st), lay.vm_image(st, pos)
    mach = Machine(lay, kv, vm)
    mach.tokens = list(prompt[:-1])
    got = mach.run(prog, token, pos)
    trace = {}
    ref = model.decode_token(token, pos, copy.deepcopy(st), trace)
    exact = bool(len(mach.logits) and np.array_equal(G.bits(mach.logits), G.bits(ref)))
    gold_tok = int(np.argmax(ref))
    counts = {u: sum(1 for f in prog if f["unit"] == u) for u in I.UNITS}
    print(f"program: {len(prog)} instructions (ME {counts[1]}, SU {counts[2]}, QE {counts[3]}, XU {counts[4]}, "
          f"HE {counts[5]}); "
          f"ME ROM {len(lay.words)} words; QE ROM {len(lay.qcodes)} words; CROM {len(lay.crom)}")
    print(f"ISA simulator at pos {pos}: token {got} golden {gold_tok} oracle {expected[0] if not args.context else '-'};"
          f" logits bit-exact with golden: {exact}")
    if not exact and len(mach.logits):
        bad = np.nonzero(G.bits(mach.logits) != G.bits(ref))[0]
        print("  mismatching logits:", len(bad), "first", bad[:5])
    ok = (exact and got == gold_tok) or args.stop is not None
    multi = None
    if args.multi:
        m2 = Machine(lay, np.zeros_like(kv), np.zeros_like(vm))
        gst = model.new_state()
        seq = list(V.prompt_and_expected()[0])
        outs, gouts, allexact = [], [], True
        for p in range(len(seq) + args.multi - 1):
            tok = seq[p]
            a = m2.run(prog, tok, p)
            lg = model.decode_token(tok, p, gst)
            allexact &= bool(np.array_equal(G.bits(m2.logits), G.bits(lg)))
            if p >= len(seq) - 1:
                outs.append(a)
                gouts.append(int(np.argmax(lg)))
                seq.append(a)
        multi = dict(generated=outs, golden=gouts, all_logits_exact=allexact, steps=len(seq) - 1)
        multi_state = (m2.vm.copy(), m2.kv.copy())
        print("multi-token from empty state: ISA", outs, "golden", gouts, "oracle", expected[:args.multi],
              "every step's logits bit-exact:", allexact)
        ok &= allexact and outs == gouts
    if args.out:
        out = args.out
        n_words = write_images(out, lay, prog, args.roms_from)
        (out / "kv.hex").write_text(hexwords(G.bits(kv).reshape(-1), 32))
        (out / "vm_init.hex").write_text(hexwords(G.bits(vm), 32))
        (out / "expect_logits.hex").write_text(hexwords(G.bits(mach.logits), 32))
        (out / "expect_vm.hex").write_text(hexwords(G.bits(mach.vm), 32))
        (out / "expect_kv.hex").write_text(hexwords(G.bits(mach.kv).reshape(-1), 32))
        prime = [int(model.engram.token_map[t]) for t in prompt[:-1]][-3:]
        (out / "prime.hex").write_text(hexwords(prime, 16))
        seqp = list(V.prompt_and_expected()[0])
        (out / "prompt.hex").write_text(hexwords(seqp, 16))
        (out / "generated.hex").write_text(hexwords(multi["generated"] if multi else expected, 16))
        if multi:
            (out / "expect_multi_vm.hex").write_text(hexwords(G.bits(multi_state[0]), 32))
            (out / "expect_multi_kv.hex").write_text(hexwords(G.bits(multi_state[1]).reshape(-1), 32))
        (out / "run.args").write_text(f"+TOKEN={token} +POS={pos} +EXPECT={got} +NPRIME={len(prime)} "
                                      f"+PFIRST={int(pos <= 3)}\n")
        (out / "expect.json").write_text(json.dumps({
            "token": token, "pos": pos, "argmax": got, "golden": gold_tok, "oracle": expected[0],
            "prog_words": n_words, "wrom_words": len(lay.words), "qrom_words": len(lay.qcodes),
            "crom_words": len(lay.crom), "erom_words": len(lay.ecodes), "multi": multi,
            "vm_map": lay.vm.map, "kv_map": lay.kv.map}))
        print("wrote", out)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
