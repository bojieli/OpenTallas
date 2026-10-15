#!/usr/bin/env python3
"""Exact gate + throughput bench of the S81 SU die master dsfd_sp_su (stream s81-suhc-1011, 2026-10-11).

One RUN drives the master through its dsfd_sp_ctrl engine adapter (controller-clock pulses, QD 8 credits) with a
program over every SU job kind: GQ / GK gain loads, QN (q RMSNorm -> FP8), KV (kv RMSNorm -> RoPE -> FP8 QDQ),
QB (act-quant bank, FP8 and FP4), SW (SwiGLU x route weight -> FP8; the shared expert as w = 1.0), SE (softmax
scores -> e, den) and SO (P.V / den -> inverse RoPE -> BF16), SE / SO on job slot 1, the rest on slot 0.  The expected
VM image is the CPU golden (tools/hdc_golden_v41 through dsrom_su_norm.golden_row, dsrom_su_swiglu.golden_swiglu,
dsrom_su_softmax.reference, rtl_hdc_v41_blockdot_campaign.aq_expect).  Golden runs take the 1M token's q / kv rows,
gains, eps and RoPE table (su_cases pickle L0 / L2 q_norm_kv_row, asserted against the case checks); stress operands
cover the rest (signed zeros, subnormals, clamp edges, wide exponents).

    python3 tools/s81_suhc/su_gate.py prep --cases su_cases.pkl --out DIR [--shape reduced|full]
    python3 tools/s81_suhc/su_gate.py run  --out DIR [--shape ...] [--mut M] [--amut A] [--fp dpi|rtl]
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import pickle
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/s81_suhc"))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import hc_gate as H                                          # noqa: E402

F = np.float32
SHAPES = dict(reduced=dict(QN_N=64, KV_N=512, QB_NB=4, SW_W=64, SM_H=2, SM_LPH=16, SM_NVMAX=40, S_RD=2, S_WR=4),
              # reduced with S_RD == 2 QB blocks a pass (L = S_RD): exercises the full shape's aligned QB tap at reduced cost
              reduced_al=dict(QN_N=64, KV_N=512, QB_NB=4, SW_W=64, SM_H=2, SM_LPH=16, SM_NVMAX=40, S_RD=4, S_WR=4),
              full=dict(QN_N=256, KV_N=512, QB_NB=32, SW_W=1024, SM_H=16, SM_LPH=16, SM_NVMAX=40, S_RD=16, S_WR=16))
# the DS HBM SU case set the golden runs draw on: tools/dshbm_baseline_measure.py prep (snapshots sha256 cd0fc866...)
# -> tools/dshbm_chain_levers.py prep (_il) -> prep2 (_ildr); recorded in results/rtl/hbm_su_fused_compiler_20261005/v2_ildr.json
CASES_SHA256 = "8c18c0655ccf6a147cde5e8a65e709ad5ccfd62ba9024e2644019289cd8d2108"
K = dict(QN=0, KV=1, QB=2, SW=3, SE=4, SO=5, GQ=6, GK=7, RA=8, RB=9, QR=10, RW=11, CN=12, IK=13)
RTL = ["rtl/dsrom_sys/s81_suhc/ot_s81_su_core.sv", "rtl/dsrom_sys/s81_suhc/ot_s81_su_rx.sv", "rtl/dsrom_sys/s81_suhc/ot_s81_su_rw.sv",
       "rtl/hdc/v41x/ot_hdc_v41x_spshort.sv", "rtl/dsrom_sys/s81_suhc/dsfd_sp_su.sv",
       "rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv", "rtl/lib/ot_async_fifo.sv", "rtl/lib/ot_reset_sync.sv",
       "rtl/hdc/v41x/ot_dsrom_su_norm.sv", "rtl/hdc/v41x/ot_dsrom_su_swiglu.sv", "rtl/hdc/v41x/ot_dsrom_su_f12.sv",
       "rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv", "rtl/hdc/v41x/ot_dsrom_su_softmax.sv",
       "rtl/hdc/v41x/ot_dsrom_su_softmax_add.sv", "rtl/hdc/v41x/ot_dsrom_su_softmax_add6.sv",
       "rtl/hdc/v41x/ot_dsrom_su_softmax_exp6.sv", "rtl/hdc/v41x/ot_dsrom_su_softmax_f12r.sv",
       "rtl/hdc/v41x/ot_dsrom_su_softmax_m9.sv", "rtl/hdc/v41x/ot_dsrom_su_add6.sv",
       "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/v41/ot_hdc_fsqrt.sv",
       "rtl/hdc/v41/ot_hdc_fdiv.sv", "rtl/hdc/v41/ot_hdc_softplus.sv", "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv",
       "rtl/hdc/v41/ot_hdc_actquant.sv", "rtl/hdc/v41x/ot_dsrom_aq12.sv", "rtl/hdc/v41x/ot_dsrom_divc.sv"]
TB = "rtl/dsrom_sys/s81_suhc/test/tb_s81_su_master.sv"
# the hierarchical slab (s81-suhc-hier-1011): control tile + engine tiles on registered chains, same pins
HIER = ["rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_hctl.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_ctl.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_norm_lg.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_tile.sv",
        "rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_qb.sv", "rtl/hdc/ot_sram_dline.sv",
        "rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sw.sv",
        "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v",
        "rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_qn.sv", "rtl/hdc/ot_sram_bank.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_kv.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv",
        "physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v",
        "rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_cn_ik.sv", "rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv",
        "rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxt.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxh.sv", "rtl/dsrom_sys/s81_suhc/hier/dsfd_sp_su_h.sv"]
u32, f32, pack, bf16bits = H.u32, H.f32, H.pack, H.bf16bits


def aq(y, fp4=False):
    import rtl_hdc_v41_blockdot_campaign as BC
    out = []
    for b in np.asarray(y, F).reshape(-1, 32):
        f_, e, codes, yy = BC.aq_expect(b, fp4)
        assert f_ == 0
        out.append((e & 0x3FF, list(codes), list(yy)))
    return out


def rows_of(words):
    w = u32(words)
    assert len(w) % 16 == 0
    return [pack(w[16 * r:16 * r + 16], 32) for r in range(len(w) // 16)]


class Run:
    def __init__(self, sh):
        self.sh = sh
        self.vm, self.exp, self.prog = {}, {}, []
        self.jexp = {}                                     # op -> (first expected row, count): the done-time check
        self.top = 64                                      # next free VM row

    def alloc(self, n):
        a = self.top
        self.top += (n + 15) // 16 * 16
        assert self.top < 16384
        return a

    def put(self, rows):
        a = self.alloc(len(rows))
        for i, r in enumerate(rows):
            self.vm[a + i] = r
        return a

    def job(self, kind, slot, dbase, gsel=0, fp4=0):
        op = len(self.prog)
        arg = (K[kind] << 20) | (gsel << 18) | (fp4 << 14) | dbase
        self.prog.append((slot << 83) | (arg << 7) | op)

    def desc(self, out, inb, cnt=0, w3=0, w4=0, extra=(), prow=()):
        words = [out, inb, cnt, w3, w4] + list(extra)
        words += [0] * (16 - len(words))
        return self.put([pack(words, 32)] + list(prow))

    def expect(self, base, rows):
        self.jexp[len(self.prog) - 1] = (base, len(rows))   # the job just issued owns these rows
        for i, r in enumerate(rows):
            self.exp[base + i] = r

    def aq_rows(self, blocks, n, fp4=False):
        """per vector of n elements: codes, exps, (no y)"""
        codes, exps = [], []
        for v in range(len(blocks) * 32 // n):
            blk = blocks[v * (n // 32):(v + 1) * (n // 32)]
            if fp4:
                cr = [pack([c for b in blk[4 * r:4 * r + 4] for c in (b[1] + [0] * 0)], 4) for r in range(len(blk) // 4)]
            else:
                cr = [pack([c for b in blk[2 * r:2 * r + 2] for c in b[1]], 8) for r in range(len(blk) // 2)]
            codes.append(cr)
            exps.append(pack([b[0] for b in blk], 16))
        return codes, exps

    # ------------------------------------------------------------------ jobs
    def gain(self, kind, gsel, w):
        a = self.put(rows_of(w))
        d = self.desc(0, a)
        self.job(kind, 0, d, gsel=gsel)

    def qn(self, x, w, eps, gsel):
        import dsrom_su_norm as NM
        y, _ = NM.golden_row("q", x, np.zeros(4, F), w, eps)
        n = self.sh["QN_N"]
        a = self.put(rows_of(x))
        out = self.alloc((1280 // n) * (n // 64 + 1))
        self.job("QN", 0, self.desc(out, a, 0, int(u32([eps])[0])), gsel=gsel)
        codes, exps = self.aq_rows(aq(y), n)
        rows = []
        for c, e in zip(codes, exps):
            rows += c + [e]
        self.expect(out, rows)
        return y

    def kv(self, x, w, eps, cos, sin, gsel):
        import dsrom_su_norm as NM
        y, ro = NM.golden_row("kv", x, np.zeros(4, F), w, eps, (cos, sin))
        a = self.put(rows_of(x))
        out = self.alloc(512 // 64 + 1 + 512 // 32)
        prow = rows_of(np.concatenate([cos, sin]))
        self.job("KV", 0, self.desc(out, a, 0, int(u32([eps])[0]), prow=prow), gsel=gsel)
        q = aq(ro)
        codes, exps = self.aq_rows(q, 512)
        yrows = [pack(b[2], 16) for b in q]
        self.expect(out, codes[0] + [exps[0]] + yrows)
        return ro

    def qb(self, x, fp4):
        nb = self.sh["QB_NB"]
        beats = len(x) // (32 * nb)
        a = self.put(rows_of(x))
        per = nb // 2 + 1 + nb
        out = self.alloc(beats * per)
        self.job("QB", 0, self.desc(out, a, beats), fp4=fp4)
        q = aq(x, bool(fp4))
        rows = []
        for bt in range(beats):
            blk = q[bt * nb:(bt + 1) * nb]
            rows += [pack([c for b in blk[2 * r:2 * r + 2] for c in b[1]], 8) for r in range(nb // 2)]
            rows.append(pack([b[0] for b in blk], 16))
            rows += [pack(b[2], 16) for b in blk]
        self.expect(out, rows)

    def sw(self, g, u, wv, lim, weights_from_rw=False):
        """weights_from_rw (s81-ftok r3, F11): the descriptor's routing-weight words start ZERO; an RW job writes them
        (rw() below) before this job runs.  Returns the descriptor row."""
        import dsrom_su_swiglu as SG
        W = self.sh["SW_W"]
        nvec = len(g) // W
        inter = []
        for v in range(nvec):
            inter.append(g[v * W:(v + 1) * W]); inter.append(u[v * W:(v + 1) * W])
        a = self.put(rows_of(np.concatenate(inter)))
        out = self.alloc(nvec * (W // 64 + 1 + W // 32))
        drow = self.desc(out, a, nvec, int(u32([lim])[0]), 0, extra=[0] * len(wv) if weights_from_rw else list(u32(wv)))
        self.sw_desc = (drow, [out, a, nvec, int(u32([lim])[0]), 0] + list(u32(wv)))
        self.job("SW", 0, drow)
        act = SG.golden_swiglu(g, u, np.repeat(wv, W).astype(F), lim)
        q = aq(act)
        rows = []
        for v in range(nvec):
            blk = q[v * (W // 32):(v + 1) * (W // 32)]
            rows += [pack([c for b in blk[2 * r:2 * r + 2] for c in b[1]], 8) for r in range(W // 64)]
            rows.append(pack([b[0] for b in blk], 16))
            rows += [pack(b[2], 16) for b in blk]                       # the QDQ BF16 (qdq_fp8) of each block
        self.expect(out, rows)

    def softmax(self, s_raw, scale, sink, pv, cos, sin):
        import dsrom_su_softmax as SM
        Hh, lph = self.sh["SM_H"], self.sh["SM_LPH"]
        T = s_raw.shape[1]
        if T < 1 or s_raw.shape[0] != Hh or not np.isfinite(scale) or scale <= 0:
            raise ValueError("softmax requires nonempty scores, the target head count, and positive finite scale")
        nv = (T + lph - 1) // lph
        if nv > self.sh["SM_NVMAX"]:
            raise ValueError("softmax score row exceeds the physical score store")
        lt = int(np.ceil(np.log2(nv))) if nv > 1 else 0
        SM.H, SM.ROW = Hh, 512
        ref = SM.reference(s_raw, scale, sink, pv, cos, sin)

        def lanes(m, v):
            return np.concatenate([m[h, v * lph:(v + 1) * lph] for h in range(Hh)])
        # Partial vectors have -Inf inactive scores. Real RTL retains these in
        # max and masks the exp output to +0 (exp's -87 clamp is NOT a mask).
        padded = np.full((Hh, nv * lph), -np.inf, F)
        padded[:, :T] = s_raw
        a = self.put([r for v in range(nv) for r in rows_of(lanes(padded, v))])
        out = self.alloc(nv * Hh * lph // 16)
        sinkrow = rows_of(np.concatenate([sink, np.zeros((-len(sink)) % 16, F)]))
        self.job("SE", 1, self.desc(out, a, nv, int(u32([scale])[0]), lt, prow=sinkrow))
        e = np.zeros((Hh, nv * lph), F)
        e[:, :T] = np.asarray(ref["e"], F)
        self.expect(out, [r for v in range(nv) for r in rows_of(lanes(e, v))])
        b = self.put([r for uu in range(512 // lph) for r in rows_of(lanes(pv, uu))])
        out2 = self.alloc((512 // lph) * Hh * lph // 32)
        prow = rows_of(np.concatenate([cos, sin]))
        self.job("SO", 1, self.desc(out2, b, 0, prow=prow))
        ob = bf16bits(np.asarray(ref["o"], F))
        orows = []
        for uu in range(512 // lph):
            lv = lanes(ob, uu)
            orows += [pack(lv[32 * r:32 * r + 32], 16) for r in range(len(lv) // 32)]
        self.expect(out2, orows)

    # ---------------------------------------------------------------- die item F1 (s81-functional-token 2026-10-14)
    def expect_at(self, addrs, rows):
        """expected rows at explicit (strided) addresses; the job's rows must be consecutive in address order among
        the expected rows (the done-time check takes the first one and a count)"""
        self.jexp[len(self.prog) - 1] = (min(addrs), len(rows))
        for a_, r_ in zip(addrs, rows):
            self.exp[a_] = r_

    def ra(self, x):
        """ffn.softplus_sqrt: r = sqrt(softplus(x)) of the die's router scores (rows of 16 binary32)"""
        import hdc_golden_v41 as V
        x = np.asarray(x, F)
        a = self.put(rows_of(x))
        out = self.alloc(len(x) // 16)
        self.job("RA", 0, self.desc(out, a, len(x) // 16))
        self.expect(out, rows_of(V.sqrt(V.softplus(x))))

    def rb(self, sc, bias):
        """ffn.bias: scores + bias (golden add); the layer's bias rows sit directly after the score rows"""
        import hdc_golden_v41 as V
        sc, bias = np.asarray(sc, F), np.asarray(bias, F)
        a = self.put(rows_of(sc) + rows_of(bias))
        out = self.alloc(len(sc) // 16)
        self.job("RB", 0, self.desc(out, a, len(sc) // 16))
        self.expect(out, rows_of(V.add(sc, bias)))

    def qr(self, q, cos, sin):
        """attn.q_rope: rope_tail of each q head (heads x 512 binary32), rotated in place (out_base = in_base)"""
        import hdc_golden_v41 as V
        q = np.asarray(q, F)
        heads = q.shape[0]
        a = self.put(rows_of(q.reshape(-1)))
        prow = rows_of(np.concatenate([cos, sin]))
        self.job("QR", 0, self.desc(a, a, heads, prow=prow))
        ro = V.rope_tail(q, (cos, sin))
        addrs, rows = [], []
        for h in range(heads):
            rr = rows_of(ro[h])
            for j in range(4):
                addrs.append(a + 32 * h + 28 + j); rows.append(rr[28 + j])
        self.expect_at(addrs, rows)

    def rw(self, scores, ids, route_scale, target):
        """ffn.weights (s81-ftok r3, die item F11): w_j = (scores[ids[j]] / (seqsum(scores[ids]) + 1e-20)) * route_scale,
        written into words 5 .. 5+k-1 of the routed SW job's descriptor row `target` = (row, its full word list).
        Operand rows: the ids row (word j = id j) directly followed by the score rows."""
        import hdc_golden_v41 as V
        sc = np.asarray(scores, F)
        ids = [int(i) for i in ids]
        tot = V.seqsum([sc[i] for i in ids])
        den = V.add(tot, F(1e-20))
        w = np.asarray([V.mul(V.div(sc[i], den), F(route_scale)) for i in ids], F)
        a = self.put([pack(ids + [0] * (16 - len(ids)), 32)] + rows_of(sc))
        self.job("RW", 0, self.desc(target[0], a, 1 + len(sc) // 16, int(u32([route_scale])[0]), 5, extra=[len(ids)]))
        words = list(target[1])
        words[5:5 + len(ids)] = list(u32(w))
        words += [0] * (16 - len(words))
        self.expect(target[0], [pack(words, 32)])
        return w

    def cn(self, x, w, eps, cos, sin):
        """CN512 norm->RoPE64->E4M3 FP4/16. Also writes pre-RoPE norm for field cmp.wk."""
        import hdc_golden_v41 as V
        x,w=np.asarray(x,F),np.asarray(w,F)
        if x.shape!=(512,) or w.shape!=(512,):raise ValueError("CN requires512 elements")
        self.gain("GK",3,w)
        a=self.put(rows_of(x));out=self.alloc(32);normout=self.alloc(16)
        self.job("CN",0,self.desc(out,a,normout,int(u32([eps])[0]),prow=rows_of(np.concatenate([cos,sin]))),gsel=3)
        y=V.rmsnorm_bf16(x,w,F(eps));ro=V.rope_tail(y,(cos,sin));qd=V.qdq_fp4_e4m3(ro,16)
        self.expect(out,[pack(bf16bits(qd)[32*i:32*i+32],16) for i in range(16)])
        import rtl_hdc_v41_blockdot_campaign as BC
        blocks=np.asarray(ro,F).reshape(-1,16)
        amax=np.maximum(np.max(np.abs(blocks),axis=1),V.FP4_AMAX_FLOOR_E4M3).astype(F)
        scales_f=np.minimum(V._e4m3_round(amax.astype(np.float64)/V.FP4_MAX),448.0)
        mag=np.abs(blocks.astype(np.float64));code=np.zeros(mag.shape,dtype=np.int64)
        for k,m in enumerate(V.E2M1_MIDPOINTS):
            threshold=m*scales_f[:,None]
            code=np.where((mag>threshold)|((mag==threshold)&((k+1)%2==0)),k+1,code)
        codes=(code+8*np.signbit(blocks)).reshape(-1)
        scales=BC.e4m3_codes(scales_f)
        for i in range(16):
            self.exp[out+16+i]=pack(codes[32*i:32*i+32],4)|(int(scales[2*i])<<128)|(int(scales[2*i+1])<<136)
            self.exp[normout+i]=pack(bf16bits(y)[32*i:32*i+32],16)
        self.jexp[len(self.prog)-1]=(out,48)
        return dict(qdq_base=out,raw_base=out+16,norm_base=normout)

    def ik(self, x, w, eps, cos, sin):
        """IK128: logical lane0 maps to physical384 in shared KV; divisor remains128."""
        import hdc_golden_v41 as V
        x,w=np.asarray(x,F),np.asarray(w,F)
        if x.shape!=(128,) or w.shape!=(128,):raise ValueError("IK requires128 elements")
        xx=np.concatenate([np.zeros(384,F),x]);ww=np.concatenate([np.zeros(384,F),w])
        self.gain("GK",0,ww)
        a=self.put(rows_of(xx));out=self.alloc(8)
        self.job("IK",0,self.desc(out,a,0,int(u32([eps])[0]),prow=rows_of(np.concatenate([cos,sin]))),gsel=0)
        y=V.rmsnorm_bf16(x,w,F(eps));ro=V.rope_tail(y,(cos,sin));qd=V.qdq_fp4_e8m0(ro,32)
        self.expect(out,[pack(bf16bits(qd)[32*i:32*i+32],16) for i in range(4)])
        for i,(e,codes,_) in enumerate(aq(ro,True)):
            self.exp[out+4+i]=pack(codes,4)|((int(e)+127)&255)<<128
        self.jexp[len(self.prog)-1]=(out,8)
        return dict(qdq_base=out,raw_base=out+4)

    def write(self, d, meta):
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "vm.mem", "w") as f:
            for a_ in sorted(self.vm):
                f.write(f"@{a_:x}\n{self.vm[a_]:0128x}\n")
        with open(d / "expa.mem", "w") as fa, open(d / "expd.mem", "w") as fd:
            for a_ in sorted(self.exp):
                fa.write(f"{a_:04x}\n")
                fd.write(f"{self.exp[a_]:0128x}\n")
        # per op: index of its first expected row in expa.mem order (rows sorted by address) and its row count; the bench
        # checks at the core's done pulse that every one of them is already in the VM with its expected value (the
        # done contract: done fires when the job's last result row has been issued; a consumer may read on done)
        order = {a_: i for i, a_ in enumerate(sorted(self.exp))}
        (d / "jexp.mem").write_text("".join(
            f"{(order[self.jexp[j][0]] if j in self.jexp else 0):08x}{(self.jexp[j][1] if j in self.jexp else 0):08x}\n"
            for j in range(len(self.prog))))
        (d / "prog.mem").write_text("".join(f"{p:021x}\n" for p in self.prog))
        (d / "n.mem").write_text(f"{len(self.prog):08x}\n{len(self.exp):08x}\n00000000\n")
        (d / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")


def build_run(sh, rng, gold=None):
    import hdc_golden_v41 as V
    r = Run(sh)
    if gold is not None:
        c = gold
        init = dict(c["init"])
        xq, xk = init[64], init[2640]
        wq, wk = f32(c["cr_lo"][0:1280]), f32(c["cr_lo"][1280:1792])
        cos, sin = f32(c["cr_lo"][1792:1824]), f32(c["cr_hi"][1792:1824])
        eps = f32([c["ops"][2]["imm2"]])[0]
    else:
        xq = V.to_bf16((rng.standard_normal(1280) * 3).astype(F)); xk = V.to_bf16((rng.standard_normal(512) * 0.2).astype(F))
        xq[:4] = [0.0, -0.0, 1e-40, -3e-39]
        wq = V.to_bf16((rng.standard_normal(1280) * 0.3 + 1).astype(F)); wk = V.to_bf16((rng.standard_normal(512) * 0.3 + 1).astype(F))
        ang = rng.random(32) * 6.28
        cos, sin = np.cos(ang).astype(F), np.sin(ang).astype(F)
        eps = F(1e-6)
    r.gain("GQ", 1, wq)
    r.gain("GK", 2, wk)
    yq = r.qn(xq, wq, eps, 1)
    ro = r.kv(xk, wk, eps, cos, sin, 2)
    if gold is not None:
        chk = {lab: np.asarray(w, np.uint32) for lab, _a, w, _k in gold["checks"]}
        labs = list(chk)
        assert np.array_equal(u32(yq), chk[labs[0]]), "q norm vs case check"
        assert np.array_equal(u32(ro)[-64:], chk[labs[1]][-64:]) or np.array_equal(u32(ro), chk[labs[1]]), "kv rope vs check"
    nb = sh["QB_NB"]
    for fp4 in (0, 1):
        e = rng.integers(-130, 40, size=(2 * nb, 1))
        x = (rng.standard_normal((2 * nb, 32)) * np.exp2(e)).astype(F)
        x[0] = 0.0; x[1] = -0.0
        r.qb(x.reshape(-1), fp4)
    W = sh["SW_W"]
    lim = F(10.0)
    sc = rng.choice([1e-3, 0.1, 1.0, 4.0, 12.0, 120.0], size=4 * W).astype(F)
    g = V.to_bf16((rng.standard_normal(4 * W) * sc).astype(F)); u = V.to_bf16((rng.standard_normal(4 * W) * sc).astype(F))
    g[:8] = [0.0, -0.0, lim, -lim, 87.0, -87.0, -100.0, 1e-40]
    wv = np.array([0.37, 1.0, 2.5, 0.0], F)                    # 1.0: the shared expert, exact
    r.sw(g, u, wv, lim)
    # die item F11 (RW): a routed SW whose routing weights an RW job writes into its descriptor first
    nsc = 384 if sh["S_RD"] >= 16 else 128
    scr = np.abs(rng.standard_normal(nsc) * rng.choice([0.01, 1.0, 3.0], nsc)).astype(F)
    rid = sorted(int(i) for i in rng.choice(nsc, 4, replace=False))
    import hdc_golden_v41 as V
    tot = V.seqsum([scr[i] for i in rid]); den = V.add(tot, F(1e-20))
    wv2 = np.asarray([V.mul(V.div(scr[i], den), F(2.5)) for i in rid], F)
    g2, u2 = g[:4 * W].copy(), u[:4 * W].copy()
    r.sw(g2, u2, wv2, lim, weights_from_rw=True)
    sw_job = r.prog.pop()                                     # issue order: RW first, then its SW
    jx = r.jexp.pop(len(r.prog), None)
    w_rw = r.rw(scr, rid, F(2.5), r.sw_desc)
    assert np.array_equal(u32(w_rw), u32(wv2))
    r.prog.append((sw_job & ~0x7F) | len(r.prog))
    if jx is not None:
        r.jexp[len(r.prog) - 1] = jx
    Hh = sh["SM_H"]
    for T in (128, 133, 640):
        s_raw = (rng.normal(0, 1, (Hh, T)) * rng.choice([1, 30, 1e3], (Hh, T))).astype(F)
        s_raw[:, 5] = s_raw.max(axis=1)
        pv = (rng.normal(0, 1, (Hh, 512)) * rng.choice([1e-3, 1, 50], (Hh, 512))).astype(F)
        sink = rng.normal(0, 3, Hh).astype(F)
        r.softmax(s_raw, F(0.0441941738), sink, pv, cos, sin)
    # die item F1: RA / RB / QR at the die's production counts (full: 96 scores = 6 rows, 384 = 24 rows, 16 q heads;
    # reduced: within its beat store of 32 rows)
    full = sh["S_RD"] >= 16
    nra, nrb, nh = (96, 384, 16) if full else (32, 128, 8)
    xr = (rng.standard_normal(nra) * rng.choice([0.05, 1.0, 4.0, 30.0], nra)).astype(F)
    xr[:8] = [0.0, -0.0, 1e-40, -1e-40, 88.0, -88.0, 20.0, -20.0]
    r.ra(xr)
    scs = np.abs(rng.standard_normal(nrb)).astype(F)
    bias = (rng.standard_normal(nrb) * 0.01).astype(F)
    scs[:4] = [0.0, 1e-38, 3.0, 0.5]; bias[:4] = [-0.0, -1e-38, -3.0, 0.0]
    r.rb(scs, bias)
    qh = (rng.standard_normal((nh, 512)) * rng.choice([1e-3, 1.0, 40.0], (nh, 512))).astype(F)
    qh[0, -64:-60] = [0.0, -0.0, 1e-40, -3e-39]
    r.qr(qh, cos, sin)
    return r


def cmd_prep(a):
    sh = SHAPES[a.shape]
    out = Path(a.out)
    if H.sha(a.cases) != CASES_SHA256:
        sys.exit(f"{a.cases}: sha256 {H.sha(a.cases)} is not the pinned su_cases_v2_ildr.pkl {CASES_SHA256}")
    cases = pickle.loads(Path(a.cases).read_bytes())
    by = {c["name"]: c for c in cases["cases"]}
    rng = np.random.default_rng(20261011)
    runs = [("golden_L0", by["L0.q_norm_kv_row"]), ("golden_L2", by["L2.q_norm_kv_row"]), ("stress_0", None)]
    rows = []
    for name, g in runs:
        r = build_run(sh, rng, g)
        meta = dict(run=name, shape=a.shape, jobs=len(r.prog), exp_rows=len(r.exp), cases_sha256=H.sha(a.cases))
        r.write(out / "runs" / name, meta)
        rows.append(meta)
        print(name, meta["jobs"], "jobs", meta["exp_rows"], "rows")
    (out / "runs.json").write_text(json.dumps(dict(runs=rows, shape=a.shape, params=sh), indent=1) + "\n")
    return 0


SUG = re.compile(r"SUG jobs=(\d+) done=(\d+) err=(\d+) rows=(\d+) fault=(\d+) code=(\d+) cyc=(\d+) bad_tag=(\d+) early=(\d+)")
JOB = re.compile(r"SUJ op=(\d+) kind=(\d+) start=(-?\d+) done=(-?\d+)")


def cmd_run(a):
    sh = SHAPES[a.shape]
    out = Path(a.out)
    tag = f"{a.shape}_{a.fp}_m{a.mut}_a{a.amut}" + (f"_x{a.xmut}" if a.xmut else "") + ("_h" if a.hier else "") + ("_t" if a.tiles else "") + (f"_lvm{a.lvm}" if a.lvm else "")
    rtl = RTL + (HIER if a.hier else [])
    gen = []
    if a.tiles:        # gate s81su_tiles: the slab with the ROUTED tops dsfd_su_t_<x> in place of the cores (su_tile_tops.py)
        import su_tile_tops as TT
        if not a.hier or a.mut or a.amut:
            sys.exit("--tiles needs --hier and no --mut/--amut (the routed tops carry no mutant parameter; use --tmut)")
        text, man = TT.build()
        (out / "tile_tops").mkdir(parents=True, exist_ok=True)
        if not (out / "tile_tops/dsfd_sp_su_h_tt.sv").exists() or (out / "tile_tops/dsfd_sp_su_h_tt.sv").read_text() != text:
            (out / "tile_tops/dsfd_sp_su_h_tt.sv").write_text(text)
        (out / "tile_tops/tile_tops.json").write_text(json.dumps(man, indent=1) + "\n")
        rtl = [s_ for s_ in rtl if s_ != TT.SLAB] + TT.WRAP
        gen = [out / "tile_tops/dsfd_sp_su_h_tt.sv"]
    obj = out / f"build_{tag}"
    exe = obj / "Vtb_s81_su_master"
    source_pins = {s: H.sha(ROOT / s) for s in H.FP[a.fp] + rtl + [TB]}
    cache_identity = dict(source_sha256=source_pins, params=sh,
                          extra_defines=os.environ.get("OT_SU_VDEFS", ""),
                          generated={str(p):H.sha(p) for p in gen})
    cache_file = obj / "build_sources.json"
    cache_matches = cache_file.exists() and json.loads(cache_file.read_text()) == cache_identity
    if not exe.exists() or not cache_matches:
        obj.mkdir(parents=True, exist_ok=True)
        srcs = [ROOT / s for s in H.FP[a.fp] + rtl] + gen + [ROOT / TB]
        if a.fp == "dpi":
            srcs = H.dpi_rest(obj) + srcs
        cmd = [H.VERILATOR, "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "--top-module", "tb_s81_su_master",
               "-Mdir", str(obj), "-j", "16", "--unroll-count", "4", "-fno-dfg", *[f"-G{k}={v}" for k, v in sh.items()],
               f"-GMUT={a.mut}", f"-GAMUT={a.amut}", *([f"-GXMUT={a.xmut}"] if a.xmut else []), *([f"-GLVM={a.lvm}"] if a.lvm else []), *(["-DSU_HIER"] if a.hier else []), *(["-DSU_TILE_TOPS"] if a.tiles else []), *os.environ.get("OT_SU_VDEFS", "").split(), *map(str, srcs), "-CFLAGS", "-O1"]
        rr = subprocess.run(cmd, capture_output=True, text=True)
        (out / f"build_{tag}.log").write_text(" ".join(cmd) + "\n" + rr.stdout + rr.stderr)
        if rr.returncode != 0:
            sys.exit(f"build failed: {out}/build_{tag}.log")
        if source_pins != {s:H.sha(ROOT / s) for s in source_pins}:
            sys.exit("source changed during SU build; refusing an unbound result")
        cache_file.write_text(json.dumps(cache_identity,sort_keys=True,indent=1)+"\n")
    res = []
    for meta in json.loads((out / "runs.json").read_text())["runs"]:
        d = out / "runs" / meta["run"]
        rr = subprocess.run([str(exe)] + ([f"+tmut={a.tmut}"] if a.tiles else []), cwd=d, capture_output=True, text=True)
        if a.tiles:
            tt = [x for x in rr.stdout.splitlines() if "SU_TILE_TOPS" in x and "tmut=" not in x]
            if tt:
                print("\n".join(tt[:60]), flush=True)
        m = SUG.search(rr.stdout)
        jobs = [dict(op=int(x[0]), kind=int(x[1]), start=int(x[2]), done=int(x[3])) for x in JOB.findall(rr.stdout)]
        if not m:
            res.append(dict(run=meta["run"], ok=False, tail=(rr.stdout + rr.stderr)[-3000:]))
            print(meta["run"], "NO RESULT", flush=True)
            continue
        g = list(map(int, m.groups()))
        row = dict(run=meta["run"], jobs=g[0], done=g[1], err_rows=g[2], rows=g[3], fault=g[4], fault_code=g[5],
                   cycles=g[6], bad_tag=g[7], early_done_rows=g[8], ok=("SUG PASS" in rr.stdout), job_cycles=jobs,
                   mismatches=[x for x in rr.stdout.splitlines() if "mismatch" in x][:5])
        res.append(row)
        print(meta["run"], "PASS" if row["ok"] else "FAIL", row["err_rows"], "/", row["rows"], "done", row["done"], "/",
              row["jobs"], "fault", row["fault"], row["fault_code"], "cyc", row["cycles"],
              "early", row["early_done_rows"], flush=True)
    rec = dict(schema="opentallas.s81_suhc.su_gate.run.v1", generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               shape=a.shape, params=sh, fp=a.fp, mut=a.mut, amut=a.amut, xmut=a.xmut, hier=bool(a.hier), lvm=(a.lvm or 10), runs=res,
               status="pass" if res and all(x["ok"] for x in res) else "fail",
               source_sha256=source_pins, build_cache_source_bound=True)
    if a.tiles:
        tag += str(a.tmut)
        rec.update(tiles=True, tmut=a.tmut, tile_tops=json.loads((out / "tile_tops/tile_tops.json").read_text()),
                   slab_tt_sha256=H.sha(out / "tile_tops/dsfd_sp_su_h_tt.sv"))
    if source_pins != {s:H.sha(ROOT / s) for s in source_pins}:
        sys.exit("source changed during SU simulation; refusing an unbound result")
    (out / f"run_{tag}.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("RUN", tag, rec["status"])
    return 0 if rec["status"] == "pass" else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prep")
    p.add_argument("--cases", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--shape", default="reduced")
    p = sp.add_parser("run")
    p.add_argument("--out", required=True)
    p.add_argument("--shape", default="reduced")
    p.add_argument("--fp", default="dpi")
    p.add_argument("--mut", type=int, default=0)
    p.add_argument("--amut", type=int, default=0)
    p.add_argument("--hier", action="store_true", help="the hierarchical slab dsfd_sp_su_h")
    p.add_argument("--tiles", action="store_true", help="the slab built from the ROUTED tile tops dsfd_su_t_<x> (su_tile_tops.py)")
    p.add_argument("--lvm", type=int, default=0, help="VM read latency of the bench VM (tb LVM; 0 = the bench default 10): "
                   "measures how many serial VM read round trips a job class holds")
    p.add_argument("--xmut", type=int, default=0, help="ot_s81_su_rx negative control (1 RA sp, 2 RB no bias, 3 QR inverse, "
                   "4 RW no route_scale)")
    p.add_argument("--tmut", type=int, default=0, help="with --tiles: output mutant of tile class K (+tmut=K, no rebuild)")
    a = ap.parse_args()
    return dict(prep=cmd_prep, run=cmd_run)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
