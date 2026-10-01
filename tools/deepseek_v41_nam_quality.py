#!/usr/bin/env python3
"""QC-NAM: quality and numerical stability of DeepSeek-V4.1-Flash with the RMSNorm scalar applied AFTER
the matrix product (norm-after-matvec, "norm folding"), against the vendor reference.

The variant (``b_nam``) is the golden's existing opt-in mode ``HDC_V41_FUSE=nfold`` on top of the adopted
deployment contract (``chunk8`` + ``osm``), emulated exactly on the GPU:

* at the four RMSNorms whose outputs feed matrix products -- attn_norm, q_norm, ffn_norm and the final
  norm -- the norm returns ``xw = bf16(gamma * x)`` (gamma stays in place, applied to the UN-normalised x)
  and ``r = rstd(x)`` (the same R-ARITH sum of squares, mean, +eps, rsqrt as the contract);
* every consumer matvec runs on ``xw``: the FP8 linears (wq_a, wkv, wq_b, indexer wq_b, shared AND routed
  expert w1/w3) block-quantise ``xw`` to E4M3 with UE8M0 scales (instead of ``bf16(gamma * x * r)``); the
  BF16 matvecs (indexer weights_proj, compressor wkv/wgate, router gate, lm_head) take ``xw`` as BF16;
* each consumer multiplies its FP32 accumulator by ``r`` (one IEEE multiply) BEFORE its own output rounding
  (BF16 for the linears, none for the FP32-out matvecs).
Norms that do not feed a matvec (kv_norm, the compressor norm, the indexer k_norm) and the hyper-connection
and Engram norms (already applied after their dot products in the release) are unchanged.

Because the UE8M0 block scale is a power of two and rstd is not, ``q8(gamma*x)*rstd != q8(gamma*x*rstd)``:
the FP8 rounding of every block moves.  That is the contract change under test.

Modes (the deployment quality tool's, plus two): ``a`` vendor reference, ``a2`` second GPU arithmetic (noise
floor), ``b`` the deployment contract, ``b_nam`` the contract plus nfold, and the teacher-forced ``b_tf``,
``b_nam_tf``, ``a2_tf`` (layer L run on the reference's own layer-L input).  Beyond PPL/MMLU every run
records, per layer and per site: the dynamic range entering every FP8 quantiser (max |x|, UE8M0 block
exponent histogram, amax-floor hits), saturation, underflow-to-zero, FP8 subnormal and NaN/Inf counts, the
per-row FP8 quantisation error, the norm sites' un-normalised range (massive-activation channels and the
BOS position), a same-input probe at every folded consumer (contract output, nfold output and an FP64
un-quantised ideal on identical inputs), and router/index flip rates by position bucket.

The default deployment tool (tools/deepseek_v41_deployment_quality.py) and the golden are not modified.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import deepseek_v41_deployment_quality as Q  # noqa: E402

F32, BF16 = Q.F32, Q.BF16
add, mul, neg, to_bf16 = Q.add, Q.mul, Q.neg, Q.to_bf16


def div(a, b):
    """IEEE binary32 division.  Q.div(a, b) with a Python-scalar divisor is NOT IEEE on CUDA: PyTorch turns
    tensor / cpu_scalar into tensor * (1 / scalar), which differs from a / b in the last bit for ~20% of
    quotients (measured).  The golden's means (sum / d, d = 5,120, 20,480, ...) are IEEE divisions."""
    if torch.is_tensor(a) and not torch.is_tensor(b):
        b = torch.tensor(b, dtype=a.dtype, device=a.device)
    return (a / b) + 0.0


class ieee_division:
    """Context: every Q engine in this process divides by IEEE rules (Q.div -> div)."""

    def __enter__(self):
        self.prev, Q.div = Q.div, div
        return self

    def __exit__(self, *exc):
        Q.div = self.prev
OUT = ROOT / "results/quality/deepseek_v41_flash_norm_after_matvec.json"
SCHEMA = "opentallas.deepseek-v41-flash-norm-after-matvec.v1"
POS_EDGES = [0, 1, 64, 256, 1024, 2048, 4096, 8192, 16384, 1 << 30]
FOLD_NORMS = ("attn_norm", "q_norm", "ffn_norm", "final_norm")
# the consumers of a folded norm (golden nfold): name -> norm
FOLDED_SITES = {"attn.wq_a": "attn_norm", "attn.wkv": "attn_norm", "attn.indexer.weights_proj": "attn_norm",
                "attn.compressor.wkv": "attn_norm", "attn.compressor.wkvgate": "attn_norm",
                "attn.wq_b": "q_norm", "attn.indexer.wq_b": "q_norm",
                "ffn.gateT": "ffn_norm", "shared.w1": "ffn_norm", "shared.w3": "ffn_norm",
                "routed.w1": "ffn_norm", "routed.w3": "ffn_norm", "headT": "final_norm"}
PROBE_ROWS = 256

# Pre-registered (2026-10-01, before any full-model nfold result existed).  Quality: the deployment tool's own
# rule (Q.THRESHOLD) applied to b_nam against a.  Stability: the user's rule, made operational.
STABILITY_RULE = {
    "rule": "b_nam is numerically stable iff (S1) no NaN or Inf appears anywhere in b_nam (every FP8 quantiser "
            "input and output, every BF16 matvec input and output, every folded norm site, every logit); (S2) "
            "b_nam's FP8 saturation count is not above the contract b's, at every quantiser site and in total; "
            "(S3) its error and selection-flip rates do not exceed the noise floor in a way that grows with depth: "
            "for the free-running router flip rate, index query flip rate and hidden-state relative RMS, and for "
            "the teacher-forced (one-layer) router flip rate and hidden relative RMS, the ratio X_L of b_nam to "
            "the noise floor (a2, resp. a2_tf) FAILS when its mean over layers 30-39 exceeds X_RATIO_MAX and "
            "exceeds its mean over layers 0-9 by more than X_GROWTH_MAX (relative); the same-input probe ratio "
            "(b_nam's per-row error / b's against the FP64 un-quantised ideal, every folded site) FAILS on the "
            "same test; (S4) nor in a way that grows with context: for the router and index flip rates by "
            "position bucket (free-running and teacher-forced; buckets with >= 500 samples, BOS excluded) and "
            "the per-token |NLL delta| by position bucket, the ratio to the noise floor at the longest bucket "
            "FAILS when it exceeds X_RATIO_MAX and exceeds the ratio at the shortest bucket by more than "
            "X_GROWTH_MAX.  Underflow-to-zero, amax-floor hits and FP8 quantisation error are reported per "
            "site against b and gate only through S3 (their effect on the outputs).",
    "X_RATIO_MAX": 1.10,
    "X_GROWTH_MAX": 0.10,
    "min_bucket_samples": 500,
}


# ======================================================================================
# the folded activation
# ======================================================================================
class FoldedT:
    """hdc_golden_v41.Folded on the GPU: xw = bf16(gamma * x) [M, d], r = rstd [M]; consumers scale their FP32
    accumulators by r.  xhat/gamma (the un-normalised input and the gain) ride along for the same-input probe."""
    __slots__ = ("xw", "r", "xhat", "gamma", "tag")

    def __init__(self, xw, r, xhat=None, gamma=None, tag=None):
        self.xw, self.r, self.xhat, self.gamma, self.tag = xw, r, xhat, gamma, tag

    @property
    def shape(self):
        return self.xw.shape

    @property
    def device(self):
        return self.xw.device

    def reshape(self, *shape):
        xw = self.xw.reshape(*shape)
        return FoldedT(xw, self.r.reshape(xw.shape[:-1]),
                       None if self.xhat is None else self.xhat.reshape(*shape), self.gamma, self.tag)

    def __getitem__(self, idx):          # routed-expert row gathers: no probe on them
        return FoldedT(self.xw[idx], self.r[idx], None, None, self.tag)

    def to(self, dtype):
        # Q.to_bf16(x) = x.to(BF16).to(F32): xw is BF16-exact already, so rounding it is the identity (the
        # golden's matvec_c re-rounds Folded.xw to BF16 the same way)
        return self

    @staticmethod
    def cat(parts):
        xh = None if any(p.xhat is None for p in parts) else torch.cat([p.xhat for p in parts])
        return FoldedT(torch.cat([p.xw for p in parts]), torch.cat([p.r for p in parts]), xh,
                       parts[0].gamma, parts[0].tag)


# ======================================================================================
# instrumentation
# ======================================================================================
def _f(x):
    return float(x)


