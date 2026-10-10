"""Qwen3 (dense, GQA, QK-norm) -> HGI-1 programs and per-die HBM images for the r25 die at TP4.

The 28 families on the HGI-1 unit operations + SU templates (spec sections 3.6 and 7.2, the owner-approved encoding),
with the bindings this compiler uses (each family's record tag starts with its family name):

  embedding        DMA.LOAD codes (TOKEN * emb_row_bytes) + DMA.LOAD its BF16 scale + SU.VOP x = code * scale
  prenorm          FUSED.ROW_NORM seg 0, out BF16 (the matvec input rounding point)
  qkv/o/gu/down/head  SM.MATVEC fmt 3 (INT8), raw FP32 sums (row scale applied by the consumer)
  row_scale_qkv / row_scale_gu / head_scale   DMA.LOAD scales + SU.VOP y = t * s (M1 = A*B)
  row_scale_o / row_scale_down + residual     DMA.LOAD scales + ONE SU.VOP x = t * s + x (M1 A*B, AD +C)
  qknorm           FUSED.ROW_NORM seg 128, out FP32 (O.fmt)
  rope             DMA.LOAD the position's cos|sin row (hoisted: once a token) + SU.VOP c_pair (i XOR 1) on the
                   offline-permuted W_q / W_k rows (spec 7.2: split-half pairs made adjacent), b_half tables
  round_q          SU.VOP rnd (BF16 q)
  kv_append        DMA.STORE K and V rows, FP8, at POS (kv_dense layout)        kv_fence  DMA.FENCE
  attention_qk     ATT.QK, one record a KV head, 4 lanes (GQA)               attention_pv  ATT.PV likewise
  softmax          SU fallback (FUSED.SOFTMAX pending CF-SFX): pass 1 RED_MAX of s*scale; pass 2 exp(s*scale - m) + RED_SUM (FP32 e);
                   pass 2b BF16 publication of e
  pv_normalize     SU.VOP o = pv / Z (M1 = A / B, B broadcast)
  swiglu           SFU.GLU: O.fmt BF16, imm_a = FLT_MAX (no clamp), C = 1.0 by ibcast (no route weight)
  all_reduce_o / all_reduce_down   COLL.ALL_REDUCE_SUM (group 4, rank order)
  argmax_local / argmax_gather+merge   ARGMAX.LOCAL (imm_a = head rows per die) + COLL.ARGMAX_MERGE
  end              CTL.END

`wait` masks come from region hazards (RAW / WAR / WAW against every other unit's records since that unit last
drained), as hdc_program_v41.schedule does; collectives order themselves by arrival but still wait for the units
that produce their input.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hbm_generic_iface as HGI  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402

from .machine import Hbm, fp8_encode  # noqa: E402
from .records import DYN, MDesc, Rec, wait_mask  # noqa: E402

F = np.float32
TP = 4
FLT_MAX = 0x7F7FFFFF


def f32bits(x):
    return int(np.asarray(F(x)).view(np.uint32))


def qwen_params(cfg):
    """Per-operation immediates from the model (the manifest's eps and softmax-scale literal)."""
    return dict(norm_eps=f32bits(cfg["rms_norm_eps"]), attn_scale=f32bits(1.0 / float(cfg["head_dim"]) ** 0.5))


def f32u(x):
    return int(np.asarray(F(x)).view(np.uint32))


def al(n, a=32):
    return -(-n // a) * a


class Geometry:
    """Per-die shapes and the VM / HBM maps for one Qwen3 config at TP4."""

    def __init__(self, cfg, ctx):
        self.H, self.NH, self.KV, self.HD = cfg["hidden_size"], cfg["num_attention_heads"], \
            cfg["num_key_value_heads"], cfg["head_dim"]
        self.FF, self.V, self.L = cfg["intermediate_size"], cfg["vocab_size"], cfg["num_hidden_layers"]
        self.nq, self.nk = self.NH // TP, self.KV // TP
        self.ff = self.FF // TP
        self.hrows = self.V // TP
        self.ctx = ctx
        self.rows_qkv = (self.nq + 2 * self.nk) * self.HD
        H, HD = self.H, self.HD
        # ---- VM (FP32 words) -------------------------------------------------------------------------------
        vm = {}
        cur = [0]

        def put(name, n, align=128):
            cur[0] = -(-cur[0] // align) * align
            vm[name] = cur[0]
            cur[0] += n
        put("X", H)
        put("H", H)
        put("QKVRAW", self.rows_qkv)
        put("QKV", self.rows_qkv)
        put("QN", (self.nq + self.nk) * HD)
        put("ROPE", HD)
        put("ONE", 1)
        put("QR", (self.nq + self.nk) * HD)
        put("QB", self.nq * HD)
        put("SC", self.nq * ctx)
        put("E", self.nq * ctx)
        put("MAX", self.nq)
        put("Z", self.nq)
        put("PV", self.nq * HD)
        put("ATTN", self.nq * HD)
        put("OPART", H)
        put("OSUM", H)
        put("SCL", max(H, 2 * self.ff, self.rows_qkv))
        put("GURAW", 2 * self.ff)
        put("GU", 2 * self.ff)
        put("ACT", self.ff)
        put("DPART", H)
        put("DSUM", H)
        put("ESC", 1)
        put("AMX", 2)
        put("TOK", 1)
        self.vm_end = cur[0]
        # the head reuses the attention scratch for its logits: raw sums in SC, scales in E, scaled logits in place
        assert self.nq * ctx >= self.hrows or ctx < 8192, "head shard must fit the score scratch"
        if self.nq * ctx >= self.hrows:
            vm["LRAW"] = vm["LOG"] = vm["SC"]
            vm["LSCL"] = vm["E"]
        else:                                 # small test contexts
            vm["LRAW"] = vm["LOG"] = cur[0]
            vm["LSCL"] = cur[0] + al(self.hrows, 128)
            self.vm_end = vm["LSCL"] + self.hrows
        assert self.vm_end <= 1 << 18, f"VM map needs {self.vm_end} words"
        self.vm = vm
        # ---- HBM (bytes), one uniform block a layer (lstride) ----------------------------------------------
        lay = {}
        off = 0

        def hput(name, nbytes):
            nonlocal off
            off = al(off)
            lay[name] = off
            off += nbytes
        hput("qkv", self.rows_qkv * H)
        hput("qkv_s", self.rows_qkv * 2)
        hput("o", H * self.nq * HD)
        hput("o_s", H * 2)
        hput("gu", 2 * self.ff * H)
        hput("gu_s", 2 * self.ff * 2)
        hput("down", H * self.ff)
        hput("down_s", H * 2)
        hput("ln1", H * 2)
        hput("ln2", H * 2)
        hput("qn", HD * 2)
        hput("kn", HD * 2)
        self.layer_bytes = al(off, 4096)
        self.lay = lay
        self.kv_plane = ctx * HD                      # bytes of one [kvh][K|V] plane (FP8)
        self.kv_layer = self.nk * 2 * self.kv_plane
        self.emb_row = al(H + 2)
        base = 1 << 32
        self.hbm = dict(EMBED=base, TABLES=base * 2, HEAD=base * 3, WEIGHTS=base * 4, KV=base * 6)
        self.tables = dict(norm=0, one=al(H * 2), rope=al(H * 2) + 32)
        self.rope_row = HD * 4                        # cos(HD/2) | sin(HD/2) FP32: angle t serves the pair (2t, 2t+1)


# ----------------------------------------------------------------------------------------------------------------
# images
# ----------------------------------------------------------------------------------------------------------------
def bf16_bytes(v):
    from . import lib as A
    return (A.to_bf16(np.asarray(v, dtype=F)).view(np.uint32) >> 16).astype(np.uint16).view(np.uint8)


def build_images(model, g: Geometry, layers, kv_state=None, shared_embed=None):
    """Per-die Hbm images.  layers: the model layer ids the image holds, in LOOP order.  kv_state(i) -> (Kc, Vc)
    full-head FP8-valued caches [KV, ctx, HD] (synthetic state) or None (empty cache)."""
    from . import lib as A
    H = g.H
    ec, es = model.img.get("embed")
    if shared_embed is None:
        emb = np.zeros((g.V, g.emb_row), dtype=np.uint8)
        emb[:, :H] = ec.view(np.uint8)
        emb[:, H:H + 2] = bf16_bytes(es).reshape(-1, 2)
        shared_embed = emb
    # rope table: row p = [cos | sin] FP32, HD/2 angles each; the SU reads angle i >> 1 for element i (b_half)
    pos = np.arange(g.ctx)
    cos, sin = A.rope_tables(pos, g.HD, model.theta)
    rope = np.concatenate([cos, sin], axis=1).astype(F)
    fnorm = bf16_bytes(model.ck.get("model.norm.weight"))
    hc, hs = model.img.get("lm_head")
    dies = []
    kvs = {i: kv_state(i) for i in layers} if kv_state else {}
    for d in range(TP):
        hb = Hbm()
        hb.add(g.hbm["EMBED"], shared_embed, "EMBED")
        tab = np.zeros(g.tables["rope"] + rope.nbytes, dtype=np.uint8)
        tab[:fnorm.size] = fnorm
        tab[g.tables["one"]:g.tables["one"] + 4] = np.asarray([1.0], dtype=F).view(np.uint8)
        tab[g.tables["rope"]:] = rope.view(np.uint8).reshape(-1)
        hb.add(g.hbm["TABLES"], tab, "TABLES")
        r0, r1 = model.head_rows(d)
        head = np.zeros(al(g.hrows * H) + al(g.hrows * 2), dtype=np.uint8)
        head[:g.hrows * H] = hc[r0:r1].view(np.uint8).reshape(-1)
        head[al(g.hrows * H):al(g.hrows * H) + g.hrows * 2] = bf16_bytes(hs[r0:r1])
        hb.add(g.hbm["HEAD"], head, "HEAD")
        wts = np.zeros(g.layer_bytes * len(layers), dtype=np.uint8)
        kv = np.zeros(g.kv_layer * len(layers), dtype=np.uint8)
        q, k, v = model.die_rows(d)
        rows = np.concatenate([q, k, v])
        for j, i in enumerate(layers):
            blk = wts[j * g.layer_bytes:(j + 1) * g.layer_bytes]

            def w(name, arr):
                arr = np.ascontiguousarray(arr).view(np.uint8).reshape(-1)
                blk[g.lay[name]:g.lay[name] + arr.size] = arr
            c, s = model.img.get(f"L{i}.qkv")
            w("qkv", c[rows])
            w("qkv_s", bf16_bytes(s[rows]))
            c, s = model.img.get(f"L{i}.o")
            w("o", c[:, d * g.nq * g.HD:(d + 1) * g.nq * g.HD])
            w("o_s", bf16_bytes(s))
            c, s = model.img.get(f"L{i}.gu")
            gr = np.concatenate([np.arange(d * g.ff, (d + 1) * g.ff), g.FF + np.arange(d * g.ff, (d + 1) * g.ff)])
            w("gu", c[gr])
            w("gu_s", bf16_bytes(s[gr]))
            c, s = model.img.get(f"L{i}.down")
            w("down", c[:, d * g.ff:(d + 1) * g.ff])
            w("down_s", bf16_bytes(s))
            w("ln1", bf16_bytes(model.lw(i, "input_layernorm")))
            w("ln2", bf16_bytes(model.lw(i, "post_attention_layernorm")))
            w("qn", bf16_bytes(model.lw(i, "self_attn.q_norm")))
            w("kn", bf16_bytes(model.lw(i, "self_attn.k_norm")))
            if i in kvs:
                Kc, Vc = kvs[i]
                P = Kc.shape[1]
                for h in range(g.nk):
                    kvh = d * g.nk + h
                    for kind, src in ((0, Kc), (1, Vc)):
                        o = j * g.kv_layer + (h * 2 + kind) * g.kv_plane
                        kv[o:o + P * g.HD] = fp8_encode(src[kvh].reshape(-1))
        hb.add(g.hbm["WEIGHTS"], wts, "WEIGHTS")
        hb.add(g.hbm["KV"], kv, "KV")
        dies.append(hb)
    return dies, shared_embed


# ----------------------------------------------------------------------------------------------------------------
# program
# ----------------------------------------------------------------------------------------------------------------
def V(g, name, n, m=1, stride=0, istride=0, off=0, n_sel=0, ibcast=0, fmt="FP32"):
    return MDesc(space="VM", fmt=fmt, base=g.vm[name] + off, n=n, m=m, stride=stride, istride=istride, n_sel=n_sel,
                 ibcast=ibcast)


def sut(**kw):
    t = {n: 0 for n, _ in HGI.SUT_FIELDS}
    t.update(a_src=I.SRC_VM, b_src=I.SRC_VM, c_src=I.SRC_VM, d_src=I.SRC_VM)
    t.update(kw)
    return t


class Builder:
    """Program assembly with wait masks from region hazards: a record waits for unit u (u != its own unit) when it
    reads a region u wrote, or writes a region u read or wrote, since u last drained (RAW / WAR / WAW; read-read is
    not a hazard).  A record's own unit orders it (in-order queue)."""

    def __init__(self, g):
        self.g = g
        self.recs = []
        self.prd = {u: set() for u in HGI.UNITS}
        self.pwr = {u: set() for u in HGI.UNITS}

    def add(self, rec: Rec, reads, writes):
        mask = 0
        rd, wr = set(reads), set(writes)
        for u in HGI.UNITS:
            if u == rec.unit:
                continue
            if (rd & self.pwr[u]) or (wr & (self.prd[u] | self.pwr[u])):
                mask |= wait_mask(u)
        for u in HGI.UNITS:
            if mask >> HGI.UNITS.index(u) & 1:
                self.prd[u], self.pwr[u] = set(), set()
        rec.wait = mask
        rec.reads, rec.writes = sorted(rd), sorted(wr)
        self.prd[rec.unit] |= rd
        self.pwr[rec.unit] |= wr
        self.recs.append(rec)
        return rec


def assign_waits(recs):
    """Wait masks for a record list with LOOPs (any number, nested): the hazard rule over the sequence in which each
    loop body appears twice (the second pass sees the pending state the back edge carries); a body record's mask is
    the union of its passes."""
    def expand(lo, hi):
        out, k = [], lo
        while k < hi:
            r = recs[k]
            if r.unit == "CTL" and r.op == "LOOP":
                depth, e = 0, k
                for e in range(k, hi):
                    if recs[e].unit == "CTL" and recs[e].op == "LOOP":
                        depth += 1
                    elif recs[e].unit == "CTL" and recs[e].op == "ENDLOOP":
                        depth -= 1
                        if depth == 0:
                            break
                body = expand(k + 1, e)
                out += [k] + body + body + [e]
                k = e + 1
            else:
                out.append(k)
                k += 1
        return out
    seq = expand(0, len(recs))
    b = Builder(None)
    masks = {}
    import copy as _c
    for k in seq:
        r = _c.copy(recs[k])
        b.add(r, recs[k].reads, recs[k].writes)
        masks[k] = masks.get(k, 0) | r.wait
    for k, r in enumerate(recs):
        r.wait = masks.get(k, 0)
    return recs


def program(g: Geometry, md, n_layers, parts=("embed", "layers", "head")):
    """The token program (SPMD, every die).  md: qwen_params(cfg).  parts: which blocks to emit (stage benches emit a
    subset)."""
    b = Builder(g)
    H, HD, nq, nk, P = g.H, g.HD, g.nq, g.nk, g.ctx
    eps = md["norm_eps"]
    scale = md["attn_scale"]
    T = g.hbm["TABLES"]
    WB = g.hbm["WEIGHTS"]
    lay = g.lay
    LB = g.layer_bytes

    def W(name, fmt, n, m, stride):
        return MDesc(space="HBM", fmt=fmt, base=WB + lay[name], n=n, m=m, stride=stride, lstride=LB)

    if "embed" in parts:
        b.add(Rec("DMA", "LOAD", desc=dict(
            A=MDesc(space="HBM", fmt="INT8", base=g.hbm["EMBED"], n=H, dyn_sel=DYN["TOKEN"], dyn_mul=g.emb_row),
            O=V(g, "X", H)), tag="embedding.codes", family="embedding"), [], ["X"])
        b.add(Rec("DMA", "LOAD", desc=dict(
            A=MDesc(space="HBM", fmt="BF16", base=g.hbm["EMBED"] + H, n=1, dyn_sel=DYN["TOKEN"], dyn_mul=g.emb_row),
            O=V(g, "ESC", 1)), tag="embedding.scale", family="embedding"), [], ["ESC"])
        b.add(Rec("SU", "VOP", sut=sut(m1=I.M1_AB, dst=I.DST_VM),
                  desc=dict(A=V(g, "X", H), B=V(g, "ESC", H, ibcast=1), O=V(g, "X", H)),
                  tag="embedding.dequant", family="embedding"), ["X", "ESC"], ["X"])
    if "layers" in parts:
        b.add(Rec("DMA", "LOAD", desc=dict(
            A=MDesc(space="HBM", fmt="FP32", base=T + g.tables["rope"], n=HD, dyn_sel=DYN["POS"],
                    dyn_mul=g.rope_row), O=V(g, "ROPE", HD)), tag="rope.table_row", family="rope"), [], ["ROPE"])
        b.add(Rec("DMA", "LOAD", desc=dict(A=MDesc(space="HBM", fmt="FP32", base=T + g.tables["one"], n=1),
                                           O=V(g, "ONE", 1)), tag="swiglu.route_one", family="swiglu"), [], ["ONE"])
        if n_layers > 1:
            b.add(Rec("CTL", "LOOP", param=n_layers, tag="layers"), [], [])
        # -- attention block ------------------------------------------------------------------------------
        b.add(Rec("FUSED", "ROW_NORM", param=H // 128, imm_a=eps, desc=dict(
            A=V(g, "X", H), B=W("ln1", "BF16", H, 1, 0), O=MDesc(space="VM", fmt="BF16", base=g.vm["H"], n=H)),
            tag="prenorm.attn", family="prenorm"), ["X"], ["H"])
        b.add(Rec("SM", "MATVEC", param=3, desc=dict(
            A=V(g, "H", H), B=W("qkv", "INT8", H, g.rows_qkv, H), O=V(g, "QKVRAW", g.rows_qkv)),
            tag="qkv", family="qkv"), ["H"], ["QKVRAW"])
        b.add(Rec("DMA", "LOAD", desc=dict(A=W("qkv_s", "BF16", g.rows_qkv, 1, 0), O=V(g, "SCL", g.rows_qkv)),
                  tag="row_scale_qkv.load", family="row_scale_qkv"), [], ["SCL"])
        b.add(Rec("SU", "VOP", sut=sut(m1=I.M1_AB, dst=I.DST_VM), desc=dict(
            A=V(g, "QKVRAW", g.rows_qkv), B=V(g, "SCL", g.rows_qkv), O=V(g, "QKV", g.rows_qkv)),
            tag="row_scale_qkv", family="row_scale_qkv"), ["QKVRAW", "SCL"], ["QKV"])
        b.add(Rec("FUSED", "ROW_NORM", param=(nq * HD // 128) | (HD << 6), imm_a=eps, desc=dict(
            A=V(g, "QKV", nq * HD), B=W("qn", "BF16", HD, 1, 0), O=V(g, "QN", nq * HD)),
            tag="qknorm.q", family="qknorm"), ["QKV"], ["QN"])
        b.add(Rec("FUSED", "ROW_NORM", param=(nk * HD // 128) | (HD << 6), imm_a=eps, desc=dict(
            A=V(g, "QKV", nk * HD, off=nq * HD), B=W("kn", "BF16", HD, 1, 0), O=V(g, "QN", nk * HD, off=nq * HD)),
            tag="qknorm.k", family="qknorm"), ["QKV"], ["QN"])
        nh = nq + nk
        b.add(Rec("SU", "VOP", sut=sut(m1=I.M1_AB, qm=I.QM_ALT_NP, ad=I.AD_Q, c_pair=1, b_half=1, dst=I.DST_VM),
                  desc=dict(A=V(g, "QN", HD, m=nh, stride=HD), B=V(g, "ROPE", HD // 2, m=nh, stride=0),
                            D=V(g, "ROPE", HD // 2, m=nh, stride=0, off=HD // 2), O=V(g, "QR", HD, m=nh, stride=HD)),
            tag="rope", family="rope"), ["QN", "ROPE"], ["QR"])
        b.add(Rec("SU", "VOP", sut=sut(rnd=1, dst=I.DST_VM), desc=dict(A=V(g, "QR", nq * HD), O=V(g, "QB", nq * HD)),
                  tag="round_q", family="round_q"), ["QR"], ["QB"])
        KVB = g.hbm["KV"]
        for kind, src, off in ((0, "QR", nq * HD), (1, "QKV", (nq + nk) * HD)):
            b.add(Rec("DMA", "STORE", desc=dict(
                A=V(g, src, HD, m=nk, stride=HD, off=off),
                O=MDesc(space="HBM", fmt="FP8E4M3", base=KVB + kind * g.kv_plane, n=HD, m=nk, stride=2 * g.kv_plane,
                        lstride=g.kv_layer, dyn_sel=DYN["POS"], dyn_mul=HD)),
                tag=f"kv_append.{'KV'[kind]}", family="kv_append"), [src], ["KVCACHE"])
        b.add(Rec("DMA", "FENCE", tag="kv_fence", family="kv_fence"), [], ["KVCACHE"])
        lanes = nq // nk
        for h in range(nk):
            b.add(Rec("ATT", "QK", param=lanes | ((HD // 64 - 1) << 4), desc=dict(
                A=V(g, "QB", HD, m=lanes, stride=HD, off=h * lanes * HD),
                B=MDesc(space="HBM", fmt="FP8E4M3", base=KVB + (h * 2) * g.kv_plane, n=1, m=1, stride=HD,
                        lstride=g.kv_layer, n_sel=DYN["POS1"]),
                O=V(g, "SC", 1, m=lanes, stride=P, off=h * lanes * P, n_sel=DYN["POS1"])),
                tag=f"attention_qk.kv{h}", family="attention_qk"), ["QB", "KVCACHE"], ["SC"])
        sc_d = V(g, "SC", 1, m=nq, stride=P, n_sel=DYN["POS1"])
        b.add(Rec("SU", "VOP", sut=sut(m1=I.M1_AIMM, imm1=scale, red=I.RED_MAX), desc=dict(
            A=sc_d, R=V(g, "MAX", 1, m=nq, stride=1)), tag="softmax.max", family="softmax"), ["SC"], ["MAX"])
        b.add(Rec("SU", "VOP", sut=sut(m1=I.M1_AIMM, imm1=scale, ad=I.AD_NEGB, sfu=I.SFU_EXP, red=I.RED_SUM,
                                       dst=I.DST_VM), desc=dict(
            A=sc_d, B=V(g, "MAX", 1, m=nq, stride=1, ibcast=1), O=V(g, "E", 1, m=nq, stride=P,
                                                                                  n_sel=DYN["POS1"]),
            R=V(g, "Z", 1, m=nq, stride=1)), tag="softmax.exp_sum", family="softmax"), ["SC", "MAX"], ["E", "Z"])
        e_d = V(g, "E", 1, m=nq, stride=P, n_sel=DYN["POS1"])
        b.add(Rec("SU", "VOP", sut=sut(rnd=1, dst=I.DST_VM), desc=dict(A=e_d, O=e_d),
                  tag="softmax.bf16_p", family="softmax"), ["E"], ["E"])
        for h in range(nk):
            b.add(Rec("ATT", "PV", param=lanes | ((HD // 64 - 1) << 4), desc=dict(
                A=V(g, "E", 1, m=lanes, stride=P, off=h * lanes * P, n_sel=DYN["POS1"]),
                B=MDesc(space="HBM", fmt="FP8E4M3", base=KVB + (h * 2 + 1) * g.kv_plane, n=1, m=1, stride=HD,
                        lstride=g.kv_layer, n_sel=DYN["POS1"]),
                O=V(g, "PV", HD, m=lanes, stride=HD, off=h * lanes * HD)),
                tag=f"attention_pv.kv{h}", family="attention_pv"), ["E", "KVCACHE"], ["PV"])
        b.add(Rec("SU", "VOP", sut=sut(m1=I.M1_DIVB, dst=I.DST_VM), desc=dict(
            A=V(g, "PV", HD, m=nq, stride=HD), B=V(g, "Z", HD, m=nq, stride=1, ibcast=1),
            O=V(g, "ATTN", HD, m=nq, stride=HD)), tag="pv_normalize", family="pv_normalize"), ["PV", "Z"], ["ATTN"])
        b.add(Rec("SM", "MATVEC", param=3, desc=dict(
            A=V(g, "ATTN", nq * HD), B=W("o", "INT8", nq * HD, H, nq * HD), O=V(g, "OPART", H)),
            tag="o", family="o"), ["ATTN"], ["OPART"])
        b.add(Rec("COLL", "ALL_REDUCE_SUM", desc=dict(A=V(g, "OPART", H), O=V(g, "OSUM", H)),
                  tag="all_reduce_o", family="all_reduce_o"), ["OPART"], ["OSUM"])
        b.add(Rec("DMA", "LOAD", desc=dict(A=W("o_s", "BF16", H, 1, 0), O=V(g, "SCL", H)),
                  tag="row_scale_o.load", family="row_scale_o"), [], ["SCL"])
        b.add(Rec("SU", "VOP", sut=sut(m1=I.M1_AB, ad=I.AD_C, dst=I.DST_VM), desc=dict(
            A=V(g, "OSUM", H), B=V(g, "SCL", H), C=V(g, "X", H), O=V(g, "X", H)),
            tag="row_scale_o+residual", family="row_scale_o"), ["OSUM", "SCL", "X"], ["X"])
        # -- FFN block ------------------------------------------------------------------------------------
        b.add(Rec("FUSED", "ROW_NORM", param=H // 128, imm_a=eps, desc=dict(
            A=V(g, "X", H), B=W("ln2", "BF16", H, 1, 0), O=MDesc(space="VM", fmt="BF16", base=g.vm["H"], n=H)),
            tag="prenorm.ffn", family="prenorm"), ["X"], ["H"])
        b.add(Rec("SM", "MATVEC", param=3, desc=dict(
            A=V(g, "H", H), B=W("gu", "INT8", H, 2 * g.ff, H), O=V(g, "GURAW", 2 * g.ff)),
            tag="gu", family="gu"), ["H"], ["GURAW"])
        b.add(Rec("DMA", "LOAD", desc=dict(A=W("gu_s", "BF16", 2 * g.ff, 1, 0), O=V(g, "SCL", 2 * g.ff)),
                  tag="row_scale_gu.load", family="row_scale_gu"), [], ["SCL"])
        b.add(Rec("SU", "VOP", sut=sut(m1=I.M1_AB, dst=I.DST_VM), desc=dict(
            A=V(g, "GURAW", 2 * g.ff), B=V(g, "SCL", 2 * g.ff), O=V(g, "GU", 2 * g.ff)),
            tag="row_scale_gu", family="row_scale_gu"), ["GURAW", "SCL"], ["GU"])
        b.add(Rec("SFU", "GLU", imm_a=FLT_MAX, desc=dict(A=V(g, "GU", g.ff), B=V(g, "GU", g.ff, off=g.ff),
                                                         C=V(g, "ONE", g.ff, ibcast=1),
                                                         O=V(g, "ACT", g.ff, fmt="BF16")),
                  tag="swiglu", family="swiglu"), ["GU", "ONE"], ["ACT"])
        b.add(Rec("SM", "MATVEC", param=3, desc=dict(
            A=V(g, "ACT", g.ff), B=W("down", "INT8", g.ff, H, g.ff), O=V(g, "DPART", H)),
            tag="down", family="down"), ["ACT"], ["DPART"])
        b.add(Rec("COLL", "ALL_REDUCE_SUM", desc=dict(A=V(g, "DPART", H), O=V(g, "DSUM", H)),
                  tag="all_reduce_down", family="all_reduce_down"), ["DPART"], ["DSUM"])
        b.add(Rec("DMA", "LOAD", desc=dict(A=W("down_s", "BF16", H, 1, 0), O=V(g, "SCL", H)),
                  tag="row_scale_down.load", family="row_scale_down"), [], ["SCL"])
        b.add(Rec("SU", "VOP", sut=sut(m1=I.M1_AB, ad=I.AD_C, dst=I.DST_VM), desc=dict(
            A=V(g, "DSUM", H), B=V(g, "SCL", H), C=V(g, "X", H), O=V(g, "X", H)),
            tag="row_scale_down+residual", family="row_scale_down"), ["DSUM", "SCL", "X"], ["X"])
        if n_layers > 1:
            b.add(Rec("CTL", "ENDLOOP", tag="layers"), [], [])
    if "head" in parts:
        hr = g.hrows
        HB = g.hbm["HEAD"]
        b.add(Rec("FUSED", "ROW_NORM", param=H // 128, imm_a=eps, desc=dict(
            A=V(g, "X", H), B=MDesc(space="HBM", fmt="BF16", base=T + g.tables["norm"], n=H),
            O=MDesc(space="VM", fmt="BF16", base=g.vm["H"], n=H)), tag="prenorm.final", family="prenorm"),
            ["X"], ["H"])
        # the logits never touch VM (hgi-adapters 10:5x: a VM-read argmax costs ~38k cycles): head matvec ->
        # STREAM 0 (SM -> SU lanes) -> row scale on the SU -> STREAM 1 (SU -> argmax) -> ARGMAX.LOCAL; the FIFOs'
        # credits order the three records (no wait bits between them)
        S0 = MDesc(space="STREAM", fmt="FP32", base=0, n=hr)
        S1 = MDesc(space="STREAM", fmt="FP32", base=1, n=hr)
        b.add(Rec("DMA", "LOAD", desc=dict(A=MDesc(space="HBM", fmt="BF16", base=HB + al(hr * H), n=hr),
                                           O=V(g, "LSCL", hr)), tag="head_scale.load", family="head_scale"),
              [], ["LSCL"])
        b.add(Rec("SM", "MATVEC", param=3, desc=dict(
            A=V(g, "H", H), B=MDesc(space="HBM", fmt="INT8", base=HB, n=H, m=hr, stride=H), O=S0),
            tag="head", family="head"), ["H"], [])
        b.add(Rec("SU", "VOP", sut=sut(m1=I.M1_AB, dst=I.DST_VM), desc=dict(
            A=S0, B=V(g, "LSCL", hr), O=S1), tag="head_scale", family="head_scale"), ["LSCL"], [])
        b.add(Rec("ARGMAX", "LOCAL", imm_a=hr, desc=dict(A=S1, O=V(g, "AMX", 2))),
              [], ["AMX"]).family = "argmax_local"
        b.add(Rec("COLL", "ARGMAX_MERGE", desc=dict(A=V(g, "AMX", 2), O=MDesc(space="VM", fmt="U32",
                                                                              base=g.vm["TOK"], n=1)),
                  tag="argmax_merge", family="argmax_merge"), ["AMX"], ["TOK"])
    b.add(Rec("CTL", "END", desc=dict(A=MDesc(space="VM", fmt="U32", base=g.vm["TOK"], n=1)), tag="end",
              family="end"), ["TOK"], [])
    for r in b.recs:
        if r.unit == "ARGMAX":
            r.tag = r.tag or "argmax_local"
    return assign_waits(b.recs)
