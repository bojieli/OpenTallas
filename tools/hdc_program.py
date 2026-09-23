#!/usr/bin/env python3
"""Program, memory images and ISA-level simulator of the hardwired decode core.

    python3 tools/hdc_program.py --out DIR      # images + expected results for the RTL

For the reduced Qwen3 vehicle this builds

* the weight ROM (bf16, W lanes per word, laid out in the order the matrix-vector
  engine streams it, plus the embedding table),
* the constant ROM (norm weights; RoPE cos/sin per position),
* the KV cache image holding positions 0 .. pos-1 from the golden prefill,
* the static program (tools/hdc_isa.py) that decodes one token at `pos`,

then runs the program on an ISA-level model whose every operation is the golden
arithmetic of tools/hdc_golden.py, and checks its logits against
hdc_golden.Model.decode_token bit for bit.  The RTL simulation is checked against
the same images and results.
"""
import argparse
import json
from pathlib import Path

import numpy as np

import hdc_golden as G
import hdc_isa as I

F = np.float32
W, IL, TMAX, GR = I.W_LANES, I.INTERLEAVE, I.T_MAX, I.GROUPS

# -- vector memory map (FP32 elements) ------------------------------------------
VM = dict(X=0, H=128, QKV=256, QN=448, QR=608, SS=736, RS=752, SSX=768, RX=769,
          M=784, Z=800, RZ=816, S=1024, ATT=1536, T1=1664, GU=1792, E1=2560,
          U=2944, ACT=3328)
S_STRIDE = TMAX        # elements per head in S


def f32(x):
    return int(G.bits(F(x)))


