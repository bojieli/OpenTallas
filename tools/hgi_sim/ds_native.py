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
                 SS=8, RS=8, qr=1280, kvn=512, kvr=512, win_new=512, q=512, ROPE=64, q_own=512, SC=640, MB=8,
                 E=640, SE=8, EB=640, SINK=8, ES=8, DEN=8, PV=512, O=512, o_own=512, zpart=8192, z=8192, y=D,
                 gsc=384, BIAS=384, router=384, rid=8, SEL=8, TOT=8, DENR=8, route_w=8, ea=7 * 2304, yf=D,
                 TOK=8, eg_rows=6144, eg_kv=25600, EGW=HC * D, EGID=32, EGC=6144, EGS=192, SSH=8, RH=8, SSK=8,
                 RK=8, RST=8, DOTR=8, GATE=8, cmp=1024, iwr=32, iq=4096, SLOTKV=1024, SLOTSC=1024, MXC=512, EC=1024,
                 DENC=512, PC=1024, P2=1024, POOL=512, LAT0=512, LAT=512, GCN=512, KIN=128, GKN=128, KN=128, KR=128,
                 LR=512, IK=128, CK=512, ROPE2=64, logits=1352)

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
SBASE = 1 << 35                      # selected compressed-KV rows per KV source (persistent across layers)
SOURCES = [2, 8, 14, 20]
SELB = 512 * 2048


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
        self.bufn = dict(qa=1280, kvraw=512, gsc=384, y=D, yf=D, iq=4096, iwr=32, eg_rows=6144, eg_kv=25600)

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
            self.bufn[out] = n
            ooff = 0 if out in ("q", "logits", "KIN") else r0          # die-local outputs
            add(Rec("SM", "MATVEC", param=fp, desc=dict(A=x_desc, B=bd, O=V(out, max(r1 - r0, 1), off=ooff,
                                                                             fmt=out_fmt)),
                    tag=tag or op["tag"], family="mv." + op["fn"]), rd or [], [out], run and r1 > r0)

        for op in ops:
            k = op["kind"]
            if k == "local":
                fn = op["fn"]
                w = op.get("which")
                if fn == "hc_mixes":
                    mix = "MIXa" if w == "attn" else "MIXf"
                    hcw = self.W(f"{P}hc_{w}", 1, 1, "bf16")
                    add(Rec("HC", "HC_MIX", param=0 if w == "attn" else 1, imm_b=L, desc=dict(
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
                    self.rope_tail(su, "q_rope", "q", 512, "q_own", inverse=False, run=head)
                elif fn == "attend":
                    self.attend(add, su, L, head, op.get("yarn"))
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
                    add(Rec("ARGMAX", "LOCAL", imm_a=r0, desc=dict(A=V("logits", r1 - r0), O=V("TOK", 2)),
                            tag="argmax_local", family="argmax"), ["logits"], ["TOK"])
                elif fn == "engram_fetch":
                    self.engram_fetch(add, su, L)
                elif fn == "engram_mix":
                    self.engram_mix(su, L)
                elif fn == "compressor":
                    self.compressor(add, su, L, op, run=rank in op["ranks"])
                elif fn == "index_q":
                    add(Rec("IDX", "INDEX_Q", imm_b=L, desc=dict(A=V("iq", 4096), B=V("iwr", 32)), tag=op["tag"],
                            family="indexer"), ["iq", "iwr"], ["IDXQ"])
                elif fn == "index_scores":
                    add(Rec("IDX", "INDEX_SCORES", param=op["src"], imm_a=op["n"], imm_b=L, tag=op["tag"],
                            family="indexer"), ["IDXQ", "kvstore"], ["IDXS"])
                elif fn == "topk_local":
                    add(Rec("IDX", "TOPK_LOCAL", param=op["k"], imm_b=L, tag=op["tag"], family="indexer"), ["IDXS"],
                        ["IDXT"])
                elif fn in ("cand_local", "cand_apply", "cand_mask"):
                    sub = {"cand_local": 1, "cand_apply": 2, "cand_mask": 3}[fn]
                    add(Rec("IDX", "SELECT", param=sub, imm_a=op.get("n", 0), imm_b=L, tag=op["tag"],
                            family="candidates"), ["IDXS", "CAND"], ["IDXS", "CAND"])
                else:
                    raise NotImplementedError(f"DS native lowering of {fn}")
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
                        n = self.bufn[buf]
                        add(Rec("COLL", "ALL_GATHER", desc=dict(A=V(buf, n), O=V(buf, n)), tag=f"{op['tag']}.{buf}",
                                family="all_gather"), [buf], [buf])
            elif k == "all_reduce":
                add(Rec("COLL", "GROUP_REDUCE_MCAST", param=8, desc=dict(A=V("zpart", 8192), O=V("z", 8192, fmt="BF16")),
                        tag=op["tag"], family="all_reduce"), ["zpart"], ["z"])
            elif k == "topk_merge":
                what = op["what"]
                if what == "argmax":
                    add(Rec("COLL", "ARGMAX_MERGE", desc=dict(A=V("TOK", 2), O=MDesc(space="VM", fmt="U32",
                                                                                     base=lay.vm["TOK"] + 4, n=1)),
                            tag=op["tag"], family="argmax"), ["TOK"], ["TOK"])
                else:
                    add(Rec("COLL", "TOPK_MERGE", param=0 if what == "sel" else 1, imm_a=op["k"], tag=op["tag"],
                            family="indexer" if what == "sel" else "candidates"), ["IDXT", "CAND"], ["SELIDX", "CAND"])
            elif k == "kv_gather":
                add(Rec("COLL", "ROW_GATHER", param=op["src"], imm_a=op["elems"] // 512, tag=op["tag"],
                        family="kv_gather"), ["SELIDX", "kvstore"], [f"SELROWS{op['src']}"])
            elif k == "expert_fetch":
                add(Rec("DMA", "FENCE", tag=op["tag"] + " (weights read in place through C3b)",
                        family="expert_fetch"), ["rid"], [])
            else:
                raise NotImplementedError(k)
        return b.recs

    # -- Engram (layers 1, 14): rows by host-hashed ids through indexed descriptors, decoded on the SU ----------------
    def engram_fetch(self, add, su, L):
        V, m = self.lay.V, self.m
        ids_n = 24
        add(Rec("DMA", "LOAD", desc=dict(A=MDesc(space="HBM", fmt="U32", base=TBASE + TABLE_OFF["EGID"], n=ids_n),
                                         O=MDesc(space="VM", fmt="U32", base=self.lay.vm["EGID"], n=ids_n)),
                tag="engram.ids", family="engram"), [], ["EGID"])
        codes, sc = m.emb_codes[L]
        width = codes.shape[1]
        ec = self.W(f"EGC{L}", 1, width, "fp8", n_experts=codes.shape[0])
        es = self.W(f"EGS{L}", 1, width // 32, "fp8", n_experts=codes.shape[0])
        for t in range(ids_n):
            add(Rec("DMA", "LOAD", desc=dict(
                A=MDesc(space="HBM", fmt="FP8E4M3", base=ec["base"], n=width, dyn_sel=IDX,
                        lstride=self.lay.vm["EGID"] + t, dyn_mul=ec["estride"]),
                O=V("EGC", width, off=t * width)), tag=f"engram.codes{t}", family="engram"), ["EGID"], ["EGC"])
            add(Rec("DMA", "LOAD", desc=dict(
                A=MDesc(space="HBM", fmt="UE8M0", base=es["base"], n=width // 32, dyn_sel=IDX,
                        lstride=self.lay.vm["EGID"] + t, dyn_mul=es["estride"]),
                O=V("EGS", width // 32, off=t * (width // 32))), tag=f"engram.scales{t}", family="engram"),
                ["EGID"], ["EGS"])
        nb = ids_n * width // 32
        su("engram.decode", "engram", dict(A=V("EGC", 32, m=nb, stride=32), B=V("EGS", 32, m=nb, stride=1,
                                                                              istride=ISTRIDE_BCAST),
                                           O=V("eg_rows", 32, m=nb, stride=32)), ["EGC", "EGS"], ["eg_rows"],
           m1=I.M1_AB, rnd=1, dst=I.DST_VM)

    def engram_mix(self, su, L):
        V, m = self.lay.V, self.m
        n = D

        def rows(name, off=0):
            return V(name, n, m=HC, stride=n, off=off)
        su("engram.wgt", "engram", dict(A=MDesc(space="HBM", fmt="FP32", base=TBASE + TABLE_OFF["EGW"], n=HC * D),
                                        O=V("EGW", HC * D)), [], ["EGW"], dst=I.DST_VM)
        for nm, src in (("H", "h"), ("K", "eg_kv")):
            su(f"engram.ss{nm}", "engram", dict(A=rows(src), R=V(f"SS{nm}", 1, m=HC, stride=1)), [src], [f"SS{nm}"],
               red=I.RED_SUM, red_sq=1)
            su(f"engram.r{nm}", "engram", dict(A=V(f"SS{nm}", HC), O=V(f"R{nm}", HC)), [f"SS{nm}"], [f"R{nm}"],
               m1=I.M1_DIVIMM, imm1=f32u(n), ad=I.AD_IMM, imm2=f32u(m.eps), sfu=I.SFU_RSQRT, dst=I.DST_VM)
        su("engram.rstd", "engram", dict(A=V("RH", HC), B=V("RK", HC), O=V("RST", HC)), ["RH", "RK"], ["RST"],
           m1=I.M1_AB, dst=I.DST_VM)
        su("engram.hw", "engram", dict(A=rows("h"), B=rows("EGW"), O=rows("RES")), ["h", "EGW"], ["RES"], m1=I.M1_AB,
           dst=I.DST_VM)
        su("engram.dot", "engram", dict(A=rows("RES"), B=rows("eg_kv"), R=V("DOTR", 1, m=HC, stride=1)),
           ["RES", "eg_kv"], ["DOTR"], m1=I.M1_AB, red=I.RED_SUM)
        su("engram.gate", "engram", dict(A=V("DOTR", HC), B=V("RST", HC), O=V("GATE", HC)), ["DOTR", "RST"], ["GATE"],
           m1=I.M1_AB, m2=I.M2_IMM, imm1=f32u(m.engram_scale), sfu=I.SFU_EGATE, dst=I.DST_VM)
        su("engram.out", "engram", dict(A=V("eg_kv", n, m=HC, stride=0, off=HC * D),
                                        B=V("GATE", n, m=HC, stride=1, istride=ISTRIDE_BCAST), C=rows("h"),
                                        O=rows("h")), ["eg_kv", "GATE", "h"], ["h"], m1=I.M1_AB, ad=I.AD_C, rnd=1,
           dst=I.DST_VM)

    # -- compressor (KV-source layers, the owner die of the closing group) ---------------------------------------------
    def compressor(self, add, su, L, op, run):
        V, m = self.lay.V, self.m
        P = m.P(L)
        r = m.ratio[L]
        grp = op["group"]
        if r > 1:
            nprev = TABLE_N["SLOTKV"] // 512
            for nm in ("SLOTKV", "SLOTSC"):
                if nprev:
                    su(f"cmp.{nm}.load", "compressor", dict(
                        A=MDesc(space="HBM", fmt="FP32", base=TBASE + TABLE_OFF[nm], n=nprev * 512),
                        O=V(nm, nprev * 512)), [], [nm], run=run, dst=I.DST_VM)
            su("cmp.kv_now", "compressor", dict(A=V("cmp", 512), O=V("SLOTKV", 512, off=nprev * 512)), ["cmp"],
               ["SLOTKV"], run=run, dst=I.DST_VM)
            su("cmp.sc_now", "compressor", dict(A=V("cmp", 512, off=512), O=V("SLOTSC", 512, off=nprev * 512)), ["cmp"],
               ["SLOTSC"], run=run, dst=I.DST_VM)
            cols = dict(m=512, stride=1, istride=512)
            su("cmp.max", "compressor", dict(A=V("SLOTSC", r, **cols), R=V("MXC", 1, m=512, stride=1)), ["SLOTSC"],
               ["MXC"], run=run, red=I.RED_MAX)
            su("cmp.exp", "compressor", dict(A=V("SLOTSC", 512, m=r, stride=512), B=V("MXC", 512, m=r, stride=0),
                                             O=V("EC", 512, m=r, stride=512)), ["SLOTSC", "MXC"], ["EC"], run=run,
               ad=I.AD_NEGB, sfu=I.SFU_EXP, dst=I.DST_VM)
            su("cmp.den", "compressor", dict(A=V("EC", r, **cols), R=V("DENC", 1, m=512, stride=1)), ["EC"], ["DENC"],
               run=run, red=I.RED_SUM)
            su("cmp.p", "compressor", dict(A=V("EC", 512, m=r, stride=512), B=V("DENC", 512, m=r, stride=0),
                                           O=V("PC", 512, m=r, stride=512)), ["EC", "DENC"], ["PC"], run=run,
               m1=I.M1_DIVB, dst=I.DST_VM)
            su("cmp.kvp", "compressor", dict(A=V("SLOTKV", 512, m=r, stride=512), B=V("PC", 512, m=r, stride=512),
                                             O=V("P2", 512, m=r, stride=512)), ["SLOTKV", "PC"], ["P2"], run=run,
               m1=I.M1_AB, dst=I.DST_VM)
            su("cmp.pool", "compressor", dict(A=V("P2", r, **cols), R=V("POOL", 1, m=512, stride=1)), ["P2"],
               ["POOL"], run=run, red=I.RED_SUM)
            su("cmp.pool_bf16", "compressor", dict(A=V("POOL", 512), O=V("LAT0", 512)), ["POOL"], ["LAT0"], run=run,
               rnd=1, dst=I.DST_VM)
            src = "LAT0"
        else:
            src = "cmp"
        self.rmsnorm(su, "cmp.norm", src, 512, "GCN", "LAT", f"{P}attn.compressor.norm.weight", run=run)
        e = self.W(f"{P}attn.indexer.wk.weight", 128, 512, "bf16")
        add(Rec("SM", "MATVEC", param=0, desc=dict(A=V("LAT", 512), B=MDesc(space="HBM", fmt="BF16", base=e["base"],
                                                                             n=512, m=128, stride=e["rowbytes"]),
                                                    O=V("KIN", 128, fmt="BF16")), tag="cmp.indexer_wk",
                family="compressor"), ["LAT"], ["KIN"], run)
        self.rmsnorm(su, "cmp.k_norm", "KIN", 128, "GKN", "KN", f"{P}attn.indexer.k_norm.weight", run=run)
        self.rope_tail(su, "cmp.k_rope", "KN", 128, "KR", inverse=False, run=run, table="ROPE2")
        self.rope_tail(su, "cmp.lat_rope", "LAT", 512, "LR", inverse=False, run=run, table="ROPE2")
        add(Rec("FUSED", "QDQ_FP4_E8M0", desc=dict(A=V("KR", 128), O=V("IK", 128)), tag="cmp.ik_qdq",
                family="compressor"), ["KR"], ["IK"], run)
        add(Rec("FUSED", "QDQ_FP4_E4M3", param=16, desc=dict(A=V("LR", 512), O=V("CK", 512)), tag="cmp.ckv_qdq",
                family="compressor"), ["LR"], ["CK"], run)
        ik = self.W(f"IKSTORE{L}", 1, 128, "fp8", n_experts=1)
        ck = self.W(f"CKSTORE{L}", 1, 512, "fp8", n_experts=1)
        for nm, e, n in (("IK", ik, 128), ("CK", ck, 512)):
            add(Rec("DMA", "STORE", param=grp & 0xFFFFFFFF, desc=dict(
                A=V(nm, n), O=MDesc(space="HBM", fmt="FP32", base=e["base"], n=n)), tag=f"cmp.store_{nm}",
                family="compressor"), [nm], ["kvstore"], run)

    # -- SU templates ----------------------------------------------------------------------------------------------
    def rmsnorm(self, su, tag, x, n, g, out, gname, run=True):
        """dshbm_baseline_measure.lower_rmsnorm as SU records: ss, rsqrt(ss / n + eps), bf16(w * (x * rs))."""
        V = self.lay.V
        su(f"{tag}.gain", tag, dict(A=MDesc(space="HBM", fmt="FP32", base=TBASE + TABLE_OFF[gname], n=n),
                                    O=V(g, n)), [], [g], run=run, dst=I.DST_VM)
        seg = 8 if n % 64 == 0 else 1
        su(f"{tag}.ss", tag, dict(A=V(x, n // seg, m=seg, stride=n // seg), R=V("SS", 1)), [x], ["SS"], run=run,
           red=I.RED_SUM, red_sq=1, red_tree=int(seg > 1), red_whole=int(seg == 1))
        su(f"{tag}.rs", tag, dict(A=V("SS", 1), O=V("RS", 1)), ["SS"], ["RS"], run=run, m1=I.M1_DIVIMM, imm1=f32u(n),
           ad=I.AD_IMM, imm2=f32u(self.m.eps), sfu=I.SFU_RSQRT, dst=I.DST_VM)
        su(f"{tag}.y", tag, dict(A=V(x, n), B=V("RS", n, istride=ISTRIDE_BCAST), C=V(g, n), O=V(out, n)),
           [x, "RS", g], [out], run=run, m1=I.M1_AB, e1=I.E1_MULC, rnd=1, dst=I.DST_VM)

    def rope_tail(self, su, tag, x, n, out, inverse, run=True, src_off=0, table="ROPE"):
        """lower_rope: copy the head, rotate the last 64 as adjacent pairs (cos/sin row from the RoPE table)."""
        V = self.lay.V
        rd = 64
        su(f"{tag}.table", tag, dict(A=MDesc(space="HBM", fmt="FP32", base=TBASE + TABLE_OFF[table], n=64),
                                     O=V(table, 64)), [], [table], run=run, dst=I.DST_VM)
        su(f"{tag}.head", tag, dict(A=V(x, n - rd, off=src_off), O=V(out, n - rd)), [x], [out], run=run,
           dst=I.DST_VM)
        su(f"{tag}.tail", tag, dict(A=V(x, rd, off=src_off + n - rd), B=V(table, rd), D=V(table, rd, off=32),
                                    O=V(out, rd, off=n - rd)), [x, table], [out], run=run, c_pair=1, b_half=1,
           m1=I.M1_AB, qm=I.QM_ALT_PN if inverse else I.QM_ALT_NP, ad=I.AD_Q, rnd=1, dst=I.DST_VM)

    def attend(self, add, su, L, head, yarn):
        V = self.lay.V
        m = self.m
        win = MDesc(space="HBM", fmt="FP32", base=TBASE + TABLE_OFF["WIN"], n=128, m=1, stride=2048)
        T = 128
        att = dict(B=win)
        rd = ["q_own", "WIN"]
        if yarn:
            s_ = m.kv_of[L]
            k = min(m.topk, (self.pos + 1) // m.ratio[L])
            att["C"] = MDesc(space="HBM", fmt="FP32", base=SBASE + SOURCES.index(s_) * SELB, n=k, m=1, stride=2048)
            T += k
            rd.append(f"SELROWS{s_}")
        add(Rec("ATT", "QK", param=1 | (7 << 4), desc=dict(A=V("q_own", 512), O=V("SC", T), **att),
                tag="attend.qk", family="attend"), rd, ["SC"], head)
        sc = f32u(self.m.attn_scale)
        su("attend.max", "attend", dict(A=V("SC", T), R=V("MB", 1)), ["SC"], ["MB"], run=head, m1=I.M1_AIMM,
           imm1=sc, red=I.RED_MAX, red_whole=1)
        su("attend.exp_sum", "attend", dict(A=V("SC", T), B=V("MB", T, istride=ISTRIDE_BCAST), O=V("E", T),
                                            R=V("SE", 1)), ["SC", "MB"], ["E", "SE"], run=head, m1=I.M1_AIMM, imm1=sc,
           ad=I.AD_NEGB, sfu=I.SFU_EXP, red=I.RED_SUM, red_whole=1, dst=I.DST_VM)
        su("attend.bf16_p", "attend", dict(A=V("E", T), O=V("EB", T)), ["E"], ["EB"], run=head, rnd=1,
           dst=I.DST_VM)
        add(Rec("ATT", "PV", param=1 | (7 << 4), desc=dict(A=V("EB", T), O=V("PV", 512), **att),
                tag="attend.pv", family="attend"), ["EB"] + rd[1:], ["PV"], head)
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


hist_of = [None]


def build_tables(m, st, L, pos, rank):
    """Per-die HBM tables (real bytes): gains, RoPE row at the position, the head's sink, gate bias, window ring."""
    P = m.P(L)
    cos, sin = V_.rope_cs(m.freqs_yarn if m.ratio[L] > 0 else m.freqs_plain, pos)
    items = [(f"{P}attn_norm.weight", m.lw(L, "attn_norm.weight")), (f"{P}ffn_norm.weight", m.lw(L, "ffn_norm.weight")),
             (f"{P}attn.q_norm.weight", m.lw(L, "attn.q_norm.weight")),
             (f"{P}attn.kv_norm.weight", m.lw(L, "attn.kv_norm.weight")),
             ("ROPE", np.concatenate([cos, sin])), ("BIAS", m.lw(L, "ffn.gate.bias")),
             ("SINK", m.lw(L, "attn.attn_sink")[rank:rank + 1] if rank < HEADS else np.zeros(1)),
             ("WIN", np.concatenate([np.asarray(st.win[L], F).reshape(-1), np.zeros(512, F)])),
             ("norm.weight", m.w["norm.weight"])]
    if L in m.engram.layer_ids:
        li = m.engram.layer_ids.index(L)
        ids = m.engram.hashes(hist_of[0], li).reshape(-1)             # host-provided per token (G13)
        items += [("EGID", ids.astype(np.uint32).view(F)), ("EGW", G_.mul(m.lw(L, "engram.q_weight"),
                                                                            m.lw(L, "engram.k_weight")))]
    r = m.ratio[L]
    if r > 0 and L == m.kv_of[L]:
        c2, s2 = V_.rope_cs(m.freqs_yarn, pos + 1 - r)
        items += [(f"{P}attn.compressor.norm.weight", m.lw(L, "attn.compressor.norm.weight")),
                  (f"{P}attn.indexer.k_norm.weight", m.lw(L, "attn.indexer.k_norm.weight")),
                  ("ROPE2", np.concatenate([c2, s2]))]
        if r > 1:
            sl = st.slots[L]
            ps = sorted(p for p in sl if p < pos)
            kvs = np.stack([sl[p][0] for p in ps]) if ps else np.zeros((0, 512), F)
            scs = np.stack([sl[p][1] for p in ps]) if ps else np.zeros((0, 512), F)
            items += [("SLOTKV", kvs), ("SLOTSC", scs)]
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
            pre, post, comb = m.hc_mixes(h, r.imm_b, which)       # imm_b: the layer's HC weight set
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

    def rk_of(die):
        if not hasattr(die, "rk"):
            die.rk = W.Rank(die.rank)
        return die.rk

    def vm_to_rk(M, die, desc, name):
        rk_of(die).put(name, M.read(desc, die, 0))

    def index_q(M, r, L):
        for die in M.dies:
            vm_to_rk(M, die, r.desc["A"], "iq")
            vm_to_rk(M, die, r.desc["B"], "iwr")
            golib.f_index_q(rk_of(die), dict(layer=r.imm_b, fn="index_q"))

    def index_scores(M, r, L):
        for die in M.dies:
            golib.f_index_scores(rk_of(die), dict(layer=r.imm_b, fn="index_scores", n=r.imm_a, src=r.param))

    def topk_local(M, r, L):
        for die in M.dies:
            golib.f_topk_local(rk_of(die), dict(layer=r.imm_b, fn="topk_local", k=r.param))

    def select_any(M, r, L):
        sub = r.param & 0xFF
        if sub == 0:
            return select(M, r, L)
        fn = {1: golib.f_cand_local, 2: golib.f_cand_apply, 3: golib.f_cand_mask}[sub]
        for die in M.dies:
            fn(rk_of(die), dict(layer=r.imm_b, n=r.imm_a))

    def topk_merge(M, r, L):
        what = "sel" if r.param == 0 else "cand"
        rks = [rk_of(d) for d in M.dies]
        v = np.concatenate([rk.get(f"{what}_v") for rk in rks])
        i = np.concatenate([rk.get(f"{what}_i") for rk in rks]).astype(np.int64)
        order = np.lexsort((i, -v.astype(np.float64)))[:r.imm_a]
        for rk in rks:
            rk.put(f"{what}_mv", v[order].astype(np.float64), n=len(order))
            rk.put(f"{what}_mi", i[order], n=len(order))
            if what == "sel":
                ss = np.sort(i[order])
                rk.put("sel", ss, n=len(ss))

    def row_gather(M, r, L):
        src, k = r.param, r.imm_a
        sel = rk_of(M.dies[0]).get("sel").astype(np.int64)
        rows = np.asarray(golib.st.ckv[src][sel], dtype=F)
        if len(sel) != k or np.isnan(rows).any():
            raise MC.Fault(1, "row gather: selection size or an unwritten compressed row")
        for d in M.dies[:HEADS]:
            d.hbm.view(SBASE + SOURCES.index(src) * SELB, k * 2048)[:] = rows.reshape(-1).view(np.uint8)

    def qdq4(M, r, L):
        f = V_.qdq_fp4_e8m0 if r.op == "QDQ_FP4_E8M0" else (lambda x: V_.qdq_fp4_e4m3(x, r.param))
        for die in M.dies:
            M.vm_write(r.desc["O"], die, L, f(M.read(r.desc["A"], die, L)))

    base_load, base_store = MC.UNITS[("DMA", "LOAD")], MC.UNITS[("DMA", "STORE")]

    def dma_load(M, r, L):
        a = r.desc["A"]
        if not (a.space == "HBM" and a.base >= WBASE):
            return base_load(M, r, L)
        for die in M.dies:
            base, n, _, _, _ = M.eff(a, die, L)
            e, ex, r0, c0 = man.find(base)
            Lk = int(e["key"][3:])
            codes, sc = m.emb_codes[Lk]
            if e["key"].startswith("EGC"):
                vals = V_.E4M3[np.asarray(codes[np.array([ex])]).reshape(-1)].astype(F)
            else:
                vals = np.exp2(np.asarray(sc[np.array([ex])], dtype=np.float64).reshape(-1)).astype(F)
            M.vm_write(r.desc["O"], die, L, vals)

    def dma_store(M, r, L):
        o = r.desc["O"]
        if not (o.space == "HBM" and o.base >= WBASE):
            return base_store(M, r, L)
        e, _, _, _ = man.find(o.base)
        Ls = int(e["key"][7:])
        grp = r.param
        for die in M.dies:
            v = M.read(r.desc["A"], die, L)
            if e["key"].startswith("IKSTORE"):
                golib.st.ik[Ls][grp] = v
            else:
                golib.st.ckv[Ls][grp] = v
                if golib.st.n[Ls] != grp:
                    raise MC.Fault(1, f"compressor appends group {grp} but the store holds {golib.st.n[Ls]}")
                golib.st.n[Ls] = grp + 1

    def att_rows(M, r, die, L):
        rows = [M.hbm_read(MDesc(space="HBM", fmt="FP32", base=r.desc["B"].base, n=512, m=r.desc["B"].n,
                                 stride=r.desc["B"].stride), die, L)]
        if "C" in r.desc:
            c = r.desc["C"]
            rows.append(M.hbm_read(MDesc(space="HBM", fmt="FP32", base=c.base, n=512, m=c.n, stride=c.stride), die, L))
        return np.concatenate(rows)

    def att_qk2(M, r, L):
        for die in M.dies:
            q = M.read(r.desc["A"], die, L)
            M.vm_write(r.desc["O"], die, L, V_.dots(q.reshape(1, -1), att_rows(M, r, die, L)).reshape(-1))

    def att_pv2(M, r, L):
        for die in M.dies:
            p = M.read(r.desc["A"], die, L)
            M.vm_write(r.desc["O"], die, L, V_.dots(p.reshape(1, -1), att_rows(M, r, die, L).T).reshape(-1))

    def argmax_off(M, r, L):
        for die in M.dies:
            v = M.read(r.desc["A"], die, L)
            j = int(np.argmax(v))
            a = M.vm_addrs(r.desc["O"], die, L, 1, 2)
            die.vm[a[0]] = np.asarray([v[j]], dtype=F).view(np.uint32)[0]
            die.vm[a[1]] = np.uint32(j + r.imm_a)

    U.update({("IDX", "INDEX_Q"): index_q, ("IDX", "INDEX_SCORES"): index_scores, ("IDX", "TOPK_LOCAL"): topk_local,
              ("COLL", "TOPK_MERGE"): topk_merge, ("COLL", "ROW_GATHER"): row_gather,
              ("FUSED", "QDQ_FP4_E8M0"): qdq4, ("FUSED", "QDQ_FP4_E4M3"): qdq4, ("DMA", "LOAD"): dma_load,
              ("DMA", "STORE"): dma_store})
    U.update({("SM", "MATVEC"): sm, ("HC", "HC_MIX"): hc_mix, ("FUSED", "HC_PRE_NORM"): hc_pre_norm,
              ("FUSED", "HC_POST"): hc_post, ("FUSED", "QDQ_FP8"): qdq, ("IDX", "SELECT"): select,
              ("COLL", "ALL_GATHER"): gather, ("COLL", "GROUP_REDUCE_MCAST"): group_reduce,
              ("ATT", "QK"): att_qk2, ("ATT", "PV"): att_pv2, ("ARGMAX", "LOCAL"): argmax_off})
    U[("IDX", "SELECT")] = select_any
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
    ap.add_argument("--head", action="store_true")
    ap.add_argument("--refs", type=Path, default=W.REF_SHARDS)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    feats = getattr(np, "_core", np.core)._multiarray_umath.__cpu_features__
    if feats.get("AVX512F"):
        raise SystemExit("set NPY_DISABLE_CPU_FEATURES (numpy AVX512 float64 trig differs from the reference)")
    t0 = time.time()
    layers = W.parse_layers(a.layers)
    first = layers[0]
    ref = json.loads(W.REF_RECORD.read_text())
    ctx, seed = ref["context"], ref["seed"]
    pos = ctx - 1
    hist = list(ref["token_history"])
    hist_of[0] = hist
    ck = W.LC.Checkpoint()
    m, init_sha = W.LC.build_model(ck, engram=True)
    st = W.State(m, ctx, seed, set(layers))
    golib = W.Executor(m, st, pos, hist, VARIANT)
    lay, man = Layout(), Manifest()
    low = Lower(m, pos, lay, man)
    units = ds_units(m, man, golib)
    dies = [MC.Die(r, MC.Hbm()) for r in range(TP)]
    for d in dies:
        d.rk = W.Rank(d.rank)
    if first == 0:
        h0 = np.repeat(ck.rows("embed.weight", [hist[-1]]), m.hc, axis=0).astype(F)
        pre0 = np.array([1, 0, 0, 0], dtype=F)
    else:                                   # enter at a layer from the reference shards (as ds_roundtrip does)
        prev = np.load(a.refs / f"ctx{ctx}_L{first - 1:02d}.npz")
        h0, pre0 = prev["h_out"], prev["pre_out"]
        carry = json.loads((a.refs / f"ctx{ctx}_L{first - 1:02d}.json").read_text())["ctx_out"]
        for s_ in m.kv_src:
            if s_ < first and s_ in st.n:
                z = np.load(a.refs / f"ctx{ctx}_L{s_:02d}.npz")
                if f"ckv{s_}" in z.files:
                    g = st.n[s_]
                    st.ckv[s_][g], st.ik[s_][g] = z[f"ckv{s_}"], z[f"ik{s_}"]
                    st.n[s_] = g + 1
                    st.slots[s_] = {}
        if "sel" in carry:
            for d in dies:
                d.rk.put("sel", np.array(carry["sel"], dtype=np.int64))
        if "cand_file" in carry:
            cand = np.load(a.refs / carry["cand_file"])["cand"]
            nb = -(-len(cand) // W.KEY_BLOCK)
            for d in dies:
                d.rk.cand = {int(b_): bool(cand[b_ * W.KEY_BLOCK]) for b_ in range(d.rank, nb, TP)}
    for d in dies:
        d.vm[lay.vm["h"]:lay.vm["h"] + HC * D] = np.asarray(h0, F).reshape(-1).view(np.uint32)
        d.vm[lay.vm["PRE"]:lay.vm["PRE"] + 4] = np.asarray(pre0, F).view(np.uint32)
    sel_hbm = {}
    results = []
    for L in list(layers) + (["head"] if a.head else []):
        tl = time.time()
        Lc = m.L if L == "head" else L
        ops = (W.Compiler(m, pos, VARIANT).compile_head() if L == "head"
               else W.Compiler(m, pos, VARIANT).compile_layer(L, first=(L == first)))
        tabs = [build_tables(m, st, min(Lc, m.L - 1), pos, r) for r in range(TP)]
        progs, nbytes = [], 0
        for r in range(TP):
            recs = low.layer(Lc, ops, r)
            b_ = encode_program(recs)
            dec = decode_program(b_)
            assert encode_program(dec) == b_
            for x, y in zip(dec, recs):
                x.tag, x.family = y.tag, y.family
            progs.append(dec)
            nbytes += len(b_)
        for r, d in enumerate(dies):
            old = d.hbm
            d.hbm = MC.Hbm()
            d.hbm.add(TBASE, tabs[r], "TABLES")
            if r not in sel_hbm:
                sel_hbm[r] = np.zeros(SELB * len(SOURCES), dtype=np.uint8)
            d.hbm.add(SBASE, sel_hbm[r], "SELROWS")
        Mach = MC.Machine(dies, units)
        snaps = {}
        watch = {"attn_norm": ("x", D), "kv_row_qdq": ("win_new", 512), "attn_out_gather.y": ("y", D),
                 "ffn_norm": ("x", D), "route.scores_bias": ("router", 384), "ffn_out_gather.yf": ("yf", D),
                 "route.top6": ("rid", 6), "engram.out": ("h", HC * D)}

        def hook(k, r0):
            if r0.tag in watch:
                nm, n = watch[r0.tag]
                snaps[r0.tag] = [d.vm[lay.vm[nm]:lay.vm[nm] + n].copy() for d in dies]
        fault = None
        try:
            run_per_die(Mach, progs, units, pos, hist[-1], hook)
        except Exception as e:                      # noqa: BLE001
            import traceback
            fault = f"{type(e).__name__}: {e} @ {traceback.format_exc().splitlines()[-3].strip()}"
        regs = []
        if L == "head":
            lg = np.zeros(129280, dtype=F)
            for d in dies:
                r0, r1 = W.even(129280)[d.rank]
                lg[r0:r1] = d.vm[lay.vm["logits"]:lay.vm["logits"] + (r1 - r0)].view(F)
            tok = int(dies[0].vm[lay.vm["TOK"] + 4]) if fault is None else -1
            ok = fault is None and tok == ref["next_token"] and W.LC.digest(lg) == ref["logits_sha256"]
            results.append(dict(layer="head", verdict="pass" if ok else "fail", fault=fault, next_token=tok,
                                reference_next_token=ref["next_token"], logits_sha256=W.LC.digest(lg),
                                reference_logits_sha256=ref["logits_sha256"],
                                tokens_agree_all_dies=all(int(d.vm[lay.vm["TOK"] + 4]) == tok for d in dies),
                                records_per_die=len(progs[0]), wall_s=round(time.time() - tl, 1)))
            print(f"head {'PASS' if ok else 'FAIL'} token {tok} fault {fault}", flush=True)
            break
        z = np.load(a.refs / f"ctx{ctx}_L{L:02d}.npz")
        js = json.loads((a.refs / f"ctx{ctx}_L{L:02d}.json").read_text())
        if fault is None:
            def chk(name, want, tag=None, buf=None, n=None):
                got = [(d, (snaps[tag][d] if tag else dies[d].vm[lay.vm[buf]:lay.vm[buf] + n]).view(F))
                       for d in range(TP)]
                regs.append(W.check(name, want, got))
            if f"L{L}.engram" in z.files:
                chk(f"L{L}.engram", z[f"L{L}.engram"], tag="engram.out")
            chk(f"L{L}.attn_norm", z[f"L{L}.attn_norm"], tag="attn_norm")
            chk(f"win{L}", z[f"win{L}"], tag="kv_row_qdq")
            chk(f"L{L}.attn", z[f"L{L}.attn"], tag="attn_out_gather.y")
            chk(f"L{L}.ffn_norm", z[f"L{L}.ffn_norm"], tag="ffn_norm")
            chk(f"L{L}.router", z[f"L{L}.router"], tag="route.scores_bias")
            chk(f"L{L}.ffn", z[f"L{L}.ffn"], tag="ffn_out_gather.yf")
            chk(f"block{L}", z[f"block{L}"], buf="h", n=HC * D)
            chk(f"pre{L}", z[f"pre{L}"], buf="PRE", n=4)
            for s_ in m.kv_src:
                if f"ckv{s_}" in z.files:
                    g = st.n[s_] - 1
                    regs.append(W.check(f"ckv{s_}", z[f"ckv{s_}"], [(-1, st.ckv[s_][g])]))
                    regs.append(W.check(f"ik{s_}", z[f"ik{s_}"], [(-1, st.ik[s_][g])]))
            if f"L{L}.index_scores" in z.files:
                want = z[f"L{L}.index_scores"]
                got = np.full(len(want), np.nan)
                for d in dies:
                    got[d.rk.get("is_i")] = d.rk.get("is_v")
                regs.append(W.check(f"L{L}.index_scores", want, [(-1, got)]))
            if js.get("index_select_sha256"):
                sel = dies[0].rk.get("sel").astype(np.int64)
                ok_s = hashlib.sha256(sel.tobytes()).hexdigest() == js["index_select_sha256"] and \
                    all(np.array_equal(d.rk.get("sel"), dies[0].rk.get("sel")) for d in dies)
                regs.append(dict(region=f"L{L}.index_select", bit_exact=bool(ok_s), ranks_checked=TP))
            ids_ok = all(np.array_equal(snaps["route.top6"][d].astype(np.int64), np.asarray(js["experts"]))
                         for d in range(TP))
            regs.append(dict(region=f"L{L}.experts", bit_exact=bool(ids_ok), ranks_checked=TP))
        ok = fault is None and all(x["bit_exact"] for x in regs)
        fams = {}
        for r_ in progs[0]:
            fams[f"{r_.unit}.{r_.op}"] = fams.get(f"{r_.unit}.{r_.op}", 0) + 1
        results.append(dict(layer=L, kind=js["kind"], verdict="pass" if ok else "fail", fault=fault, regions=regs,
                            records_per_die=len(progs[0]), image_bytes_all_dies=nbytes, unit_ops=fams,
                            wall_s=round(time.time() - tl, 1)))
        print(f"L{L:02d} {js['kind']:28s} {'PASS' if ok else 'FAIL'} records {len(progs[0])} "
              f"{time.time() - tl:.0f} s fault {fault} bad {[x['region'] for x in regs if not x['bit_exact']]}",
              flush=True)
        for k_ in [k_ for k_ in m.w if k_.startswith(f"layers.{L}.")]:
            del m.w[k_]
        if not ok:
            break
    rec = dict(schema="opentallas.hgi_sim.ds_native.v1",
               status="pass" if results and all(x["verdict"] == "pass" for x in results) and
               len(results) == len(layers) + int(a.head) else "fail",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               host=os.uname().nodename, context=ctx, position=pos, layers=a.layers, head=a.head, results=results,
               provisional=["FUSED.QDQ_FP8 / QDQ_FP4_E8M0 / QDQ_FP4_E4M3 (G8)", "COLL.GROUP_REDUCE_MCAST (G10)",
                            "COLL.ROW_GATHER (G14)", "ALL_GATHER even split (G9)", "indexed descriptors (C3b)",
                            "per-die programs of identical structure (G11)", "Engram ids host-provided (G13)",
                            "ATT row list B + C (selected rows continue the window rows, G12)",
                            "window ring read oldest-first from slot 0 (exact at this position; G12 wrap)",
                            "compressor store row from param (DS DYN group index)"],
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