class Stats:
    """Per-layer, per-mode accumulators (GPU tensors until flushed)."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.q, self.mvs, self.norm, self.probe = {}, {}, {}, {}

    # ---- an FP8 activation quantiser ----
    def quant(self, site, x, xq, xe, folded, out):
        d = self.q.get(site)
        if d is None:
            d = self.q[site] = {"calls": 0, "rows": 0, "blocks": 0, "elems": 0, "nonzero": 0, "max_abs": 0.0,
                                "floor_hits": 0, "zero_blocks": 0, "saturated": 0, "underflow_to_zero": 0,
                                "fp8_subnormal": 0, "nan_in": 0, "inf_in": 0, "nan_out": 0, "inf_out": 0,
                                "folded": bool(folded), "exp_min": 10 ** 9, "exp_max": -10 ** 9,
                                "amax_log2_hist": torch.zeros(160, dtype=torch.int64, device=x.device),
                                "qerr_log10_hist": torch.zeros(120, dtype=torch.int64, device=x.device),
                                "qerr_max": 0.0, "qerr_sum": 0.0, "qerr_rows": 0}
        M, K = x.shape
        xb = x.reshape(M, K // 32, 32)
        amax = xb.abs().amax(-1)
        d["calls"] += 1
        d["rows"] += M
        d["blocks"] += amax.numel()
        d["elems"] += x.numel()
        nz = x != 0
        d["nonzero"] += int(nz.sum())
        d["max_abs"] = max(d["max_abs"], _f(amax.max()) if amax.numel() else 0.0)
        d["floor_hits"] += int((amax < Q.f32c(Q.GV.FP8_AMAX_FLOOR)).sum())
        d["zero_blocks"] += int((amax == 0).sum())
        d["nan_in"] += int(torch.isnan(x).sum())
        d["inf_in"] += int(torch.isinf(x).sum())
        d["saturated"] += int(((xb.abs() * Q.pow2(-xe)[..., None]) > 448.0).sum())
        d["underflow_to_zero"] += int((nz & (xq == 0)).sum())
        d["fp8_subnormal"] += int(((xq != 0) & (xq.abs() < 2.0 ** -6)).sum())
        d["exp_min"] = min(d["exp_min"], int(xe.min()))
        d["exp_max"] = max(d["exp_max"], int(xe.max()))
        pos = amax > 0
        if bool(pos.any()):
            lg = torch.floor(torch.log2(amax[pos])).to(torch.int64) + 100
            d["amax_log2_hist"] += torch.bincount(lg.clamp(0, 159), minlength=160)
        dq = (xq.reshape(M, K // 32, 32) * Q.pow2(xe)[..., None]).reshape(M, K)
        nx = x.double().norm(dim=-1)
        ok = nx > 0
        if bool(ok.any()):
            rel = ((dq.double() - x.double()).norm(dim=-1)[ok] / nx[ok])
            d["qerr_max"] = max(d["qerr_max"], _f(rel.max()))
            d["qerr_sum"] += _f(rel.sum())
            d["qerr_rows"] += int(ok.sum())
            lr = torch.floor(torch.log10(torch.clamp_min(rel, 1e-12)) * 20).to(torch.int64) + 120
            d["qerr_log10_hist"] += torch.bincount(lr.clamp(0, 119), minlength=120)
        d["nan_out"] += int(torch.isnan(out).sum())
        d["inf_out"] += int(torch.isinf(out).sum())

    # ---- a BF16-weight matvec ----
    def mv(self, site, x, out, folded):
        d = self.mvs.get(site)
        if d is None:
            d = self.mvs[site] = {"calls": 0, "rows": 0, "max_abs_in": 0.0, "max_abs_out": 0.0, "nan_in": 0,
                                  "inf_in": 0, "nan_out": 0, "inf_out": 0, "folded": bool(folded)}
        d["calls"] += 1
        d["rows"] += x.shape[0]
        d["max_abs_in"] = max(d["max_abs_in"], _f(x.abs().max()))
        d["max_abs_out"] = max(d["max_abs_out"], _f(torch.nan_to_num(out, 0.0, 0.0, 0.0).abs().max()))
        d["nan_in"] += int(torch.isnan(x).sum())
        d["inf_in"] += int(torch.isinf(x).sum())
        d["nan_out"] += int(torch.isnan(out).sum())
        d["inf_out"] += int(torch.isinf(out).sum())

    # ---- a norm feeding matvecs ----
    def normsite(self, tag, x, r, w, pos):
        d = self.norm.get(tag)
        if d is None:
            d = self.norm[tag] = {"rows": 0, "max_abs_x": 0.0, "max_abs_gx": 0.0, "max_abs_xnorm": 0.0,
                                  "rstd_min": math.inf, "rstd_max": 0.0, "rms_min": math.inf, "rms_max": 0.0,
                                  "nan": 0, "inf": 0,
                                  "chan_max": torch.zeros(x.shape[-1], device=x.device),
                                  "pos_max_abs_x": [0.0] * (len(POS_EDGES) - 1),
                                  "pos_rms_max": [0.0] * (len(POS_EDGES) - 1)}
        ax = x.abs()
        d["rows"] += x.shape[0]
        d["max_abs_x"] = max(d["max_abs_x"], _f(ax.max()))
        d["max_abs_gx"] = max(d["max_abs_gx"], _f(to_bf16(mul(w, x)).abs().max()))
        d["max_abs_xnorm"] = max(d["max_abs_xnorm"], _f((ax * r[:, None] * w.abs()).max()))
        d["rstd_min"] = min(d["rstd_min"], _f(r.min()))
        d["rstd_max"] = max(d["rstd_max"], _f(r.max()))
        rms = 1.0 / r.double()
        d["rms_min"] = min(d["rms_min"], _f(rms.min()))
        d["rms_max"] = max(d["rms_max"], _f(rms.max()))
        d["nan"] += int(torch.isnan(x).sum() + torch.isnan(r).sum())
        d["inf"] += int(torch.isinf(x).sum() + torch.isinf(r).sum())
        d["chan_max"] = torch.maximum(d["chan_max"], ax.amax(0))
        if pos is not None and pos.numel() == x.shape[0]:
            b = torch.bucketize(pos, torch.tensor(POS_EDGES[1:], device=pos.device), right=True)
            rowmax = ax.amax(-1)
            for i in range(len(POS_EDGES) - 1):
                m = b == i
                if bool(m.any()):
                    d["pos_max_abs_x"][i] = max(d["pos_max_abs_x"][i], _f(rowmax[m].max()))
                    d["pos_rms_max"][i] = max(d["pos_rms_max"][i], _f(rms[m].max()))

    # ---- same-input probe ----
    def add_probe(self, site, e_b, e_n, d_bn, peak_b, peak_n):
        p = self.probe.setdefault(site, {"e_b": [], "e_n": [], "d_bn": [], "peak_b": [], "peak_n": []})
        for k, v in (("e_b", e_b), ("e_n", e_n), ("d_bn", d_bn), ("peak_b", peak_b), ("peak_n", peak_n)):
            p[k].append(v.double().cpu())

    def flush(self):
        out = {"quant": {}, "mv": dict(self.mvs), "norm": {}, "probe": {}}
        for s, d in self.q.items():
            d = dict(d)
            d["amax_log2_hist"] = {str(i - 100): int(c) for i, c in enumerate(d["amax_log2_hist"].tolist()) if c}
            d["qerr_log10_hist"] = {str((i - 120) / 20): int(c) for i, c in enumerate(d["qerr_log10_hist"].tolist())
                                    if c}
            d["qerr_mean"] = d["qerr_sum"] / max(1, d["qerr_rows"])
            out["quant"][s] = d
        for t, d in self.norm.items():
            d = dict(d)
            cm = d.pop("chan_max")
            v, i = cm.topk(min(8, cm.numel()))
            d["top_channels"] = [[int(a), _f(b)] for a, b in zip(i.tolist(), v.tolist())]
            d["channel_max_median"] = _f(cm.median())
            out["norm"][t] = d
        for s, p in self.probe.items():
            rec = {}
            for k, vs in p.items():
                v = torch.cat(vs).numpy()
                rec[k] = {"rows": int(v.size), "mean": float(v.mean()), "p50": float(np.percentile(v, 50)),
                          "p99": float(np.percentile(v, 99)), "max": float(v.max())}
            out["probe"][s] = rec
        self.reset()
        return out


# ======================================================================================
# the engine: contract (fold=False, = Q.Engine exact) and contract + nfold (fold=True)
# ======================================================================================
class NamEngine(Q.Engine):
    """Q.Engine(cfg, exact=True) with hdc_golden_v41's nfold as an option, plus instrumentation.  With
    fold=False every value is Q.Engine's (the overrides below reduce to its code); with fold=True it is
    hdc_golden_v41 under HDC_V41_ARITH=chunk8, HDC_V41_FUSE=nfold,osm."""

    def __init__(self, cfg, fold, instrument=True):
        super().__init__(cfg, True)
        self.fold = fold
        self.instrument = instrument
        self.stats = Stats()
        self.sites = {}           # id(weight object) -> site name (set per layer)
        self.pos = None           # positions of the rows of the current call (norm-site position stats)
        self.probe_n = 0          # leading rows eligible for the same-input probe (0: off)

    def set_weights(self, W):
        self.sites = {}
        for k, v in W.items():
            if k == "shared":
                for n, qw in zip(("w1", "w2", "w3"), v):
                    self.sites[id(qw)] = f"shared.{n}"
            else:
                self.sites[id(v)] = k

    def _site(self, w):
        return self.sites.get(id(w), "other")

    # ---- norms --------------------------------------------------------------------------
    def rmsnorm_fold(self, x, w, tag):
        d = x.shape[-1]
        r = self.rsqrt(add(div(self.rowsum(mul(x, x)), float(d)), self.cfg.eps))
        if self.instrument:
            self.stats.normsite(tag, x, r, w, self.pos)
        if self.fold:
            return FoldedT(to_bf16(mul(w, x)), r, x, w, tag)
        return to_bf16(mul(w, mul(x, r[..., None])))

    # ---- matvecs ------------------------------------------------------------------------
    def linq(self, qw, x, site=None):
        site = site or self._site(qw)
        folded = isinstance(x, FoldedT)
        xin = x.xw if folded else x
        xq, xe = Q.quant_fp8(xin)
        outs = []
        step = max(1, (1 << 27) // max(1, qw.N * (-(-(qw.K // 32) // 8))))
        for m0 in range(0, xin.shape[0], step):
            outs.append(Q.tree_t(Q.qdot_chunks(xq[m0:m0 + step], xe[m0:m0 + step], qw)))
        acc = torch.cat(outs, 0)
        if folded:
            acc = mul(acc, x.r[:, None])
        out = to_bf16(acc)
        if self.instrument:
            self.stats.quant(site, xin, xq, xe, folded, out)
            if folded:
                self._probe(site, qw, x, out, "q")
        return out

    def mv(self, w, x, w_kmajor=False, site=None):
        site = site or self._site(w)
        if isinstance(x, FoldedT):
            out = mul(Q.csum_mm(x.xw, w, w_kmajor=w_kmajor)[0], x.r[:, None])
            if self.instrument:
                self.stats.mv(site, x.xw, out, True)
                self._probe(site, w, x, out, "kmajor" if w_kmajor else "nk")
            return out
        out = Q.csum_mm(x, w, w_kmajor=w_kmajor)[0]
        if self.instrument and site != "other":
            self.stats.mv(site, x, out, False)
        return out

    def lin_bf16(self, w, x, w_kmajor=False):
        if isinstance(x, FoldedT):
            return to_bf16(self.mv(w, x, w_kmajor))
        return to_bf16(self.mv(w, to_bf16(x), w_kmajor))

    def _probe(self, site, w, x, out, kind):
        """Same-input probe at a folded consumer: on identical un-normalised rows, the contract's output
        (normalise, round BF16, then the matvec), this nfold output, and the FP64 un-quantised ideal
        W . (gamma * x * rstd) with an exact rstd."""
        if self.probe_n <= 0 or x.xhat is None or x.gamma is None:
            return
        n = min(self.probe_n, x.xw.shape[0])
        S = torch.arange(0, n, max(1, n // PROBE_ROWS), device=x.xw.device)[:PROBE_ROWS]
        xs, rs, g = x.xhat[S], x.r[S], x.gamma
        xn = to_bf16(mul(g, mul(xs, rs[:, None])))                   # the contract's normed input
        was, self.instrument = self.instrument, False
        try:
            if kind == "q":
                yb = self.linq(w, xn, site)
            else:
                yb = Q.csum_mm(xn, w, w_kmajor=(kind == "kmajor"))[0]
        finally:
            self.instrument = was
        yn = out[S]
        x64 = xs.double()
        r64 = 1.0 / torch.sqrt((x64 * x64).mean(-1) + float(self.cfg.eps))
        xi = g.double() * x64 * r64[:, None]
        if kind == "q":
            yi = xi @ w.dense_T().double()
        else:
            wk = w if kind == "kmajor" else w.t()                    # [K, N]
            yi = torch.cat([xi @ wk[:, c0:c0 + 16384].double() for c0 in range(0, wk.shape[1], 16384)], 1)
        ni = yi.norm(dim=-1)
        ok = ni > 0
        ni, yi, yb, yn = ni[ok], yi[ok], yb[ok].double(), yn[ok].double()
        rms = ni / math.sqrt(yi.shape[-1])
        self.stats.add_probe(site, (yb - yi).norm(dim=-1) / ni, (yn - yi).norm(dim=-1) / ni,
                             (yn - yb).norm(dim=-1) / ni, (yb - yi).abs().amax(-1) / rms,
                             (yn - yi).abs().amax(-1) / rms)

    # ---- the sublayers that hold a folded norm -------------------------------------------
    def attn_half(self, L, W, h, pre, st, B, T, engram_rows=None, trace=None):
        if engram_rows is not None:
            h = self.engram(h, W, engram_rows)
        res = h
        a_pre, a_post, a_comb = self.hc_mixes(h, W, "attn")
        x = self.rmsnorm_fold(self.hc_pre(h, pre), W["attn_norm"], "attn_norm")
        qr = self.rmsnorm_fold(self.linq(W["attn.wq_a"], x), W["attn.q_norm"], "q_norm")
        y = self.attention(L, W, x, qr, st, T, B, trace)
        if trace is not None and trace.get("debug"):
            trace["attn_out"] = y
        return self.hc_post(y, res, a_post, a_comb), a_pre

    def ffn_prep(self, W, h, a_pre):
        f_pre, f_post, f_comb = self.hc_mixes(h, W, "ffn")
        x = self.rmsnorm_fold(self.hc_pre(h, a_pre), W["ffn_norm"], "ffn_norm")
        return x, f_pre, f_post, f_comb

    def moe(self, W, experts, x, trace):
        cfg = self.cfg
        raw = self.mv(W["ffn.gateT"], x, w_kmajor=True)
        scores = Q.sqrt_g(self.softplus(raw))
        biased = add(scores, W["ffn.gate.bias"][None])
        chosen = self.topk_sel(biased, cfg.k_exp)
        ids = torch.sort(chosen, -1).values
        sel_scores = scores.gather(1, ids)
        total = sel_scores[:, 0]
        for j in range(1, cfg.k_exp):
            total = add(total, sel_scores[:, j])
        den = add(total, Q.f32c(1e-20))
        wgt = mul(div(sel_scores, den[:, None]), cfg.route_scale)
        xw = x.xw if isinstance(x, FoldedT) else x
        y = torch.zeros_like(xw)
        flat = ids.flatten()
        order = torch.argsort(flat, stable=True)
        counts = torch.bincount(flat, minlength=cfg.n_exp).tolist()
        o0 = 0
        for i in range(cfg.n_exp):
            if counts[i] == 0:
                continue
            seg = order[o0:o0 + counts[i]]
            o0 += counts[i]
            tok, slot = seg // cfg.k_exp, seg % cfg.k_exp
            out = self.expert(experts(i), x[tok], wgt[tok, slot][:, None], "routed")
            y[tok] = add(y[tok], out)
        y = add(y, self.expert(W["shared"], x, None, "shared"))
        if trace is not None:
            trace["router"] = ids
        return to_bf16(y)

    def expert(self, ws, x, weight, tag="shared"):
        w1, w2, w3 = ws
        g = self.linq(w1, x, f"{tag}.w1")
        u = self.linq(w3, x, f"{tag}.w3")
        u = torch.clamp(u, -self.cfg.limit, self.cfg.limit)
        g = torch.clamp_max(g, self.cfg.limit)
        a = mul(self.silu(g), u)
        if weight is not None:
            a = mul(weight, a)
        return self.linq(w2, to_bf16(a), f"{tag}.w2")

    def final(self, h, pre, W):
        xf = self.rmsnorm_fold(self.hc_pre(h, pre), W["norm"], "final_norm")
        return self.mv(W["headT"], xf, w_kmajor=True, site="headT")


# ======================================================================================
# whole-model logits (tests): one engine factory
# ======================================================================================
def model_logits(snap, ids, fold, device="cuda"):
    with ieee_division():
        return _model_logits(snap, ids, fold, device)


def _model_logits(snap, ids, fold, device="cuda"):
    dev = torch.device(device)
    snap = Path(snap)
    cfg, ck, tok = Q.Cfg(snap), Q.Checkpoint(snap), Q.tokenizer_for(snap)
    ids = torch.as_tensor(ids, dtype=torch.int64)
    B, T = ids.shape
    vend = Q.Vendor(snap, B, T, device)
    hashes = torch.stack(vend.hashes(tok, [r.tolist() for r in ids])) if cfg.engram_layers else None
    h = ck.get("embed.weight").to(dev)[ids.to(dev)][:, :, None, :].repeat(1, 1, cfg.hc, 1).contiguous()
    pre = torch.zeros(B, T, cfg.hc, device=dev)
    pre[..., 0] = 1.0
    eng = NamEngine(cfg, fold)
    st = Q.new_state(cfg, B, T, dev)
    for L in range(cfg.L):
        blk = vend.block(L, ck)
        er = None
        if L in cfg.engram_layers:
            er = Q.engram_rows(ck, cfg, L, hashes[:, :, cfg.engram_layers.index(L), :], dev)
        W, experts = Q.contract_weights(cfg, blk, ck, L, dev)
        eng.set_weights(W)
        hf, pf = eng.layer(L, W, experts, h.reshape(B * T, cfg.hc, cfg.dim).float(), pre.reshape(B * T, cfg.hc),
                           st, B, T, er.reshape(B * T, -1).float() if er is not None else None, {})
        h, pre = hf.reshape(B, T, cfg.hc, cfg.dim).to(BF16), pf.reshape(B, T, cfg.hc)
        del blk
    Wh = {"norm": ck.get("norm.weight").to(dev).float(), "headT": ck.get("head.weight").to(dev).t().contiguous()}
    logits = eng.final(h.reshape(B * T, cfg.hc, cfg.dim).float(), pre.reshape(B * T, cfg.hc), Wh)
    return logits.reshape(B, T, -1), eng


# ======================================================================================
# evaluation sets
# ======================================================================================
def stress_sequences(tok, T, seed=7):
    """Worst-case inputs, BOS + T-1 tokens each: one token repeated, a rare token repeated, a short phrase
    repeated, and uniformly random vocabulary ids (mostly rare tokens)."""
    rng = np.random.default_rng(seed)
    bos = tok.bos_token_id
    n = T - 1
    the = tok(" the", add_special_tokens=False).input_ids[-1]
    rare = int(rng.integers(100000, 127000))
    phrase = tok(" The quick brown fox jumps over the lazy dog.", add_special_tokens=False).input_ids
    rep = (phrase * (n // len(phrase) + 1))[:n]
    rnd = rng.integers(3, 127000, n).tolist()
    return [("repeat_the", [bos] + [the] * n), ("repeat_rare_%d" % rare, [bos] + [rare] * n),
            ("repeat_phrase", [bos] + rep), ("random_vocab", [bos] + rnd)]


# ======================================================================================
# the layer-streamed driver (Q.run with the nfold modes, stress sets and instrumentation)
# ======================================================================================
MODE_SPEC = {"a": ("vendor", None), "a2": ("torch", None), "b": ("contract", None), "b_nam": ("nam", None),
             "b_tf": ("contract", "a"), "b_nam_tf": ("nam", "a"), "a2_tf": ("torch", "a")}


def _bucket(pos):
    return torch.bucketize(pos, torch.tensor(POS_EDGES[1:], device=pos.device), right=True)


def _sel_changed_per_query(ia, im):
    k = max(ia.shape[1], im.shape[1])
    if k == 0:
        return torch.zeros(ia.shape[0], dtype=torch.bool)
    if ia.shape[1] < k:
        ia = torch.cat([ia, ia.new_full((ia.shape[0], k - ia.shape[1]), -1)], 1)
    if im.shape[1] < k:
        im = torch.cat([im, im.new_full((im.shape[0], k - im.shape[1]), -1)], 1)
    ia, im = ia.long(), im.to(ia.device).long()
    va, vm = ia >= 0, im >= 0
    ina = (ia[:, :, None] == im[:, None, :]).any(-1) & va
    inm = (im[:, :, None] == ia[:, None, :]).any(-1) & vm
    return ((va & ~ina).sum(-1) + (vm & ~inm).sum(-1)) > 0


def run(args):
    dev = torch.device("cuda")
    snap = Path(args.snapshot)
    cfg = Q.Cfg(snap)
    if args.max_layers:
        cfg.L = min(cfg.L, args.max_layers)
    ck = Q.Checkpoint(snap)
    tok = Q.tokenizer_for(snap)
    seqs = []
    if args.windows:
        wins, _ = Q.wikitext_windows(tok, args.ctx, args.windows)
        for w, ids in enumerate(wins):
            seqs.append({"ids": ids, "kind": "wt", "w": w})
    if args.stress:
        for name, ids in stress_sequences(tok, args.stress_ctx):
            seqs.append({"ids": ids, "kind": "stress", "name": name})
    if args.gen_file:
        for g in json.loads(Path(args.gen_file).read_text()):
            seqs.append({"ids": g["ids"], "kind": "gen", "name": g["name"], "prompt_len": g["prompt_len"]})
    cand = None
    if args.mmlu:
        items, cand = Q.mmlu_items(tok, args.mmlu, seed=args.mmlu_seed)
        for q, it in enumerate(items):
            seqs.append({"ids": it["ids"], "kind": "mmlu", "q": q, "answer": it["answer"], "index": it["index"]})
    chunks = []
    for kind in ("wt", "stress", "gen"):
        ss = [s for s in seqs if s["kind"] == kind]
        for i in range(0, len(ss), args.batch):
            chunks.append(ss[i:i + args.batch])
    mm = sorted([s for s in seqs if s["kind"] == "mmlu"], key=lambda s: len(s["ids"]))
    tok_budget = args.batch * args.ctx
    i = 0
    while i < len(mm):
        j = i
        while j < len(mm) and (j - i + 1) * len(mm[j]["ids"]) <= tok_budget:
            j += 1
        j = max(j, i + 1)
        chunks.append(mm[i:j])
        i = j
    chunk_meta = []
    for c in chunks:
        Tm = max(len(s["ids"]) for s in c)
        for s in c:
            s["len"] = len(s["ids"])
        c_ids = torch.tensor([s["ids"] + [2] * (Tm - len(s["ids"])) for s in c], dtype=torch.int64)
        chunk_meta.append({"T": Tm, "B": len(c), "ids": c_ids, "seqs": c})
    max_T = max(cm["T"] for cm in chunk_meta)
    max_B = max(cm["B"] for cm in chunk_meta)
    vend = Q.Vendor(snap, max_B, max_T)
    modes = args.modes.split(",")
    assert modes[0] == "a"
    eng = {"contract": NamEngine(cfg, False), "nam": NamEngine(cfg, True), "torch": Q.Engine(cfg, False)}
    print(f"sequences {len(seqs)} in {len(chunk_meta)} chunks, max T {max_T}, modes {modes}", flush=True)
    if cfg.engram_layers:
        for cm in chunk_meta:
            cm["hash"] = torch.stack(vend.hashes(tok, [row.tolist() for row in cm["ids"]]))

    offs, ntok = [], 0
    for cm in chunk_meta:
        offs.append(ntok)
        ntok += cm["B"] * cm["T"]
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    full_modes = [m for m in modes if MODE_SPEC[m][1] is None]
    nbytes = ntok * cfg.hc * cfg.dim * 2
    H = {}
    for m in full_modes:
        for par in (0, 1):
            f = work / f"h_{m}_{par}.bin"
            if not f.exists() or f.stat().st_size != nbytes:
                with open(f, "wb") as fh:
                    fh.truncate(nbytes)
            H[(m, par)] = torch.from_file(str(f), shared=True, size=ntok * cfg.hc * cfg.dim,
                                          dtype=BF16).view(ntok, cfg.hc, cfg.dim)
    ckpt = work / "checkpoint.pt"
    sig = {"ids": [cm["ids"].tolist() for cm in chunk_meta], "modes": modes, "tf_chunks": args.tf_chunks}
    start = 0
    if args.resume and ckpt.exists():
        saved = torch.load(ckpt, weights_only=False)
        assert saved["sig"] == sig, "checkpoint belongs to another evaluation set"
        start, pre_state, small, stats = saved["layer_done"] + 1, saved["pre"], saved["small"], saved["stats"]
        print(f"resuming after layer {start - 1}", flush=True)
    else:
        embed = ck.get("embed.weight").to(dev)
        pre_state = {}
        for m in full_modes:
            for ci, cm in enumerate(chunk_meta):
                n = cm["B"] * cm["T"]
                h0 = embed[cm["ids"].to(dev)].reshape(n, 1, cfg.dim).repeat(1, cfg.hc, 1)
                H[(m, 0)][offs[ci]:offs[ci] + n] = h0.cpu()
            pre_state[m] = torch.zeros(ntok, cfg.hc)
            pre_state[m][:, 0] = 1.0
        small = {(m, ci): {"sh": {}, "st": Q._st_to(Q.new_state(cfg, cm["B"], cm["T"], "cpu"), "cpu")}
                 for m in modes for ci, cm in enumerate(chunk_meta)}
        stats = {"layers": []}
        del embed
    torch.cuda.empty_cache()

    def active(m, ci):
        return MODE_SPEC[m][1] is None or ci < args.tf_chunks

    t_start = time.time()
    valid, posv = [], []
    for cm in chunk_meta:
        v = torch.zeros(cm["B"], cm["T"], dtype=torch.bool)
        for bi, s_ in enumerate(cm["seqs"]):
            v[bi, :s_["len"]] = True
        valid.append(v.reshape(-1))
        posv.append(torch.arange(cm["T"]).repeat(cm["B"]))
    probe_len = chunk_meta[0]["seqs"][0]["len"]
    nb = len(POS_EDGES) - 1
    for L in range(start, cfg.L):
        pin, pout = L % 2, 1 - L % 2
        tl0 = time.time()
        blk = vend.block(L, ck)
        W, experts = Q.contract_weights(cfg, blk, ck, L, dev)
        for e in (eng["contract"], eng["nam"]):
            e.set_weights(W)
        erows = {}
        if L in cfg.engram_layers:
            li = cfg.engram_layers.index(L)
            for ci, cm in enumerate(chunk_meta):
                erows[ci] = Q.engram_rows(ck, cfg, L, cm["hash"][:, :, li, :], dev).cpu()
        tload = time.time() - tl0
        lst = {"layer": L, "load_s": tload, "mode_s": {m: 0.0 for m in modes}, "attn_s": {m: 0.0 for m in modes},
               "router": {}, "index": {}, "hidden_rel_rms": {}, "hidden_max_abs": {}, "router_by_pos": {},
               "index_by_pos": {}, "instr": {}}
        a_index, router_a = {}, None
        new_pre = {}
        for m in modes:
            kind, src = MODE_SPEC[m]
            srcm = "a" if src == "a" else m
            cis = [ci for ci in range(len(chunk_meta)) if active(m, ci)]
            E = eng.get(kind)
            inst = isinstance(E, NamEngine)
            A = {"router_tok": 0, "router_any": 0, "router_changed": 0, "idx_q": 0, "idx_any": 0,
                 "idx_diff": 0, "idx_tot": 0, "dh2": 0.0, "h2": 0.0, "hmax": 0.0}
            rb_tok, rb_flip = torch.zeros(nb, dtype=torch.int64), torch.zeros(nb, dtype=torch.int64)
            ib_q, ib_flip = torch.zeros(nb, dtype=torch.int64), torch.zeros(nb, dtype=torch.int64)
            t0 = time.time()
            mids, aps = [], []
            for ci in cis:
                cm = chunk_meta[ci]
                B, T = cm["B"], cm["T"]
                n = B * T
                h = H[(srcm, pin)][offs[ci]:offs[ci] + n].to(dev)
                pre = pre_state[srcm][offs[ci]:offs[ci] + n].to(dev)
                er = erows[ci].to(dev) if ci in erows else None
                S = small[(m, ci)]
                tr = {}
                if kind == "vendor":
                    sh = {k: (v.to(dev) if torch.is_tensor(v) else v) for k, v in S["sh"].items()}
                    hm, ap = vend.attn_half(blk, h.view(B, T, cfg.hc, cfg.dim), pre.view(B, T, cfg.hc), sh, er, tr)
                    S["sh"] = {k: (v.cpu() if torch.is_tensor(v) else v) for k, v in sh.items()}
                    hm, ap = hm.reshape(n, cfg.hc, cfg.dim), ap.reshape(n, cfg.hc)
                else:
                    st = Q._st_to(S["st"], dev)
                    rows = er.reshape(n, -1).float() if er is not None else None
                    if inst:
                        E.pos = posv[ci].to(dev)
                        E.probe_n = probe_len if ci == 0 else 0
                    hm, ap = E.attn_half(L, W, h.float(), pre.float(), st, B, T, rows, tr)
                    S["st"] = Q._st_to(st, "cpu")
                mids.append(hm.to(BF16))
                aps.append(ap.float())
                if "index" in tr:
                    sel = [x.to(torch.int32).cpu() for x in tr["index"]]
                    if m == "a":
                        a_index[ci] = sel
                    else:
                        for bi, s_ in enumerate(cm["seqs"]):
                            ia, im = a_index[ci][bi][: s_["len"]], sel[bi][: s_["len"]]
                            d, tot, anyd = Q._sel_diff(ia, im)
                            A["idx_q"] += s_["len"]
                            A["idx_any"] += anyd
                            A["idx_diff"] += d
                            A["idx_tot"] += tot
                            ch = _sel_changed_per_query(ia, im).cpu()
                            bq = _bucket(torch.arange(s_["len"]))
                            ib_q += torch.bincount(bq, minlength=nb)
                            ib_flip += torch.bincount(bq[ch], minlength=nb)
                del h, pre, er, tr
            torch.cuda.synchronize()
            lst["attn_s"][m] = time.time() - t0
            xs, fps, fpo, fco = [], [], [], []
            for j, ci in enumerate(cis):
                if kind == "vendor":
                    x, fp, fpost, fcomb = vend.ffn_prep(blk, mids[j][None], aps[j][None])
                    xs.append(x[0])
                    fps.append(fp[0])
                    fpo.append(fpost[0])
                    fco.append(fcomb[0])
                else:
                    if inst:
                        E.pos = posv[ci].to(dev)
                    x, fp, fpost, fcomb = E.ffn_prep(W, mids[j].float(), aps[j])
                    xs.append(x if isinstance(x, FoldedT) else x.to(BF16))
                    fps.append(fp)
                    fpo.append(fpost)
                    fco.append(fcomb)
            if xs and isinstance(xs[0], FoldedT):
                X = FoldedT.cat(xs)
            else:
                X = torch.cat(xs)
            del xs
            tr = {}
            if kind == "vendor":
                Y = vend.moe(blk, X[None], tr)[0]
            else:
                if inst:
                    E.pos = None
                    E.probe_n = probe_len if (cis and cis[0] == 0) else 0
                Y = E.moe(W, experts, X if isinstance(X, FoldedT) else X.float(), tr)
            del X
            ids = tr["router"].reshape(-1, cfg.k_exp)
            o0 = 0
            vflat = torch.cat([valid[ci] for ci in cis]).to(dev)
            pflat = torch.cat([posv[ci] for ci in cis]).to(dev)
            if src is None:
                new_pre[m] = pre_state[m].clone()
            for j, ci in enumerate(cis):
                n = chunk_meta[ci]["B"] * chunk_meta[ci]["T"]
                if kind == "vendor":
                    ho = vend.ffn_post(blk, Y[o0:o0 + n][None], mids[j][None], fpo[j][None], fco[j][None])[0]
                else:
                    ho = E.hc_post(Y[o0:o0 + n].float(), mids[j].float(), fpo[j], fco[j])
                ho = ho.to(BF16)
                v = valid[ci].to(dev)
                A["hmax"] = max(A["hmax"], float(ho.float().abs()[v].max()))
                if src is None:
                    H[(m, pout)][offs[ci]:offs[ci] + n] = ho.cpu()
                    new_pre[m][offs[ci]:offs[ci] + n] = fps[j].float().cpu()
                if m != "a":
                    ha = H[("a", pout)][offs[ci]:offs[ci] + n].to(dev).float()
                    A["dh2"] += float(((ho.float() - ha) ** 2)[v].sum())
                    A["h2"] += float((ha ** 2)[v].sum())
                o0 += n
            del Y, mids, aps, fps, fpo, fco
            lst["hidden_max_abs"][m] = A["hmax"]
            if m == "a":
                router_a = ids
            else:
                sa_ = torch.sort(router_a[:ids.shape[0]], -1).values
                sm_ = torch.sort(ids.to(sa_.dtype), -1).values
                diff = Q._set_diff(sa_, sm_)
                A["router_tok"] += int(vflat.sum())
                A["router_any"] += int(((diff > 0) & vflat).sum())
                A["router_changed"] += int(diff[vflat].sum())
                bk = _bucket(pflat[vflat]).cpu()
                rb_tok += torch.bincount(bk, minlength=nb)
                rb_flip += torch.bincount(bk[(diff[vflat] > 0).cpu()], minlength=nb)
                lst["router"][m] = {"tokens": A["router_tok"], "tokens_with_flip": A["router_any"],
                                    "flip_rate": A["router_any"] / max(1, A["router_tok"]),
                                    "experts_changed_per_token": A["router_changed"] / max(1, A["router_tok"])}
                lst["router_by_pos"][m] = {"tokens": rb_tok.tolist(), "flips": rb_flip.tolist()}
                if A["idx_q"]:
                    lst["index"][m] = {"queries": A["idx_q"], "queries_with_diff": A["idx_any"],
                                       "query_flip_rate": A["idx_any"] / A["idx_q"],
                                       "selected_positions_changed_frac": A["idx_diff"] / max(1, A["idx_tot"])}
                    lst["index_by_pos"][m] = {"queries": ib_q.tolist(), "flips": ib_flip.tolist()}
                lst["hidden_rel_rms"][m] = math.sqrt(A["dh2"] / max(A["h2"], 1e-30))
            if inst:
                lst["instr"][m] = E.stats.flush()
            torch.cuda.synchronize()
            lst["mode_s"][m] = time.time() - t0
            torch.cuda.empty_cache()
        pre_state.update(new_pre)
        lst["rss_anon_gb"], lst["rss_file_gb"], lst["peak_rss_gb"] = Q._rss_gb()
        lst["gpu_peak_gb"] = torch.cuda.max_memory_allocated() / 1e9
        stats["layers"].append(lst)
        nq = {m: sum(d["saturated"] + d["nan_in"] + d["inf_in"] + d["nan_out"] + d["inf_out"]
                     for d in lst["instr"][m]["quant"].values()) for m in lst["instr"]}
        print(f"layer {L}: load {tload:.1f}s " + " ".join(f"{m} {lst['mode_s'][m]:.1f}s" for m in modes) +
              " | router flips " + " ".join(f"{m} {lst['router'][m]['flip_rate']:.4f}" for m in lst["router"]) +
              " | index " + " ".join(f"{m} {lst['index'][m]['query_flip_rate']:.4f}" for m in lst["index"]) +
              " | rel rms " + " ".join(f"{m} {v:.2e}" for m, v in lst["hidden_rel_rms"].items()) +
              " | sat/nan/inf " + " ".join(f"{m} {v}" for m, v in nq.items()) +
              f" | gpu peak {lst['gpu_peak_gb']:.1f} GB | {time.time() - t_start:.0f}s", flush=True)
        del blk, W, experts, erows
        gc.collect()
        torch.cuda.empty_cache()
        tmp = work / "checkpoint.tmp"
        torch.save({"sig": sig, "layer_done": L, "pre": pre_state, "small": small, "stats": stats}, tmp)
        os.replace(tmp, ckpt)
        if args.partial:
            Path(args.partial).write_text(json.dumps(stats) + "\n")
    parity = cfg.L % 2

    head = ck.get("head.weight").to(dev)
    Wh = {"norm": ck.get("norm.weight").to(dev).float(), "headT": head.t().contiguous()}
    headf = head.float()
    Wh["head_f32"] = headf
    del head
    for e in (eng["contract"], eng["nam"]):
        e.set_weights({})
    final_modes = [m for m in modes if MODE_SPEC[m][1] is None]
    per_seq = {m: [] for m in final_modes}

    def logits_rows(m, ci, rows, probe):
        h = H[(m, parity)][offs[ci] + rows].to(dev)
        pre = pre_state[m][offs[ci] + rows].to(dev)
        if MODE_SPEC[m][0] == "vendor":
            x = Q._vendor_final(vend, h[None], pre[None], Wh["norm"])[0]
            return torch.nn.functional.linear(x.float(), headf)
        e = eng[MODE_SPEC[m][0]]
        step = 64 if e.exact else 1024
        if isinstance(e, NamEngine):
            e.pos = None
        outs = []
        for r0 in range(0, h.shape[0], step):
            if isinstance(e, NamEngine):
                e.probe_n = 64 if (probe and r0 < 256) else 0
            outs.append(e.final(h[r0:r0 + step].float(), pre[r0:r0 + step].float(), Wh))
        return torch.cat(outs)

    for ci, cm in enumerate(chunk_meta):
        T = cm["T"]
        for bi, s_ in enumerate(cm["seqs"]):
            n = s_["len"]
            ids = cm["ids"][bi, :n].to(dev)
            if s_["kind"] in ("wt", "stress", "gen"):
                rows = torch.arange(bi * T, bi * T + n - 1)
            else:
                rows = torch.tensor([bi * T + n - 1])
            la = None
            for m in final_modes:
                l = logits_rows(m, ci, rows, ci == 0 and bi == 0)
                rec = {"kind": s_["kind"], "nan_logits": int(torch.isnan(l).sum()), "inf_logits": int(torch.isinf(l).sum())}
                if s_["kind"] in ("stress", "gen"):
                    rec["name"] = s_["name"]
                if s_["kind"] == "gen":
                    rec["prompt_len"] = s_["prompt_len"]
                if s_["kind"] in ("wt", "stress", "gen"):
                    lp = torch.log_softmax(l.double(), -1)
                    rec["nll"] = (-lp.gather(1, ids[1:, None])[:, 0]).cpu().numpy()
                    top = l.topk(2, -1)
                    rec["arg"] = top.indices[:, 0].cpu().numpy()
                    rec["margin"] = (top.values[:, 0] - top.values[:, 1]).cpu().numpy()
                    if m == "a":
                        la = lp
                    else:
                        rec["kl_a"] = (la.exp() * (la - lp)).sum(-1).cpu().numpy()
                    del lp
                else:
                    rec["pick"] = int(torch.argmax(l[0, cand]).item())
                    rec["answer"] = s_["answer"]
                    rec["mmlu_index"] = s_["index"]
                per_seq[m].append(rec)
                del l
            del la
        torch.cuda.empty_cache()
    head_instr = {m: eng[MODE_SPEC[m][0]].stats.flush() for m in final_modes
                  if isinstance(eng.get(MODE_SPEC[m][0]), NamEngine)}
    return cfg, seqs, per_seq, stats, head_instr, time.time() - t_start


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, float) and not math.isfinite(o):
        return str(o)
    return o


# ======================================================================================
# the committed record
# ======================================================================================
def _load_run(d):
    d = Path(d)
    run_rec = json.loads((d / "run.json").read_text())
    raw = json.loads((d / "raw.json").read_text())
    per_seq = {m: [{k: (np.array(v) if isinstance(v, list) else v) for k, v in r.items()} for r in recs]
               for m, recs in raw.items()}
    return run_rec, per_seq


def _mmlu_pooled(runs, modes):
    """MMLU records of every run, pooled by question index (a later run's record replaces an earlier one's)."""
    pool = {}
    for run_rec, per_seq in runs:
        if any(m not in per_seq for m in modes):
            continue
        ref = per_seq["a"]
        for i, r in enumerate(ref):
            if r["kind"] == "mmlu":
                pool[r["mmlu_index"]] = {m: per_seq[m][i] for m in modes}
    keys = sorted(pool)
    out = {}
    cor = {m: np.array([pool[k][m]["pick"] == pool[k][m]["answer"] for k in keys], dtype=float) for m in modes}
    for m in modes:
        same = np.array([pool[k][m]["pick"] == pool[k]["a"]["pick"] for k in keys], dtype=float)
        n = len(keys)
        out[m] = {"questions": n, "accuracy": float(cor[m].mean()),
                  "accuracy_ci95": Q._boot(lambda ix: float(cor[m][ix].mean()), n),
                  "delta_pt": float(100 * (cor[m].mean() - cor["a"].mean())),
                  "delta_pt_ci95": Q._boot(lambda ix: float(100 * (cor[m][ix].mean() - cor["a"][ix].mean())), n),
                  "same_answer_as_ref": float(same.mean()),
                  "discordant_with_ref": int((same == 0).sum())}
    if "b" in modes and "b_nam" in modes:
        out["b_nam_vs_b"] = {
            "delta_pt": float(100 * (cor["b_nam"].mean() - cor["b"].mean())),
            "delta_pt_ci95": Q._boot(lambda ix: float(100 * (cor["b_nam"][ix].mean() - cor["b"][ix].mean())),
                                     len(keys)),
            "same_answer": float(np.mean([pool[k]["b_nam"]["pick"] == pool[k]["b"]["pick"] for k in keys]))}
    return out


def _seq_tables(per_seq, kind, modes):
    """per sequence of `kind` (wt/stress): top-1 agreement with a, mean |NLL delta|, NLL delta, mean KL."""
    ref = per_seq["a"]
    out = {}
    for i, r in enumerate(ref):
        if r["kind"] != kind:
            continue
        name = r.get("name", f"w{i}")
        row = {"tokens": int(len(r["nll"])), "nll_a": float(np.mean(r["nll"]))}
        for m in modes:
            if m == "a":
                continue
            x = per_seq[m][i]
            dn = x["nll"] - r["nll"]
            row[m] = {"top1_agree": float((x["arg"] == r["arg"]).mean()), "nll_delta_mean": float(dn.mean()),
                      "nll_delta_abs_mean": float(np.abs(dn).mean()), "kl_mean": float(np.mean(x["kl_a"])),
                      "first_top1_disagreement": int(np.argmax(x["arg"] != r["arg"])) if (x["arg"] != r["arg"]).any()
                      else None}
        out[name] = row
    return out


def _by_position(per_seq, kind, modes):
    """per position bucket over all sequences of `kind`: top-1 agreement and mean |NLL delta| vs a."""
    ref = per_seq["a"]
    idx = [i for i, r in enumerate(ref) if r["kind"] == kind]
    if not idx:
        return {}
    out = {}
    for m in modes:
        if m == "a":
            continue
        agree, dabs, cnt = np.zeros(len(POS_EDGES) - 1), np.zeros(len(POS_EDGES) - 1), np.zeros(len(POS_EDGES) - 1)
        for i in idx:
            pos = np.arange(1, len(ref[i]["nll"]) + 1)          # the position whose token is predicted
            b = np.searchsorted(POS_EDGES[1:], pos, side="right")
            np.add.at(cnt, b, 1)
            np.add.at(agree, b, (per_seq[m][i]["arg"] == ref[i]["arg"]).astype(float))
            np.add.at(dabs, b, np.abs(per_seq[m][i]["nll"] - ref[i]["nll"]))
        out[m] = {"buckets": [[POS_EDGES[k], POS_EDGES[k + 1]] for k in range(len(cnt)) if cnt[k]],
                  "tokens": [int(c) for c in cnt if c],
                  "top1_agree": [float(agree[k] / cnt[k]) for k in range(len(cnt)) if cnt[k]],
                  "nll_delta_abs_mean": [float(dabs[k] / cnt[k]) for k in range(len(cnt)) if cnt[k]]}
    return out


def _growth(series, floor, lo=range(0, 10), hi=range(30, 40)):
    x = np.array(series, dtype=float) / np.maximum(np.array(floor, dtype=float), 1e-30)
    lo_m = float(np.mean(x[[i for i in lo if i < len(x)]]))
    hi_m = float(np.mean(x[[i for i in hi if i < len(x)]]))
    fail = hi_m > STABILITY_RULE["X_RATIO_MAX"] and hi_m > lo_m * (1 + STABILITY_RULE["X_GROWTH_MAX"])
    return {"ratio_by_layer": [float(v) for v in x], "mean_layers_0_9": lo_m, "mean_layers_30_39": hi_m,
            "fails": bool(fail)}


def _growth_ctx(num, den, n):
    keep = [k for k in range(1, len(n)) if n[k] >= STABILITY_RULE["min_bucket_samples"]]
    if len(keep) < 2:
        return {"buckets_used": keep, "fails": False, "note": "fewer than two usable buckets"}
    x = [num[k] / max(den[k], 1e-30) for k in keep]
    fail = x[-1] > STABILITY_RULE["X_RATIO_MAX"] and x[-1] > x[0] * (1 + STABILITY_RULE["X_GROWTH_MAX"])
    return {"buckets_used": [[POS_EDGES[k], POS_EDGES[k + 1]] for k in keep], "ratio": [float(v) for v in x],
            "fails": bool(fail)}


def _sum_layers(layers, key, m, field):
    tok = np.zeros(len(POS_EDGES) - 1)
    fl = np.zeros(len(POS_EDGES) - 1)
    for l in layers:
        d = l.get(key, {}).get(m)
        if d:
            tok += np.array(d[field[0]])
            fl += np.array(d[field[1]])
    return fl, tok


def stability(runs_named):
    """the S1-S4 verdicts and the per-layer, per-site evidence tables from the run records."""
    crit = {}
    # ---- S1 / S2 --------------------------------------------------------------------
    nan_inf = {}
    sat = {"b": {}, "b_nam": {}}
    for name, (run_rec, per_seq) in runs_named.items():
        for l in run_rec["layers"]:
            for m, ins in l.get("instr", {}).items():
                if m in ("b_nam", "b_nam_tf"):
                    for s, d in ins["quant"].items():
                        nan_inf[f"{name}.L{l['layer']}.{m}.{s}.quant"] = d["nan_in"] + d["inf_in"] + d["nan_out"] + d["inf_out"]
                    for s, d in ins["mv"].items():
                        nan_inf[f"{name}.L{l['layer']}.{m}.{s}.mv"] = d["nan_in"] + d["inf_in"] + d["nan_out"] + d["inf_out"]
                    for s, d in ins["norm"].items():
                        nan_inf[f"{name}.L{l['layer']}.{m}.{s}.norm"] = d["nan"] + d["inf"]
                if m in sat:
                    for s, d in ins["quant"].items():
                        sat[m][s] = sat[m].get(s, 0) + d["saturated"]
        for m, ins in run_rec.get("head_instr", {}).items():
            if m == "b_nam":
                for s, d in ins["mv"].items():
                    nan_inf[f"{name}.head.{m}.{s}.mv"] = d["nan_in"] + d["inf_in"] + d["nan_out"] + d["inf_out"]
                for s, d in ins["norm"].items():
                    nan_inf[f"{name}.head.{m}.{s}.norm"] = d["nan"] + d["inf"]
        for m, recs in per_seq.items():
            if m == "b_nam":
                nan_inf[f"{name}.logits.{m}"] = sum(int(r.get("nan_logits", 0)) + int(r.get("inf_logits", 0)) for r in recs)
    bad = {k: v for k, v in nan_inf.items() if v}
    crit["S1_no_nan_inf"] = {"pass": not bad, "checks": len(nan_inf), "nonzero": bad}
    sites = sorted(set(sat["b"]) | set(sat["b_nam"]))
    over = {s: [sat["b_nam"].get(s, 0), sat["b"].get(s, 0)] for s in sites if sat["b_nam"].get(s, 0) > sat["b"].get(s, 0)}
    crit["S2_saturation_not_above_b"] = {"pass": not over and sum(sat["b_nam"].values()) <= sum(sat["b"].values()),
                                         "saturated_total": {m: int(sum(v.values())) for m, v in sat.items()},
                                         "sites_above_b": over}
    # ---- S3: depth -------------------------------------------------------------------
    core_rec, _ = runs_named["core"]
    layers = core_rec["layers"]
    s3 = {}
    def ser(key, m, sub=None):
        out = []
        for l in layers:
            v = l[key].get(m)
            out.append(np.nan if v is None else (v[sub] if sub else v))
        return out
    s3["router_flip_free"] = _growth(ser("router", "b_nam", "flip_rate"), ser("router", "a2", "flip_rate"))
    s3["hidden_rel_rms_free"] = _growth(ser("hidden_rel_rms", "b_nam"), ser("hidden_rel_rms", "a2"))
    s3["router_flip_one_layer"] = _growth(ser("router", "b_nam_tf", "flip_rate"), ser("router", "a2_tf", "flip_rate"))
    s3["hidden_rel_rms_one_layer"] = _growth(ser("hidden_rel_rms", "b_nam_tf"), ser("hidden_rel_rms", "a2_tf"))
    idx_layers = [l["layer"] for l in layers if "b_nam" in l["index"]]
    if idx_layers:
        bn = [l["index"]["b_nam"]["query_flip_rate"] for l in layers if "b_nam" in l["index"]]
        a2 = [l["index"]["a2"]["query_flip_rate"] for l in layers if "b_nam" in l["index"]]
        lo = [i for i, L in enumerate(idx_layers) if L < 10]
        hi = [i for i, L in enumerate(idx_layers) if L >= 30]
        s3["index_flip_free"] = dict(_growth(bn, a2, lo or [0], hi or [len(bn) - 1]), layers=idx_layers)
        bn = [l["index"]["b_nam_tf"]["query_flip_rate"] for l in layers if "b_nam_tf" in l["index"]]
        a2 = [l["index"]["a2_tf"]["query_flip_rate"] for l in layers if "a2_tf" in l["index"]]
        if bn:
            s3["index_flip_one_layer"] = dict(_growth(bn, a2, lo or [0], hi or [len(bn) - 1]), layers=idx_layers)
    probe = {}
    for mode in ("b_nam", "b_nam_tf"):
        sites = sorted({s for l in layers for s in l["instr"].get(mode, {}).get("probe", {})})
        for s in sites:
            eb = [l["instr"][mode]["probe"].get(s, {}).get("e_b", {}).get("mean", np.nan) for l in layers]
            en = [l["instr"][mode]["probe"].get(s, {}).get("e_n", {}).get("mean", np.nan) for l in layers]
            ok = [i for i in range(len(eb)) if np.isfinite(eb[i]) and np.isfinite(en[i])]
            g = _growth([en[i] for i in ok], [eb[i] for i in ok],
                        [j for j, i in enumerate(ok) if i < 10], [j for j, i in enumerate(ok) if i >= 30])
            probe[f"{mode}.{s}"] = g
    s3["probe_error_ratio"] = {"fails": any(v["fails"] for v in probe.values()), "sites": probe}
    crit["S3_no_growth_with_depth"] = {"pass": not any(v["fails"] for v in s3.values()), "tests": s3}
    # ---- S4: context -----------------------------------------------------------------
    s4 = {}
    for name, (run_rec, per_seq) in runs_named.items():
        L_ = run_rec["layers"]
        for key, fld in (("router_by_pos", ("tokens", "flips")), ("index_by_pos", ("queries", "flips"))):
            for m, fl_ in (("b_nam", "a2"), ("b_nam_tf", "a2_tf")):
                fn, tn = _sum_layers(L_, key, m, fld)
                ff, tf_ = _sum_layers(L_, key, fl_, fld)
                if tn.sum() == 0 or tf_.sum() == 0:
                    continue
                rn = fn / np.maximum(tn, 1)
                rf = ff / np.maximum(tf_, 1)
                s4[f"{name}.{key}.{m}"] = _growth_ctx(rn, rf, np.minimum(tn, tf_))
        for kind in ("wt",):
            bp = _by_position(per_seq, kind, [m for m in ("a", "a2", "b_nam") if m in per_seq])
            if "b_nam" in bp and "a2" in bp:
                n = np.array(bp["b_nam"]["tokens"])
                edges = bp["b_nam"]["buckets"]
                ks = [POS_EDGES.index(e[0]) for e in edges]
                num, den, cnt = np.zeros(len(POS_EDGES) - 1), np.zeros(len(POS_EDGES) - 1), np.zeros(len(POS_EDGES) - 1)
                for j, k in enumerate(ks):
                    num[k] = bp["b_nam"]["nll_delta_abs_mean"][j]
                    den[k] = bp["a2"]["nll_delta_abs_mean"][j]
                    cnt[k] = n[j]
                s4[f"{name}.nll_delta_abs.{kind}"] = _growth_ctx(num, den, cnt)
    crit["S4_no_growth_with_context"] = {"pass": not any(v["fails"] for v in s4.values()), "tests": s4}
    return crit


def site_tables(layers, modes=("b", "b_nam", "b_tf", "b_nam_tf")):
    """compact per-layer, per-site evidence: quantiser range / floor / underflow / error, probe errors, norm range."""
    out = []
    for l in layers:
        row = {"layer": l["layer"], "hidden_max_abs": l.get("hidden_max_abs", {})}
        for m in modes:
            ins = l.get("instr", {}).get(m)
            if not ins:
                continue
            q = {}
            for s, d in ins["quant"].items():
                q[s] = {"folded": d["folded"], "max_abs": d["max_abs"], "exp_range": [d["exp_min"], d["exp_max"]],
                        "blocks": d["blocks"], "floor_hits": d["floor_hits"], "zero_blocks": d["zero_blocks"],
                        "saturated": d["saturated"],
                        "underflow_to_zero_rate": d["underflow_to_zero"] / max(1, d["nonzero"]),
                        "fp8_subnormal_rate": d["fp8_subnormal"] / max(1, d["elems"]),
                        "qerr_mean": d["qerr_mean"], "qerr_max": d["qerr_max"],
                        "amax_log2_hist": d["amax_log2_hist"]}
            row[m] = {"quant": q, "norm": ins["norm"], "probe": ins.get("probe", {}),
                      "mv": {s: {k: d[k] for k in ("max_abs_in", "max_abs_out", "folded")} for s, d in ins["mv"].items()}}
        out.append(row)
    return out


def finalize(run_dirs, out, meta):
    runs = {k: _load_run(v) for k, v in run_dirs.items()}
    core_rec, core_seq = runs["core"]
    modes_core = list(core_seq)

    class A:
        ctx = core_rec["args"]["ctx"]
    summ = Q.summarize(None, {m: core_seq[m] for m in modes_core}, None, None, A, {})
    mm_modes = [m for m in ("a", "a2", "b", "b_nam") if all(m in ps for _, ps in runs.values()
                                                               if any(r["kind"] == "mmlu" for r in ps["a"]))]
    mmlu = _mmlu_pooled([runs[k] for k in runs if any(r["kind"] == "mmlu" for r in runs[k][1]["a"])], mm_modes)
    bn = summ["modes"]["b_nam"]
    ppl_rel = bn["wikitext2"]["rel_delta_ppl"]
    mmlu_drop = -mmlu["b_nam"]["delta_pt"]
    ok_ppl = ppl_rel <= Q.THRESHOLD["ppl_rel_max"]
    ok_mmlu = mmlu_drop <= Q.THRESHOLD["mmlu_drop_max_pt"]
    stab = stability(runs)
    st_pass = all(c["pass"] for c in stab.values())
    rec = {"schema": SCHEMA, "tool": "tools/deepseek_v41_nam_quality.py", "test": "tests/test_deepseek_v41_nam_quality.py"}
    rec.update(meta)
    rec["threshold"] = Q.THRESHOLD
    rec["stability_rule"] = STABILITY_RULE
    quality = {"acceptable": bool(ok_ppl and ok_mmlu), "ppl_rel_delta": ppl_rel,
               "ppl_rel_delta_ci95": bn["wikitext2"]["rel_delta_ppl_ci95"], "ppl_ok": bool(ok_ppl),
               "mmlu_questions": mmlu["b_nam"]["questions"], "mmlu_drop_pt": mmlu_drop,
               "mmlu_delta_pt_ci95": mmlu["b_nam"]["delta_pt_ci95"], "mmlu_ok": bool(ok_mmlu)}
    rec["verdict"] = {"quality": quality,
                      "stability": {"pass": bool(st_pass), "criteria": stab},
                      "adopt": bool(ok_ppl and ok_mmlu and st_pass)}
    rec["summary"] = {"wikitext2_core": summ["modes"], "mmlu_pooled": mmlu,
                      "layer_tables": Q._layer_tables(core_rec["layers"])}
    for k, (rr, ps) in runs.items():
        if k == "core":
            continue
        if any(r["kind"] == "wt" for r in ps["a"]):
            class A2:
                ctx = rr["args"]["ctx"]
            rec["summary"][f"wikitext2_{k}"] = Q.summarize(None, ps, None, None, A2, {})["modes"]
            rec["summary"][f"wikitext2_{k}_by_position"] = _by_position(ps, "wt", list(ps))
            rec["summary"][f"layer_tables_{k}"] = Q._layer_tables(rr["layers"])
    rec["summary"]["wikitext2_core_by_position"] = _by_position(core_seq, "wt", modes_core)
    rec["summary"]["stress"] = _seq_tables(core_seq, "stress", modes_core)
    for k, (rr, ps) in runs.items():
        if any(r["kind"] == "gen" for r in ps["a"]):
            rec["summary"][f"greedy_{k}"] = _seq_tables(ps, "gen", list(ps))
    rec["runs"] = {k: {"args": rr["args"], "wall_s": rr["wall_s"]} for k, (rr, _) in runs.items()}
    rec["site_tables"] = {k: site_tables(rr["layers"]) for k, (rr, _) in runs.items()}
    rec["head_instr"] = {k: rr.get("head_instr", {}) for k, (rr, _) in runs.items()}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(_jsonable(rec), indent=1) + "\n")
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--finalize", nargs="+", metavar="NAME=RUN_DIR",
                    help="write the committed record from run directories (run.json + raw.json); needs core=...")
    ap.add_argument("--meta", default=None, help="provenance JSON merged into the committed record")
    ap.add_argument("--snapshot", default=str(Q.SNAPSHOT))
    ap.add_argument("--windows", type=int, default=16)
    ap.add_argument("--ctx", type=int, default=2048)
    ap.add_argument("--mmlu", type=int, default=0)
    ap.add_argument("--mmlu-seed", type=int, default=0)
    ap.add_argument("--stress", action="store_true", help="add the four worst-case stress sequences")
    ap.add_argument("--stress-ctx", type=int, default=2048)
    ap.add_argument("--gen-file", default=None, help="JSON [{name, ids, prompt_len}]: greedy continuations to score")
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--modes", default="a,a2,b,b_nam,b_tf,b_nam_tf,a2_tf")
    ap.add_argument("--tf-chunks", type=int, default=2)
    ap.add_argument("--work", default=None)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--max-layers", type=int, default=0)
    ap.add_argument("--out", default=None, help="run record (per-layer stats, args); the committed record with --finalize")
    ap.add_argument("--raw-out", default=None, help="per-sequence raw records")
    ap.add_argument("--partial", default=None)
    args = ap.parse_args()
    if args.finalize:
        meta = json.loads(Path(args.meta).read_text()) if args.meta else {}
        rec = finalize(dict(a.split("=", 1) for a in args.finalize), args.out or str(OUT), meta)
        print(json.dumps(rec["verdict"]["quality"], indent=1))
        print(json.dumps({k: v["pass"] for k, v in rec["verdict"]["stability"]["criteria"].items()}, indent=1))
        return
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    with ieee_division():
        cfg, seqs, per_seq, stats, head_instr, wall = run(args)
    rec = {"schema": SCHEMA + ".run", "tool": "tools/deepseek_v41_nam_quality.py", "args": vars(args),
           "wall_s": wall, "layers": stats["layers"], "head_instr": head_instr}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(_jsonable(rec)) + "\n")
    Path(args.raw_out).write_text(json.dumps(_jsonable(per_seq)))
    print("done", wall, flush=True)


if __name__ == "__main__":
    main()