class Layout:
    """Weight ROM, constant ROM and KV placement for one model."""

    def __init__(self, model):
        self.m = model
        c = model.cfg
        self.H, self.L = c["hidden_size"], c["num_hidden_layers"]
        self.NH, self.KV, self.HD = c["num_attention_heads"], c["num_key_value_heads"], c["head_dim"]
        self.FF, self.V = c["intermediate_size"], c["vocab_size"]
        self.half = self.HD // 2
        self.eps = F(c["rms_norm_eps"])
        assert self.HD % W == 0 or W % self.HD == 0
        self.TW = TMAX // W
        # weight ROM
        self.words = []            # list of np.uint16[W * GR]
        self.mat = {}
        for L in range(self.L):
            lw = lambda n: model.lw(L, n)
            qkv = np.concatenate([lw("self_attn.q_proj.weight"), lw("self_attn.k_proj.weight"),
                                  lw("self_attn.v_proj.weight")])
            # gate and up interleaved by output tile, so each engine round yields
            # matching gate/up rows and SiLU can run on it while the next computes
            gate, up = lw("mlp.gate_proj.weight"), lw("mlp.up_proj.weight")
            tb = W * IL
            gu = np.concatenate([m[i:i + tb] for i in range(0, gate.shape[0], tb) for m in (gate, up)])
            for name, w in (("qkv", qkv), ("o", lw("self_attn.o_proj.weight")), ("gu", gu),
                            ("down", lw("mlp.down_proj.weight"))):
                self.mat[(L, name)] = self.place_matrix(w)
        self.mat["lm_head"] = self.place_matrix(model.w["lm_head.weight"])
        emb = model.w["model.embed_tokens.weight"]
        self.emb_word = len(self.words)
        flat = (G.bits(emb.reshape(-1)) >> 16).astype(np.uint16)
        for i in range(0, len(flat), W * GR):
            self.words.append(flat[i:i + W * GR])
        # constant ROM: (lo, hi) pairs
        self.crom = []
        self.cb = {}
        for L in range(self.L):
            self.cb[(L, "in")] = self.put_const(model.lw(L, "input_layernorm.weight"))
            qk = np.concatenate([np.tile(model.lw(L, "self_attn.q_norm.weight"), self.NH),
                                 np.tile(model.lw(L, "self_attn.k_norm.weight"), self.KV)])
            self.cb[(L, "qk")] = self.put_const(qk)
            self.cb[(L, "post")] = self.put_const(model.lw(L, "post_attention_layernorm.weight"))
        self.cb["final"] = self.put_const(model.w["model.norm.weight"])
        self.cb["rope"] = len(self.crom)
        for pos in range(TMAX):
            cos, sin, _ = G.rope_tables(pos, self.HD, model.theta)
            self.crom.extend(zip(cos, sin))
        # KV cache (FP32 elements)
        self.kv_v0 = self.L * self.KV * self.TW * self.HD * W
        self.kv_elems = 2 * self.kv_v0

    def place_matrix(self, w):
        """Words in engine order (round, k, slot); lane g*W+l of a word holds
        row (t*IL + j)*W + l, column c*kc + k, for group g = q*S + c and tile
        t = round*(GR/S) + q (zero past the last row)."""
        n, k = w.shape
        split = G.split_for(n, k, GR, W, IL)
        kc = k // split
        tiles = -(-n // (W * IL))
        per_round = GR // split
        rounds = -(-tiles // per_round)
        base = len(self.words)
        wb = (G.bits(np.asarray(w, dtype=F)) >> 16).astype(np.uint16)
        pad = np.zeros((rounds * per_round * W * IL, k), dtype=np.uint16)
        pad[:n] = wb
        blk = pad.reshape(rounds, per_round, IL, W, split, kc)      # [r, q, j, l, c, k']
        for r in range(rounds):
            for kk in range(kc):
                for j in range(IL):
                    word = np.empty(W * GR, dtype=np.uint16)
                    for g in range(GR):
                        q, c = divmod(g, split)
                        word[g * W:(g + 1) * W] = blk[r, q, j, :, c, kk]
                    self.words.append(word)
        return dict(base=base, n=n, k=kc, tiles=rounds, split=split)

    def put_const(self, v):
        base = len(self.crom)
        self.crom.extend((F(x), F(0)) for x in v)
        return base

    def k_elem(self, L, g, t, d):
        return ((L * self.KV + g) * self.TW + t // W) * self.HD * W + d * W + t % W

    def v_elem(self, L, g, t, d):
        return self.kv_v0 + ((L * self.KV + g) * TMAX + t) * self.HD + d

    def kv_image(self, cache):
        kv = np.zeros(self.kv_elems, dtype=F)
        for L in range(self.L):
            for t, (k, v) in enumerate(cache[L]):
                for g in range(self.KV):
                    for d in range(self.HD):
                        kv[self.k_elem(L, g, t, d)] = k[g][d]
                        kv[self.v_elem(L, g, t, d)] = v[g][d]
        return kv


# -- program -----------------------------------------------------------------------
def build_program(lay):
    prog = []          # (fields, reads, writes)

    def me(mat, x, out, rnd=True, amax=False, oen=True, reads=(), writes=(), **over):
        f = dict(unit=I.UNIT_ME, me_nout=mat["n"], me_tiles=mat["tiles"], me_k=mat["k"], me_wsrc=0,
                 me_wbase=mat["base"], me_ts=mat["k"] * IL, me_ks=IL, me_js=1, me_xbase=x, me_xks=1,
                 me_round=int(rnd), me_obase=out // W, me_ots=IL, me_ojs=1, me_oen=int(oen),
                 me_amax=int(amax), me_split=mat.get("split", 1).bit_length() - 1,
                 me_xcs=mat["k"])
        f.update(over)
        prog.append((f, set(reads), set(writes)))

    def su(reads=(), writes=(), red_writes=(), **f):
        f = dict(f, unit=I.UNIT_SU, _red_regions=set(red_writes))
        prog.append((f, set(reads), set(writes) | set(red_writes)))

    # The sum of squares of x is reduced by the op that produced x (red_sq).
    sq = dict(red=I.RED_SUM, red_sq=1, r_base=VM["SSX"])

    def rmsnorm(src, n, wbase, dst):
        su(su_nout=1, su_nin=1, a_base=VM["SSX"], ma=I.MA_AIMM, imm1=f32(1.0 / n), ad=I.AD_IMM,
           imm2=f32(lay.eps), sfu=I.SFU_RSQRT, dst=I.DST_VM, d_base=VM["RX"],
           reads={"SSX"}, writes={"RX"})
        su(su_nout=1, su_nin=n, a_base=VM[src], a_si=1, ma=I.MA_AB, b_base=VM["RX"],
           c_src=I.SRC_ALT, c_base=wbase, c_si=1, mc=I.MC_C, dst=I.DST_VM, d_base=VM[dst], d_si=1,
           reads={src, "RX"}, writes={dst})

    H, HD, NH, KV, half = lay.H, lay.HD, lay.NH, lay.KV, lay.half
    group = NH // KV
    su(su_nout=1, su_nin=H, a_src=I.SRC_ALT, a_base=lay.emb_word * W * GR, a_d=I.DYN_EMBED, a_si=1,
       dst=I.DST_VM, d_base=VM["X"], d_si=1, reads={"EMB"}, writes={"X"}, red_writes={"SSX"}, **sq)
    for L in range(lay.L):
        rmsnorm("X", H, lay.cb[(L, "in")], "H")
        me(lay.mat[(L, "qkv")], VM["H"], VM["QKV"], reads={"H"}, writes={"QKV"})
        nh = NH + KV
        su(su_nout=nh, su_nin=HD, a_base=VM["QKV"], a_so=HD, a_si=1, ma=I.MA_AA, red=I.RED_SUM,
           r_base=VM["SS"], r_so=1, reads={"QKV"}, red_writes={"SS"})
        su(su_nout=1, su_nin=nh, a_base=VM["SS"], a_si=1, ma=I.MA_AIMM, imm1=f32(1.0 / HD),
           ad=I.AD_IMM, imm2=f32(lay.eps), sfu=I.SFU_RSQRT, dst=I.DST_VM, d_base=VM["RS"], d_si=1,
           reads={"SS"}, writes={"RS"})
        su(su_nout=nh, su_nin=HD, a_base=VM["QKV"], a_so=HD, a_si=1, ma=I.MA_AB, b_base=VM["RS"],
           b_so=1, c_src=I.SRC_ALT, c_base=lay.cb[(L, "qk")], c_so=HD, c_si=1, mc=I.MC_C,
           dst=I.DST_VM, d_base=VM["QN"], d_so=HD, d_si=1, reads={"QKV", "RS"}, writes={"QN"})
        rope = dict(b_src=I.SRC_ALT, b_base=lay.cb["rope"], b_d=I.DYN_ROPE, b_si=1, ma=I.MA_AB,
                    ad=I.AD_Q, a_so=HD, a_si=1, c_so=HD, c_si=1, su_nin=half)
        for lo in (True, False):
            a_off, c_off, mb = (0, half, I.MB_NEG) if lo else (half, 0, I.MB_POS)
            su(su_nout=NH, a_base=VM["QN"] + a_off, c_base=VM["QN"] + c_off, mb=mb,
               dst=I.DST_VM, d_base=VM["QR"] + a_off, d_so=HD, d_si=1,
               reads={"QN"}, writes={"QR"}, **rope)
            kq = VM["QN"] + NH * HD
            su(su_nout=KV, a_base=kq + a_off, c_base=kq + c_off, mb=mb, dst=I.DST_KV,
               d_base=lay.k_elem(L, 0, 0, a_off), d_d=I.DYN_KWRITE,
               d_so=lay.k_elem(L, 1, 0, 0) - lay.k_elem(L, 0, 0, 0), d_si=W,
               reads={"QN"}, writes={f"K{L}"}, **rope)
        su(su_nout=KV, su_nin=HD, a_base=VM["QKV"] + (NH + KV) * HD, a_so=HD, a_si=1,
           dst=I.DST_KV, d_base=lay.v_elem(L, 0, 0, 0), d_d=I.DYN_VWRITE,
           d_so=lay.v_elem(L, 1, 0, 0) - lay.v_elem(L, 0, 0, 0), d_si=1,
           reads={"QKV"}, writes={f"V{L}"})
        jsh = group.bit_length() - 1
        assert 1 << jsh == group and NH <= IL
        heads = {f"S{h}" for h in range(NH)}
        # scores[h, t] = sum_d K[g(h), t, d] q[h, d]: lanes t, slots h, k = d
        me(dict(n=0, tiles=0, k=HD, base=lay.k_elem(L, 0, 0, 0) // W), VM["QR"], VM["S"], rnd=False, me_xcs=0,
           me_wsrc=1, me_ts=HD, me_ks=1, me_js=(lay.k_elem(L, 1, 0, 0) - lay.k_elem(L, 0, 0, 0)) // W,
           me_jsh=jsh, me_xks=1, me_xjs=HD, me_ots=1, me_ojs=S_STRIDE // W, me_mmode=1,
           me_d_nout=I.DYN_T, me_d_tiles=I.DYN_TTILES, reads={"QR", f"K{L}"}, writes=heads)
        heads = {f"S{h}" for h in range(NH)}
        sm = dict(su_nout=NH, su_d_nin=I.DYN_T, a_base=VM["S"], a_so=S_STRIDE, a_si=1,
                  d_base=VM["S"], d_so=S_STRIDE, d_si=1, dst=I.DST_VM)
        su(ma=I.MA_AIMM, imm1=f32(1.0 / np.sqrt(HD)), red=I.RED_MAX, r_base=VM["M"], r_so=1,
           reads=heads, writes=heads, red_writes={"M"}, **sm)
        su(b_base=VM["M"], b_so=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, red=I.RED_SUM, r_base=VM["Z"],
           r_so=1, reads=heads | {"M"}, writes=heads, red_writes={"Z"}, **sm)
        su(su_nout=1, su_nin=NH, a_base=VM["Z"], a_si=1, sfu=I.SFU_RECIP, dst=I.DST_VM,
           d_base=VM["RZ"], d_si=1, reads={"Z"}, writes={"RZ"})
        su(ma=I.MA_AB, b_base=VM["RZ"], b_so=1, reads=heads | {"RZ"}, writes=heads, **sm)
        # attn[h, d] = sum_t V[g(h), t, d] p[h, t]: lanes d, slots h, k = t
        me(dict(n=HD, tiles=-(-HD // W), k=0, base=lay.v_elem(L, 0, 0, 0) // W), VM["S"], VM["ATT"],
           rnd=False, me_xcs=0, me_wsrc=1, me_ts=1, me_ks=max(1, HD // W),
           me_js=(lay.v_elem(L, 1, 0, 0) - lay.v_elem(L, 0, 0, 0)) // W, me_jsh=jsh, me_xks=1,
           me_xjs=S_STRIDE, me_ots=1, me_ojs=max(1, HD // W), me_mmode=1, me_d_k=I.DYN_T,
           reads=heads | {f"V{L}"}, writes={"ATT"})
        me(lay.mat[(L, "o")], VM["ATT"], VM["T1"], reads={"ATT"}, writes={"T1"})
        su(su_nout=1, su_nin=H, a_base=VM["X"], a_si=1, c_base=VM["T1"], c_si=1, ad=I.AD_C,
           dst=I.DST_VM, d_base=VM["X"], d_si=1, reads={"X", "T1"}, writes={"X"}, red_writes={"SSX"}, **sq)
        rmsnorm("X", H, lay.cb[(L, "post")], "H")
        me(lay.mat[(L, "gu")], VM["H"], VM["GU"], reads={"H"}, writes={f"GU{r}" for r in range(lay.FF // (W * IL))})
        FF = lay.FF
        tb = W * IL
        for r in range(FF // tb):                           # one fused SiLU*up op per tile pair
            g0 = VM["GU"] + 2 * tb * r
            su(su_nout=1, su_nin=tb, a_base=g0, a_si=1, ma=I.MA_AIMM, imm1=f32(-1.0), sfu=I.SFU_SIGM,
               c_base=g0, c_si=1, mc=I.MC_C, b_base=g0 + tb, b_si=1, md=I.MD_B, dst=I.DST_VM,
               d_base=VM["ACT"] + tb * r, d_si=1, reads={f"GU{r}"}, writes={f"ACT{r}"})
        me(lay.mat[(L, "down")], VM["ACT"], VM["T1"], reads={f"ACT{r}" for r in range(lay.FF // (W * IL))},
           writes={"T1"})
        su(su_nout=1, su_nin=H, a_base=VM["X"], a_si=1, c_base=VM["T1"], c_si=1, ad=I.AD_C,
           dst=I.DST_VM, d_base=VM["X"], d_si=1, reads={"X", "T1"}, writes={"X"}, red_writes={"SSX"}, **sq)
    rmsnorm("X", H, lay.cb["final"], "H")
    me(lay.mat["lm_head"], VM["H"], 0, amax=True, oen=False, reads={"H"})
    prog.append((dict(unit=I.UNIT_END, barrier=1), set(), set()))
    # Barriers: an instruction waits for everything in flight when it touches a
    # region an in-flight instruction writes, or writes one it reads.
    # ELEMENT CHAINING.  An op whose only hazards are reads of what the OTHER
    # unit's latest op writes need not wait for a barrier: it may start once
    # that op has made `chase_n` progress (stream unit: elements written, in
    # emission order; matrix engine: result slots, in round/slot order).
    # chase_n is derived from the producer's write order and the consumer's
    # read order so that no read can overtake its write:
    #   * engine reading stream output: x element at producer position p is
    #     read no sooner than 8*k' cycles after start, the stream writes one
    #     element per cycle, so chase_n >= p - 8*k' + 1 for every read;
    #   * stream reading engine output: chase_n = the last result slot any of
    #     its reads needs.
    # Each unit retires in order, so once the latest op has written anything,
    # every older op of that unit has written all its main output: reads of
    # those need only chase_n >= 1.  Reads of reducer outputs or of the same
    # unit's in-flight writes are never chased.
    out, rd, wr = [], set(), set()
    last = {I.UNIT_ME: None, I.UNIT_SU: None}
    main = {I.UNIT_ME: set(), I.UNIT_SU: set()}      # in-flight main writes per unit
    for f, reads, writes in prog:
        assert all(isinstance(r, str) for r in reads | writes), (reads, writes)
        conflict = (reads & wr) | (writes & (rd | wr))
        other = I.UNIT_SU if f["unit"] == I.UNIT_ME else I.UNIT_ME
        prod = last.get(other)
        chase_n = None
        if (conflict and prod is not None and f["unit"] != I.UNIT_END and not (writes & (rd | wr))
                and conflict <= main[other]):
            chase_n = chase_threshold(f, prod[0])
        if chase_n is not None:
            f["chase"], f["chase_n"] = 1, chase_n
        elif conflict or f.get("barrier"):
            f["barrier"] = 1
            rd, wr = set(), set()
            main = {I.UNIT_ME: set(), I.UNIT_SU: set()}
        rd |= reads
        wr |= writes
        out.append(f)
        if f["unit"] in last:
            red = set(f.get("_red_regions", ()))
            last[f["unit"]] = (f, reads, writes, red)
            main[f["unit"]] |= writes - red
    for f in out:
        f.pop("_red_regions", None)
    return out


def su_write_order(f):
    """Destination element addresses of a stream op, in emission order."""
    if f.get("dst", 0) != I.DST_VM:
        return {}
    o, i = np.meshgrid(np.arange(f["su_nout"]), np.arange(f["su_nin"]), indexing="ij")
    addr = (f["d_base"] + o * f.get("d_so", 0) + i * f.get("d_si", 0)).reshape(-1)
    return {int(a): n for n, a in enumerate(addr)}


def me_write_slots(f):
    """Vector-memory element -> result slot (1-based) of a ROM matrix-vector op."""
    split = f.get("me_split", 0)
    per_round = GR >> split
    slots = {}
    for r in range(f["me_tiles"]):
        for j in range(IL):
            for q in range(per_round):
                t = r * per_round + q
                word = f["me_obase"] + t * f["me_ots"] + j * f["me_ojs"]
                for l in range(W):
                    if (t * IL + j) * W + l < f["me_nout"]:
                        slots[word * W + l] = r * IL + j + 1
    return slots


def chase_threshold(f, prod):
    """chase_n for consumer `f` of producer `prod` (other unit), or None."""
    if f["unit"] == I.UNIT_ME and prod["unit"] == I.UNIT_SU:
        if f.get("me_wsrc") or f.get("me_xjs") or f.get("me_d_k") or f.get("me_xks", 1) != 1:
            return None
        order = su_write_order(prod)
        need = 1
        for c in range(1 << f.get("me_split", 0)):
            for k in range(f["me_k"]):
                p = order.get(f["me_xbase"] + c * f.get("me_xcs", 0) + k)
                if p is not None:
                    need = max(need, p - 8 * k + 1)
        return need
    if f["unit"] == I.UNIT_SU and prod["unit"] == I.UNIT_ME:
        if prod.get("me_wsrc") or f.get("su_d_nin"):
            return None
        slots = me_write_slots(prod)
        need = 0
        for s_ in "abc":
            if f.get(f"{s_}_src", 0) != I.SRC_VM or (s_ == "b" and not (f.get("ma") == I.MA_AB or f.get("md") or f.get("ad") == I.AD_NEGB)):
                continue
            o, i = np.meshgrid(np.arange(f["su_nout"]), np.arange(f["su_nin"]), indexing="ij")
            for a in (f.get(f"{s_}_base", 0) + o * f.get(f"{s_}_so", 0) + i * f.get(f"{s_}_si", 0)).reshape(-1):
                need = max(need, slots.get(int(a), 0))
        return need or None
    return None


# -- ISA-level simulator --------------------------------------------------------------
def dyn_values(lay, token, pos):
    return [0, token * lay.H, pos * lay.half,
            (pos // W) * lay.HD * W + pos % W, pos * lay.HD, pos + 1, pos // W + 1]


class Machine:
    def __init__(self, lay, kv):
        self.lay = lay
        self.vm = np.zeros(I.VM_ELEMS, dtype=F)
        self.kv = kv.copy()
        self.wrom = np.stack(lay.words).reshape(-1)                 # bf16 element view (W*GR per word)
        self.crom = np.array(lay.crom, dtype=F)                     # [n, 2]
        self.argmax = None
        self.logits = []

    def wrom_f32(self, elems):
        return G.from_bits(self.wrom[elems].astype(np.uint32) << 16)

    def run(self, prog, token, pos):
        dyn = dyn_values(self.lay, token, pos)
        for f in prog:
            f = {name: f.get(name, 0) for name, _ in I.FIELDS}
            if f["unit"] == I.UNIT_ME:
                self.me(f, dyn)
            elif f["unit"] == I.UNIT_SU:
                self.su(f, dyn)
        return self.argmax

    def me(self, f, dyn):
        n = f["me_nout"] + dyn[f["me_d_nout"]]
        tiles = f["me_tiles"] + dyn[f["me_d_tiles"]]
        K = f["me_k"] + dyn[f["me_d_k"]]
        wb = f["me_wbase"] + dyn[f["me_d_wbase"]]
        xb = f["me_xbase"] + dyn[f["me_d_xbase"]]
        ob = f["me_obase"] + dyn[f["me_d_obase"]]
        split = 0 if f["me_wsrc"] else f["me_split"]
        S = 1 << split
        per_round = 1 if f["me_wsrc"] else GR // S
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
                word = wb + r * f["me_ts"] + k * f["me_ks"] + (j >> f["me_jsh"]) * f["me_js"]
                if f["me_wsrc"]:
                    w = self.kv[word * W + l]
                else:
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

    def stream(self, f, dyn, s, n_out, n_in):
        base = f[f"{s}_base"] + dyn[f[f"{s}_d"]]
        o, i = np.meshgrid(np.arange(n_out), np.arange(n_in), indexing="ij")
        return (base + o * f[f"{s}_so"] + i * f[f"{s}_si"]).reshape(-1)

    def su(self, f, dyn):
        n_out = f["su_nout"]
        n_in = f["su_nin"] + dyn[f["su_d_nin"]]
        ea = self.stream(f, dyn, "a", n_out, n_in)
        eb = self.stream(f, dyn, "b", n_out, n_in)
        ec = self.stream(f, dyn, "c", n_out, n_in)
        a = self.wrom_f32(ea) if f["a_src"] else self.vm[ea]
        if f["b_src"]:
            blo, bhi = self.crom[eb, 0], self.crom[eb, 1]
        else:
            blo, bhi = self.vm[eb], np.zeros(len(eb), dtype=F)
        c = self.crom[ec, 0] if f["c_src"] else self.vm[ec]
        imm1, imm2 = G.from_bits(np.uint32(f["imm1"])), G.from_bits(np.uint32(f["imm2"]))
        p = {I.MA_BYP: a, I.MA_AB: lambda: G.mul(a, blo), I.MA_AA: lambda: G.mul(a, a),
             I.MA_AIMM: lambda: G.mul(a, imm1)}[f["ma"]]
        p = p() if callable(p) else p
        q = {I.MB_OFF: None, I.MB_POS: lambda: G.mul(c, bhi), I.MB_NEG: lambda: G.mul(c, G.neg(bhi))}[f["mb"]]
        q = q() if callable(q) else q
        r = {I.AD_BYP: lambda: p, I.AD_Q: lambda: G.add(p, q), I.AD_C: lambda: G.add(p, c),
             I.AD_NEGB: lambda: G.add(p, G.neg(blo)), I.AD_IMM: lambda: G.add(p, imm2)}[f["ad"]]()
        s = {I.SFU_NONE: lambda: r, I.SFU_EXP: lambda: G.exp(r), I.SFU_RECIP: lambda: G.reciprocal(r),
             I.SFU_RSQRT: lambda: G.rsqrt(r),
             I.SFU_SIGM: lambda: G.reciprocal(G.add(G.exp(r), F(1.0)))}[f["sfu"]]()
        out = G.mul(s, c) if f["mc"] == I.MC_C else s
        if f["md"] == I.MD_B:
            out = G.mul(out, blo)
        out = np.asarray(out, dtype=F).reshape(-1)
        if f["red"]:
            seg = (G.mul(out, out) if f["red_sq"] else out).reshape(n_out, n_in)
            vals = [G.reduce_sum(v) if f["red"] == I.RED_SUM else np.max(v) for v in seg]
            for o, v in enumerate(vals):
                self.vm[f["r_base"] + o * f["r_so"]] = v
        if f["dst"]:
            ed = self.stream(f, dyn, "d", n_out, n_in)
            (self.vm if f["dst"] == I.DST_VM else self.kv)[ed] = out


# -- images ----------------------------------------------------------------------------
def hexwords(values, width_bits):
    digits = width_bits // 4
    return "".join(f"{int(v):0{digits}x}\n" for v in values)


def pack_lanes(lanes, bits_per_lane):
    word = 0
    for i, v in enumerate(lanes):
        word |= int(v) << (bits_per_lane * i)
    return word


def golden_state():
    model = G.Model(GR)
    prompt, expected = G.prompt_and_expected()
    cache = [[] for _ in range(model.layers)]
    for pos, tok in enumerate(prompt[:-1]):
        model.decode_token(tok, pos, cache)
    return model, prompt, expected, cache


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, help="write RTL images and expectations here")
    ap.add_argument("--stop", type=int, help="debug: end the program after this many instructions")
    args = ap.parse_args()
    model, prompt, expected, cache = golden_state()
    lay = Layout(model)
    token, pos = prompt[-1], len(prompt) - 1
    kv = lay.kv_image(cache)
    prog = build_program(lay)
    if args.stop is not None:
        prog = prog[:args.stop] + [dict(unit=I.UNIT_END, barrier=1)]
    mach = Machine(lay, kv)
    got = mach.run(prog, token, pos)
    ref = model.decode_token(token, pos, [list(c) for c in cache])
    exact = bool(np.array_equal(G.bits(mach.logits), G.bits(ref))) if len(mach.logits) else False
    n_bar = sum(1 for f in prog if f.get("barrier"))
    print(f"program: {len(prog)} instructions, {n_bar} barriers; weight ROM {len(lay.words)} words; "
          f"constant ROM {len(lay.crom)}; KV {lay.kv_elems} elements")
    print(f"ISA simulator: token {got} (oracle {expected[0]}), logits bit-exact with golden: {exact}")
    if args.out:
        out = args.out
        out.mkdir(parents=True, exist_ok=True)
        (out / "wrom.hex").write_text(hexwords((pack_lanes(w, 16) for w in lay.words), 16 * W * GR))
        (out / "crom.hex").write_text(hexwords(
            ((f32(hi) << 32) | f32(lo) for lo, hi in lay.crom), 64))
        kvw = G.bits(kv).reshape(-1, W)
        (out / "kv.hex").write_text(hexwords((pack_lanes(w, 32) for w in kvw), 32 * W))
        words = [I.encode(**{k: v for k, v in f.items()}) for f in prog]
        (out / "prog.hex").write_text(hexwords(words, I.INSTR_BITS))
        (out / "expect_logits.hex").write_text(hexwords(G.bits(mach.logits), 32))
        (out / "expect_vm.hex").write_text(hexwords(G.bits(mach.vm), 32))
        (out / "expect_kv.hex").write_text(hexwords(G.bits(mach.kv), 32))
        (out / "prompt.hex").write_text(hexwords(prompt, 16))
        (out / "generated.hex").write_text(hexwords(expected, 16))
        (out / "run.args").write_text(f"+TOKEN={token} +POS={pos} +EXPECT={got}\n")
        (out / "expect.json").write_text(json.dumps({
            "token": token, "pos": pos, "argmax": got, "oracle": expected[0],
            "logits": [int(b) for b in G.bits(mach.logits)],
            "vm": [int(b) for b in G.bits(mach.vm)],
            "kv_words": len(kvw), "wrom_words": len(lay.words), "crom_words": len(lay.crom),
            "prog_words": len(words)}))
        print("wrote", out)
    return 0 if exact and got == expected[0] else 1


if __name__ == "__main__":
    raise SystemExit(main())
