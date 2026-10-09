#!/usr/bin/env python3
"""Gated DeltaNet (Qwen3-Next / Qwen3.5-3.8 linear-attention layers) on the r25 die, in SOFTWARE on existing engines
(owner decision 2026-10-09): golden, HGI-1 lowering at TP4, bit-exact simulator run, rate.

ONE DECODE STEP of the token mixer (transformers Qwen3NextGatedDeltaNet with cache: causal_conv1d_update +
torch_recurrent_gated_delta_rule + Qwen3NextRMSNormGated + out_proj), per die d of TP4 (4 of the 16 key heads,
8 of the 32 value heads, their conv channels; out_proj K-split over the value heads + owner-tree all-reduce):

  h        = bf16(RMSNorm(x))                                         FUSED.ROW_NORM          (prenorm)
  qkvz, ba = W_qkvz h, W_ba h  (the die's 4 key-head groups)          SM.MATVEC fmt 0/3
  conv     X4[c] = [ring c (3 older inputs) | new]; y = silu(csum4(w[c] * X4[c]))   DMA.LOAD ring, SU copy, SU
           reduction (n = 4 taps), SU silu; DMA.STORE ring <- X4[:, 1:4]
  l2norm   q = (q * rsqrt(csum(q*q) + 1e-6)) * 128^-0.5;  k likewise unscaled        SU (red_sq, rsqrt, mul)
  gates    beta = sigmoid(b);  g = (-exp(A_log)) * softplus(a + dt_bias);  alpha = exp(g)
           softplus = max(x, 0) + log1p(exp(-|x|)) (the golden's series log1p, as the DS SFU's SPSQRT computes it)
           as an exact 17-record SU template (no softplus SFU code exists)
  delta rule, per value head h (key head h // 2), state ST[j][i] = S[i][j] (FP32, HBM, 64 KiB a head):
           ST = alpha * ST;  kv[j] = csum_i(ST[j,i] * k[i]);  delta = (v - kv) * beta;
           ST[j,i] = ST[j,i] + k[i] * delta[j];  o[j] = csum_i(ST[j,i] * q[i])          SU (8 records a step)
           DMA.LOAD / DMA.STORE of the 8 heads' state (512 KiB a die a layer)
  gated norm  o = RMSNorm_128(o) * w;  o = o * silu(z)                FUSED.ROW_NORM seg 128 + SU (silu * c)
  out      partial = W_out[:, die's 1,024 value columns] bf16(o); x = x + pairwise(partials)   SM, COLL, SU

Why SU and not ATT for S.k / S.q: the state is FP32 and the attention tiles' p.v reads FP8 / BF16 rows (an FP32
row operand would need a new tile datapath): interface gap GDN-1.  The arithmetic library order (csum8) is the
golden's; transformers' reference is matched numerically (max abs / rel error reported), as qwen_r25 is to HF.

    python3 -m hgi_sim.gdn --out REC.json            (synthetic weights at Qwen3-Next-80B dims; seconds-minutes)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import hbm_generic_iface as HGI  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402

from hgi_sim import lib as A  # noqa: E402
from hgi_sim import timing as T  # noqa: E402
from hgi_sim.machine import UNITS, Die, Fault, Hbm, Machine  # noqa: E402
from hgi_sim.qwen_compiler import Builder, assign_waits, sut  # noqa: E402
from hgi_sim.records import ISTRIDE_BCAST, MDesc, Rec, decode_program, encode_program  # noqa: E402

F = np.float32
TP = 4
CFG = dict(hidden=2048, nk=16, nv=32, dk=128, dv=128, conv=4, eps=1e-6)        # Qwen3-Next-80B-A3B


def bf(x):
    return A.to_bf16(np.asarray(x, dtype=F))


def make_weights(c, seed=0):
    rng = np.random.default_rng(seed)
    H, nk, nv, dk, dv = c["hidden"], c["nk"], c["nv"], c["dk"], c["dv"]
    grp = 2 * dk + 2 * dv * nv // nk
    conv_dim = 2 * nk * dk + nv * dv
    return dict(
        ln=bf(rng.uniform(0.5, 1.5, H)), Wqkvz=bf(rng.standard_normal((nk * grp, H)) * 0.02),
        Wba=bf(rng.standard_normal((nk * 2 * (nv // nk), H)) * 0.05),
        conv_w=bf(rng.standard_normal((conv_dim, c["conv"])) * 0.3),
        A_log=bf(np.log(rng.uniform(1, 16, nv))), dt_bias=bf(rng.uniform(0.5, 1.5, nv)),
        norm_w=bf(rng.uniform(0.5, 1.5, dv)), Wout=bf(rng.standard_normal((H, nv * dv)) * 0.02))


def make_state(c, seed=1):
    rng = np.random.default_rng(seed)
    conv_dim = 2 * c["nk"] * c["dk"] + c["nv"] * c["dv"]
    return dict(S=(rng.standard_normal((c["nv"], c["dk"], c["dv"])) * 0.05).astype(F),
                ring=(rng.standard_normal((conv_dim, c["conv"] - 1)) * 0.5).astype(F))


class Geo:
    def __init__(self, c):
        self.c = c
        self.H, self.nk, self.nv, self.dk, self.dv = c["hidden"], c["nk"], c["nv"], c["dk"], c["dv"]
        self.r = self.nv // self.nk                          # value heads per key head
        self.kd, self.vd = self.nk // TP, self.nv // TP       # key / value heads a die
        self.grp = 2 * self.dk + 2 * self.dv * self.r
        self.rows_qkvz = self.kd * self.grp
        self.rows_ba = self.kd * 2 * self.r
        self.cq, self.cv = self.kd * self.dk, self.vd * self.dv
        self.C = 2 * self.cq + self.cv                       # conv channels a die
        self.conv_dim = 2 * self.nk * self.dk + self.nv * self.dv

    def die_channels(self, d):
        """global conv channel ids of die d, in its local order [q | k | v]."""
        q = d * self.cq + np.arange(self.cq)
        k = self.nk * self.dk + d * self.cq + np.arange(self.cq)
        v = 2 * self.nk * self.dk + d * self.cv + np.arange(self.cv)
        return np.concatenate([q, k, v])


# ----------------------------------------------------------------------------------------------------------------
# golden (die-decomposed; the arithmetic library)
# ----------------------------------------------------------------------------------------------------------------
def golden(c, w, st, x):
    g = Geo(c)
    eps = F(c["eps"])
    h = bf(A.row_norm(x, w["ln"], eps))
    tr = dict(h=h, parts=[], S_new=np.empty_like(st["S"]), ring_new=np.empty_like(st["ring"]), die={})
    scale = F(1.0 / np.sqrt(g.dk))
    for d in range(TP):
        t = {}
        rq = np.arange(d * g.rows_qkvz, (d + 1) * g.rows_qkvz)
        rb = np.arange(d * g.rows_ba, (d + 1) * g.rows_ba)
        qkvz = A.sm_bf16(w["Wqkvz"][rq], h)
        ba = A.sm_bf16(w["Wba"][rb], h)
        G4 = qkvz.reshape(g.kd, g.grp)
        q = G4[:, :g.dk].reshape(-1)
        k = G4[:, g.dk:2 * g.dk].reshape(-1)
        v = G4[:, 2 * g.dk:2 * g.dk + g.r * g.dv].reshape(-1)
        zz = G4[:, 2 * g.dk + g.r * g.dv:].reshape(g.vd, g.dv)
        B4 = ba.reshape(g.kd, 2 * g.r)
        b = B4[:, :g.r].reshape(-1)
        a = B4[:, g.r:].reshape(-1)
        ch = g.die_channels(d)
        X4 = np.concatenate([st["ring"][ch], np.concatenate([q, k, v])[:, None]], axis=1).astype(F)
        y = A.silu(A.csum(A.mul(X4, w["conv_w"][ch])))
        tr["ring_new"][ch] = X4[:, 1:]
        qc, kc, vc = y[:g.cq].reshape(g.kd, g.dk), y[g.cq:2 * g.cq].reshape(g.kd, g.dk), y[2 * g.cq:].reshape(g.vd, g.dv)
        qn = A.mul(A.mul(qc, A.rsqrt(A.add(A.csum(A.mul(qc, qc)), eps_l2()))[:, None]), scale)
        kn = A.mul(kc, A.rsqrt(A.add(A.csum(A.mul(kc, kc)), eps_l2()))[:, None])
        hv = np.arange(d * g.vd, (d + 1) * g.vd)
        beta = A.sigmoid(b)
        sp = A.softplus(A.add(a, w["dt_bias"][hv]))
        alpha = A.exp(A.mul(A.neg(A.exp(w["A_log"][hv])), sp))
        o = np.empty((g.vd, g.dv), dtype=F)
        for j in range(g.vd):
            kk, qq = kn[j // g.r], qn[j // g.r]
            ST = np.ascontiguousarray(st["S"][hv[j]].T)          # [dv][dk]
            ST = A.mul(ST, alpha[j])
            kv = A.csum(A.mul(ST, kk[None, :]))
            delta = A.mul(A.add(vc[j], A.neg(kv)), beta[j])
            ST = A.add(ST, A.mul(kk[None, :], delta[:, None]))
            o[j] = A.csum(A.mul(ST, qq[None, :]))
            tr["S_new"][hv[j]] = ST.T
        n = A.row_norm(o.reshape(-1), w["norm_w"], eps, seg=g.dv).reshape(g.vd, g.dv)
        og = A.mul(A.silu(zz), n)
        part = A.sm_bf16(w["Wout"][:, hv[0] * g.dv:(hv[-1] + 1) * g.dv], og.reshape(-1))
        tr["parts"].append(part)
        t.update(qkvz=qkvz, ba=ba, conv=y, q=qn, k=kn, beta=beta, alpha=alpha, sp=sp, o=o, og=og, part=part)
        tr["die"][d] = t
    tr["x_out"] = A.add(A.pairwise(tr["parts"]), x)
    return tr


def eps_l2():
    return F(1e-6)


# ----------------------------------------------------------------------------------------------------------------
# transformers reference (numerical agreement)
# ----------------------------------------------------------------------------------------------------------------
def hf_reference(c, w, st, x, tr):
    import types
    import torch
    from transformers.models.qwen3_next import modeling_qwen3_next as MQ
    from transformers.models.qwen3_next.configuration_qwen3_next import Qwen3NextConfig
    MQ.FusedRMSNormGated = None
    MQ.is_fast_path_available = False
    cfg = Qwen3NextConfig(hidden_size=c["hidden"], linear_num_key_heads=c["nk"], linear_num_value_heads=c["nv"],
                          linear_key_head_dim=c["dk"], linear_value_head_dim=c["dv"], linear_conv_kernel_dim=c["conv"],
                          rms_norm_eps=c["eps"], num_hidden_layers=4)
    mod = MQ.Qwen3NextGatedDeltaNet(cfg, 0).float()
    mod.causal_conv1d_update = MQ.torch_causal_conv1d_update
    mod.recurrent_gated_delta_rule = MQ.torch_recurrent_gated_delta_rule
    t = lambda a: torch.from_numpy(np.ascontiguousarray(a, dtype=np.float32))  # noqa: E731
    with torch.no_grad():
        mod.in_proj_qkvz.weight.copy_(t(w["Wqkvz"]))
        mod.in_proj_ba.weight.copy_(t(w["Wba"]))
        mod.conv1d.weight.copy_(t(w["conv_w"])[:, None, :])
        mod.A_log.copy_(t(w["A_log"]))
        mod.dt_bias.copy_(t(w["dt_bias"]))
        mod.norm.weight.copy_(t(w["norm_w"]))
        mod.out_proj.weight.copy_(t(w["Wout"]))
    conv_state = torch.zeros(1, Geo(c).conv_dim, c["conv"])
    conv_state[0, :, 1:] = t(st["ring"])
    cache = types.SimpleNamespace(conv_states=[conv_state], recurrent_states=[t(st["S"])[None]],
                                  has_previous_state=True)
    with torch.no_grad():
        out = mod(t(tr["h"])[None, None], cache_params=cache, cache_position=torch.tensor([5]))
    ref = out[0, 0].numpy()
    got = A.pairwise(tr["parts"])
    S_ref = cache.recurrent_states[0][0].numpy()
    err = lambda a, b: dict(max_abs=float(np.max(np.abs(a - b))),                       # noqa: E731
                            max_rel=float(np.max(np.abs(a - b) / (np.abs(b) + 1e-6))),
                            rms_rel=float(np.sqrt(np.mean((a - b) ** 2)) / (np.sqrt(np.mean(b ** 2)) + 1e-30)))
    g = Geo(c)
    exact_in = sum(w["Wout"][:, d * g.vd * g.dv:(d + 1) * g.vd * g.dv].astype(np.float64)
                   @ tr["die"][d]["og"].reshape(-1).astype(np.float64) for d in range(TP))
    return dict(mixer_out=err(got, ref), mixer_out_before_bf16_rounding=err(exact_in.astype(F), ref),
                o_gated_vs_core=None, state=err(tr["S_new"], S_ref),
                conv_ring=err(tr["ring_new"], cache.conv_states[0][0, :, 1:].numpy()),
                note="transformers 4.57 torch_causal_conv1d_update + torch_recurrent_gated_delta_rule + "
                     "Qwen3NextRMSNormGated (FP32 module, same BF16-valued weights); reductions in torch order")


# ----------------------------------------------------------------------------------------------------------------
# HGI-1 lowering
# ----------------------------------------------------------------------------------------------------------------
def layout(g):
    vm, cur = {}, [0]

    def put(name, n, al=128):
        cur[0] = -(-cur[0] // al) * al
        vm[name] = cur[0]
        cur[0] += n
    put("X", g.H); put("H", g.H); put("QKVZ", g.rows_qkvz); put("BA", g.rows_ba)          # noqa: E702
    put("X4", g.C * 4); put("CPRE", g.C); put("CONV", g.C)                                  # noqa: E702
    put("SSQ", 2 * g.kd); put("INV", 2 * g.kd); put("QN", g.kd * g.dk); put("KN", g.kd * g.dk)  # noqa: E702
    for nm in ("SA", "NSA", "AX", "T", "TP2", "U", "U2", "P", "R", "SP", "ALPHA", "BETA", "NEGA", "DT"):
        put(nm, g.vd, 8)
    put("ST", g.vd * g.dv * g.dk); put("KV", g.vd * g.dv); put("DELTA", g.vd * g.dv)       # noqa: E702
    put("O", g.vd * g.dv); put("ON", g.vd * g.dv); put("OG", g.vd * g.dv); put("PART", g.H); put("SUM", g.H)  # noqa
    put("TOK", 1)
    assert cur[0] <= 1 << 18, cur[0]
    hb = dict(W=1 << 32, CONVW=2 << 32, TAB=3 << 32, STATE=4 << 32, RING=5 << 32)
    return vm, cur[0], hb


def build_images(g, w, st):
    dies = []
    for d in range(TP):
        hb = Hbm()
        _, _, B = layout(g)
        rq = np.arange(d * g.rows_qkvz, (d + 1) * g.rows_qkvz)
        rb = np.arange(d * g.rows_ba, (d + 1) * g.rows_ba)
        hv = np.arange(d * g.vd, (d + 1) * g.vd)

        def b16(a):
            return (np.asarray(a, dtype=F).view(np.uint32) >> 16).astype(np.uint16)
        wq, wb = b16(w["Wqkvz"][rq]).reshape(-1), b16(w["Wba"][rb]).reshape(-1)
        wo = b16(w["Wout"][:, hv[0] * g.dv:(hv[-1] + 1) * g.dv]).reshape(-1)
        ln = b16(w["ln"])
        blob = np.concatenate([wq, wb, wo, ln]).view(np.uint8)
        hb.add(B["W"], blob, "W")
        ch = g.die_channels(d)
        hb.add(B["CONVW"], w["conv_w"][ch].astype(F).reshape(-1).copy(), "CONVW")
        tab = np.concatenate([A.neg(A.exp(w["A_log"][hv])), w["dt_bias"][hv], w["norm_w"]]).astype(F)
        hb.add(B["TAB"], tab, "TAB")
        STd = np.ascontiguousarray(np.transpose(st["S"][hv], (0, 2, 1))).astype(F)      # [head][j][i]
        hb.add(B["STATE"], STd.reshape(-1).copy(), "STATE")
        hb.add(B["RING"], st["ring"][ch].astype(F).reshape(-1).copy(), "RING")
        dies.append(hb)
    return dies


def program(g, eps):
    vm, _, B = layout(g)
    b = Builder(None)
    ep = int(np.asarray(F(eps)).view(np.uint32))

    def V(name, n, m=1, stride=0, istride=0, off=0):
        return MDesc(space="VM", fmt="FP32", base=vm[name] + off, n=n, m=m, stride=stride, istride=istride)

    def HB(region, off, fmt, n, m=1, stride=0, istride=0):
        return MDesc(space="HBM", fmt=fmt, base=B[region] + off, n=n, m=m, stride=stride, istride=istride)

    def su(tag, fam, desc, rd, wr, **t):
        b.add(Rec("SU", "VOP", sut=sut(**t), desc=desc, tag=tag, family=fam), rd, wr)
    woff_b = g.rows_qkvz * g.H * 2
    woff_o = woff_b + g.rows_ba * g.H * 2
    woff_ln = woff_o + g.H * g.vd * g.dv * 2
    C, kd, vd, dk, dv, r = g.C, g.kd, g.vd, g.dk, g.dv, g.r
    b.add(Rec("FUSED", "ROW_NORM", param=0, imm_a=ep, desc=dict(A=V("X", g.H), B=HB("W", woff_ln, "BF16", g.H),
          O=MDesc(space="VM", fmt="BF16", base=vm["H"], n=g.H)), tag="prenorm", family="prenorm"), ["X"], ["H"])
    b.add(Rec("SM", "MATVEC", param=0, desc=dict(A=V("H", g.H), B=HB("W", 0, "BF16", g.H, g.rows_qkvz, g.H * 2),
          O=V("QKVZ", g.rows_qkvz)), tag="in_proj_qkvz", family="in_proj"), ["H"], ["QKVZ"])
    b.add(Rec("SM", "MATVEC", param=0, desc=dict(A=V("H", g.H), B=HB("W", woff_b, "BF16", g.H, g.rows_ba, g.H * 2),
          O=V("BA", g.rows_ba)), tag="in_proj_ba", family="in_proj"), ["H"], ["BA"])
    # conv: ring -> X4[:, 0:3]; new inputs -> X4[:, 3]; taps reduction; silu; ring <- X4[:, 1:4]
    b.add(Rec("DMA", "LOAD", desc=dict(A=HB("RING", 0, "FP32", 3 * C), O=V("X4", 3, m=C, stride=4)),
              tag="conv.ring_load", family="conv"), [], ["X4"])
    for part, (src_off, n, dst_ch) in dict(q=(0, dk, 0), k=(dk, dk, kd * dk), v=(2 * dk, r * dv, 2 * kd * dk)).items():
        su(f"conv.new_{part}", "conv", dict(A=V("QKVZ", n, m=kd, stride=g.grp, off=src_off),
                                            O=V("X4", n, m=kd, stride=n * 4, istride=4, off=dst_ch * 4 + 3)),
           ["QKVZ"], ["X4"], dst=I.DST_VM)
    su("conv.taps", "conv", dict(A=V("X4", 4, m=C, stride=4), B=MDesc(space="HBM", fmt="FP32", base=B["CONVW"], n=4,
                                                                       m=C, stride=16),
                                 R=V("CPRE", 1, m=C, stride=1)), ["X4"], ["CPRE"], m1=I.M1_AB, red=I.RED_SUM)
    su("conv.silu", "conv", dict(A=V("CPRE", C), O=V("CONV", C)), ["CPRE"], ["CONV"], sfu=I.SFU_SILU, dst=I.DST_VM)
    b.add(Rec("DMA", "STORE", desc=dict(A=V("X4", 3, m=C, stride=4, off=1), O=HB("RING", 0, "FP32", 3, m=C, stride=12)),
              tag="conv.ring_store", family="conv"), ["X4"], ["RINGS"])
    # l2norm (q scaled by dk^-0.5), k
    su("l2norm.ss", "l2norm", dict(A=V("CONV", dk, m=2 * kd, stride=dk), R=V("SSQ", 1, m=2 * kd, stride=1)),
       ["CONV"], ["SSQ"], red=I.RED_SUM, red_sq=1)
    su("l2norm.rsqrt", "l2norm", dict(A=V("SSQ", 2 * kd), O=V("INV", 2 * kd)), ["SSQ"], ["INV"], ad=I.AD_IMM,
       imm2=int(np.asarray(eps_l2()).view(np.uint32)), sfu=I.SFU_RSQRT, dst=I.DST_VM)
    sc = int(np.asarray(F(1.0 / np.sqrt(dk))).view(np.uint32))
    su("l2norm.q", "l2norm", dict(A=V("CONV", dk, m=kd, stride=dk), B=V("INV", dk, m=kd, stride=1,
                                                                       istride=ISTRIDE_BCAST),
                                  O=V("QN", dk, m=kd, stride=dk)), ["CONV", "INV"], ["QN"],
       m1=I.M1_AB, m2=I.M2_IMM, imm1=sc, dst=I.DST_VM)
    su("l2norm.k", "l2norm", dict(A=V("CONV", dk, m=kd, stride=dk, off=kd * dk),
                                  B=V("INV", dk, m=kd, stride=1, istride=ISTRIDE_BCAST, off=kd),
                                  O=V("KN", dk, m=kd, stride=dk)), ["CONV", "INV"], ["KN"], m1=I.M1_AB, dst=I.DST_VM)
    # gates: b, a are [kd][r] in BA; beta = sigmoid(b); alpha = exp(-exp(A_log) * softplus(a + dt_bias))
    b.add(Rec("DMA", "LOAD", desc=dict(A=HB("TAB", 0, "FP32", 2 * vd), O=V("NEGA", 2 * vd)),
              tag="gates.table", family="gates"), [], ["NEGA", "DT"])
    bv = V("BA", r, m=kd, stride=2 * r)
    av = V("BA", r, m=kd, stride=2 * r, off=r)

    def g8(name):
        return V(name, r, m=kd, stride=r)
    su("gates.beta", "gates", dict(A=bv, O=g8("BETA")), ["BA"], ["BETA"], sfu=I.SFU_SIGM, dst=I.DST_VM)
    su("softplus.x", "softplus", dict(A=av, C=g8("DT"), O=g8("SA")), ["BA", "DT"], ["SA"], ad=I.AD_C, dst=I.DST_VM)
    m1 = int(np.asarray(F(-1.0)).view(np.uint32))
    su("softplus.neg", "softplus", dict(A=g8("SA"), O=g8("NSA")), ["SA"], ["NSA"], m1=I.M1_AIMM, imm1=m1, dst=I.DST_VM)
    su("softplus.abs", "softplus", dict(A=g8("SA"), B=g8("NSA"), O=g8("AX")), ["SA", "NSA"], ["AX"], m1=I.M1_MAXB,
       dst=I.DST_VM)
    su("softplus.exp", "softplus", dict(A=g8("AX"), O=g8("T")), ["AX"], ["T"], m1=I.M1_AIMM, imm1=m1, sfu=I.SFU_EXP,
       dst=I.DST_VM)
    two = int(np.asarray(F(2.0)).view(np.uint32))
    su("softplus.tp2", "softplus", dict(A=g8("T"), O=g8("TP2")), ["T"], ["TP2"], ad=I.AD_IMM, imm2=two, dst=I.DST_VM)
    su("softplus.u", "softplus", dict(A=g8("T"), B=g8("TP2"), O=g8("U")), ["T", "TP2"], ["U"], m1=I.M1_DIVB,
       dst=I.DST_VM)
    su("softplus.u2", "softplus", dict(A=g8("U"), O=g8("U2")), ["U"], ["U2"], m1=I.M1_AA, dst=I.DST_VM)
    co = [int(np.asarray(c).view(np.uint32)) for c in A.LOG1P_ODD]
    su("softplus.h1", "softplus", dict(A=g8("U2"), O=g8("P")), ["U2"], ["P"], m1=I.M1_AIMM, imm1=co[0], ad=I.AD_IMM,
       imm2=co[1], dst=I.DST_VM)
    for k in range(2, len(co)):
        su(f"softplus.h{k}", "softplus", dict(A=g8("P"), B=g8("U2"), O=g8("P")), ["P", "U2"], ["P"], m1=I.M1_AB,
           ad=I.AD_IMM, imm2=co[k], dst=I.DST_VM)
    su("softplus.r", "softplus", dict(A=g8("U"), B=g8("P"), O=g8("R")), ["U", "P"], ["R"], m1=I.M1_AB, m2=I.M2_IMM,
       imm1=two, dst=I.DST_VM)
    su("softplus.out", "softplus", dict(A=g8("SA"), C=g8("R"), O=g8("SP")), ["SA", "R"], ["SP"], a_relu=1,
       ad=I.AD_C, dst=I.DST_VM)
    su("gates.alpha", "gates", dict(A=g8("SP"), B=g8("NEGA"), O=g8("ALPHA")), ["SP", "NEGA"], ["ALPHA"],
       m1=I.M1_AB, sfu=I.SFU_EXP, dst=I.DST_VM)
    # delta rule
    nS = dv * dk
    b.add(Rec("DMA", "LOAD", desc=dict(A=HB("STATE", 0, "FP32", vd * nS), O=V("ST", vd * nS)),
              tag="state.load", family="state_io"), [], ["ST"])
    for j in range(vd):
        STj = V("ST", dk, m=dv, stride=dk, off=j * nS)
        kj = V("KN", dk, m=dv, stride=0, off=(j // r) * dk)
        su(f"delta.decay{j}", "delta_rule", dict(A=STj, B=V("ALPHA", dk, m=dv, stride=0, istride=ISTRIDE_BCAST, off=j),
                                                  O=STj), ["ST", "ALPHA"], ["ST"], m1=I.M1_AB, dst=I.DST_VM)
        su(f"delta.kv{j}", "delta_rule", dict(A=STj, B=kj, R=V("KV", 1, m=dv, stride=1, off=j * dv)), ["ST", "KN"],
           ["KV"], m1=I.M1_AB, red=I.RED_SUM)
    su("delta.delta", "delta_rule", dict(A=V("CONV", dv, m=vd, stride=dv, off=2 * kd * dk), B=V("KV", dv, m=vd, stride=dv),
                                         C=V("BETA", dv, m=vd, stride=1, istride=ISTRIDE_BCAST),
                                         O=V("DELTA", dv, m=vd, stride=dv)), ["CONV", "KV", "BETA"], ["DELTA"],
       ad=I.AD_NEGB, e1=I.E1_MULC, dst=I.DST_VM)
    for j in range(vd):
        STj = V("ST", dk, m=dv, stride=dk, off=j * nS)
        su(f"delta.update{j}", "delta_rule", dict(A=V("KN", dk, m=dv, stride=0, off=(j // r) * dk),
                                                   B=V("DELTA", dk, m=dv, stride=1, istride=ISTRIDE_BCAST, off=j * dv),
                                                   C=STj, O=STj), ["KN", "DELTA", "ST"], ["ST"], m1=I.M1_AB, ad=I.AD_C,
           dst=I.DST_VM)
        su(f"delta.out{j}", "delta_rule", dict(A=STj, B=V("QN", dk, m=dv, stride=0, off=(j // r) * dk),
                                                R=V("O", 1, m=dv, stride=1, off=j * dv)), ["ST", "QN"], ["O"],
           m1=I.M1_AB, red=I.RED_SUM)
    b.add(Rec("DMA", "STORE", desc=dict(A=V("ST", vd * nS), O=HB("STATE", 0, "FP32", vd * nS)),
              tag="state.store", family="state_io"), ["ST"], ["STATES"])
    # gated RMSNorm, out_proj, all-reduce, residual
    b.add(Rec("FUSED", "ROW_NORM", param=dv, imm_a=ep, desc=dict(A=V("O", vd * dv), B=HB("TAB", 8 * vd, "FP32", dv),
          O=V("ON", vd * dv)), tag="gated_norm.norm", family="gated_norm"), ["O"], ["ON"])
    su("gated_norm.gate", "gated_norm", dict(A=V("QKVZ", r * dv, m=kd, stride=g.grp, off=2 * dk + r * dv),
                                             C=V("ON", r * dv, m=kd, stride=r * dv), O=V("OG", r * dv, m=kd,
                                                                                          stride=r * dv)),
       ["QKVZ", "ON"], ["OG"], sfu=I.SFU_SILU, e1=I.E1_MULC, dst=I.DST_VM)
    b.add(Rec("SM", "MATVEC", param=0, desc=dict(A=V("OG", vd * dv), B=HB("W", woff_o, "BF16", vd * dv, g.H,
                                                                          vd * dv * 2), O=V("PART", g.H)),
              tag="out_proj", family="out_proj"), ["OG"], ["PART"])
    b.add(Rec("COLL", "ALL_REDUCE_SUM", desc=dict(A=V("PART", g.H), O=V("SUM", g.H)), tag="all_reduce_out",
              family="all_reduce_out"), ["PART"], ["SUM"])
    su("residual", "residual", dict(A=V("SUM", g.H), C=V("X", g.H), O=V("X", g.H)), ["SUM", "X"], ["X"], ad=I.AD_C,
       dst=I.DST_VM)
    b.add(Rec("CTL", "END", desc=dict(A=MDesc(space="VM", fmt="U32", base=vm["TOK"], n=1)), tag="end", family="end"),
          ["TOK"], [])
    return assign_waits(b.recs)


def run_sim(c, w, st, x, mutant=None):
    g = Geo(c)
    vm, _, _ = layout(g)
    recs = program(g, c["eps"])
    if mutant == "gqa_map":
        for r in recs:
            if r.tag.startswith("delta.kv") or r.tag.startswith("delta.update"):
                j = int(r.tag[len(r.tag.rstrip("0123456789")):])
                key = "A" if r.tag.startswith("delta.update") else "B"
                r.desc[key].base = vm["KN"] + (j % g.kd) * g.dk           # wrong key head for value head j
    image = encode_program(recs)
    assert encode_program(decode_program(image)) == image
    dies = [Die(d, hb) for d, hb in enumerate(build_images(g, w, st))]
    M = Machine(dies, UNITS)
    words = HGI.pack(HGI.from_config("qwen3_8b")[0])
    assert M.cfg_commit(words) == 0
    for d in dies:
        d.vm[vm["X"]:vm["X"] + g.H] = np.asarray(x, dtype=F).view(np.uint32)
    tok, trace = M.run(image, 0, 5)
    return recs, image, dies, vm


def compare(c, tr, dies, vm):
    g = Geo(c)
    rows = []

    def eq(fam, what, d, got, want):
        gb, wb = np.asarray(got, F).view(np.uint32).reshape(-1), np.asarray(want, F).view(np.uint32).reshape(-1)
        ok = gb.shape == wb.shape and bool(np.array_equal(gb, wb))
        rows.append(dict(family=fam, what=what, die=d, n=int(wb.size), bit_exact=ok))
    for d, die in enumerate(dies):
        t = tr["die"][d]
        rd = lambda nm, n: die.vm[vm[nm]:vm[nm] + n].view(F)          # noqa: E731
        eq("in_proj", "qkvz", d, rd("QKVZ", g.rows_qkvz), t["qkvz"])
        eq("conv", "conv_out", d, rd("CONV", g.C), t["conv"])
        eq("l2norm", "q", d, rd("QN", g.kd * g.dk), t["q"])
        eq("l2norm", "k", d, rd("KN", g.kd * g.dk), t["k"])
        eq("gates", "beta", d, rd("BETA", g.vd), t["beta"])
        eq("softplus", "softplus", d, rd("SP", g.vd), t["sp"])
        eq("gates", "alpha", d, rd("ALPHA", g.vd), t["alpha"])
        eq("delta_rule", "o", d, rd("O", g.vd * g.dv), t["o"])
        eq("gated_norm", "og", d, rd("OG", g.vd * g.dv), t["og"])
        hv = np.arange(d * g.vd, (d + 1) * g.vd)
        buf, off, _ = die.hbm.find(4 << 32, g.vd * g.dv * g.dk * 4)
        STd = buf[off:off + g.vd * g.dv * g.dk * 4].view(F).reshape(g.vd, g.dv, g.dk)
        eq("state_io", "state_new", d, np.transpose(STd, (0, 2, 1)), tr["S_new"][hv])
        ch = g.die_channels(d)
        buf, off, _ = die.hbm.find(5 << 32, g.C * 12)
        eq("conv", "ring_new", d, buf[off:off + g.C * 12].view(F).reshape(g.C, 3), tr["ring_new"][ch])
        eq("out_proj+all_reduce+residual", "x_out", d, rd("X", g.H), tr["x_out"])
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--no-hf", action="store_true")
    a = ap.parse_args()
    c = CFG
    t0 = time.time()
    w, st = make_weights(c), make_state(c)
    rng = np.random.default_rng(7)
    x = (rng.standard_normal(c["hidden"]) * 0.5).astype(F)
    tr = golden(c, w, st, x)
    res = dict(config=c, model="Qwen3-Next-80B-A3B linear-attention layer dims (synthetic BF16 weights / state)")
    if not a.no_hf:
        res["hf_agreement"] = hf_reference(c, w, st, x, tr)
        print("HF", json.dumps(res["hf_agreement"]), flush=True)
    recs, image, dies, vm = run_sim(c, w, st, x)
    rows = compare(c, tr, dies, vm)
    fam = {}
    for r in rows:
        f = fam.setdefault(r["family"], dict(checks=0, exact=0))
        f["checks"] += 1
        f["exact"] += int(r["bit_exact"])
    ok = all(r["bit_exact"] for r in rows)
    res["sim"] = dict(pass_=ok, records=len(recs), image_bytes=len(image), families=fam,
                      failures=[r for r in rows if not r["bit_exact"]][:10])
    _, _, dies_m, vm_m = run_sim(c, w, st, x, mutant="gqa_map")
    rows_m = compare(c, tr, dies_m, vm_m)
    res["mutant_gqa_map_fails"] = not all(r["bit_exact"] for r in rows_m)
    print("sim", json.dumps(res["sim"]["families"]), "pass" if ok else "FAIL", "mutant fails:",
          res["mutant_gqa_map_fails"], flush=True)
    # timing (one die, TP4) and the comparison with full attention
    s = T.schedule(recs, 8191, "S2")
    s0 = T.schedule(recs, 8191, "S0")
    fam_c = s["family_unit_cycles"]
    g = Geo(c)
    state_bytes = 2 * g.vd * g.dv * g.dk * 4 + 2 * g.C * 3 * 4
    res["timing"] = dict(S2_cycles=round(s["total_cycles"], 1), S0_cycles=round(s0["total_cycles"], 1),
                         records=s["records_executed"], family_unit_cycles=fam_c,
                         state_bytes_per_token_per_die=state_bytes,
                         state_bytes_per_token_per_layer_all_dies=state_bytes * TP,
                         per_unit=s["per_unit"])
    rec = dict(schema="opentallas.hgi_sim.gdn.v1", status="pass" if ok and res["mutant_gqa_map_fails"] else "fail",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               host=os.uname().nodename, wall_s=round(time.time() - t0, 1), result=res,
               source_sha256={p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest() for p in (
                   "hgi_sim/gdn.py", "hgi_sim/lib.py", "hgi_sim/machine.py", "hgi_sim/timing.py",
                   "hgi_sim/records.py")})
    print(json.dumps(res["timing"], indent=1, default=float)[:2500])
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    print(rec["status"])
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
