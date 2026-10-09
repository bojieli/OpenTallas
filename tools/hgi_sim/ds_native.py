#!/usr/bin/env python3
"""DeepSeek-V4.1-Flash on r25 in NATIVE HGI-1 unit ops (no SIMT.RUN: the r25 SMs are fixed-function matvec engines),
executed in the simulator on 96 dies and checked bit for bit against the released-checkpoint golden at 1M.

Lowering of the executed TP-96 program (tools/w19_hbm_tp96_isa.Compiler, variant oreduce), one die program per rank
(the structure is identical on every die; only rank constants differ, and ops a die does not run are CTL.NOP, so the
collectives line up record for record):

  hc_mixes        HC.HC_MIX (HCP unit) -> [pre4 | post4 | comb16];  SU copy h -> residual
  hc_pre_norm     FUSED.HC_PRE_NORM (norm engine: hc_pre mix + RMSNorm, D5120)
  mv              SM.MATVEC fmt 1 / 2 (FP8 / FP4 block dot, FP8 k32 activations) or fmt 0 (BF16); output format = O.fmt;
                  the die's rows; grouped wo_a = one record per o-group; K-split wo_a = a column window of B;
                  expert slots: B is an INDEXED descriptor (C3b) on the router's id word
  all_gather      COLL.ALL_GATHER per buffer (even-split segments, G9)
  o-group reduce  COLL.GROUP_REDUCE_MCAST (provisional, G10)
  q_norm_kv_row   SU templates (RMSNorm q, RMSNorm kv, adjacent-pair RoPE tail) + FUSED.QDQ_FP8 (provisional, G8)
                  + DMA.STORE of the window row into the window ring (HBM)
  q_rope          SU template (adjacent-pair RoPE tail of the die's head, BF16)
  attend          ATT.QK over the 128 window rows (HBM) -> SU: max of s*scale, exp + sum, BF16 p -> ATT.PV ->
                  SU: exp(sink - max), den, BF16(pv / den), inverse RoPE tail
  router_act      SU template (sqrt(softplus)) on the die's router rows
  route           SU bias add; IDX.SELECT top-6 (router unit) -> U32 ids; SU gathers of the selected scores through
                  INDEXED descriptors (C3b); SU sum + 1e-20, divide, x route_scale
  swiglu          SU template (min g, clip u, silu, x u, x route weight, BF16) on the die's rows of each slot
  moe_sum         SU templates (7 ordered adds, BF16)
  hc_post         FUSED.HC_POST (pre <- ffn mix pre: SU copy)

Arithmetic: SU templates run Machine.su1 (tools/hgi_sim/machine.u_su_vop); SM / HC / norm engine / QDQ / ATT use the
golden's unit functions (hdc_golden_v41).  Weights are read where the image manifest places them (B descriptor base ->
tensor rows), small tables (gains, RoPE row, sink, gate bias, window ring) are real HBM bytes.

    HDC_V41_ARITH=chunk8 python3 -m hgi_sim.ds_native --layers 0 --refs DIR --out REC.json
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import hdc_isa_v41 as I  # noqa: E402
import w19_hbm_tp96_isa as W  # noqa: E402

from hgi_sim import machine as MC  # noqa: E402
from hgi_sim.qwen_compiler import Builder, sut  # noqa: E402
from hgi_sim.records import ISTRIDE_BCAST, MDesc, Rec, decode_program, encode_program  # noqa: E402

F = np.float32
G_, V_ = W.G, W.V
TP, HEADS, D, HC = W.TP, W.HEAD_DIES, 5120, 4
VARIANT = "oreduce"
IDX = MC.IDX_DYN


def f32u(x):
    return int(np.asarray(F(x)).view(np.uint32))


# ----------------------------------------------------------------------------------------------------------------
# image: VM map (same on every die), HBM tables (per die) and the weight manifest
# ----------------------------------------------------------------------------------------------------------------
class Layout:
    SIZES = dict(h=HC * D, RES=HC * D, PRE=4, MIXa=24, MIXf=24, x=D, qa=1280, kvraw=512, GQN=1280, GKV=512,
                 SS=8, RS=8, qr=1280, kvn=512, kvr=512, win_new=512, q=32768, ROPE=64, q_own=512, SC=128, MB=8,
                 E=128, SE=8, EB=128, SINK=8, ES=8, DEN=8, PV=512, O=512, o_own=512, zpart=8192, z=8192, y=D,
                 gsc=384, BIAS=384, router=384, rid=8, SEL=8, TOT=8, DENR=8, route_w=8, ea=7 * 2304, yf=D,
                 TOK=8)

    def __init__(self):
        self.vm, cur = {}, 0
        names = list(self.SIZES)
        for e in range(7):
            names += [f"e{e}.g", f"e{e}.u", f"e{e}.d"]
        for nm in names:
            n = self.SIZES.get(nm, 2304 if nm.endswith((".g", ".u")) else D)
            cur = -(-cur // 64) * 64
            self.vm[nm] = cur
            cur += n
        assert cur <= MC.VM_WORDS, cur
        self.end = cur

    def V(self, name, n, off=0, m=1, stride=0, istride=0, fmt="FP32"):
        return MDesc(space="VM", fmt=fmt, base=self.vm[name] + off, n=n, m=m, stride=stride, istride=istride)


ESZ = {"fp8": 1.0, "fp4": 0.5, "bf16": 2.0}
HFMT = {"fp8": "FP8E4M3", "fp4": "FP4E2M1", "bf16": "BF16"}
WBASE = 1 << 36
TBASE = 1 << 34


class Manifest:
    """Weight placement: each matrix (or expert table) gets an HBM extent; descriptors address its rows."""

    def __init__(self):
        self.ent, self.cur = [], WBASE

    def place(self, key, rows, cols, fmt, n_experts=1):
        rb = int(cols * ESZ[fmt])
        rb = -(-rb // 32) * 32
        size = rb * rows * n_experts
        e = dict(key=key, base=self.cur, rows=rows, cols=cols, fmt=fmt, rowbytes=rb, experts=n_experts,
                 estride=rb * rows)
        self.ent.append(e)
        self.cur += -(-size // 4096) * 4096 + 4096
        return e

    def find(self, addr):
        for e in self.ent:
            if e["base"] <= addr < e["base"] + e["estride"] * e["experts"]:
                off = addr - e["base"]
                ex, off = divmod(off, e["estride"])
                r0, cb = divmod(off, e["rowbytes"])
                return e, ex, r0, int(cb / ESZ[e["fmt"]])
        raise MC.Fault(3, f"weight address {addr:#x} outside the manifest")


# ----------------------------------------------------------------------------------------------------------------
# the lowering
# ----------------------------------------------------------------------------------------------------------------
class Lower:
    def __init__(self, m, pos, lay: Layout, man: Manifest):
        self.m, self.pos, self.lay, self.man = m, pos, lay, man
        self.ent = {}

    def W(self, key, rows, cols, fmt, n_experts=1):
        if key not in self.ent:
            self.ent[key] = self.man.place(key, rows, cols, fmt, n_experts)
        return self.ent[key]

    def layer(self, L, ops, rank):
        """The die program of one layer for `rank` (identical structure on every rank)."""
        m, lay = self.m, self.lay
        b = Builder(None)
        V = lay.V
        P = m.P(L)
        head = rank < HEADS

        def add(rec, rd, wr, run=True):
            if not run:
                rec = Rec("CTL", "NOP", tag=rec.tag, family=rec.family)
            b.add(rec, rd if run else [], wr if run else [])

        def su(tag, fam, desc, rd, wr, run=True, **t):
            add(Rec("SU", "VOP", sut=sut(**t), desc=desc, tag=tag, family=fam), rd, wr, run)

        def tab(name):
            return MDesc(space="HBM", fmt="FP32", base=TBASE + TABLE_OFF[name], n=TABLE_N[name])

        def mv(op, x_desc, rows, out, n, w_key, fmt, out_fmt, run=True, col0=0, kcols=None, expert_slot=None,
               tag=None, rd=None, wcols=None):
            k = op["k"] if kcols is None else kcols
            r0, r1 = rows
            if expert_slot is not None:
                e = self.W(w_key, n, op["k"], fmt, n_experts=m.n_exp)
                bd = MDesc(space="HBM", fmt=HFMT[fmt], base=e["base"] + r0 * e["rowbytes"], n=k, m=max(r1 - r0, 1),
                           stride=e["rowbytes"], dyn_sel=IDX, lstride=lay.vm["rid"] + expert_slot,
                           dyn_mul=e["estride"])
            else:
                e = self.W(w_key, n, wcols or op["k"], fmt)
                bd = MDesc(space="HBM", fmt=HFMT[fmt], base=e["base"] + r0 * e["rowbytes"] + int(col0 * ESZ[fmt]),
                           n=k, m=max(r1 - r0, 1), stride=e["rowbytes"])
            fp = {"bf16": 0, "fp8": 1, "fp4": 2}[fmt]
            add(Rec("SM", "MATVEC", param=fp, desc=dict(A=x_desc, B=bd, O=V(out, max(r1 - r0, 1), off=r0, fmt=out_fmt)),
                    tag=tag or op["tag"], family="mv." + op["fn"]), rd or [], [out], run and r1 > r0)

        for op in ops:
            k = op["kind"]
            if k == "local":
                fn = op["fn"]
                w = op.get("which")
                if fn == "hc_mixes":
                    mix = "MIXa" if w == "attn" else "MIXf"
                    hcw = self.W(f"{P}hc_{w}", 1, 1, "bf16")
                    add(Rec("HC", "HC_MIX", param=0 if w == "attn" else 1, desc=dict(
                        A=V("h", HC * D), B=MDesc(space="HBM", fmt="BF16", base=hcw["base"], n=1),
                        O=V(mix, 24)), tag=op["tag"], family="hc_mixes"), ["h"], [mix])
                    su(f"{w}.res_copy", "hc_mixes", dict(A=V("h", HC * D), O=V("RES", HC * D)), ["h"], ["RES"],
                       dst=I.DST_VM)
                elif fn in ("hc_pre_norm", "final_norm"):
                    gname = {"attn": f"{P}attn_norm.weight", "ffn": f"{P}ffn_norm.weight"}.get(w, "norm.weight")
                    pre = V("PRE", 4) if w in ("attn", None) else V("MIXa", 4)
                    add(Rec("FUSED", "HC_PRE_NORM", imm_a=f32u(m.eps), desc=dict(
                        A=V("h", HC * D), B=tab(gname), C=pre, O=V("x", D, fmt="BF16")),
                        tag=op["tag"], family="hc_pre_norm"), ["h", "PRE", "MIXa"], ["x"])
                elif fn == "hc_post":
                    mix = "MIXa" if w == "attn" else "MIXf"
                    yv = "y" if w == "attn" else "yf"
                    add(Rec("FUSED", "HC_POST", desc=dict(A=V(yv, D), B=V("RES", HC * D), C=V(mix, 20, off=4),
                                                           O=V("h", HC * D)), tag=op["tag"], family="hc_post"),
                        [yv, "RES", mix], ["h"])
                    if w == "ffn":
                        su("pre <- ffn mix pre", "hc_post", dict(A=V("MIXf", 4), O=V("PRE", 4)), ["MIXf"], ["PRE"],
                           dst=I.DST_VM)
                elif fn == "q_norm_kv_row":
                    self.rmsnorm(su, "q_norm", "qa", 1280, "GQN", "qr", f"{P}attn.q_norm.weight")
                    self.rmsnorm(su, "kv_norm", "kvraw", 512, "GKV", "kvn", f"{P}attn.kv_norm.weight")
                    self.rope_tail(su, "kv_rope", "kvn", 512, "kvr", inverse=False, run=True)
                    add(Rec("FUSED", "QDQ_FP8", desc=dict(A=V("kvr", 512), O=V("win_new", 512)), tag="kv_row_qdq",
                            family="q_norm_kv_row"), ["kvr"], ["win_new"])
                    add(Rec("DMA", "STORE", desc=dict(A=V("win_new", 512), O=MDesc(
                        space="HBM", fmt="FP32", base=TBASE + TABLE_OFF["WIN"] + 127 * 2048, n=512)),
                        tag="window_row_append", family="q_norm_kv_row"), ["win_new"], ["WIN"])
                elif fn == "q_rope":
                    self.rope_tail(su, "q_rope", "q", 512, "q_own", inverse=False, run=head,
                                   src_off=rank * 512 if head else 0)
                elif fn == "attend":
                    self.attend(add, su, L, head)
                elif fn == "router_act":
                    r0, r1 = W.even(384)[rank]
                    su("router_act", "router_act", dict(A=V("gsc", r1 - r0, off=r0), O=V("gsc", r1 - r0, off=r0)),
                       ["gsc"], ["gsc"], sfu=I.SFU_SPSQRT, dst=I.DST_VM)
                elif fn == "route":
                    self.route(add, su)
                elif fn == "swiglu":
                    e = op["slot"]
                    r0, r1 = W.even(2304)[rank]
                    t = dict(a_min=1, imm3=f32u(m.limit), sfu=I.SFU_SILU, c_clip=1, e1=I.E1_MULC, rnd=1, dst=I.DST_VM)
                    desc = dict(A=V(f"e{e}.g", r1 - r0, off=r0), C=V(f"e{e}.u", r1 - r0, off=r0),
                                O=V("ea", r1 - r0, off=e * 2304 + r0))
                    if e < m.k_exp:
                        t["e2"] = I.E2_MULB
                        desc["B"] = V("route_w", r1 - r0, off=e, istride=ISTRIDE_BCAST)
                    su(f"swiglu.s{e}", "swiglu", desc, [f"e{e}.g", f"e{e}.u", "route_w"], ["ea"], **t)
                elif fn == "moe_sum":
                    r0, r1 = W.even(D)[rank]
                    n = r1 - r0
                    su("moe_sum.0", "moe_sum", dict(A=V("e0.d", n, off=r0), O=V("yf", n, off=r0)), ["e0.d"], ["yf"],
                       ad=I.AD_IMM, imm2=0, dst=I.DST_VM)
                    for e in range(1, m.k_exp + 1):
                        su(f"moe_sum.{e}", "moe_sum", dict(A=V("yf", n, off=r0), C=V(f"e{e}.d", n, off=r0),
                                                           O=V("yf", n, off=r0)), ["yf", f"e{e}.d"], ["yf"],
                           ad=I.AD_C, rnd=int(e == m.k_exp), dst=I.DST_VM)
                elif fn == "argmax_local":
                    r0, r1 = W.even(129280)[rank]
                    add(Rec("ARGMAX", "LOCAL", desc=dict(A=V("logits", r1 - r0, off=r0), O=V("TOK", 2))), ["logits"],
                        ["TOK"])
                else:
                    raise NotImplementedError(f"DS native lowering of {fn} (layer type not in this stage)")
            elif k == "mv":
                fn, fmt = op["fn"], op["fmt"]
                r0, r1 = op["rows"][rank]
                w = op["w"]
                if fn == "linear_q":
                    out_fmt = "BF16"
                elif fn in ("mv", "wo_a_part"):
                    out_fmt = "FP32"
                else:
                    out_fmt = "BF16"
                x = op["x"]
                if isinstance(w, (list, tuple)) and len(w) == 2 and isinstance(w[0], int):
                    slot, mat = w
                    xin = "ea" if mat == "w2" else x
                    xd = V("ea", 2304, off=slot * 2304) if mat == "w2" else V(x, op["k"])
                    if slot < m.k_exp:          # routed: weight base through the router's id word (C3b)
                        mv(op, xd, (r0, r1), op["out"], op["n"], f"{P}ffn.experts.{mat}", fmt, out_fmt,
                           expert_slot=slot, rd=[xin, "rid"])
                    else:                       # the shared expert: a fixed descriptor
                        mv(op, xd, (r0, r1), op["out"], op["n"], f"{P}ffn.shared_experts.{mat}.weight", fmt, out_fmt,
                           rd=[xin])
                elif fn == "wo_a_part":
                    j = rank % 8
                    mv(op, V("o_own", 512), (r0, r1), "zpart", op["n"], w, "bf16", "FP32", run=head, col0=j * 512,
                       kcols=512, rd=["o_own"], wcols=4096)
                elif fn == "wo_a":
                    raise NotImplementedError("gather variant")
                else:
                    wk = "|".join(w) if isinstance(w, list) else w
                    mv(op, V(x, op["k"]), (r0, r1), op["out"], op["n"], wk, fmt if fn == "linear_q" else "bf16",
                       out_fmt, rd=[x])
            elif k == "all_gather":
                for buf in op["bufs"]:
                    if buf == "ea":
                        for e in range(m.k_exp + 1):
                            add(Rec("COLL", "ALL_GATHER", desc=dict(A=V("ea", 2304, off=e * 2304),
                                                                     O=V("ea", 2304, off=e * 2304)),
                                    tag=f"{op['tag']}.s{e}", family="all_gather"), ["ea"], ["ea"])
                    else:
                        n = lay.SIZES.get(buf, 0) if buf in ("qa", "kvraw", "gsc", "y", "yf") else None
                        n = {"qa": 1280, "kvraw": 512, "gsc": 384, "y": D, "yf": D}[buf]
                        add(Rec("COLL", "ALL_GATHER", desc=dict(A=V(buf, n), O=V(buf, n)), tag=f"{op['tag']}.{buf}",
                                family="all_gather"), [buf], [buf])
            elif k == "all_reduce":
                add(Rec("COLL", "GROUP_REDUCE_MCAST", param=8, desc=dict(A=V("zpart", 8192), O=V("z", 8192, fmt="BF16")),
                        tag=op["tag"], family="all_reduce"), ["zpart"], ["z"])
            elif k == "expert_fetch":
                add(Rec("DMA", "FENCE", tag=op["tag"] + " (weights read in place through C3b)",
                        family="expert_fetch"), ["rid"], [])
            else:
                raise NotImplementedError(k)
        return b.recs

    # -- SU templates ----------------------------------------------------------------------------------------------
    def rmsnorm(self, su, tag, x, n, g, out, gname):
        """dshbm_baseline_measure.lower_rmsnorm as SU records: ss, rsqrt(ss / n + eps), bf16(w * (x * rs))."""
        V = self.lay.V
        su(f"{tag}.gain", tag, dict(A=MDesc(space="HBM", fmt="FP32", base=TBASE + TABLE_OFF[gname], n=n),
                                    O=V(g, n)), [], [g], dst=I.DST_VM)
        seg = 8 if n % 64 == 0 else 1
        su(f"{tag}.ss", tag, dict(A=V(x, n // seg, m=seg, stride=n // seg), R=V("SS", 1)), [x], ["SS"], red=I.RED_SUM,
           red_sq=1, red_tree=int(seg > 1), red_whole=int(seg == 1))
        su(f"{tag}.rs", tag, dict(A=V("SS", 1), O=V("RS", 1)), ["SS"], ["RS"], m1=I.M1_DIVIMM, imm1=f32u(n),
           ad=I.AD_IMM, imm2=f32u(self.m.eps), sfu=I.SFU_RSQRT, dst=I.DST_VM)
        su(f"{tag}.y", tag, dict(A=V(x, n), B=V("RS", n, istride=ISTRIDE_BCAST), C=V(g, n), O=V(out, n)),
           [x, "RS", g], [out], m1=I.M1_AB, e1=I.E1_MULC, rnd=1, dst=I.DST_VM)

    def rope_tail(self, su, tag, x, n, out, inverse, run=True, src_off=0):
        """lower_rope: copy the head, rotate the last 64 as adjacent pairs (cos/sin row from the RoPE table)."""
        V = self.lay.V
        rd = 64
        su(f"{tag}.table", tag, dict(A=MDesc(space="HBM", fmt="FP32", base=TBASE + TABLE_OFF["ROPE"], n=64),
                                     O=V("ROPE", 64)), [], ["ROPE"], run=run, dst=I.DST_VM)
        su(f"{tag}.head", tag, dict(A=V(x, n - rd, off=src_off), O=V(out, n - rd)), [x], [out], run=run,
           dst=I.DST_VM)
        su(f"{tag}.tail", tag, dict(A=V(x, rd, off=src_off + n - rd), B=V("ROPE", rd), D=V("ROPE", rd, off=32),
                                    O=V(out, rd, off=n - rd)), [x, "ROPE"], [out], run=run, c_pair=1, b_half=1,
           m1=I.M1_AB, qm=I.QM_ALT_PN if inverse else I.QM_ALT_NP, ad=I.AD_Q, rnd=1, dst=I.DST_VM)

    def attend(self, add, su, L, head):
        V = self.lay.V
        win = MDesc(space="HBM", fmt="FP32", base=TBASE + TABLE_OFF["WIN"], n=128, m=1, stride=2048)
        add(Rec("ATT", "QK", param=1 | (7 << 4), desc=dict(A=V("q_own", 512), B=win, O=V("SC", 128)),
                tag="attend.qk", family="attend"), ["q_own", "WIN"], ["SC"], head)
        sc = f32u(self.m.attn_scale)
        su("attend.max", "attend", dict(A=V("SC", 128), R=V("MB", 1)), ["SC"], ["MB"], run=head, m1=I.M1_AIMM,
           imm1=sc, red=I.RED_MAX, red_whole=1)
        su("attend.exp_sum", "attend", dict(A=V("SC", 128), B=V("MB", 128, istride=ISTRIDE_BCAST), O=V("E", 128),
                                            R=V("SE", 1)), ["SC", "MB"], ["E", "SE"], run=head, m1=I.M1_AIMM, imm1=sc,
           ad=I.AD_NEGB, sfu=I.SFU_EXP, red=I.RED_SUM, red_whole=1, dst=I.DST_VM)
        su("attend.bf16_p", "attend", dict(A=V("E", 128), O=V("EB", 128)), ["E"], ["EB"], run=head, rnd=1,
           dst=I.DST_VM)
        add(Rec("ATT", "PV", param=1 | (7 << 4), desc=dict(A=V("EB", 128), B=win, O=V("PV", 512)),
                tag="attend.pv", family="attend"), ["EB", "WIN"], ["PV"], head)
        su("attend.sink_table", "attend", dict(A=MDesc(space="HBM", fmt="FP32", base=TBASE + TABLE_OFF["SINK"], n=1),
                                               O=V("SINK", 1)), [], ["SINK"], run=head, dst=I.DST_VM)
        su("attend.sink_exp", "attend", dict(A=V("SINK", 1), B=V("MB", 1), O=V("ES", 1)), ["SINK", "MB"], ["ES"],
           run=head, ad=I.AD_NEGB, sfu=I.SFU_EXP, dst=I.DST_VM)
        su("attend.den", "attend", dict(A=V("SE", 1), C=V("ES", 1), O=V("DEN", 1)), ["SE", "ES"], ["DEN"], run=head,
           ad=I.AD_C, dst=I.DST_VM)
        su("attend.norm", "attend", dict(A=V("PV", 512), B=V("DEN", 512, istride=ISTRIDE_BCAST), O=V("O", 512)),
           ["PV", "DEN"], ["O"], run=head, m1=I.M1_DIVB, rnd=1, dst=I.DST_VM)
        self.rope_tail(su, "attend.inv_rope", "O", 512, "o_own", inverse=True, run=head)

    def route(self, add, su):
        V = self.lay.V
        m = self.m
        su("route.bias", "route", dict(A=MDesc(space="HBM", fmt="FP32", base=TBASE + TABLE_OFF["BIAS"], n=384),
                                       O=V("BIAS", 384)), [], ["BIAS"], dst=I.DST_VM)
        su("route.scores_bias", "route", dict(A=V("gsc", 384), C=V("BIAS", 384), O=V("router", 384)),
           ["gsc", "BIAS"], ["router"], ad=I.AD_C, dst=I.DST_VM)
        add(Rec("IDX", "SELECT", param=0 | (6 << 8), desc=dict(A=V("router", 384), O=MDesc(
            space="VM", fmt="U32", base=self.lay.vm["rid"], n=6)), tag="route.top6", family="route"),
            ["router"], ["rid"])
        for j in range(m.k_exp):                 # gather the selected scores: indexed descriptors (C3b)
            su(f"route.gather{j}", "route", dict(
                A=MDesc(space="VM", fmt="FP32", base=self.lay.vm["gsc"], n=1, dyn_sel=IDX,
                        lstride=self.lay.vm["rid"] + j, dyn_mul=1), O=V("SEL", 1, off=j)), ["gsc", "rid"], ["SEL"],
               dst=I.DST_VM)
        su("route.total", "route", dict(A=V("SEL", m.k_exp), R=V("TOT", 1)), ["SEL"], ["TOT"], red=I.RED_SUM,
           red_whole=1)
        su("route.den", "route", dict(A=V("TOT", 1), O=V("DENR", 1)), ["TOT"], ["DENR"], ad=I.AD_IMM,
           imm2=f32u(1e-20), dst=I.DST_VM)
        su("route.weights", "route", dict(A=V("SEL", m.k_exp), B=V("DENR", m.k_exp, istride=ISTRIDE_BCAST),
                                          O=V("route_w", m.k_exp)), ["SEL", "DENR"], ["route_w"], m1=I.M1_DIVB,
           e1=I.E1_MULIMM, imm2=f32u(m.route_scale), dst=I.DST_VM)


TABLE_N = {}
TABLE_OFF = {}


def build_tables(m, st, L, pos, rank):
    """Per-die HBM tables (real bytes): gains, RoPE row at the position, the head's sink, gate bias, window ring."""
    P = m.P(L)
    cos, sin = V_.rope_cs(m.freqs_yarn if m.ratio[L] > 0 else m.freqs_plain, pos)
    items = [(f"{P}attn_norm.weight", m.lw(L, "attn_norm.weight")), (f"{P}ffn_norm.weight", m.lw(L, "ffn_norm.weight")),
             (f"{P}attn.q_norm.weight", m.lw(L, "attn.q_norm.weight")),
             (f"{P}attn.kv_norm.weight", m.lw(L, "attn.kv_norm.weight")),
             ("ROPE", np.concatenate([cos, sin])), ("BIAS", m.lw(L, "ffn.gate.bias")),
             ("SINK", m.lw(L, "attn.attn_sink")[rank:rank + 1] if rank < HEADS else np.zeros(1)),
             ("WIN", np.concatenate([np.asarray(st.win[L], F).reshape(-1), np.zeros(512, F)]))]
    off, blobs = 0, []
    for name, arr in items:
        a = np.asarray(arr, dtype=F).reshape(-1)
        off = -(-off // 32) * 32
        TABLE_OFF[name], TABLE_N[name] = off, a.size
        blobs.append((off, a))
        off += a.size * 4
    buf = np.zeros(off, dtype=np.uint8)
    for o, a in blobs:
        buf[o:o + a.nbytes] = a.view(np.uint8)
    return buf


# ----------------------------------------------------------------------------------------------------------------
# DS unit models (registered beside the generic ones)
# ----------------------------------------------------------------------------------------------------------------
def ds_units(m, man, golib):
    U = dict(MC.UNITS)

    def wrows(e, ex, r0, nrows, c0, ncols, L):
        key = e["key"]
        if e["experts"] > 1:
            pre, mat = key.rsplit(".", 1)
            name = f"{pre}.{ex}.{mat}.weight"
        else:
            name = key.split("|") if "|" in key else key
        w = golib.wrows(name, r0, r0 + nrows)
        if c0 or ncols != e["cols"]:
            w = (w.q[:, c0:c0 + ncols], w.e) if isinstance(w, V_.Q8) else w[:, c0:c0 + ncols]
        return w

    def sm(M, r, L):
        a, bd, o = r.desc["A"], r.desc["B"], r.desc["O"]
        fmt = r.param & 3
        for die in M.dies:
            base, n, mrows, st, _ = M.eff(bd, die, L)
            e, ex, r0, c0 = man.find(base)
            w = wrows(e, ex, r0, mrows, c0, n, L)
            x = M.read(a, die, L)
            if fmt in (1, 2):
                out = V_.linear_q(w, x)
            else:
                out = V_.mv(np.asarray(w, dtype=F), x)
                if o.fmt == "BF16":
                    out = G_.to_bf16(out)
            M.vm_write(o, die, L, out)

    def hc_mix(M, r, L):
        which = "attn" if r.param == 0 else "ffn"
        for die in M.dies:
            h = M.read(r.desc["A"], die, L).reshape(HC, D)
            pre, post, comb = m.hc_mixes(h, L, which)
            M.vm_write(r.desc["O"], die, L, np.concatenate([np.asarray(pre, F), np.asarray(post, F),
                                                            np.asarray(comb, F).reshape(-1)]))

    def hc_pre_norm(M, r, L):
        for die in M.dies:
            h = M.read(r.desc["A"], die, L).reshape(HC, D)
            g = M.read(r.desc["B"], die, L)
            pre = M.read(r.desc["C"], die, L)
            M.vm_write(r.desc["O"], die, L, V_.rmsnorm_fold(m.hc_pre(h, pre), g, m.eps))

    def hc_post(M, r, L):
        for die in M.dies:
            y = M.read(r.desc["A"], die, L)
            res = M.read(r.desc["B"], die, L).reshape(HC, D)
            pc = M.read(r.desc["C"], die, L)
            M.vm_write(r.desc["O"], die, L, m.hc_post(y, res, pc[:4], pc[4:20].reshape(HC, HC)))

    def qdq(M, r, L):
        for die in M.dies:
            M.vm_write(r.desc["O"], die, L, V_.qdq_fp8(M.read(r.desc["A"], die, L)))

    def select(M, r, L):
        k = (r.param >> 8) & 0xFF
        for die in M.dies:
            v = M.read(r.desc["A"], die, L)
            ids = sorted(int(i) for i in V_.topk_lowest_index(v, k))
            die.vm[M.vm_addrs(r.desc["O"], die, L)] = np.asarray(ids, dtype=np.uint32)

    def gather(M, r, L):
        a = r.desc["A"]
        dies = M.dies
        n = a.n
        full = np.zeros(n, dtype=np.uint32)
        G = len(dies)
        for d in dies:
            lo, hi = d.rank * n // G, (d.rank + 1) * n // G
            full[lo:hi] = d.vm[M.vm_addrs(a, d, L)][lo:hi]
        for d in dies:
            d.vm[M.vm_addrs(r.desc["O"], d, L)] = full

    def group_reduce(M, r, L):
        g = r.param
        n = r.desc["A"].n
        span = n // g
        z = np.zeros(n, dtype=F)
        for grp in range(g):
            parts = [M.vm_read(r.desc["A"], M.dies[grp * g + j], L)[grp * span:(grp + 1) * span] for j in range(g)]
            while len(parts) > 1:
                parts = [G_.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
            z[grp * span:(grp + 1) * span] = parts[0]
        if r.desc["O"].fmt == "BF16":
            z = G_.to_bf16(z)
        for d in M.dies:
            M.vm_write(r.desc["O"], d, L, z)

    def att_qk(M, r, L):
        for die in M.dies:
            q = M.read(r.desc["A"], die, L)
            rows = M.hbm_read(MDesc(space="HBM", fmt="FP32", base=r.desc["B"].base, n=512, m=r.desc["B"].n,
                                    stride=r.desc["B"].stride), die, L)
            M.vm_write(r.desc["O"], die, L, V_.dots(q.reshape(1, -1), rows).reshape(-1))

    def att_pv(M, r, L):
        for die in M.dies:
            p = M.read(r.desc["A"], die, L)
            rows = M.hbm_read(MDesc(space="HBM", fmt="FP32", base=r.desc["B"].base, n=512, m=r.desc["B"].n,
                                    stride=r.desc["B"].stride), die, L)
            M.vm_write(r.desc["O"], die, L, V_.dots(p.reshape(1, -1), rows.T).reshape(-1))

    def argmax_local(M, r, L):
        for die in M.dies:
            v = M.read(r.desc["A"], die, L)
            j = int(np.argmax(v))
            a = M.vm_addrs(r.desc["O"], die, L, 1, 2)
            die.vm[a[0]] = np.asarray([v[j]], dtype=F).view(np.uint32)[0]
            die.vm[a[1]] = np.uint32(j)

    U.update({("SM", "MATVEC"): sm, ("HC", "HC_MIX"): hc_mix, ("FUSED", "HC_PRE_NORM"): hc_pre_norm,
              ("FUSED", "HC_POST"): hc_post, ("FUSED", "QDQ_FP8"): qdq, ("IDX", "SELECT"): select,
              ("COLL", "ALL_GATHER"): gather, ("COLL", "GROUP_REDUCE_MCAST"): group_reduce,
              ("ATT", "QK"): att_qk, ("ATT", "PV"): att_pv, ("ARGMAX", "LOCAL"): argmax_local})
    return U


def run_per_die(Mach, progs, units, pos, token, hook=None):
    """Execute per-die programs of identical structure: record k of die d on die d; collectives on all dies."""
    nrec = len(progs[0])
    assert all(len(p) == nrec for p in progs)
    dies = Mach.dies
    for d in dies:
        d.dyn[:8] = [0, pos, pos + 1, token, 0, d.rank, 0, pos]
    for k in range(nrec):
        r0 = progs[0][k]
        if r0.unit == "COLL":
            units[(r0.unit, r0.op)](Mach, r0, 0)
        else:
            for d, die in enumerate(dies):
                r = progs[d][k]
                if r.unit == "CTL":
                    continue
                Mach.dies = [die]
                try:
                    units[(r.unit, r.op)](Mach, r, 0)
                finally:
                    Mach.dies = dies
        if hook:
            hook(k, r0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layers", default="0")
    ap.add_argument("--refs", type=Path, default=W.REF_SHARDS)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    feats = getattr(np, "_core", np.core)._multiarray_umath.__cpu_features__
    if feats.get("AVX512F"):
        raise SystemExit("set NPY_DISABLE_CPU_FEATURES (numpy AVX512 float64 trig differs from the reference)")
    t0 = time.time()
    layers = W.parse_layers(a.layers)
    assert layers[0] == 0, "the native stage run starts from the embedding (layer 0)"
    ref = json.loads(W.REF_RECORD.read_text())
    ctx, seed = ref["context"], ref["seed"]
    pos = ctx - 1
    hist = list(ref["token_history"])
    ck = W.LC.Checkpoint()
    m, init_sha = W.LC.build_model(ck, engram=any(L in (1, 14) for L in layers))
    st = W.State(m, ctx, seed, set(layers))
    golib = W.Executor(m, st, pos, hist, VARIANT)
    lay, man = Layout(), Manifest()
    low = Lower(m, pos, lay, man)
    units = ds_units(m, man, golib)
    h0 = np.repeat(ck.rows("embed.weight", [hist[-1]]), m.hc, axis=0).astype(F)
    results = []
    dies = None
    for L in layers:
        ops = W.Compiler(m, pos, VARIANT).compile_layer(L, first=(L == layers[0]))
        progs, imgs = [], []
        tabs = [build_tables(m, st, L, pos, r) for r in range(TP)]
        for r in range(TP):
            recs = low.layer(L, ops, r)
            b = encode_program(recs)
            assert encode_program(decode_program(b)) == b
            dec = decode_program(b)
            for x, y in zip(dec, recs):
                x.tag, x.family = y.tag, y.family
            progs.append(dec)
            imgs.append(len(b))
        if dies is None:
            dies = []
            for r in range(TP):
                hb = MC.Hbm()
                hb.add(TBASE, tabs[r], "TABLES")
                dies.append(MC.Die(r, hb))
                dies[-1].vm[lay.vm["h"]:lay.vm["h"] + HC * D] = h0.reshape(-1).view(np.uint32)
                dies[-1].vm[lay.vm["PRE"]:lay.vm["PRE"] + 4] = np.array([1, 0, 0, 0], F).view(np.uint32)
        else:
            for r in range(TP):
                dies[r].hbm = MC.Hbm()
                dies[r].hbm.add(TBASE, tabs[r], "TABLES")
        Mach = MC.Machine(dies, units)
        snaps = {}
        watch = {"attn_norm": ("x", D), "kv_row_qdq": ("win_new", 512), "attn_out_gather.y": ("y", D),
                 "ffn_norm": ("x", D), "route.scores_bias": ("router", 384), "ffn_out_gather.yf": ("yf", D),
                 "route.top6": ("rid", 6)}

        def hook(k, r0):
            if r0.tag in watch:
                nm, n = watch[r0.tag]
                snaps[r0.tag] = [d.vm[lay.vm[nm]:lay.vm[nm] + n].copy() for d in dies]
        tl = time.time()
        fault = None
        try:
            run_per_die(Mach, progs, units, pos, hist[-1], hook)
        except Exception as e:                      # noqa: BLE001
            fault = f"{type(e).__name__}: {e}"
        z = np.load(a.refs / f"ctx{ctx}_L{L:02d}.npz")
        js = json.loads((a.refs / f"ctx{ctx}_L{L:02d}.json").read_text())
        regs = []
        if fault is None:
            def chk(name, want, tag=None, buf=None, n=None, ranks=None, u32=False):
                got = [(d, (snaps[tag][d] if tag else dies[d].vm[lay.vm[buf]:lay.vm[buf] + n]))
                       for d in (ranks or range(TP))]
                if u32:
                    ok = all(np.array_equal(g.astype(np.int64), np.asarray(want)) for _, g in got)
                    regs.append(dict(region=name, bit_exact=bool(ok), ranks_checked=len(got)))
                    return
                regs.append(W.check(name, want, [(d, g.view(F)) for d, g in got]))
            chk(f"L{L}.attn_norm", z[f"L{L}.attn_norm"], tag="attn_norm")
            chk(f"win{L}", z[f"win{L}"], tag="kv_row_qdq")
            chk(f"L{L}.attn", z[f"L{L}.attn"], tag="attn_out_gather.y")
            chk(f"L{L}.ffn_norm", z[f"L{L}.ffn_norm"], tag="ffn_norm")
            chk(f"L{L}.router", z[f"L{L}.router"], tag="route.scores_bias")
            chk(f"L{L}.ffn", z[f"L{L}.ffn"], tag="ffn_out_gather.yf")
            chk(f"block{L}", z[f"block{L}"], buf="h", n=HC * D)
            chk(f"pre{L}", z[f"pre{L}"], buf="PRE", n=4)
            chk(f"L{L}.experts", js["experts"], tag="route.top6", u32=True)
        ok = fault is None and all(x["bit_exact"] for x in regs)
        fams = {}
        for r in progs[0]:
            fams[f"{r.unit}.{r.op}"] = fams.get(f"{r.unit}.{r.op}", 0) + 1
        results.append(dict(layer=L, kind=js["kind"], verdict="pass" if ok else "fail", fault=fault, regions=regs,
                            records_per_die=len(progs[0]), image_bytes_die0=imgs[0], unit_ops=fams,
                            wall_s=round(time.time() - tl, 1)))
        print(f"L{L:02d} {'PASS' if ok else 'FAIL'} records {len(progs[0])} fault {fault} "
              f"bad {[x['region'] for x in regs if not x['bit_exact']]}", flush=True)
        if not ok:
            break
    rec = dict(schema="opentallas.hgi_sim.ds_native.v1",
               status="pass" if results and all(x["verdict"] == "pass" for x in results) else "fail",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               host=os.uname().nodename, context=ctx, position=pos, layers=a.layers, results=results,
               provisional=["FUSED.QDQ_FP8 (G8)", "COLL.GROUP_REDUCE_MCAST (G10)", "ALL_GATHER even split (G9)",
                            "indexed descriptors (C3b)", "per-die programs of identical structure (G11)",
                            "window ring read oldest-first from slot 0 (exact at this position; G12 wrap)"],
               wall_s=round(time.time() - t0, 1), model_init_sha256=init_sha,
               source_sha256={p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest() for p in (
                   "hgi_sim/ds_native.py", "hgi_sim/machine.py", "hgi_sim/records.py", "hgi_sim/lib.py",
                   "w19_hbm_tp96_isa.py", "hdc_golden_v41.py")})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=int) + "\n")
    print(rec["status"])
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
