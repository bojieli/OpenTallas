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
# before the SiLU of routed expert MOE_HOOK (k_exp: after the last).  Swept with
# tools/hdc_timing_v41.py: late enough that the HE's chain (80 x 8 cycles with
# the 8-chunk split) has run, early enough that the Sinkhorn (the routed unit,
# 41 steps x 7 core cycles) hides behind the rest.
ATTN_HOOK = "scores"
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

    def __init__(self, m, mtp=None):
        """mtp: None (the one-position core), or {"slots": NS} -- the multi-token-
        prediction configuration: NS position slots, each with its own copy of
        every per-position vector-memory region (slot j's at + j*slot_stride),
        the compressor slot ring of I.POS_RING entries, the DSpark stages'
        weights, constants and window caches, RoPE tables to I.ROPE_POS."""
        self.m = m
        c = m.c
        self.mtp = mtp
        self.L, self.dim, self.hc = m.L, m.dim, m.hc
        self.nh, self.ih = m.heads, m.ih
        assert m.hd == HD and m.ihd == HD and m.rd == 4 and m.window >= PMAX
        self.ring = mtp.get("ring", I.POS_RING) if mtp else 2   # "ring": 2 only as a mutation check
        self.nmtp = m.n_mtp if mtp else 0
        self.rope_pos = I.ROPE_POS if mtp else PMAX
        layers = range(self.L + self.nmtp)
        # -- vector memory ------------------------------------------------------
        v = self.vm = Alloc(I.VM_ELEMS_MTP if mtp else I.VM_ELEMS)
        scratch = [("H", 640), ("T", 640), ("SSX", 1), ("RF", 1), ("MIX", 32), ("PA", 4), ("POA", 4),
                   ("CA", 16), ("PF", 4), ("POF", 4), ("CF", 16), ("CRAW", 16), ("M4", 4), ("E16", 32),
                   ("X", 160), ("XN", 160), ("SS", 8), ("RS", 8), ("QA", 32), ("QR", 32), ("KVA", 32),
                   ("KVN", 32), ("KVQ", 32), ("Q", 2048), ("S", self.nh * STR), ("M", 64), ("Z", 64),
                   ("DEN", 64), ("ACC", 2048), ("ZA", 256), ("Y", 160),
                   ("CM", 32), ("CE", 64), ("CD", 32), ("CP", 64), ("POOL", 32), ("CKA", 32), ("LAT", 32),
                   ("IKA", 32), ("IKN", 32), ("IKQ", 32), ("IQ", 1024), ("IQQ", 1024), ("WP", 32),
                   ("WTS", 32), ("IS", 128), ("SEL", 16),
                   ("G12", 16), ("SC", 16), ("BI", 16), ("EID", 8), ("TOT", 1), ("DEN1", 1), ("WGT", 8),
                   ("ER", 768), ("EKV", 800), ("ESS", 8), ("ERS", 8), ("ED", 4), ("EDOT", 4), ("EG", 4)]
        if mtp:
            # per slot: the Engram rows of both Engram layers (gathered at the slot's
            # hash), the DSpark main hidden (3 x dim) and main_x; S (scores) is shared:
            # attention runs one slot at a time
            scratch = [(n, k) for n, k in scratch if n not in ("S", "ER")] + \
                      [(f"ER{L}", 768) for L in m.engram.layer_ids] + \
                      [("MH", self.dim * len(m.dspark_targets)), ("MXA", self.dim), ("MX", self.dim)]
        for name, n in scratch:
            v(name, n)
        for k in range(7):
            v(f"GU{k}", 128)
            v(f"ACT{k}", 64)
            v(f"E{k}", 160)
        self.scratch_names = {n for n, _ in scratch} | {f"{x}{k}" for x in ("GU", "ACT", "E") for k in range(7)}
        if mtp:
            v.top = -(-v.top // 32) * 32
            self.slot_stride = v.top
            self.nslots = mtp["slots"]
            assert self.nslots <= I.NSLOT and (self.nslots + 1 <= self.ring or mtp.get("mutation"))
            v.top = self.slot_stride * self.nslots
            # shared by the slots (used one slot at a time): scores, the draft's
            # logits and Markov bias, the Markov embedding row, the draft tokens
            for name, n in (("S", self.nh * STR), ("LG", 4048), ("MB", 4048), ("MBX", 32), ("DTOK", 8)):
                v(name, n)
        # persistent: compressor slots and compressed KV rows per source layer
        self.nrows = {s: PMAX // (m.ratio[s]) for s in m.kv_src}
        for s in m.kv_src:
            v(f"SLOT{s}", 64 * self.ring)
            v(f"CKV{s}", self.nrows[s] * HD)
        self.vm_persist = [(self.vm.map[f"SLOT{s}"], 64 * self.ring) for s in m.kv_src] + \
                          [(self.vm.map[f"CKV{s}"], self.nrows[s] * HD) for s in m.kv_src]
        # -- KV SRAM (elements; W per word) ---------------------------------------------
        k = self.kv = Alloc(I.KV_WORDS * W, align=W)
        for L in layers:
            k(f"KT{L}", KT_WORDS * W)
            k(f"KR{L}", KR_WORDS * W)
        for s in m.kv_src:
            k(f"IK{s}", (self.nrows[s] // W) * HD * W)
        # -- constant ROM -------------------------------------------------------------------
        self.crom = []
        self.cb = {}
        lw = m.lw
        for L in layers:
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
        if mtp:
            self.cb["main_norm"] = self.put(m.w["mtp.0.main_norm.weight"])
            self.cb["mtp_norm"] = self.put(lw(self.L + self.nmtp - 1, "norm.weight"))
        for tname, fr in (("rope_plain", m.freqs_plain), ("rope_yarn", m.freqs_yarn)):
            self.cb[tname] = len(self.crom)
            for p in range(self.rope_pos):
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
        if mtp:
            # the Markov head's embedding, element-addressed like the embedding (SU gather)
            memb = lw(self.L + self.nmtp - 1, "markov_head.embed.weight")
            self.memb_word = len(self.words)
            flat = (G.bits(memb.reshape(-1)) >> 16).astype(np.uint16)
            for i in range(0, len(flat), W * GR):
                wd = np.zeros(W * GR, dtype=np.uint16)
                wd[:len(flat[i:i + W * GR])] = flat[i:i + W * GR]
                self.words.append(wd)
        for L in layers:
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
        if mtp:
            self.mat["markov"] = self.place(lw(self.L + self.nmtp - 1, "markov_head.head.weight"))
        # -- QE weight ROM: per word BL lanes x (32 codes, exponent) -------------------
        self.qcodes, self.qexp = [], []
        self.qmat = {}
        for L in layers:
            for nm in ("wq_a", "wkv", "wq_b", "wo_b"):
                self.qmat[(L, nm)] = self.qplace(lw(L, f"attn.{nm}.weight"))
            if L in m.idx_src:
                self.qmat[(L, "iwq_b")] = self.qplace(lw(L, "attn.indexer.wq_b.weight"))
            base = len(self.qcodes)
            n_exp = m.n_exp if L < self.L else m.dspark_n_exp
            for e in range(n_exp):
                self.qexpert(f"{m.P(L)}ffn.experts.{e}.", (L, "exp", e))
            self.qmat[(L, "exp_base")] = base
            self.qmat[(L, "exp_stride")] = self.qmat[(L, "exp", 1, "w13")]["base"] - self.qmat[(L, "exp", 0, "w13")]["base"]
            for e in range(1, n_exp):
                assert self.qmat[(L, "exp", e, "w13")]["base"] - base == e * self.qmat[(L, "exp_stride")]
            self.qexpert(f"{m.P(L)}ffn.shared_experts.", (L, "shared"))
            if L in m.engram.layer_ids:
                self.qmat[(L, "ewkv")] = self.qplace(lw(L, "engram.wkv.weight"))
        if mtp:
            self.qmat["main_proj"] = self.qplace(m.w["mtp.0.main_proj.weight"])
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

    def slot_map(self, j):
        """The vector-memory map slot j's instructions address."""
        if not self.mtp:
            return self.vm.map
        return {n: a + (j * self.slot_stride if n in self.scratch_names else 0) for n, a in self.vm.map.items()}

    def rname(self, name, j):
        """A region's hazard name: per-slot regions are distinct per slot."""
        return f"{name}#{j}" if self.mtp and name in self.scratch_names else name

    def put(self, v):
        base = len(self.crom)
        self.crom.extend((F(x), F(0)) for x in np.asarray(v, dtype=F).reshape(-1))
        return base

    # ME placement: words in (round, k', slot) order; lane g*W+l of group g = q*S + c
    # holds row_of(t, j, l), column c*kc + k' of tile t = round*(GR/S) + q
    def place_rows(self, w, row_of, tiles_total, split=1):
        n, k = w.shape
        kc = k // split
        assert kc * split == k
        per_round = GR // split
        rounds = -(-tiles_total // per_round)
        base = len(self.words)
        wb = (G.bits(np.asarray(w, dtype=F)) >> 16).astype(np.uint16)
        for r in range(rounds):
            for kk in range(kc):
                for j in range(IL):
                    word = np.zeros(W * GR, dtype=np.uint16)
                    for g in range(GR):
                        q, c = divmod(g, split)
                        t = r * per_round + q
                        for l in range(W):
                            row = row_of(t, j, l)
                            if 0 <= row < n:
                                word[g * W + l] = wb[row, c * kc + kk]
                    self.words.append(word)
        return dict(base=base, n=n, k=kc, tiles=rounds, split=split)

    def place(self, w):
        """A matrix with the golden's engine split (hdc_golden_v41.mv)."""
        n, k = w.shape
        return self.place_rows(w, lambda t, j, l: (t * IL + j) * W + l, -(-n // (W * IL)),
                               G.split_for(n, k, GR, W, IL))

    def place_wo_a(self, w):
        """Grouped wo_a: slot j is group j, tile t its rows t*W .. t*W+15, so every
        slot reads its own group's 256 attention outputs (xjs = 256), in
        WO_A_SPLIT chunks (xcs = the chunk length)."""
        o_rank = self.m.o_rank
        assert w.shape == (self.m.groups * o_rank, 256) and self.m.groups == IL
        return self.place_rows(w, lambda t, j, l: j * o_rank + t * W + l if t * W + l < o_rank else -1,
                               o_rank // W, V.WO_A_SPLIT)

    def hplace(self, w):
        """HE placement (FP32 weights), K in HC_SPLIT chunks of kc: word k'*IL + j
        holds, in lane c*NL + l, row j*NL + l at column c*kc + k'."""
        n, k = w.shape
        S, NL = V.HC_SPLIT, I.HE_LANES
        kc = k // S
        assert n <= NL * IL and kc * S == k
        base = len(self.hwords)
        wf = np.zeros((NL * IL, k), dtype=F)
        wf[:n] = w
        for kk in range(kc):
            for j in range(IL):
                self.hwords.append(np.concatenate([wf[j * NL:(j + 1) * NL, c * kc + kk] for c in range(S)]))
        return dict(base=base, n=n, k=kc)

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
        wins = list(st["win"]) + (list(st["dsk"]) if self.mtp and "dsk" in st else [])
        for L, rows in enumerate(wins):
            for t, row in enumerate(rows):
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
        vm = np.zeros(self.vm.size, dtype=F)
        for s in self.m.kv_src:
            for i, (kv, sc) in enumerate(st["slots"][s]):
                slot = (pos - len(st["slots"][s]) + i) % self.ring
                vm[self.vm.map[f"SLOT{s}"] + slot * 64: self.vm.map[f"SLOT{s}"] + slot * 64 + 64] = \
                    np.concatenate([kv, sc])
            for t, row in enumerate(st["ckv"][s]):
                vm[self.vm.map[f"CKV{s}"] + t * HD: self.vm.map[f"CKV{s}"] + (t + 1) * HD] = row
        return vm


# -- program -------------------------------------------------------------------------
SCALAR_SFU = (I.SFU_RSQRT, I.SFU_SQRT, I.SFU_SPSQRT, I.SFU_EGATE)   # lane 0 only
DYN_GUESS = 16                   # a count taken from a DYN value: assume a short context


def su_vec_mode(f, lanes=None):
    """The stream unit's lane axis for one op: SCALAR where only lane 0 can do the
    op (lane-0-only SFU functions, SEQ, the whole-op P=8 reduction), VEC_O where
    each segment must stay in one lane (a per-segment reduction or the segmented
    tree), else whichever axis issues fewer vectors (VEC_I on a tie)."""
    lanes = lanes or I.SU_LANES
    if f.get("sfu", 0) in SCALAR_SFU or f.get("red", 0) == I.RED_SEQ or \
            (f.get("red_whole", 0) and not f.get("red_tree", 0)):
        return I.VEC_SCALAR
    no = f.get("su_nout", 0) or DYN_GUESS
    ni = f.get("su_nin", 0) or DYN_GUESS
    if f.get("red", 0) or f.get("red_tree", 0):
        return I.VEC_O if no > 1 else I.VEC_SCALAR
    vi, vo = no * -(-ni // lanes), -(-no // lanes) * ni
    if min(vi, vo) == no * ni:
        return I.VEC_SCALAR
    return I.VEC_I if vi <= vo else I.VEC_O


def segmented(f, segs):
    """An op over n elements whose sum (of squares) is one long sum, cut into
    `segs` contiguous segments of n/segs (one per outer index, so every lane owns
    one) and summed by the segment tree: the golden's split_sum."""
    n = f["su_nin"]
    assert f.get("su_nout", 1) == 1 and n % segs == 0 and f.get("red") == I.RED_SUM
    f = dict(f, su_nout=segs, su_nin=n // segs, red_tree=1)
    for x in "abcdo":
        f[f"{x}_so"] = f.get(f"{x}_si", 0) * (n // segs)
    return f


class Builder:
    def __init__(self, lay, qchunk=None, slot=0):
        """qchunk (HBM weights): a LINQ op of more than qchunk words is issued as
        chunks of whole rounds, so its start threshold fits the QE streamer's
        window (rounds are independent output rows; each chunk re-quantises the
        same activation, deterministically).

        slot (MTP layouts): the position slot this builder's instructions serve:
        its vector-memory copy, its DYN bank (dslot), its region names."""
        self.qchunk = qchunk
        self.lay, self.m = lay, lay.m
        self.prog = []
        self.slot = slot
        self.V = lay.slot_map(slot)
        self.K = lay.kv.map
        self.serial_id = None           # MTP: the serial section an op belongs to
        self.n_serial = 0
        self.dslot_over = None          # MTP: an op's DYN bank, when not its own slot's

    def emit(self, f, reads, writes, tag):
        f = dict(f)
        if self.lay.mtp:
            f.setdefault("dslot", self.slot if self.dslot_over is None else self.dslot_over)
            f["_serial"], f["_slot"] = self.serial_id, self.slot
            if f.get("wrel"):
                # the slots' SELECTs interleave, so a later one no longer proves this
                # slot's ids written: a release waits for the XU itself (HBM fetch list)
                f["wait"] = f.get("wait", 0) | 1 << (I.UNIT_XU - 1)
            if "_redw" in f:
                f["_redw"] = {self.lay.rname(n, self.slot) for n in f["_redw"]}
            reads = {self.lay.rname(n, self.slot) for n in reads}
            writes = {self.lay.rname(n, self.slot) for n in writes}
        self.prog.append((f, set(reads), set(writes), tag))

    def serial(self, on):
        """MTP: the ops emitted between serial(True) and serial(False) run for one
        slot after another, as a block (attention over shared scores, a slot's
        hash then its gathers, the draft's sampling chain)."""
        if on:
            self.serial_id = self.n_serial
            self.n_serial += 1
        else:
            self.serial_id = None

    def me(self, mat, x, out, reads, writes, tag, **over):
        f = dict(unit=I.UNIT_ME, me_nout=mat["n"], me_tiles=mat["tiles"], me_k=mat["k"], me_wsrc=0,
                 me_wbase=mat["base"], me_ts=mat["k"] * IL, me_ks=IL, me_js=1, me_xbase=x, me_xks=1,
                 me_round=1, me_obase=out // W, me_ots=IL, me_ojs=1, me_oen=1, me_xcs=mat["k"],
                 me_split=mat.get("split", 1).bit_length() - 1)
        f.update(over)
        self.emit(f, reads, writes, tag)

    def su(self, reads, writes, tag, **f):
        f = dict(f, unit=I.UNIT_SU)
        f.setdefault("su_vec", su_vec_mode(f))
        if f.get("red"):                             # the region the reducer writes
            f["_redw"] = {self.region_of(f.get("r_base", 0))} & set(writes)
            assert f["_redw"], (tag, f.get("r_base"))
        self.emit(f, reads, writes, tag)

    def region_of(self, addr):
        name, base = max(((n, b) for n, b in self.V.items() if b <= addr), key=lambda nb: nb[1])
        return name

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
        self.su({src}, {dst}, tag, **segmented(dict(pred=pred, su_nout=1, su_nin=n, a_base=self.V[src], a_si=1,
                                                     red=I.RED_SUM, red_sq=1, r_base=self.V[dst]), V.RMS_SPLIT))

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
            f = segmented(dict(f, red=I.RED_SUM, red_sq=1, r_base=self.V[sq]), V.RMS_SPLIT)
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
        rw = f["qe_nb"] * IL                               # words per round
        if self.qchunk and f["qe_tiles"] * rw > self.qchunk:
            rc = max(1, self.qchunk // rw)
            for r0 in range(0, f["qe_tiles"], rc):
                c = dict(f, qe_tiles=min(rc, f["qe_tiles"] - r0), qe_wbase=f["qe_wbase"] + r0 * rw,
                         qe_obase=f["qe_obase"] + r0 * IL * BL, qe_nout=f["qe_nout"] - r0 * IL * BL)
                self.qe(reads | {x}, writes | {out}, tag, **c)
            return
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
        self.su({"H", pre, "T"}, {dst, ss}, tag, **segmented(dict(
            su_nout=1, su_nin=160, a_base=h + 480, a_si=1, b_base=V_[pre] + 3, m1=I.M1_AB, c_base=V_["T"],
            c_si=1, ad=I.AD_C, rnd=1, dst=I.DST_VM, o_base=V_[dst], o_si=1, red=I.RED_SUM, red_sq=1,
            r_base=V_[ss]), V.RMS_SPLIT))

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
                dst=I.DST_VM, o_base=h, o_so=160, o_si=1, red=I.RED_SUM, red_sq=1, red_tree=1,
                r_base=V_["SSX"])

    def engram(self, L):
        m, V_, lay = self.m, self.V, self.lay
        t = f"L{L}.engram"
        li = m.engram.layer_ids.index(L)
        h = V_["H"]
        er = f"ER{L}" if self.lay.mtp else "ER"
        if not self.lay.mtp:
            self.xu({"EH"}, {"ER"}, t, xu_op=I.XU_EGATHER, xu_src=lay.ebase[L], xu_dst=V_["ER"], xu_layer=li,
                    xu_n=24)
        self.linq(lay.qmat[(L, "ewkv")], er, "EKV", set(), set(), t)
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
                dst=I.DST_VM, o_base=h, o_so=160, o_si=1, red=I.RED_SUM, red_sq=1, red_tree=1,
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
            # the ring: a position's slot entry at (pos mod ring)*64; an odd position
            # pools its pair (pos-1, pos), at DYN SLOTP8 (ring > 2) or 0
            ring8 = self.lay.ring > 2
            self.me(mat, V_["XN"], V_[slot], {"XN"}, {slot}, t, me_d_obase=DY["SLOTW8" if ring8 else "SLOTW"])
            sp = DY["SLOTP8"] if ring8 else 0
            s0, s1 = V_[slot], V_[slot] + 64
            self.su({slot}, {"CM"}, t, pred=pred, su_nout=1, su_nin=32, a_base=s0 + 32, a_si=1, b_base=s1 + 32,
                    b_si=1, m1=I.M1_MAXB, dst=I.DST_VM, o_base=V_["CM"], o_si=1, a_d=sp, b_d=sp)
            self.su({slot, "CM"}, {"CE"}, t, pred=pred, su_nout=2, su_nin=32, a_base=s0 + 32, a_so=64, a_si=1,
                    b_base=V_["CM"], b_si=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, dst=I.DST_VM, o_base=V_["CE"],
                    o_so=32, o_si=1, a_d=sp)
            self.su({"CE"}, {"CD"}, t, pred=pred, su_nout=1, su_nin=32, a_base=V_["CE"], a_si=1,
                    c_base=V_["CE"] + 32, c_si=1, ad=I.AD_C, dst=I.DST_VM, o_base=V_["CD"], o_si=1)
            self.su({"CE", "CD"}, {"CP"}, t, pred=pred, su_nout=2, su_nin=32, a_base=V_["CE"], a_so=32, a_si=1,
                    b_base=V_["CD"], b_si=1, m1=I.M1_DIVB, dst=I.DST_VM, o_base=V_["CP"], o_so=32, o_si=1)
            self.su({slot, "CP"}, {"POOL", "SS"}, t, **segmented(dict(
                pred=pred, su_nout=1, su_nin=32, a_base=s0, a_si=1, b_base=V_["CP"], b_si=1, m1=I.M1_AB,
                c_base=s1, c_si=1, d_base=V_["CP"] + 32, d_si=1, qm=I.QM_POS, ad=I.AD_Q, rnd=1, dst=I.DST_VM,
                o_base=V_["POOL"], o_si=1, red=I.RED_SUM, red_sq=1, r_base=V_["SS"], a_d=sp, c_d=sp), V.RMS_SPLIT))
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
        rnds16 = DY["RND16_N2"] if r == 2 else DY["RND16_POS1"]
        for hb in range(0, m.ih, IL * GR):         # 4 head groups of 8 heads: one 16-row tile per round
            self.me(dict(n=0, tiles=0, k=HD, base=self.K[f"IK{src}"] // W), V_["IQQ"] + hb * HD,
                    V_["S"] + hb * STR, {"IQQ", f"IK{src}"}, {"S"}, t, pred=pred, me_xcs=IL * HD, me_wsrc=1,
                    me_ts=HD, me_ks=1, me_js=0, me_jsh=3, me_xks=1, me_xjs=HD, me_ots=1, me_ojs=STR // W,
                    me_mmode=1, me_d_nout=nsel, me_d_tiles=rnds16, me_hg=2, me_ogs=IL * STR // W)
        self.su({"S", "WTS"}, {"IS"}, t, pred=pred, su_nout=0, su_d_nout=nsel, su_nin=m.ih, a_base=V_["S"], a_so=1,
                a_si=STR, a_rnd=1, a_relu=1, b_base=V_["WTS"], b_si=1, m1=I.M1_AB, rnd=1, red=I.RED_SUM,
                red_rnd=1, r_base=V_["IS"], r_so=1)
        self.xu({"IS"}, {"SEL"}, t, pred=pred, xu_op=I.XU_SEL, xu_src=V_["IS"], xu_dst=V_["SEL"], xu_d_n=nsel,
                xu_d_k=DY["NSEL2"] if r == 2 else DY["NSEL1"])

    def attention(self, L, hook=None, draft=False):
        """draft (a DSpark stage): the block rows' KV go to the stage's window
        cache at their positions, every row attends to the window and the whole
        block (T = the last block row's position + 1, DYN bank draft_last)."""
        m, V_, lay, K = self.m, self.V, self.lay, self.K
        t = f"L{L}.attn"
        r = m.ratio_all[L]
        table = "rope_yarn" if r > 0 else "rope_plain"
        self.linq(lay.qmat[(L, "wq_a")], "XN", "QA", set(), set(), t)
        self.linq(lay.qmat[(L, "wkv")], "XN", "KVA", set(), set(), t)
        self.rmsnorm("QA", 32, lay.cb[(L, "q_norm")], "QR", t)
        self.linq(lay.qmat[(L, "wq_b")], "QR", "Q", set(), set(), t)
        self.rmsnorm("KVA", 32, lay.cb[(L, "kv_norm")], "KVN", t)
        self.rope("KVN", V_["KVN"], 1, HD, table, DY["ROPE"], False, t)
        self.qdq(I.QE_QDQ8, "KVN", 1, V_["KVQ"], {"KVQ"}, t)
        if lay.mtp and not draft:
            self.serial(True)          # a slot's window row, its gathered rows, its scores: one slot at a time
        self.kvt_write("KVQ", f"KT{L}", K[f"KT{L}"], DY["POS"], t)
        self.su({"KVQ"}, {f"KR{L}"}, t, su_nout=1, su_nin=HD, a_base=V_["KVQ"], a_si=1, dst=I.DST_KV,
                o_base=K[f"KR{L}"], o_d=DY["ROW"], o_si=1)
        self.rope("Q", V_["Q"], m.heads, HD, table, DY["ROPE"], False, t)
        if draft:
            self.serial(True)          # every block row's KV is written: now one row at a time
            self.dslot_over = self.draft_last
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
        T16 = {0: DY["RND16_POS1"], 1: DY["RND16_T1"], 2: DY["RND16_T2"]}[r]
        for hb in range(0, m.heads, IL * GR):      # 4 head groups of 8 heads: one 16-row tile per round
            self.me(dict(n=0, tiles=0, k=HD, base=K[f"KT{L}"] // W), V_["Q"] + hb * HD, V_["S"] + hb * STR,
                    {"Q", f"KT{L}"}, {"S"}, ts, me_xcs=IL * HD, me_wsrc=1, me_ts=HD, me_ks=1, me_js=0, me_jsh=3,
                    me_xks=1, me_xjs=HD, me_ots=1, me_ojs=STR // W, me_mmode=1, me_d_nout=T, me_d_tiles=T16,
                    me_hg=2, me_ogs=IL * STR // W)
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
        for hb in range(0, m.heads, IL * 2):       # 2 head groups of 8 heads x 2 tiles of 16 dimensions
            self.me(dict(n=HD, tiles=1, k=0, base=K[f"KR{L}"] // W), V_["S"] + hb * STR, V_["ACC"] + hb * HD,
                    {"S", f"KR{L}"}, {"ACC"}, tp, me_xcs=IL * STR, me_wsrc=1, me_ts=1, me_ks=HD // W, me_js=0,
                    me_jsh=3, me_xks=1, me_xjs=STR, me_ots=1, me_ojs=HD // W, me_mmode=1, me_d_k=T,
                    me_hg=1, me_ogs=IL * HD // W)
        self.su({"M", "Z"}, {"DEN"}, tsm, su_nout=1, su_nin=m.heads, a_src=I.SRC_CLO, a_base=lay.cb[(L, "sink")],
                a_si=1, b_base=V_["M"], b_si=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, c_base=V_["Z"], c_si=1,
                e1=I.E1_ADDC, dst=I.DST_VM, o_base=V_["DEN"], o_si=1)
        self.su({"ACC", "DEN"}, {"ACC"}, tsm, su_nout=m.heads, su_nin=HD, a_base=V_["ACC"], a_so=HD, a_si=1,
                b_base=V_["DEN"], b_so=1, m1=I.M1_DIVB, rnd=1, dst=I.DST_VM, o_base=V_["ACC"], o_so=HD, o_si=1)
        self.dslot_over = None
        self.rope("ACC", V_["ACC"], m.heads, HD, table, DY["ROPE"], True, tsm)
        if lay.mtp:
            self.serial(False)
        if hook and ATTN_HOOK == "pv":
            hook()
        to = f"L{L}.out"
        mat = lay.mat[(L, "wo_a")]
        self.me(mat, V_["ACC"], V_["ZA"], {"ACC"}, {"ZA"}, to, me_xjs=256, me_ots=1, me_ojs=2)
        self.bf16("ZA", 256, "ZA", to)
        self.linq(lay.qmat[(L, "wo_b")], "ZA", "Y", set(), set(), to)

    def moe(self, L, hook=None):
        """The router, then the experts software-pipelined across the quantised
        engine and the stream unit: w13 of expert k+1 runs while expert k's SiLU
        does, and w2 of expert k while expert k+1's SiLU does (the engine is
        sequential, so issuing its next op proves the previous one complete).
        The shared expert reads only x, so it runs beside the router."""
        m, V_, lay = self.m, self.V, self.lay
        t = f"L{L}.router"
        stride = lay.qmat[(L, "exp_stride")]
        k_exp = m.k_exp if L < m.L else m.dspark_k_exp
        n_exp = m.n_exp if L < m.L else m.dspark_n_exp

        def expert(k):
            shared = k == k_exp
            te = f"L{L}.shared" if shared else f"L{L}.experts"
            if shared:
                w13, w2, ind = lay.qmat[(L, "shared", "w13")], lay.qmat[(L, "shared", "w2")], {}
            else:
                w13, w2 = lay.qmat[(L, "exp", 0, "w13")], lay.qmat[(L, "exp", 0, "w2")]
                ind = dict(qe_ind=1, qe_ibase=V_["EID"] + k, qe_istride=stride)
            gu = V_[f"GU{k}"]
            f = dict(su_nout=1, su_nin=64, a_base=gu, a_si=1, a_min=1, imm3=f32(m.limit), c_base=gu + 64, c_si=1,
                     c_clip=1, sfu=I.SFU_SILU, e1=I.E1_MULC, rnd=1, dst=I.DST_VM, o_base=V_[f"ACT{k}"], o_si=1)
            if not shared:
                f.update(b_base=V_["WGT"] + k, e2=I.E2_MULB)
            return (lambda: self.linq(w13, "XN", f"GU{k}", {"EID"}, set(), te, **ind),
                    lambda: self.su({f"GU{k}", "WGT"}, {f"ACT{k}"}, te, **f),
                    lambda: self.linq(w2, f"ACT{k}", f"E{k}", {"EID"}, set(), te, **ind))

        sh = expert(k_exp)
        sh[0]()                                        # shared w13 beside the router
        self.me(lay.mat[(L, "gate")], V_["XN"], V_["G12"], {"XN"}, {"G12"}, t)
        sh[1]()
        sh[2]()
        self.su({"G12"}, {"SC"}, t, su_nout=1, su_nin=n_exp, a_base=V_["G12"], a_si=1, sfu=I.SFU_SPSQRT,
                dst=I.DST_VM, o_base=V_["SC"], o_si=1)
        self.su({"SC"}, {"BI"}, t, su_nout=1, su_nin=n_exp, a_base=V_["SC"], a_si=1, d_src=I.SRC_CLO,
                d_base=lay.cb[(L, "bias")], d_si=1, ad=I.AD_D, dst=I.DST_VM, o_base=V_["BI"], o_si=1)
        self.xu({"BI"}, {"EID"}, t, xu_op=I.XU_SEL, xu_src=V_["BI"], xu_dst=V_["EID"], xu_n=n_exp,
                xu_k=k_exp)
        # wrel: this op waits for the SELECT that wrote EID, so its issue releases
        # the HBM fetch of the routed experts' weights (tools/hdc_program_v41.py
        # qe_fetch_list; rtl/hdc/hbm/ot_hdc_qstream.sv)
        self.su({"SC", "EID"}, {"TOT"}, t, su_nout=1, su_nin=k_exp, a_base=V_["SC"], a_si=1, a_ind=I.IND_I,
                a_ibase=V_["EID"], red=I.RED_SEQ, r_base=V_["TOT"], wrel=1)
        self.su({"TOT"}, {"DEN1"}, t, su_nout=1, su_nin=1, a_base=V_["TOT"], ad=I.AD_IMM, imm2=f32(1e-20),
                dst=I.DST_VM, o_base=V_["DEN1"])
        self.su({"SC", "EID", "DEN1"}, {"WGT"}, t, su_nout=1, su_nin=k_exp, a_base=V_["SC"], a_si=1,
                a_ind=I.IND_I, a_ibase=V_["EID"], b_base=V_["DEN1"], m1=I.M1_DIVB, m2=I.M2_IMM,
                imm1=f32(m.route_scale), dst=I.DST_VM, o_base=V_["WGT"], o_si=1)
        ex = [expert(k) for k in range(k_exp)]
        ex[0][0]()
        if k_exp > 1:
            ex[1][0]()
        for k in range(k_exp):
            if hook and k == MOE_HOOK:
                hook()
            if k > 0:
                ex[k - 1][2]()                         # w2 of the previous expert (its SiLU drained)
            ex[k][1]()                                 # SiLU k (its w13 completed: a later QE op issued)
            if k + 2 < k_exp:
                ex[k + 2][0]()                         # w13 two ahead
        ex[k_exp - 1][2]()
        if hook and MOE_HOOK >= k_exp:
            hook()
        ty = f"L{L}.moe_sum"
        for k in range(1, k_exp + 1):
            src = V_["E0"] if k == 1 else V_["Y"]
            self.su({"E0" if k == 1 else "Y", f"E{k}"}, {"Y"}, ty, su_nout=1, su_nin=160, a_base=src, a_si=1,
                    c_base=V_[f"E{k}"], c_si=1, ad=I.AD_C, rnd=int(k == k_exp), dst=I.DST_VM, o_base=V_["Y"],
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
                    o_si=1, red=I.RED_SUM, red_sq=1, red_tree=1, r_base=V_["SSX"])
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

    # -- multi-token prediction (Layout(mtp=...)) ------------------------------------------
    def ctl(self, op, tag, slot=0, lane=0, wait=0):
        self.emit(dict(unit=I.UNIT_CTL, ctl=op, ctl_slot=slot, ctl_lane=lane, wait=wait), set(), set(), tag)

    def mh_capture(self, part):
        """The DSpark head's main hidden part: the mean of the residual's copies at
        this layer's input, ((h0 + h1) + h2) + h3 times 1/4, BF16 (golden
        main_hidden_part), into MH[part]."""
        V_ = self.V
        h, o = V_["H"], V_["MH"] + part * self.m.dim
        t = "mtp.main_hidden"
        n = self.m.dim
        self.su({"H"}, {"MH"}, t, su_nout=1, su_nin=n, a_base=h, a_si=1, c_base=h + n, c_si=1, ad=I.AD_C,
                dst=I.DST_VM, o_base=o, o_si=1)
        self.su({"H", "MH"}, {"MH"}, t, su_nout=1, su_nin=n, a_base=o, a_si=1, c_base=h + 2 * n, c_si=1,
                ad=I.AD_C, dst=I.DST_VM, o_base=o, o_si=1)
        self.su({"H", "MH"}, {"MH"}, t, su_nout=1, su_nin=n, a_base=o, a_si=1, c_base=h + 3 * n, c_si=1,
                ad=I.AD_C, e2=I.E2_MULIMM, imm1=f32(1.0 / self.m.hc), rnd=1, dst=I.DST_VM, o_base=o, o_si=1)

    def dspark_seed(self):
        """Every DSpark stage's window row of this slot's position, from its main
        hidden (golden dspark_seed): main_x = main_norm(main_proj(MH)), then per
        stage kv_norm(wkv(main_x)), RoPE (plain) at the position, FP8 QDQ."""
        m, V_, lay, K = self.m, self.V, self.lay, self.K
        t = "mtp.seed"
        self.linq(lay.qmat["main_proj"], "MH", "MXA", set(), set(), t)
        self.rmsnorm("MXA", m.dim, lay.cb["main_norm"], "MX", t)
        for st in range(m.n_mtp):
            L = m.L + st
            self.linq(lay.qmat[(L, "wkv")], "MX", "KVA", set(), set(), t)
            self.rmsnorm("KVA", 32, lay.cb[(L, "kv_norm")], "KVN", t)
            self.rope("KVN", V_["KVN"], 1, HD, "rope_plain", DY["ROPE"], False, t)
            self.qdq(I.QE_QDQ8, "KVN", 1, V_["KVQ"], {"KVQ"}, t)
            self.kvt_write("KVQ", f"KT{L}", K[f"KT{L}"], DY["POS"], t)
            self.su({"KVQ"}, {f"KR{L}"}, t, su_nout=1, su_nin=HD, a_base=V_["KVQ"], a_si=1, dst=I.DST_KV,
                    o_base=K[f"KR{L}"], o_d=DY["ROW"], o_si=1)

    def position_body(self, seed=True, verify=True):
        """One slot of a (multi-)position pass of the main model: this slot's hash
        and Engram rows, embedding, the 40 layers (capturing the DSpark main
        hidden at the target layers), the head (verify: its argmax latched as
        target ttok[slot]), and (seed) the DSpark window rows of the position."""
        m, V_, lay = self.m, self.V, self.lay
        self.serial(True)               # the XU holds one hash: a slot's gathers follow its own hash
        self.xu(set(), {"EH"}, "embed", xu_op=I.XU_EHASH, xu_src=lay.cb["tmap"])
        for li, L in enumerate(m.engram.layer_ids):
            self.xu({"EH"}, {f"ER{L}"}, f"L{L}.engram", xu_op=I.XU_EGATHER, xu_src=lay.ebase[L],
                    xu_dst=V_[f"ER{L}"], xu_layer=li, xu_n=24)
        self.serial(False)
        self.su(set(), {"PF"}, "embed", su_nout=1, su_nin=4, a_src=I.SRC_CLO, a_base=lay.cb["pre0"], a_si=1,
                dst=I.DST_VM, o_base=V_["PF"], o_si=1)
        self.su(set(), {"H", "SSX"}, "embed", su_nout=4, su_nin=160, a_src=I.SRC_WROM,
                a_base=lay.emb_word * W * GR, a_d=DY["EMBED"], a_si=1, dst=I.DST_VM, o_base=V_["H"], o_so=160,
                o_si=1, red=I.RED_SUM, red_sq=1, red_tree=1, r_base=V_["SSX"])
        for L in range(m.L):
            if L in m.engram.layer_ids:
                self.engram(L)
            if L in m.dspark_targets:
                self.mh_capture(m.dspark_targets.index(L))
            self.layer(L)
        self.hc_pre("PF", "X", "head", "SS")
        self.rmsnorm("X", 160, lay.cb["norm"], "XN", "head", have_ss="SS")
        if verify:
            self.serial(True)           # the argmax register holds one head's result
            self.me(lay.mat["head"], V_["XN"], 0, {"XN"}, set(), "head", me_amax=1, me_oen=0)
            self.ctl(I.CTL_AMAX, "head", slot=self.slot, wait=1 << (I.UNIT_ME - 1))
            self.serial(False)
        else:
            self.me(lay.mat["head"], V_["XN"], 0, {"XN"}, set(), "head", me_amax=1, me_oen=0)
        if seed:
            self.dspark_seed()

    def layer(self, L, draft=False):
        lay = self.lay
        self.hc_mix_issue(L, "attn")
        self.hc_pre("PF", "X", f"L{L}.attn_norm", "SS")
        self.rmsnorm("X", 160, lay.cb[(L, "attn_norm")], "XN", f"L{L}.attn_norm", have_ss="SS")
        self.attention(L, hook=lambda: self.hc_mix_finish(L, "attn"), draft=draft)
        self.hc_post("Y", "POA", "CA", f"L{L}.hc_post")
        self.hc_mix_issue(L, "ffn")
        self.hc_pre("PA", "X", f"L{L}.ffn_norm", "SS")
        self.rmsnorm("X", 160, lay.cb[(L, "ffn_norm")], "XN", f"L{L}.ffn_norm", have_ss="SS")
        self.moe(L, hook=lambda: self.hc_mix_finish(L, "ffn"))
        self.hc_post("Y", "POF", "CF", f"L{L}.hc_post")

    def draft_body(self, rows, sample=None):
        """Block row `self.slot` of the DSpark draft (golden Model.draft), at
        position pos + row (the anchor is pos - 1): row 0 embeds the pending
        token stok[0], the others the noise token; the three stages; the last
        stage's hc_pre and norm, the lm_head, then -- one row after another --
        the Markov bias of the previous row's token (row 0: stok[0]), its argmax
        (a SELECT of 1), latched as draft token stok[row + 1].  Only the first
        `sample` rows are sampled (the verify pass checks gamma drafts): the
        other rows' chains are emitted with zero counts, so the slots' programs
        stay aligned and those instructions skip."""
        m, V_, lay = self.m, self.V, self.lay
        i = self.slot
        off = sample is not None and i >= sample
        self.draft_last = rows - 1
        self.su(set(), {"PF"}, "draft.embed", su_nout=1, su_nin=4, a_src=I.SRC_CLO, a_base=lay.cb["pre0"],
                a_si=1, dst=I.DST_VM, o_base=V_["PF"], o_si=1)
        emb = dict(a_d=DY["EMBED"]) if i == 0 else dict()
        self.su(set(), {"H", "SSX"}, "draft.embed", su_nout=4, su_nin=160, a_src=I.SRC_WROM,
                a_base=lay.emb_word * W * GR + (0 if i == 0 else m.noise_id * m.dim), a_si=1, dst=I.DST_VM,
                o_base=V_["H"], o_so=160, o_si=1, red=I.RED_SUM, red_sq=1, red_tree=1, r_base=V_["SSX"], **emb)
        for st in range(m.n_mtp):
            self.layer(m.L + st, draft=True)
        t = "draft.head"
        self.hc_pre("PF", "X", t, "SS")
        self.rmsnorm("X", 160, lay.cb["mtp_norm"], "XN", t, have_ss="SS")
        self.serial(True)               # the sampling chain: row i needs row i-1's token
        z = dict(me_nout=0) if off else {}
        self.me(lay.mat["head"], V_["XN"], V_["LG"], {"XN"}, {"LG"}, t, **z)
        g = dict(a_d=DY["TOK32"]) if i == 0 else dict(a_ind=I.IND_O, a_ibase=V_["DTOK"] + i - 1, a_so=32)
        self.su({"DTOK"}, {"MBX"}, t, su_nout=0 if off else 1, su_nin=32, a_src=I.SRC_WROM,
                a_base=lay.memb_word * W * GR, a_si=1, dst=I.DST_VM, o_base=V_["MBX"], o_si=1, **g)
        self.me(lay.mat["markov"], V_["MBX"], V_["MB"], {"MBX"}, {"MB"}, t, **z)
        nv = m.c["vocab_size"]
        self.su({"LG", "MB"}, {"LG"}, t, su_nout=0 if off else 1, su_nin=nv, a_base=V_["LG"], a_si=1,
                c_base=V_["MB"], c_si=1, ad=I.AD_C, dst=I.DST_VM, o_base=V_["LG"], o_si=1)
        self.xu({"LG"}, {"DTOK"}, t, xu_op=I.XU_SEL, xu_src=V_["LG"], xu_dst=V_["DTOK"] + i, xu_n=0 if off else nv,
                xu_k=1)
        self.ctl(I.CTL_TOKX, t, slot=i + 1, wait=1 << (I.UNIT_XU - 1))
        self.serial(False)


SU_BATCH = True                  # the stream unit's lane multiplier (its copies) serves batched slots


def su_shift(f, p):
    """Stream-unit copy p of a batched op: every vector-memory stream (A..D
    reads, the element write, the reducer write) moves by p slot strides."""
    if p == 0:
        return f
    g = dict(f)
    for x in "abcd":
        if g.get(f"{x}_src", 0) == I.SRC_VM:
            g[f"{x}_base"] = g.get(f"{x}_base", 0) + p * g["mx_xps"]
    if g.get("dst", 0) == I.DST_VM:
        g["o_base"] = g.get("o_base", 0) + p * g["mx_ops"]
    if g.get("red", 0):
        g["r_base"] = g.get("r_base", 0) + p * g["mx_ops"]
    return g


def su_sig(f):
    """Which stream-unit copies an op occupies: a one-slot op runs on copy 0,
    a batched op on copies 0 .. m-1 for its slot group."""
    m = max(1, f.get("mx_m", 0))
    return (1, None) if m == 1 else (m, f.get("_slot"))


def mx_batchable(f):
    """An op one issue of which may serve several slots: always issued, its
    addresses and counts free of DYN values, not expert-indexed.  Weight ops
    (ME from the weight ROM, QE LINQ, HE: one weight read for the slots) and,
    with SU_BATCH, static stream ops writing the vector memory (the stream
    unit's copies)."""
    if f.get("pred", 0) != I.PRED_ALWAYS:
        return False
    u = f["unit"]
    if u == I.UNIT_SU:
        return SU_BATCH and su_static(f) and f.get("dst", 0) in (I.DST_NONE, I.DST_VM)
    if u == I.UNIT_ME:
        return not f.get("me_wsrc", 0) and not f.get("me_amax", 0) and \
            not any(f.get(k, 0) for k in ("me_d_wbase", "me_d_xbase", "me_d_obase", "me_d_nout", "me_d_tiles",
                                          "me_d_k"))
    if u == I.UNIT_QE:
        return f.get("qe_mode", 0) == I.QE_LINQ and not f.get("qe_ind", 0) and not f.get("qe_d_obase", 0)
    return u == I.UNIT_HE


def mx_combine(lay, grp):
    """One weight op for the slots of grp (consecutive): slot p's x at + p*xps,
    its output at + p*ops."""
    f, reads, writes, tag = grp[0]
    if len(grp) == 1:
        return grp[0]
    f = dict(f)
    ss = lay.slot_stride
    u = f["unit"]
    if u == I.UNIT_SU:
        f.update(mx_m=len(grp), mx_xps=ss, mx_ops=ss)
        for p, (g, _, _, _) in enumerate(grp):
            want = su_shift(f, p)
            skip = ("dslot", "_slot", "_redw", "mx_m", "mx_xps", "mx_ops")
            if {k: v for k, v in g.items() if k not in skip} != \
                    {k: v for k, v in want.items() if k not in skip}:
                return None                    # the slots' copies differ (e.g. the draft's row 0): one by one
        f["_redw"] = set().union(*(g.get("_redw", set()) for g, _, _, _ in grp))
        return (f, set().union(*(r for _, r, _, _ in grp)), set().union(*(w for _, _, w, _ in grp)), tag)
    xk, ok, oscale = {I.UNIT_ME: ("me_xbase", "me_obase", W), I.UNIT_QE: ("qe_xbase", "qe_obase", 1),
                      I.UNIT_HE: ("he_xbase", "he_obase", 1)}[u]
    for p, (g, _, _, _) in enumerate(grp):
        assert g[xk] == f[xk] + p * ss and g[ok] == f[ok] + p * ss // oscale, (tag, p)
        assert {k: v for k, v in g.items() if k not in (xk, ok, "dslot", "_slot")} == \
            {k: v for k, v in f.items() if k not in (xk, ok, "dslot", "_slot")}, tag
    f.update(mx_m=len(grp), mx_xps=ss, mx_ops=ss // oscale)
    return (f, set().union(*(r for _, r, _, _ in grp)), set().union(*(w for _, _, w, _ in grp)), tag)


def merge_slots(lay, builders, m=1):
    """Interleave the slots' (structurally identical) instruction lists: op k of
    every slot before op k+1 of any, so a layer's weight ops for all slots sit
    together -- and a batchable weight op is ONE instruction per m consecutive
    slots (mx_m); a serial section runs whole for slot 0, then slot 1, ..."""
    progs = [b.prog for b in builders]
    n = len(progs[0])
    assert all(len(pr) == n for pr in progs), [len(pr) for pr in progs]
    out, k = [], 0
    while k < n:
        f0 = progs[0][k][0]
        for pr in progs:
            assert pr[k][0]["unit"] == f0["unit"] and pr[k][3] == progs[0][k][3], (k, pr[k][3])
        sid = f0.get("_serial")
        if sid is not None:
            e = k
            while e < n and progs[0][e][0].get("_serial") == sid:
                e += 1
            for pr in progs:
                out.extend(pr[k:e])
            k = e
            continue
        if m > 1 and mx_batchable(f0):
            for c in range(0, len(progs), m):
                grp = [pr[k] for pr in progs[c:c + m]]
                one = mx_combine(lay, grp)
                out.extend(grp if one is None else [one])
        else:
            out.extend(pr[k] for pr in progs)
        k += 1
    return out


def build_mtp(lay, gamma, m=1, qchunk=None, chain=None):
    """The MTP configuration's two programs, one image:

    STEP (entry 0): one position (prefill, or plain decode) -- the pass of one
    slot, seeding the DSpark window rows, END with the token.

    ITER (entry `iter_entry`): one speculative step from the pending token
    stok[0] at pos (anchor pos-1): the DSpark draft over its block
    (dspark_block_size rows, gamma of whose tokens are verified), DYN, the
    verify pass of slots 0 .. gamma (tokens stok[0 .. gamma], positions pos ..
    pos+gamma) with its weight ops m slots per read, ACCEPT, END with the
    bonus token.  Returns (program, iter_entry)."""
    mm = lay.m
    chain = CHAIN_MTP if chain is None else chain
    B = mm.dspark_block
    assert 1 <= gamma <= B and gamma + 1 <= lay.nslots and B <= lay.nslots
    step = Builder(lay, qchunk, 0)
    step.position_body(seed=True, verify=False)
    prog = merge_slots(lay, [step])
    prog.append((dict(unit=I.UNIT_END, wait=31), set(), set(), "end"))
    step_prog = schedule(prog, chain=chain)
    drafts = [Builder(lay, qchunk, i) for i in range(B)]
    for b in drafts:
        b.draft_body(B, sample=gamma)
    ver = [Builder(lay, qchunk, j) for j in range(gamma + 1)]
    for b in ver:
        b.position_body(seed=True, verify=True)
    prog = merge_slots(lay, drafts, m)
    prog.append((dict(unit=I.UNIT_CTL, ctl=I.CTL_DYN, wait=0), set(), set(), "dyn"))
    prog += merge_slots(lay, ver, m)
    prog.append((dict(unit=I.UNIT_CTL, ctl=I.CTL_ACCEPT, ctl_slot=gamma, wait=31), set(), set(), "accept"))
    prog.append((dict(unit=I.UNIT_END, wait=31), set(), set(), "end"))
    return step_prog + schedule(prog, chain=chain), len(step_prog)


def su_static(f):
    """A stream op whose vector-memory traffic is the same at every position: it
    always issues, its counts and vector-memory bases take no DYN value, and A is
    not gathered."""
    if f.get("pred", 0) != I.PRED_ALWAYS or f.get("su_d_nout", 0) or f.get("su_d_nin", 0) or f.get("a_ind", 0):
        return False
    if f.get("red", 0) == I.RED_SEQ:
        return False
    return all(not f.get(f"{x}_d", 0) for x in "abcd" if f.get(f"{x}_src", 0) == I.SRC_VM) and \
        not (f.get("dst", 0) == I.DST_VM and f.get("o_d", 0))


def su_vectors(f, lanes=None):
    """Per element (o, i) of a static stream op: its vector index, and its
    vector-memory addresses read (A..D) and written (the element write).  A
    batched op's copies run in lockstep: copy p's element has copy 0's vector
    index."""
    if max(1, f.get("mx_m", 0)) > 1:
        parts = [su_vectors(dict(su_shift(f, p), mx_m=1), lanes) for p in range(f["mx_m"])]
        v = np.concatenate([x[0] for x in parts])
        reads = [np.concatenate([x[1][k] for x in parts]) for k in range(len(parts[0][1]))]
        w = None if parts[0][2] is None else np.concatenate([x[2] for x in parts])
        return v, reads, w
    lanes = lanes or I.SU_LANES
    no, ni = f.get("su_nout", 0), f.get("su_nin", 0)
    o, i = (x.reshape(-1) for x in np.meshgrid(np.arange(no), np.arange(ni), indexing="ij"))
    vec = f.get("su_vec", 0)
    if vec == I.VEC_I:
        v = o * -(-ni // lanes) + i // lanes
    elif vec == I.VEC_O:
        v = (o // lanes) * ni + i
    else:
        v = o * ni + i

    def at(x, half=False):
        ii = i >> 1 if half else i
        return f.get(f"{x}_base", 0) + o * f.get(f"{x}_so", 0) + ii * f.get(f"{x}_si", 0)
    reads = []
    for x in "abcd":
        if f.get(f"{x}_src", 0) != I.SRC_VM:
            continue
        if x == "c" and f.get("c_pair"):
            reads.append(at("a") ^ 1)
        else:
            reads.append(at(x, x in "bd" and f.get("b_half")))
    writes = at("o") if f.get("dst", 0) == I.DST_VM else None
    return v, reads, writes


def chase_distance(prev, cur, lanes=None):
    """The stream unit's chase distance D for `cur` right behind `prev` (both
    static, same class): `cur` emits its first vector once fewer than D vectors
    are in flight, then one per cycle, while `prev` (emitted without gaps)
    retires one per cycle ahead of it -- so vector v goes only once `prev` has
    retired every vector that wrote what v reads.  With n1 vectors in `prev`
    and need[v] = 1 + the last of them that v reads (0 if none),
    D = 1 + min_v (n1 + v - need[v])."""
    pv, _, pw = su_vectors(prev, lanes)
    n1 = int(pv.max()) + 1
    writer = {}
    if pw is not None:
        for a, v in zip(pw.tolist(), pv.tolist()):
            writer[a] = max(writer.get(a, -1), v)
    cv, reads, _ = su_vectors(cur, lanes)
    nv = int(cv.max()) + 1
    need = np.zeros(nv, dtype=np.int64)
    for r in reads:
        w = np.array([writer.get(a, -1) for a in r.tolist()], dtype=np.int64) + 1
        np.maximum.at(need, cv, w)
    return int(1 + np.min(n1 + np.arange(nv) - need))


def never_skipped(f):
    """An op that issues at every position: no predicate and no count from a DYN value."""
    if f.get("pred", 0) != I.PRED_ALWAYS:
        return False
    if f["unit"] == I.UNIT_XU and f.get("xu_op", 0) == I.XU_SEL:
        return f.get("xu_d_n", 0) == 0 and f.get("xu_n", 0) > 0
    return True


CHASE = True                     # stream ops chase the previous stream op (su_chase) where they can
CHAIN_MTP = False                # chase whole same-class runs in the MTP programs (schedule chain=True): measured no gain


def su_class(f):
    """The stream unit's class: the depth an element of the op takes (ot_hdc_v41_stream)."""
    return (f.get("m1", 0) in (I.M1_DIVB, I.M1_DIVIMM), f.get("sfu", 0)) + su_stages(f)


def su_stages(f):
    """Which 5-cycle stages an op uses: M1 (a multiply or divide), M2 (a multiply, or
    Q's multiply, which spans it), AD, E1, E2."""
    return (f.get("m1", 0) not in (I.M1_BYP, I.M1_MAXB), f.get("m2", 0) != I.M2_BYP or f.get("qm", 0) != I.QM_OFF,
            f.get("ad", 0) != I.AD_BYP, f.get("e1", 0) != I.E1_BYP, f.get("e2", 0) != I.E2_BYP)


def su_nvec(f):
    """Vectors a stream op emits: exact for a static op, else a lower bound (0)."""
    if not su_static(f):
        return 0
    v, _, _ = su_vectors(f)
    return int(v.max()) + 1 if len(v) else 0


def chain_distance(chain, cur):
    """The chase distance D of `cur` behind a CHAIN of same-class stream ops
    (oldest first, [(op, vectors)]): the unit retires vectors in emission order,
    so once fewer than D are in flight every vector emitted at least D-1
    vectors before cur's first has retired; D = 1 + the fewest vectors emitted
    after any vector cur reads.  Every chain op writing an address cur reads
    must be static; the others count as their lower bound.  None: not
    computable (drain instead); 0: no dependency on the chain."""
    after = 0                                  # vectors emitted after the op being looked at
    best = None
    _, reads, _ = su_vectors(cur)
    need = set()
    for r in reads:
        need.update(r.tolist())
    for g, n in reversed(chain):
        if not need:
            break
        if su_static(g):
            v, _, w = su_vectors(g)
            if w is not None:
                hit = [(a, vv) for a, vv in zip(w.tolist(), v.tolist()) if a in need]
                if hit:
                    last = max(vv for _, vv in hit)
                    a_after = after + (n - 1 - last)
                    best = a_after if best is None else min(best, a_after)
                    need -= {a for a, _ in hit}
        after += n
    return 0 if best is None else best + 1


def schedule(prog, chain=False):
    """Wait masks: an instruction waits for every unit holding an in-flight
    instruction it conflicts with.  On ANOTHER unit a conflict is any overlap (it
    reads what that unit writes, or writes what it reads or writes).  On its OWN
    unit only a read of what the unit writes conflicts: a unit starts an op after
    the previous op's last element has been read, and writes in issue order --
    the stream unit because a class change drains it and a class fixes the depth
    (its reducer writes later, so a write over a reducer's output still waits),
    the matrix engine when consecutive ops share the split and weight source
    (the result latency).  A unit executes in order, so waiting for it to drain
    covers all its older work.  The quantised engine and the auxiliary unit are
    SEQUENTIAL (an op is accepted only once the previous one has written
    everything), so once an op that is never skipped has issued on one of them,
    every older op there is complete: its conflicts are forgotten.

    chain=True (the MTP programs): a stream op of another CLASS than the
    previous one is accepted only once the unit has drained (ot_hdc_v41_stream
    `ready`), so element writes before a class change are never waited on;
    within a same-class run a read of an earlier op's writes CHASES the whole
    run (chain_distance) when every writer involved is static -- the multi-slot
    programs place the slots' copies of an op side by side, so a slot's
    producer sits several ops back."""
    out = []
    su_chain, su_chain_w = [], []                   # same-class stream ops since the last drain / class change
    su_sig_w = {}                                   # stream-unit copy signature -> regions written since a drain
    rd = {u: set() for u in I.UNITS}
    wr = {u: set() for u in I.UNITS}
    rw = {u: set() for u in I.UNITS}              # reducer outputs (stream unit)
    last = {}
    last_su = None                                  # the previous stream op (chase source)
    sequential = (I.UNIT_QE, I.UNIT_XU)
    for f, reads, writes, tag in prog:
        f = dict(f)
        wait = f.get("wait", 0)
        own = f["unit"]
        red = set(f.pop("_redw", ()))
        chase = 0
        cls_change = own == I.UNIT_SU and last_su is not None and su_class(f) != su_class(last_su)
        if chain and cls_change:
            su_chain, su_chain_w = [], []
        for u in I.UNITS:
            if u == own:
                c = reads & wr[u]
                if u == I.UNIT_SU and c and CHASE and chain:
                    if cls_change:
                        c = reads & rw[u]          # the element pipeline drains; a reducer may still write
                    elif not (reads & rw[u]):
                        live = reads & set().union(set(), *su_chain_w)
                        if not live:
                            c = set()              # its writers precede a drain or a class change
                        elif su_static(f):
                            relevant = [g for g, w in zip(su_chain, su_chain_w) if w & reads]
                            if all(su_static(g) for g, _ in relevant):
                                chase = chain_distance(su_chain, f)
                                c = set()
                elif u == I.UNIT_SU and c and CHASE and not (reads & rw[u]) and su_static(f) and last_su \
                        and su_static(last_su) and su_class(f) == su_class(last_su) and \
                        su_sig(f) == su_sig(last_su) and \
                        not (reads & set().union(set(), *(w for s, w in su_sig_w.items() if s != su_sig(f)))):
                    # a copy's chase counts only its own vectors: never across copies
                    chase = chase_distance(last_su, f)
                    c = set()                      # chase the previous stream op instead of draining
                if u == I.UNIT_SU:
                    c = c or (writes & rw[u])
                if u == I.UNIT_ME and last.get(u) != (f.get("me_split", 0), f.get("me_wsrc", 0)):
                    c = c or (writes & wr[u])
            else:
                c = (reads & wr[u]) or (writes & (rd[u] | wr[u]))
            if c:
                wait |= 1 << (u - 1)
        for u in I.UNITS:
            if wait >> (u - 1) & 1:
                rd[u], wr[u], rw[u] = set(), set(), set()
        f["wait"] = wait
        if wait >> (I.UNIT_SU - 1) & 1:
            su_sig_w = {}
        if own == I.UNIT_SU:
            f["su_chase"] = chase if not (wait >> (I.UNIT_SU - 1) & 1) else 0
            last_su = f
            su_sig_w.setdefault(su_sig(f), set()).update(writes)
            if chain:
                if wait >> (I.UNIT_SU - 1) & 1:
                    su_chain, su_chain_w = [], []
                su_chain.append((f, su_nvec(f)))
                su_chain_w.append(set(writes))
        elif chain and wait >> (I.UNIT_SU - 1) & 1:
            su_chain, su_chain_w = [], []
        if own in sequential and never_skipped(f):
            rd[own], wr[own] = set(), set()
        if own in rd:
            rd[own] |= reads
            wr[own] |= writes
            rw[own] |= red
            if own == I.UNIT_ME:
                last[own] = (f.get("me_split", 0), f.get("me_wsrc", 0))
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
        self.mtp = lay.mtp is not None
        self.amax_lane = [0] * 8
        self.head_log = []                             # every argmax head's logits, in execution order
        self.sel_first = 0
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
        self.slot_logits = {}
        self.logits = []
        self.trace = {}

    def wrom_f32(self, e):
        return G.from_bits(self.wrom[e].astype(np.uint32) << 16)

    def run(self, prog, token, pos, stop=None, entry=0):
        """Run from `entry` to the next END.  MTP layouts: slot j of the step sits at
        pos + j with token stok[j] (stok[0] = token); the Engram history
        (self.tokens) takes a slot's token only when END (a one-position step) or
        ACCEPT commits it.  Returns the token END reports."""
        self.token, self.pos = token, pos
        if self.mtp:
            self.stok = [int(token)] + [0] * (I.NSLOT - 1)
            self.ttok = [0] * I.NSLOT
            self.banks = [I.dyn_values(self.stok[j], pos + j) for j in range(I.NSLOT)]
            self.accepted = None
            self.drafts = []
        else:
            self.dyn = I.dyn_values(token, pos)
            self.tokens.append(int(token))
        for n in range(entry, len(prog)):
            f = prog[n]
            if stop is not None and n >= stop:
                break
            f = {name: f.get(name, 0) for name, _ in I.FIELDS} | {"_tag": f.get("_tag", "")}
            if f["unit"] == I.UNIT_CTL:
                if f["ctl"] == I.CTL_END:
                    if self.mtp and self.accepted is None:
                        self.tokens.append(self.stok[0])
                    break
                self.control(f)
                continue
            p = pos
            if self.mtp:
                self.dyn = self.banks[f["dslot"]]
                p = pos + f["dslot"]
            if f["pred"] == I.PRED_ODD and not (p & 1):
                continue
            if f["pred"] == I.PRED_NZ and p == 0:
                continue
            {I.UNIT_ME: self.me, I.UNIT_SU: self.su, I.UNIT_QE: self.qe, I.UNIT_XU: self.xu,
             I.UNIT_HE: self.he}[f["unit"]](f)
        return self.argmax

    def poison(self, n):
        """NaN into every position-indexed row at or past position n (window rows
        of every layer and DSpark stage, compressed rows, index keys, slot ring
        entries of positions >= n): a correct machine never reads them before the
        next step rewrites them."""
        lay, nan = self.lay, F(np.nan)
        for L in range(lay.L + lay.nmtp):
            for t in range(n, TMAX):
                for d in range(HD):
                    self.kv[lay.kt_elem(lay.kv.map[f"KT{L}"], t, d)] = nan
                    self.kv[lay.kv.map[f"KR{L}"] + t * HD + d] = nan
        for s in self.m.kv_src:
            r = self.m.ratio[s]
            for g in range(n // r, lay.nrows[s]):
                self.vm[lay.vm.map[f"CKV{s}"] + g * HD: lay.vm.map[f"CKV{s}"] + (g + 1) * HD] = nan
                for d in range(HD):
                    self.kv[lay.kt_elem(lay.kv.map[f"IK{s}"], g, d)] = nan
            if lay.ring > 2:
                # live: only the entry of position n-1 when its group (n-1, n) is still open
                keep = (n - 1) % lay.ring if (n - 1) % 2 == 0 else None
                for e_i in range(lay.ring):
                    if e_i != keep:
                        e = lay.vm.map[f"SLOT{s}"] + e_i * 64
                        self.vm[e:e + 64] = nan

    def control(self, f):
        op, j = f["ctl"], f["ctl_slot"]
        if op == I.CTL_TOKX:
            self.stok[j] = self.sel_first
            self.drafts = self.stok[1:j + 1]
        elif op == I.CTL_AMAX:
            self.ttok[j] = self.amax_lane[f["ctl_lane"]]
        elif op == I.CTL_DYN:
            if getattr(self, "force", None) is not None:
                self.stok[1:len(self.drafts) + 1] = [int(x) for x in self.force(list(self.drafts))]
                self.drafts = self.stok[1:len(self.drafts) + 1]
            self.banks = [I.dyn_values(self.stok[k], self.pos + k) for k in range(I.NSLOT)]
        elif op == I.CTL_ACCEPT:
            g = j                                      # drafts verified
            a = 0
            while a < g and self.stok[a + 1] == self.ttok[a]:
                a += 1
            self.accepted = a
            self.emitted = self.ttok[:a + 1]
            self.tokens.extend(self.stok[:a + 1])      # the hash history: committed positions only
            self.argmax = self.ttok[a]

    # -- matrix engine (tools/hdc_program.py semantics, FP32 lane mode) ------------------
    def me(self, f):
        d = self.dyn
        n = f["me_nout"] + d[f["me_d_nout"]]
        tiles = f["me_tiles"] + d[f["me_d_tiles"]]
        K = f["me_k"] + d[f["me_d_k"]]
        if n == 0 or tiles == 0 or K == 0:
            return
        for lane in range(max(1, f["mx_m"])):
            self.me_lane(f, n, tiles, K, lane)

    def me_lane(self, f, n, tiles, K, lane):
        d = self.dyn
        wb = f["me_wbase"] + d[f["me_d_wbase"]]
        xb = f["me_xbase"] + d[f["me_d_xbase"]] + lane * f["mx_xps"]
        ob = f["me_obase"] + d[f["me_d_obase"]] + lane * f["mx_ops"]
        split = 0 if f["me_wsrc"] else f["me_split"]
        hg = f["me_hg"] if f["me_wsrc"] else 0
        S = 1 << split
        per_round = GR // S >> hg                    # tiles one round covers
        r, h, q, j, l = (a.reshape(-1) for a in np.meshgrid(np.arange(tiles), np.arange(1 << hg), np.arange(per_round),
                                                            np.arange(IL), np.arange(W), indexing="ij"))
        t = r * per_round + q
        nidx = (t * IL + j) * W + l
        keep = (nidx < n) if f["me_mmode"] == 0 else (t * W + l < n)
        r, h, q, t, j, l, nidx = r[keep], h[keep], q[keep], t[keep], j[keep], l[keep], nidx[keep]
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
                x = self.vm[xb + (c + h) * f["me_xcs"] + k * f["me_xks"] + j * f["me_xjs"]]
                if f["me_round"]:
                    x = G.to_bf16(x)
                acc = G.add(acc, G.mul(w, x))
            parts.append(acc)
        while len(parts) > 1:
            parts = [G.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
        acc = parts[0]
        if f["me_oen"]:
            self.vm[(ob + t * f["me_ots"] + h * f["me_ogs"] + j * f["me_ojs"]) * W + l] = acc
        if f["me_amax"]:
            order = np.argsort(nidx)
            self.logits = acc[order]
            self.argmax = int(nidx[order][np.argmax(acc[order])])
            self.amax_lane[lane] = self.argmax
            self.head_log.append(self.logits)
            if self.mtp:
                self.slot_logits[f["dslot"] + lane] = self.logits

    # -- hyper-connection projection engine ------------------------------------------------
    def he(self, f):
        """out[row] = sum_k w[row, k] * x[k]: chunk c (he_k terms from x[c*he_k])
        sequential from +0 in lane group c, the HC_SPLIT chunk sums a pairwise tree."""
        n, K, S, NL = f["he_nout"], f["he_k"], V.HC_SPLIT, I.HE_LANES
        for lane in range(max(1, f["mx_m"])):
            xb, ob = f["he_xbase"] + lane * f["mx_xps"], f["he_obase"] + lane * f["mx_ops"]
            acc = np.zeros((S, NL * IL), dtype=F)
            for k in range(K):
                w = self.hrom[f["he_wbase"] + k * IL: f["he_wbase"] + (k + 1) * IL].reshape(IL, S, NL)
                w = w.transpose(1, 0, 2).reshape(S, IL * NL)               # [chunk, row j*NL + l]
                x = self.vm[xb + np.arange(S) * K + k]
                acc = G.add(acc, G.mul(w, x[:, None]))
            parts = list(acc)
            while len(parts) > 1:
                parts = [G.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
            self.vm[ob:ob + n] = parts[0][:n]

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
        if max(1, f["mx_m"]) > 1:
            for p in range(f["mx_m"]):
                self.su1(dict(su_shift(f, p), mx_m=1))
            return
        self.su1(f)

    def su1(self, f):
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
        if f["red"] and f["red_tree"]:
            v = G.mul(out, out) if f["red_sq"] else out
            x = V.split_sum_parts([G.reduce_sum(sg) for sg in v.reshape(no, ni)])
            if f["red_rnd"]:
                x = G.to_bf16(x)
            self.vm[f["r_base"]] = x
        elif f["red"]:
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
        wb = f["qe_wbase"]
        if f["qe_ind"]:
            wb += int(to_u32(self.vm[f["qe_ibase"]])) * f["qe_istride"]
        n, rounds = f["qe_nout"], f["qe_tiles"]
        table = V.E2M1 if f["qe_fp4"] else V.E4M3
        for lane in range(max(1, f["mx_m"])):
            xb = f["qe_xbase"] + lane * f["mx_xps"]
            xq, xe = V.quant_fp8(self.vm[xb:xb + nb * 32])
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
                    self.vm[f["qe_obase"] + lane * f["mx_ops"] + rows[ok]] = y[ok]

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
            if sel:
                self.sel_first = sel[0]
        elif op == I.XU_SINK:
            e = self.vm[f["xu_src"]:f["xu_src"] + 16].reshape(4, 4)
            self.vm[f["xu_dst"]:f["xu_dst"] + 16] = sinkhorn(e, self.m).reshape(-1)
        elif op == I.XU_EHASH:
            hist = self.tokens + self.stok[:f["dslot"] + 1] if self.mtp else self.tokens
            self.eh = [self.m.engram.hashes(hist, li) for li in range(len(self.m.engram.layer_ids))]
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


# -- HBM image of the quantised weights (rtl/hdc/hbm/ot_hdc_qstream.sv) --------------------
QSEC = 256                                  # HBM sector (burst) bits
QSPW8 = QLANE_BITS * BL // QSEC             # an FP8 word: 17 sectors
QSPW4 = (128 + 16) * BL // QSEC             # an FP4 word, packed (32 nibbles + exponent per lane): 9 sectors
LIST_BITS = 128
QCHUNK = 512                                # LINQ chunk (words): the QE streamer's window less its lead


def qe_word_formats(lay):
    """FP4 flag of every quantised-ROM word (each placed matrix is one format)."""
    fmt = np.zeros(len(lay.qcodes), dtype=np.uint8)
    for k, m in lay.qmat.items():
        if isinstance(m, dict):
            fmt[m["base"]:m["base"] + m["tiles"] * m["nb"] * IL] = m["fp4"]
    return fmt


def qe_hbm_image(lay):
    """The quantised weights as the HBM holds them: the ROM's words in ROM order
    (the routed experts sit at a fixed stride, as in the ROM), an FP8 word as
    its 17 sectors, an FP4 word packed into 9 (per lane 32 E2M1 nibbles and the
    16-bit exponent: the ROM's 8-bit code slots hold 4-bit codes).  Returns the
    sectors and each word's first sector."""
    fmt = qe_word_formats(lay)
    sectors, first = [], np.zeros(len(lay.qcodes) + 1, dtype=np.int64)
    for w, (cw, ew) in enumerate(zip(lay.qcodes, lay.qexp)):
        first[w] = len(sectors)
        if fmt[w]:
            assert int(cw.max()) < 16
            lanes = [pack_lanes(cw[l], 4) | ((int(ew[l]) & 0xFFFF) << 128) for l in range(BL)]
            word, spw = pack_lanes(lanes, 144), QSPW4
        else:
            lanes = [pack_lanes(cw[l], 8) | ((int(ew[l]) & 0xFFFF) << 256) for l in range(BL)]
            word, spw = pack_lanes(lanes, QLANE_BITS), QSPW8
        sectors.extend((word >> (QSEC * j)) & ((1 << QSEC) - 1) for j in range(spw))
    first[len(lay.qcodes)] = len(sectors)
    return sectors, first


def qe_fetch_list(lay, prog, first):
    """The QE's weight fetches in consumption order: every LINQ op, in program
    order, as (HBM sector base, ROM word base, words, FP4, predicate, indexed,
    index element, stride in words, release group).  An expert-indexed op adds
    id * stride (the id read from the vector memory once the program's release
    instruction `grp` has issued)."""
    fmt = qe_word_formats(lay)
    ents, grp = [], 0
    for f in prog:
        if f.get("wrel"):
            assert f["wait"] >> (I.UNIT_XU - 1) & 1, "a release must wait for the XU (the expert ids)"
            grp += 1
        if f["unit"] != I.UNIT_QE or f.get("qe_mode", 0) != I.QE_LINQ:
            continue
        b, n = f["qe_wbase"], f["qe_tiles"] * f["qe_nb"] * IL
        ind = f.get("qe_ind", 0)
        assert all(fmt[b:b + n] == f["qe_fp4"])
        if ind:
            spw = QSPW4 if f["qe_fp4"] else QSPW8
            assert first[b + f["qe_istride"]] - first[b] == f["qe_istride"] * spw
        ents.append(dict(hbm=int(first[b]), rom=b, n=n, fp4=f["qe_fp4"], pred=f.get("pred", 0), ind=ind,
                         ibase=f.get("qe_ibase", 0), istride=f.get("qe_istride", 0), grp=grp if ind else 0))
    return ents


def encode_list(ents):
    """128-bit fetch-list words: [23:0] HBM sector base, [47:24] ROM word base,
    [63:48] words (0 ends the list), [64] FP4, [66:65] predicate, [67] indexed,
    [91:68] index element, [115:92] stride (words), [123:116] release group."""
    out = []
    for e in ents + [dict(hbm=0, rom=0, n=0, fp4=0, pred=0, ind=0, ibase=0, istride=0, grp=0)]:
        assert e["hbm"] < 1 << 24 and e["n"] < 1 << 16 and e["grp"] < 1 << 8
        out.append(e["hbm"] | e["rom"] << 24 | e["n"] << 48 | e["fp4"] << 64 | e["pred"] << 65 | e["ind"] << 67 |
                   e["ibase"] << 68 | e["istride"] << 92 | e["grp"] << 116)
    return out


def write_hbm_images(out, lay, prog):
    sectors, first = qe_hbm_image(lay)
    ents = qe_fetch_list(lay, prog, first)
    (out / "hbm_q.hex").write_text(hexwords(sectors, QSEC))
    (out / "qlist.hex").write_text(hexwords(encode_list(ents), LIST_BITS))
    fmt = qe_word_formats(lay)
    meta = {"qrom_words": len(lay.qcodes), "fp4_words": int(fmt.sum()), "hbm_sectors": len(sectors),
            "list_entries": len(ents), "indexed_entries": sum(e["ind"] for e in ents),
            "release_groups": max(e["grp"] for e in ents),
            "words_per_token_by_pred": {str(p): sum(e["n"] for e in ents if e["pred"] == p) for p in (0, 1, 2)},
            "fp8_words_per_token_pred0": sum(e["n"] for e in ents if not e["fp4"] and e["pred"] == 0),
            "fp4_words_per_token_pred0": sum(e["n"] for e in ents if e["fp4"] and e["pred"] == 0),
            # HBM sectors a decode step at an odd position > 0 reads (every predicate holds)
            "hbm_sectors_per_token": sum(e["n"] * (QSPW4 if e["fp4"] else QSPW8) for e in ents)}
    (out / "hbm_q.json").write_text(json.dumps(meta))
    (out / "hbm_q.args").write_text(f"+QSEC={len(sectors)}\n")
    return meta


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
    (out / "hrom.hex").write_text(hexwords((pack_lanes(G.bits(w), 32) for w in lay.hwords),
                                           32 * I.HE_LANES * V.HC_SPLIT))
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


def mtp_layout(model, gamma):
    return Layout(model, mtp={"slots": max(model.dspark_block, gamma + 1)})


def mtp_run(lay, prog, entry, prompt, n, gamma, forced=None, poison=False, record=None):
    """The MTP configuration on the ISA model from an EMPTY state: the prompt
    through the STEP program one position at a time, then ITER steps until n
    tokens.  forced(q, drafts) may replace the draft tokens (the TOKX results)
    before the verify pass -- an acceptance-coverage device; poison=True fills
    every row past the committed positions with NaN after each step (the
    dead-row invariant: nothing past them may be read before it is rewritten).
    Returns (tokens, per-token logits, per-step records)."""
    mach = Machine(lay, np.zeros(I.KV_WORDS * W, dtype=F), np.zeros(lay.vm.size, dtype=F))
    for p, t in enumerate(prompt):
        mach.run(prog, t, p, entry=0)
    out, rows = [mach.argmax], [mach.logits.copy()]
    q, y = len(prompt) - 1, mach.argmax
    steps = []
    max_pos = int(lay.m.c["max_seq_len"])
    while len(out) < n:
        assert q + 1 + gamma < max_pos, "the step would pass max_seq_len"
        if forced is not None:
            mach.force = lambda d, q=q: forced(q, d)
        mach.slot_logits = {}
        mach.run(prog, y, q + 1, entry=entry)
        a = mach.accepted
        steps.append({"pos": q + 1, "token": y, "drafts": list(mach.drafts), "targets": mach.ttok[:gamma + 1],
                      "accepted": a, "emitted": list(mach.emitted)})
        out += mach.emitted
        rows += [mach.slot_logits[j] for j in range(a + 1)]
        q, y = q + 1 + a, mach.argmax
        if poison:
            mach.poison(q + 1)
    if record is not None:
        record["machine"] = mach
    return out[:n], rows[:n], steps


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, help="write RTL images and expectations here")
    ap.add_argument("--context", type=int, help="decode at position N-1 of the oracle prompt cycled to N tokens")
    ap.add_argument("--multi", type=int, default=0,
                    help="also run the ISA model from an empty state over the prompt and K generated tokens")
    ap.add_argument("--stop", type=int, help="debug: run only this many instructions")
    ap.add_argument("--roms-from", type=Path, help="debug: symlink the ROM images from this directory")
    ap.add_argument("--check-layers", action="store_true", help="debug: compare the residual after every layer")
    ap.add_argument("--hbm", action="store_true", help="also write the HBM image of the quantised weights and the "
                                                        "QE fetch list (hbm_q.hex, qlist.hex)")
    args = ap.parse_args()
    model = V.Model()
    prompt, expected = V.prompt_and_expected()
    if args.context:
        prompt = (list(prompt) * (-(-args.context // len(prompt))))[:args.context]
    lay = Layout(model)
    prog = Builder(lay, qchunk=QCHUNK if args.hbm else None).build()
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
        if args.hbm:
            print("HBM quantised weights:", write_hbm_images(out, lay, prog))
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
