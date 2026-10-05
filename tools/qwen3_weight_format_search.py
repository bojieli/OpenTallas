#!/usr/bin/env python3
"""Search for the lowest-bit Qwen3-8B weight format that a mask ROM can ship and that
meets the deployment quality threshold (tools/qwen3_deployment_quality.py THRESHOLD:
<= +2% WikiText-2 perplexity at 2K and 8K, <= 1.0 pt MMLU drop, against vendor BF16).

Every format here is a FIXED post-training format: integer codes (or indices into a
fixed codebook) with one BF16 scale per group of g weights along K, optionally two
code widths mixed per group (one width-flag bit per group), and optionally a fixed
orthogonal transform folded into the stored matrices.  Nothing depends on runtime
data, so every format can be written into mask ROM.

Methods (all built in memory from the HF snapshot; nothing quantised is written to
disk):

* GPTQ (Frantar et al. 2022) with STATIC groups (scales fixed before the column
  sweep, so the ROM stores contiguous groups) and optional act-order (columns swept
  in decreasing Hessian-diagonal order; only the sweep order changes, not the
  storage), 1% dampening, sequential layer by layer on C4 calibration text through
  the already-quantised earlier layers.
* Sensitivity-based mixed precision (``--alloc fisher``): each group's benefit of the
  high width is its loss-weighted output-error reduction,
  F_out[n] * sum_{k in group} E[x_k^2] * (e_lo[n,k]^2 - e_hi[n,k]^2), with E[x_k^2]
  the input second moment and F_out[n] = E[(dL/dy_n)^2] the empirical Fisher of the
  output channel (a diagonal K-FAC estimate), both measured in one backward pass of
  the BF16 model on calibration text in the (rotated) coordinates the ROM stores.
  ``--scope global`` ranks all groups of the whole model against one budget (layers
  and matrices get different high-width fractions); ``matrix`` keeps the fraction
  per matrix.  ``--alloc weight`` is the plain weight-space MSE reduction of the
  earlier tool.
* AWQ-style input channel scaling (``--awq``): s = E|x|^alpha, alpha grid-searched per
  matrix for the output error of the RTN-quantised W diag(s).  ``down`` folds 1/s
  into the up-projection rows (free in the datapath); ``all`` also scales the q/k/v
  and gate/up inputs, which under the contract's norm fold costs one per-channel
  multiply of the normalised input (``pre`` vectors).
* Rotation (QuaRot/SpinQuant-style randomised Hadamard, ``--rot``): ``res`` rotates
  the residual stream (embedding, every matrix reading or writing it, final norm
  folded into lm_head; zero datapath cost because the contract already folds the
  RMSNorm weights); ``vo`` adds a per-head rotation of V folded into v_proj rows and
  o_proj columns (free); ``down`` adds an ONLINE randomised Hadamard of the down
  projection input in blocks of 4,096 (a new datapath unit: an FWHT per token).
* Codebooks (``lm3``/``lm4`` element types): a fixed, global Lloyd-Max codebook for
  a unit Gaussian (the weight distribution after rotation) on the INT8 grid, scaled
  per group: a 2^b-entry lookup per weight ahead of the multiplier.

Format specs: ``<elem>[+<elem>@<frac>]:g<group>`` where elem is int<b> or lm<b>, e.g.
``int3+int6@0.125:g128`` (the earlier q35 point), ``int4:g128``,
``int4+int8@0.0625:g128``.  bits/weight = b_lo + (b_hi - b_lo) frac + 16/g
(+ 1/g flag bit when mixed).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as Fn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qwen3_deployment_quality as Q  # noqa: E402

F32, BF16 = torch.float32, torch.bfloat16
ROOT = Path(__file__).resolve().parents[1]


# -- element types and formats ------------------------------------------------------
def lloyd_max_gaussian(nlev, iters=400):
    """Lloyd-Max quantiser levels of N(0, 1) with nlev levels (symmetric)."""
    from math import erf, exp, pi, sqrt
    pdf = lambda t: exp(-t * t / 2) / sqrt(2 * pi)
    cdf = lambda t: 0.5 * (1 + erf(t / sqrt(2)))
    lev = np.linspace(-2.5, 2.5, nlev)
    for _ in range(iters):
        b = np.concatenate([[-np.inf], (lev[1:] + lev[:-1]) / 2, [np.inf]])
        new = []
        for i in range(nlev):
            a, c = b[i], b[i + 1]
            pa = 0.0 if a == -np.inf else pdf(a)
            pc = 0.0 if c == np.inf else pdf(c)
            mass = (1.0 if c == np.inf else cdf(c)) - (0.0 if a == -np.inf else cdf(a))
            new.append((pa - pc) / mass)
        lev = np.array(new)
    return lev


class Elem:
    """A code set: integer codes, or a codebook of integers on the INT8 grid.
    `lmax` is the level a group's scale maps to its clipped absmax."""

    def __init__(self, name):
        self.name = name
        if name.startswith("int"):
            # int<b>: codes -2^(b-1) .. 2^(b-1)-1; int<b>s: symmetric, -(2^(b-1)-1) .. 2^(b-1)-1
            sym = name.endswith("s")
            self.b = int(name[3:].rstrip("s"))
            self.kind = "int"
            self.qmin, self.qmax = -(2 ** (self.b - 1)) + int(sym), 2 ** (self.b - 1) - 1
            self.lmax = self.qmax
            self.levels = None
            self.clip_grid = np.linspace(0.5, 1.0, 21)
        elif name == "fp8":
            # FP8 E4M3 (bias 7, max 448, subnormals, RNE, saturating): the golden's to_fp8,
            # i.e. the KV cache's element type, here as a weight element with a BF16 scale
            self.b = 8
            self.kind = "fp8"
            self.levels = None
            self.lmax = 448.0
            self.clip_grid = np.linspace(0.5, 1.0, 21)
        elif name.startswith("lm"):
            self.b = int(name[2:])
            self.kind = "cb"
            lev = lloyd_max_gaussian(2 ** self.b)
            lev = np.round(lev / lev.max() * 127).astype(np.int64)
            assert len(set(lev.tolist())) == len(lev)
            self.levels_np = lev
            self.levels = torch.tensor(lev, dtype=F32)
            self.mids = (self.levels[1:] + self.levels[:-1]) / 2
            self.lmax = 127
            self.clip_grid = np.linspace(0.3, 1.0, 29)
        else:
            raise ValueError(name)

    def q(self, t):
        """Nearest code value of t (already divided by the scale)."""
        if self.kind == "int":
            return torch.clamp(torch.round(t), self.qmin, self.qmax)
        if self.kind == "fp8":
            return Q.to_fp8(t)
        if self.levels.device != t.device:
            self.levels = self.levels.to(t.device)
            self.mids = (self.levels[1:] + self.levels[:-1]) / 2
        return self.levels[torch.bucketize(t.contiguous(), self.mids)]


class Fmt:
    """``g0`` = one scale per output channel (a group of the whole row, g = K).
    A trailing ``:absmax`` fixes every scale at absmax / lmax (no clip search)."""

    def __init__(self, spec):
        self.spec = spec
        absmax = spec.endswith(":absmax")
        if absmax:
            spec = spec[:-len(":absmax")]
        body, g = spec.split(":g")
        self.g = int(g)
        if "+" in body:
            lo, rest = body.split("+")
            hi, frac = rest.split("@")
            self.lo, self.hi, self.frac = Elem(lo), Elem(hi), float(frac)
        else:
            self.lo, self.hi, self.frac = Elem(body), None, 0.0
        if absmax:
            for e in (self.lo, self.hi):
                if e is not None:
                    e.clip_grid = np.array([1.0])

    def for_k(self, K):
        """This format with a per-channel group (g0) resolved to the row length K."""
        if self.g:
            return self
        f = Fmt(self.spec.replace(":g0", f":g{K}"))
        f.spec = self.spec
        return f

    @property
    def code_dtype(self):
        """Stored code tensor: integers (INT, codebook levels) in int8; E4M3 values in
        BF16, which holds every E4M3 value exactly."""
        kinds = {self.lo.kind} | ({self.hi.kind} if self.hi is not None else set())
        return BF16 if "fp8" in kinds else torch.int8

    @property
    def mixed(self):
        return self.hi is not None and self.frac > 0

    def bits(self, f_hi=None):
        f = self.frac if f_hi is None else f_hi
        b = self.lo.b + ((self.hi.b - self.lo.b) * f if self.mixed else 0) + 16.0 / self.g
        return b + (1.0 / self.g if self.mixed else 0.0)


def rtn_scales(wg, e, colw=None):
    """Per-group BF16 scale of element type e for wg [..., G, g], clip ratio chosen per
    group to minimise the (column-weighted by colw [G, g], if given) squared error.
    Returns (scale [..., G, 1], err [..., G])."""
    amax = wg.abs().amax(-1, keepdim=True).clamp_min(1e-30)
    best_e = best_s = None
    for r in e.clip_grid:
        s = Q.to_bf16(amax * float(r) / e.lmax).clamp_min(1e-30)
        d = (e.q(wg / s) * s - wg) ** 2
        err = (d * colw).sum(-1) if colw is not None else d.sum(-1)
        if best_e is None:
            best_e, best_s = err, s
        else:
            better = err < best_e
            best_e = torch.where(better, err, best_e)
            best_s = torch.where(better[..., None], s, best_s)
    return best_s, best_e


# -- orthogonal transforms (folded into the ROM matrices) ------------------------------
def signs(n, seed):
    g = torch.Generator().manual_seed(seed)
    return (torch.randint(0, 2, (n,), generator=g) * 2 - 1).to(F32)


def had_k(W, d, n):
    """W [N, K] -> W diag(d) blockdiag(H_n / sqrt n)   (rotate along K)."""
    return Q.hadamard_blocks(W * d.to(W.device)[None, :], n)


def had_n(W, d, n):
    """W [N, K] -> blockdiag(H_n / sqrt n) diag(d) W   (rotate along N)."""
    return Q.hadamard_blocks((W * d.to(W.device)[:, None]).t().contiguous(), n).t().contiguous()


class Prep:
    """The stored (pre-quantisation) matrices: norm-folded, optionally rotated, in
    FP32 on the GPU, one layer at a time."""

    def __init__(self, sd, cfg, rot, device):
        self.sd, self.cfg, self.rot, self.dev = sd, cfg, set(rot.split("+")) - {"none", ""}, device
        self.H, self.NH, self.KV, self.HD = cfg["hidden_size"], cfg["num_attention_heads"], cfg["num_key_value_heads"], cfg["head_dim"]
        self.FF = cfg["intermediate_size"]
        self.d_res = signs(self.H, 1)
        self.d_v = signs(self.HD, 2)
        self.d_down = signs(self.FF, 3)
        self.nd = min(4096, self.FF & -self.FF)      # the online Hadamard block (4,096 for 12,288)

    def g(self, n):
        return self.sd[n].to(self.dev).to(F32)

    def layer(self, i):
        p = f"model.layers.{i}."
        ln1, ln2 = self.g(p + "input_layernorm.weight"), self.g(p + "post_attention_layernorm.weight")
        q, k, v = self.g(p + "self_attn.q_proj.weight"), self.g(p + "self_attn.k_proj.weight"), self.g(p + "self_attn.v_proj.weight")
        o = self.g(p + "self_attn.o_proj.weight")
        gt, up, dn = self.g(p + "mlp.gate_proj.weight"), self.g(p + "mlp.up_proj.weight"), self.g(p + "mlp.down_proj.weight")
        # norm fold (the contract's W' = W diag(w)), in FP32 here; the stored matrix is quantised
        q, k, v = q * ln1[None], k * ln1[None], v * ln1[None]
        gt, up = gt * ln2[None], up * ln2[None]
        if "vo" in self.rot:
            dv = self.d_v.repeat(self.KV)
            v = had_n(v, dv, self.HD)
            o = had_k(o, self.d_v.repeat(self.NH), self.HD)
        if "res" in self.rot:
            q, k, v = (had_k(m, self.d_res, self.H) for m in (q, k, v))
            gt, up = had_k(gt, self.d_res, self.H), had_k(up, self.d_res, self.H)
            o, dn = had_n(o, self.d_res, self.H), had_n(dn, self.d_res, self.H)
        if "down" in self.rot:
            dn = had_k(dn, self.d_down, self.nd)
        return {"qkv": torch.cat([q, k, v]), "o": o, "gu": torch.cat([gt, up]), "down": dn,
                "qn": self.g(p + "self_attn.q_norm.weight"), "kn": self.g(p + "self_attn.k_norm.weight")}

    def lm(self):
        w = self.g("lm_head.weight") * self.g("model.norm.weight")[None]
        return had_k(w, self.d_res, self.H) if "res" in self.rot else w

    def embed_rows(self, ids):
        """Embedding rows (BF16, as stored) of token ids (any shape), rotated."""
        e = self.sd["model.embed_tokens.weight"][ids.reshape(-1)].to(self.dev).to(F32)
        if "res" in self.rot:
            e = Q.hadamard_blocks(e * self.d_res.to(self.dev), self.H)
        return e.to(BF16).reshape(*ids.shape, self.H)

    def embed_table(self):
        e = self.sd["model.embed_tokens.weight"]
        if "res" not in self.rot:
            return e
        out = torch.empty_like(e)
        for r0 in range(0, e.shape[0], 16384):
            out[r0:r0 + 16384] = Q.hadamard_blocks(e[r0:r0 + 16384].to(self.dev).to(F32) * self.d_res.to(self.dev),
                                                    self.H).to(BF16).cpu()
        return out

    # activations as the ROM matrices see them
    def rot_res_act(self, x):
        return Q.hadamard_blocks(x * self.d_res.to(x.device), self.H) if "res" in self.rot else x

    def rot_v_act(self, a, heads):
        if "vo" not in self.rot:
            return a
        return Q.hadamard_blocks(a * self.d_v.to(a.device).repeat(heads), self.HD)

    def rot_down_act(self, m):
        return Q.hadamard_blocks(m * self.d_down.to(m.device), self.nd) if "down" in self.rot else m


# -- sensitivity: input second moments and output Fisher, in stored coordinates ---------
def fisher_pass(snap, prep, tok, nseq=32, seqlen=1024, seed=1, calib=None):
    """One forward+backward of the BF16 HF model on C4 text.  Returns, per matrix key,
    (E[x_k^2] [K], E[(dL/dy_n)^2] [N]) in the coordinates of the stored matrix."""
    from transformers import AutoModelForCausalLM
    dev = prep.dev
    model = AutoModelForCausalLM.from_pretrained(str(snap), dtype=BF16, attn_implementation="sdpa").to(dev)
    model.eval()
    for p_ in model.parameters():
        p_.requires_grad_(False)
    NH, KV = prep.NH, prep.KV
    L = len(model.model.layers)
    acc = {}
    ntok = [0]

    def add(key, idx, v):
        a = acc.setdefault(key, [None, None])
        v = v.detach().to(F32).reshape(-1, v.shape[-1]).pow(2).sum(0)
        a[idx] = v if a[idx] is None else a[idx] + v

    def xhat(x):
        x = x.to(F32)
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + prep.cfg["rms_norm_eps"])

    hooks = []
    for i, lay in enumerate(model.model.layers):
        at, ml = lay.self_attn, lay.mlp
        hooks.append(lay.input_layernorm.register_forward_pre_hook(
            lambda m, a, i=i: add(f"{i}.qkv", 0, prep.rot_res_act(xhat(a[0])))))
        hooks.append(lay.post_attention_layernorm.register_forward_pre_hook(
            lambda m, a, i=i: add(f"{i}.gu", 0, prep.rot_res_act(xhat(a[0])))))
        hooks.append(at.o_proj.register_forward_pre_hook(
            lambda m, a, i=i: add(f"{i}.o", 0, prep.rot_v_act(a[0].to(F32), NH))))
        hooks.append(ml.down_proj.register_forward_pre_hook(
            lambda m, a, i=i: add(f"{i}.down", 0, prep.rot_down_act(a[0].to(F32)))))
        for nm, mod in (("q", at.q_proj), ("k", at.k_proj), ("v", at.v_proj), ("g", ml.gate_proj), ("u", ml.up_proj)):
            if nm == "v":
                f = lambda m, gi, go, i=i: add(f"{i}.v", 1, prep.rot_v_act(go[0].to(F32), KV))
            else:
                f = lambda m, gi, go, i=i, nm=nm: add(f"{i}.{nm}", 1, go[0])
            hooks.append(mod.register_full_backward_hook(f))
        hooks.append(at.o_proj.register_full_backward_hook(
            lambda m, gi, go, i=i: add(f"{i}.o", 1, prep.rot_res_act(go[0].to(F32)))))
        hooks.append(ml.down_proj.register_full_backward_hook(
            lambda m, gi, go, i=i: add(f"{i}.down", 1, prep.rot_res_act(go[0].to(F32)))))
    hooks.append(model.model.norm.register_forward_pre_hook(
        lambda m, a: add("lm_head", 0, prep.rot_res_act(xhat(a[0])))))
    hooks.append(model.lm_head.register_full_backward_hook(lambda m, gi, go: add("lm_head", 1, go[0])))
    if calib is None:
        calib = Q.c4_calibration(tok, nseq, seqlen, seed=seed)
    for s in range(calib.shape[0]):
        ids = calib[s:s + 1].to(dev)
        with torch.enable_grad():
            emb = model.model.embed_tokens(ids).detach().requires_grad_(True)
            out = model(inputs_embeds=emb, labels=ids, use_cache=False)
            out.loss.backward()
        ntok[0] += ids.numel()
    for h in hooks:
        h.remove()
    res = {}
    for i in range(L):
        a = acc
        res[f"{i}.qkv"] = (a[f"{i}.qkv"][0], torch.cat([a[f"{i}.q"][1], a[f"{i}.k"][1], a[f"{i}.v"][1]]))
        res[f"{i}.gu"] = (a[f"{i}.gu"][0], torch.cat([a[f"{i}.g"][1], a[f"{i}.u"][1]]))
        res[f"{i}.o"] = tuple(a[f"{i}.o"])
        res[f"{i}.down"] = tuple(a[f"{i}.down"])
    res["lm_head"] = tuple(acc["lm_head"])
    res = {k: (v[0].cpu() / ntok[0], v[1].cpu() / ntok[0]) for k, v in res.items()}
    del model
    torch.cuda.empty_cache()
    return res


def kth_largest(v, k):
    return torch.sort(v.to("cuda"), descending=True).values[k - 1].item()


def group_gains(W, fmt, hx=None, fy=None, rows=4096):
    """Per-group benefit [N, K/g] of the high width: (output-Fisher x input-moment)
    weighted squared-error reduction, or plain weight MSE reduction if hx is None."""
    N, K = W.shape
    g = fmt.g
    out = torch.empty((N, K // g), dtype=F32)
    colw = hx.to(W.device).view(K // g, g) if hx is not None else None
    for r0 in range(0, N, rows):
        wg = W[r0:r0 + rows].reshape(-1, K // g, g)
        _, e_lo = rtn_scales(wg, fmt.lo, colw)
        _, e_hi = rtn_scales(wg, fmt.hi, colw)
        gain = e_lo - e_hi
        if fy is not None:
            gain = gain * fy[r0:r0 + rows].to(W.device)[:, None]
        out[r0:r0 + rows] = gain.cpu()
    return out


# -- GPTQ with static groups and optional act-order ---------------------------------------
def gptq(W, H, fmt, use_hi, actorder=True, percdamp=0.01, blocksize=128, row_chunk=32768, lazy=False):
    """W [N, K] FP32 (GPU), H [K, K].  Returns (codes int8 [N, K] CPU, scales BF16
    [N, K/g] CPU).  Groups are contiguous in the stored (original) column order; the
    columns may be swept in act-order.  Scales (Hessian-diagonal weighted MSE clip):
    static = fixed from the original W before the sweep; lazy = fixed when the sweep
    reaches the group's first column, from the group's error-updated weights at that
    moment (so the clip covers what GPTQ's updates pushed into the group; still one
    stored scale per group)."""
    N, K = W.shape
    g = fmt.g
    H = H.clone()
    dead = torch.diag(H) == 0
    H[dead, dead] = 1
    W = W.clone()
    W[:, dead] = 0
    colw = torch.diag(H).view(K // g, g)
    perm = torch.argsort(torch.diag(H), descending=True) if actorder else torch.arange(K, device=W.device)
    inv = torch.argsort(perm)
    H = H[perm][:, perm]
    H += percdamp * torch.mean(torch.diag(H)) * torch.eye(K, device=W.device)
    Hinv = torch.linalg.cholesky(torch.cholesky_inverse(torch.linalg.cholesky(H)), upper=True)
    del H
    gidx = (perm // g).tolist()
    gpos = inv.view(K // g, g)          # permuted positions of each group's columns
    codes = torch.empty((N, K), dtype=fmt.code_dtype)
    scales = torch.empty((N, K // g), dtype=BF16)
    for r0 in range(0, N, row_chunk):
        Wr = W[r0:r0 + row_chunk]
        n = Wr.shape[0]
        wg = Wr.reshape(n, K // g, g)
        s_lo, _ = rtn_scales(wg, fmt.lo, colw)
        sc = s_lo[..., 0]
        uh = None
        if fmt.mixed:
            s_hi, _ = rtn_scales(wg, fmt.hi, colw)
            uh = use_hi[r0:r0 + row_chunk].to(W.device)
            sc = torch.where(uh, s_hi[..., 0], sc)
        done = [not lazy] * (K // g)
        Wp = Wr[:, perm].clone()
        cp = torch.empty_like(Wp)
        for i1 in range(0, K, blocksize):
            i2 = min(i1 + blocksize, K)
            W1 = Wp[:, i1:i2].clone()
            Err1 = torch.zeros_like(W1)
            Hinv1 = Hinv[i1:i2, i1:i2]
            for i in range(i2 - i1):
                col = gidx[i1 + i]
                if not done[col]:
                    pp = gpos[col]
                    cur = Wp[:, pp].clone()
                    inb = (pp >= i1) & (pp < i2)
                    cur[:, inb] = W1[:, pp[inb] - i1]
                    cw = colw[col][None]
                    s_new = rtn_scales(cur[:, None, :], fmt.lo, cw)[0][:, 0, 0]
                    if uh is not None:
                        s_new = torch.where(uh[:, col], rtn_scales(cur[:, None, :], fmt.hi, cw)[0][:, 0, 0], s_new)
                    sc[:, col] = s_new
                    done[col] = True
                w = W1[:, i]
                s = sc[:, col]
                t = w / s
                q = fmt.lo.q(t)
                if uh is not None:
                    q = torch.where(uh[:, col], fmt.hi.q(t), q)
                cp[:, i1 + i] = q
                err = (w - q * s) / Hinv1[i, i]
                W1[:, i:] -= err[:, None] * Hinv1[i, i:][None, :]
                Err1[:, i] = err
            Wp[:, i2:] -= Err1 @ Hinv[i1:i2, i2:]
        scales[r0:r0 + n] = sc.to(BF16).cpu()
        codes[r0:r0 + n] = cp[:, inv].to(fmt.code_dtype).cpu()
        del Wp, cp
    return codes, scales


def rtn(W, fmt, rows=8192):
    """Round-to-nearest (per-group MSE-optimal clip, data-free): W [N, K] ->
    (codes [N, K] CPU, scales BF16 [N, K/g] CPU)."""
    N, K = W.shape
    g = fmt.g
    codes = torch.empty((N, K), dtype=fmt.code_dtype)
    scales = torch.empty((N, K // g), dtype=BF16)
    for r0 in range(0, N, rows):
        wg = W[r0:r0 + rows].to(F32).reshape(-1, K // g, g)
        sc, _ = rtn_scales(wg, fmt.lo)
        codes[r0:r0 + rows] = fmt.lo.q(wg / sc).reshape(-1, K).to(fmt.code_dtype).cpu()
        scales[r0:r0 + rows] = sc[..., 0].to(BF16).cpu()
    return codes, scales


def dq(codes, scales, dev):
    g = codes.shape[1] // scales.shape[1]
    return Q.dequant(codes.to(dev), scales.to(dev), g=g)


# -- AWQ-style scale search ----------------------------------------------------------------
def awq_scale(W, X, fmt, grid=np.linspace(0, 1, 11), rows=2048):
    """X [T, K] sample of the matrix input.  s = mean|x|^a / normaliser, a chosen to
    minimise ||X W^T - (X/s) Q(W s)^T||^2 (RTN in the low element type).  Returns
    (s with BF16-exact 1/s, alpha)."""
    xm = X.abs().mean(0).clamp_min(1e-6)
    ref = X @ W.t()
    best = (None, None, 0.0)
    for a in grid:
        s = xm ** float(a)
        s = s / (s.max() * s.min()).sqrt()
        pre = Q.to_bf16(1.0 / s)
        s = 1.0 / pre
        Ws = W * s[None]
        wg = Ws.reshape(W.shape[0], -1, fmt.g)
        sc, _ = rtn_scales(wg, fmt.lo)
        Wq = (fmt.lo.q(wg / sc) * sc).reshape(W.shape)
        err = ((X * pre[None]) @ Wq.t() - ref).pow(2).sum().item()
        if best[0] is None or err < best[0]:
            best = (err, s, float(a))
    return best[1], best[2]


# -- the sequential build -------------------------------------------------------------------
@torch.no_grad()
def build(snap, fmt, rot="none", actorder=True, alloc="weight", scope="matrix", awq="none",
          nseq=128, seqlen=2048, chunk=8, fisher=None, log=print, quantise=True, calib=None, fisher_calib=None,
          embed_fmt=None, lazy=False, method="gptq", post_scale=False):
    """Returns a weight dict for Q.Qwen3(wfile=...) (norm-folded matrices, usable in
    both the GPU and the contract arithmetic) plus build metadata."""
    from transformers import AutoTokenizer
    dev = torch.device("cuda")
    tok = AutoTokenizer.from_pretrained(str(snap)) if calib is None else None
    if calib is not None:
        nseq, seqlen = calib.shape
        chunk = min(chunk, nseq)
    if method == "rtn":             # data-free: the calibration pass only feeds nothing
        nseq, chunk = min(nseq, chunk), min(nseq, chunk)
    cfg = json.loads((Path(snap) / "config.json").read_text())
    L, Hd, NH, KV, HD, FF = (cfg[k] for k in ("num_hidden_layers", "hidden_size", "num_attention_heads",
                                               "num_key_value_heads", "head_dim", "intermediate_size"))
    eps, theta = cfg["rms_norm_eps"], cfg["rope_theta"]
    sd = Q.load_state(snap, "cpu")
    prep = Prep(sd, cfg, rot, dev)
    meta = {"fmt_spec": fmt.spec, "rot": rot, "actorder": actorder, "alloc": alloc, "scope": scope, "awq": awq,
            "calib": f"C4 en train shard 00000, {nseq} x {seqlen} tokens, seed 0",
            "scales": "lazy" if lazy else "static", "method": method, "post_scale": post_scale}
    if post_scale:
        assert fmt.g == 0 and not fmt.mixed, "a post-accumulation scale needs one scale per output channel"
    t_all = time.time()
    # ---- allocation of the high width -------------------------------------------------
    use_hi = {}
    if quantise and fmt.mixed:
        if alloc == "fisher" and fisher is None:
            t0 = time.time()
            fisher = fisher_pass(snap, prep, tok, calib=fisher_calib)
            meta["fisher_s"] = time.time() - t0
            log(f"  fisher pass {meta['fisher_s']:.0f}s")
        gains = {}
        for i in range(L):
            lay = prep.layer(i)
            for key in ("qkv", "o", "gu", "down"):
                hx, fy = fisher[f"{i}.{key}"] if alloc == "fisher" else (None, None)
                gains[f"{i}.{key}"] = group_gains(lay[key], fmt, hx, fy)
            del lay
        hx, fy = fisher["lm_head"] if alloc == "fisher" else (None, None)
        gains["lm_head"] = group_gains(prep.lm(), fmt, hx, fy)
        if scope == "global":
            allg = torch.cat([v.reshape(-1) for v in gains.values()])
            nhi = int(round(fmt.frac * allg.numel()))
            thr = kth_largest(allg, nhi)
            del allg
            use_hi = {k: v >= thr for k, v in gains.items()}
        else:
            for k, v in gains.items():
                nhi = int(round(fmt.frac * v.numel()))
                thr = kth_largest(v.reshape(-1), nhi)
                use_hi[k] = v >= thr
        del gains
        meta["hi_fraction_by_matrix"] = {k: float(v.float().mean()) for k, v in use_hi.items()}
        log(f"  allocation done ({time.time() - t_all:.0f}s)")
    res = {"fmt": fmt.spec, "fold": True, "w": {}, "pre": {}, "norm": torch.ones(Hd, dtype=BF16),
           "post_scale": post_scale,
           "embed": prep.embed_table() if "res" in prep.rot else None,
           "down_had": prep.d_down.clone() if "down" in prep.rot else None, "down_had_block": prep.nd}
    nbits = {}

    def store(key, W, H, name):
        if not quantise:
            res["w"][key] = (W.to(BF16).cpu(), None, 16.0)
            return W.to(BF16)
        uh = use_hi.get(key)
        fk = fmt.for_k(W.shape[1])
        if method == "rtn":
            c, s = rtn(W, fk)
        else:
            c, s = gptq(W, H, fk, uh, actorder=actorder, lazy=lazy)
        f_hi = float(uh.float().mean()) if uh is not None else 0.0
        b = fk.bits(f_hi)
        res["w"][key] = (c, s, b)
        nbits.setdefault(name, []).append((b, W.numel()))
        return dq(c, s, dev).to(BF16)

    if calib is None:
        calib = Q.c4_calibration(tok, nseq, seqlen)
    xs = torch.empty((nseq, seqlen, Hd), dtype=BF16)
    for c0 in range(0, nseq, chunk):
        xs[c0:c0 + chunk] = prep.embed_rows(calib[c0:c0 + chunk]).cpu()
    inv = 1.0 / (theta ** (torch.arange(0, HD, 2, dtype=torch.int64).to(F32) / HD))
    fr = torch.arange(seqlen, dtype=F32)[:, None] * inv[None, :]
    emb = torch.cat([fr, fr], -1).to(dev)
    cos, sin = emb.cos().to(BF16), emb.sin().to(BF16)
    rotf = lambda t: torch.cat([-t[..., HD // 2:], t[..., :HD // 2]], -1)

    def rms(x, w=None):
        xf = x.to(F32)
        xf = xf * torch.rsqrt(xf.pow(2).mean(-1, keepdim=True) + eps)
        return xf.to(BF16) if w is None else w.to(BF16) * xf.to(BF16)

    def hess(fn, K):
        if method == "rtn":
            return None
        Hm = torch.zeros((K, K), device=dev, dtype=F32)
        for c0 in range(0, nseq, chunk):
            a = fn(c0).reshape(-1, K).to(F32)
            Hm += a.t() @ a
        return Hm * (2.0 / (nseq * seqlen))

    X = lambda c0: xs[c0:c0 + chunk].to(dev)
    awq_meta = {}
    for i in range(L):
        t0 = time.time()
        lay = prep.layer(i)
        qn, kn = lay["qn"], lay["kn"]
        pre1 = pre2 = None
        if awq != "none" and quantise:
            def samp(fn):
                parts = []
                for c0 in range(0, min(nseq, 32), chunk):
                    a_ = fn(c0)
                    parts.append(a_.reshape(-1, a_.shape[-1])[::8].to(F32))
                return torch.cat(parts)
            if awq == "all":
                s, a1 = awq_scale(lay["qkv"], samp(lambda c0: rms(X(c0))), fmt)
                lay["qkv"] = lay["qkv"] * s[None]
                pre1 = 1.0 / s
                s, a2 = awq_scale(lay["gu"], samp(lambda c0: rms(X(c0))), fmt)
                lay["gu"] = lay["gu"] * s[None]
                pre2 = 1.0 / s
                awq_meta[f"{i}.qkv"], awq_meta[f"{i}.gu"] = a1, a2
                res["pre"][f"{i}.qkv"], res["pre"][f"{i}.gu"] = pre1.cpu(), pre2.cpu()
            if "down" not in prep.rot:
                gu_f = lay["gu"].to(BF16)

                def mlp_in(c0):
                    h = rms(X(c0)) if pre2 is None else (rms(X(c0)).to(F32) * pre2).to(BF16)
                    gt, up = Fn.linear(h, gu_f).split([FF, FF], -1)
                    return Fn.silu(gt) * up
                s, a3 = awq_scale(lay["down"], samp(mlp_in), fmt)
                lay["down"] = lay["down"] * s[None]
                lay["gu"][FF:] = lay["gu"][FF:] / s[:, None]
                awq_meta[f"{i}.down"] = a3
                del gu_f
        in1 = (lambda x: rms(x)) if pre1 is None else (lambda x: (rms(x).to(F32) * pre1).to(BF16))
        in2 = (lambda x: rms(x)) if pre2 is None else (lambda x: (rms(x).to(F32) * pre2).to(BF16))
        qkv_q = store(f"{i}.qkv", lay["qkv"], hess(lambda c0: in1(X(c0)), Hd) if quantise else None, "qkv")

        def attn_in(c0):
            x = X(c0)
            B = x.shape[0]
            q, k, v = Fn.linear(in1(x), qkv_q).split([NH * HD, KV * HD, KV * HD], -1)
            q = rms(q.view(B, seqlen, NH, HD), qn).transpose(1, 2)
            k = rms(k.view(B, seqlen, KV, HD), kn).transpose(1, 2)
            v = v.view(B, seqlen, KV, HD).transpose(1, 2)
            q, k = q * cos + rotf(q) * sin, k * cos + rotf(k) * sin
            a = Fn.scaled_dot_product_attention(q, k, v, is_causal=True, enable_gqa=True)
            return a.transpose(1, 2).reshape(B, seqlen, NH * HD)
        o_q = store(f"{i}.o", lay["o"], hess(attn_in, NH * HD) if quantise else None, "o")
        for c0 in range(0, nseq, chunk):
            xs[c0:c0 + chunk] = (X(c0) + Fn.linear(attn_in(c0), o_q)).cpu()
        gu_q = store(f"{i}.gu", lay["gu"], hess(lambda c0: in2(X(c0)), Hd) if quantise else None, "gate_up")

        def down_in(c0):
            gt, up = Fn.linear(in2(X(c0)), gu_q).split([FF, FF], -1)
            m = Fn.silu(gt) * up
            return prep.rot_down_act(m.to(F32)).to(BF16) if "down" in prep.rot else m
        d_q = store(f"{i}.down", lay["down"], hess(down_in, FF) if quantise else None, "down")
        for c0 in range(0, nseq, chunk):
            xs[c0:c0 + chunk] = (X(c0) + Fn.linear(down_in(c0), d_q)).cpu()
        del qkv_q, o_q, gu_q, d_q, lay
        torch.cuda.empty_cache()
        log(f"  layer {i} ({time.time() - t0:.0f}s)")
    store("lm_head", prep.lm(), hess(lambda c0: rms(X(c0)), Hd) if quantise else None, "lm_head")
    meta["awq_alpha"] = awq_meta
    if embed_fmt:
        # The embedding table is ROM-resident too: round-to-nearest (per-group MSE clip)
        # in embed_fmt's low element type along the hidden dimension, kept as the exact
        # FP32 dequantised values (the GPU arithmetic rounds them to BF16 on lookup).
        ef = Fmt(embed_fmt).for_k(Hd)
        tab = res["embed"] if res["embed"] is not None else sd["model.embed_tokens.weight"]
        out = torch.empty(tab.shape, dtype=F32)
        for r0 in range(0, tab.shape[0], 8192):
            wg = tab[r0:r0 + 8192].to(dev).to(F32).reshape(-1, Hd // ef.g, ef.g)
            sc, _ = rtn_scales(wg, ef.lo)
            out[r0:r0 + 8192] = (ef.lo.q(wg / sc) * sc).reshape(-1, Hd).cpu()
        res["embed"] = out
        meta["embed_fmt"] = embed_fmt
        meta["embed_bits"] = ef.bits()
    if nbits:
        tot = sum(n for v in nbits.values() for _, n in v)
        meta["bits_per_weight_matrices"] = sum(b * n for v in nbits.values() for b, n in v) / tot
        meta["bits_by_matrix_type"] = {k: sum(b * n for b, n in v) / sum(n for _, n in v) for k, v in nbits.items()}
    meta["build_s"] = time.time() - t_all
    res["meta"] = meta
    del sd, xs
    torch.cuda.empty_cache()
    return res


# -- evaluation ----------------------------------------------------------------------------
def evaluate(snap, wsrc, arith, kv, tasks, out_path, windows_2k=1000, windows_8k=1000, mmlu=1000):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(snap))
    t0 = time.time()
    model = Q.Qwen3(snap, arith, "bf16", kv, wfile=wsrc)
    if wsrc is None:            # the vendor BF16 reference itself
        wf, meta = "bf16", None
    else:
        wf = wsrc["fmt"] + "|" + ",".join(f"{k}={v}" for k, v in wsrc["meta"].items()
                                          if k in ("rot", "actorder", "alloc", "scope", "awq", "embed_fmt", "scales",
                                                   "method", "post_scale"))
        meta = wsrc["meta"]
    out = {"mode": "wfs", "arith": arith, "weights": wf, "kv": kv, "groups": Q.SPEC_GROUPS,
           "build": meta, "snapshot": str(snap), "load_s": time.time() - t0,
           "weight_bits": {k: float(np.mean(v)) for k, v in model.bits.items()}}
    outp = Path(out_path)

    def save():
        out["recip_sat_hits"] = int(Q.RECIP_SAT_HITS[0])
        outp.write_text(json.dumps(out))
    print(f"[{arith}/{kv}] {wf} loaded in {out['load_s']:.0f}s mem={torch.cuda.memory_allocated() / 2**30:.1f} GiB", flush=True)
    if "ppl2k" in tasks or "ppl8k" in tasks:
        ids = Q.wikitext_ids(tok)
        if "ppl2k" in tasks:
            Q.run_ppl(model, ids, 2048, windows_2k, out)
            save()
        if "ppl8k" in tasks:
            Q.run_ppl(model, ids, 8192, windows_8k, out)
            save()
    if "mmlu" in tasks:
        out["mmlu"] = Q.run_mmlu(model, tok, Q.mmlu_items(mmlu))
        print(f"  mmlu acc {np.mean([r['correct'] for r in out['mmlu']]):.4f}", flush=True)
        save()
    if "mmlu_full" in tasks:
        # all 14,042 MMLU test questions: resolves the MMLU delta ~4x finer than the
        # 1,000-question verdict subset (supplementary; the verdict keeps the subset)
        out["mmlu_full"] = Q.run_mmlu(model, tok, Q.mmlu_items(14042))
        print(f"  mmlu_full acc {np.mean([r['correct'] for r in out['mmlu_full']]):.4f}", flush=True)
        save()
    out["wall_s"] = time.time() - t0
    save()
    del model
    torch.cuda.empty_cache()
    return out


def quick_stats(raw, ref):
    """Point estimates of one raw run against the reference raw (for logs)."""
    s = {}
    for ctx in (2048, 8192):
        k = f"ppl_{ctx}"
        if k in raw and k in ref:
            n = min(len(raw[k]), len(ref[k]))
            a = np.concatenate([w["nll"] for w in raw[k][:n]]).mean()
            b = np.concatenate([w["nll"] for w in ref[k][:n]]).mean()
            s[k] = float(np.exp(a - b) - 1)
    if "mmlu" in raw and "mmlu" in ref:
        s["mmlu_pt"] = 100 * (np.mean([r["correct"] for r in raw["mmlu"]]) - np.mean([r["correct"] for r in ref["mmlu"]]))
    return s


# -- ROM capacity under the repository's compute-in-ROM cell rule --------------------------
QWEN3_PARAMS = 8_190_735_360        # configs/models/qwen3-8b.json total_parameters (ROM-resident, incl. embedding)


def cells_per_weight(fmt, width=4, side_bits=None):
    """CimCellAccounting (src/opentallas/roofline.py): each weight element takes
    ceil(bits / width) select cells of its own; block scales (and the per-group width
    flag of a mixed format) are stored at full cell width.  side_bits overrides the
    per-weight scale overhead (a per-channel format's depends on the row length)."""
    f = fmt.frac if fmt.mixed else 0.0
    el = (1 - f) * math.ceil(fmt.lo.b / width) + (f * math.ceil(fmt.hi.b / width) if fmt.mixed else 0.0)
    if side_bits is None:
        side_bits = (16.0 + (1.0 if fmt.mixed else 0.0)) / fmt.g
    return el + side_bits / width


def rom_capacity(fmt, f_hi=None, bits_measured=None):
    """Historical one-reticle feasibility counterfactual for format screening.

    The adopted O4 baseline is a two-reticle package in qwen3_budget.json.  Keep
    this screen tied to the frozen C0 one-reticle scenario so an unrelated O4
    re-budget cannot silently change the search record's area comparison.
    """
    sys.path.insert(0, str(ROOT / "src"))
    from opentallas.roofline import Technology
    tech = Technology(raw=json.loads((ROOT / "configs/hardware/technology.json").read_text()))
    cells_mm2 = tech.rom_bits_per_mm2_for("N6", "per_stream", None).value     # select cells / mm2
    scenario = json.loads((ROOT / "results/arch/qwen3_8bit_design.json").read_text())
    base = scenario["configurations"]["C0_single_reticle"]["ledger"]
    anchor_rom = scenario["density"]["anchor_35bit_rom_mm2"]
    drafter_params = scenario["inventory"]["drafter_params"]
    if f_hi is not None and fmt.mixed:
        fmt = Fmt(f"{fmt.lo.name}+{fmt.hi.name}@{f_hi}:g{fmt.g}")
    side = None
    if bits_measured is not None and not fmt.mixed:
        side = bits_measured - fmt.lo.b           # the measured per-weight scale overhead
    bits = fmt.bits() if side is None else bits_measured
    cpw = cells_per_weight(fmt, side_bits=side)
    target = QWEN3_PARAMS * cpw / cells_mm2
    drafter = drafter_params * cpw / cells_mm2
    # The C0 ledger stores the pool implicitly as its two ROM allocations plus
    # its signed slack.  It is the exact 442.6 mm2 used in the search run.
    pool = base["target_rom_mm2"] + base["drafter_rom_mm2"] + base["slack_mm2"]
    rest = pool - target - drafter
    copy_area = base["lane_copy_mm2"]
    copies = max(0, int(rest // copy_area)) if rest >= 0 else 0
    drafter_35 = drafter_params * (7 / 6) / cells_mm2
    design_m = 1 + max(0, int((pool - anchor_rom - drafter_35) // copy_area))
    eff_3p5 = QWEN3_PARAMS * 3.5 / anchor_rom             # stored bits / mm2 at the historical design point
    return {"bits_per_weight": bits, "cells_per_weight": cpw, "cell_density_per_mm2": cells_mm2,
            "target_rom_mm2": target, "delta_vs_3p5_design_mm2": target - anchor_rom,
            "drafter_rom_mm2_same_format": drafter,
            "pool_target_drafter_lanecopies_mm2": pool, "left_after_roms_mm2": rest,
            "fits_reticle": rest >= 0, "lane_copies_added": copies, "lane_multiplier_m": 1 + copies if rest >= 0 else 0,
            "slack_mm2": rest - copies * copy_area if rest >= 0 else rest,
            "design_point_lane_multiplier_m": design_m,
            "linear_bits_reading_target_rom_mm2": QWEN3_PARAMS * bits / eff_3p5,
            "weight_read_delivery_mj_per_token": 7_568_097_280 * bits / 8 * (0.08 + 0.23) * 1e-9}


def summarize_search(raw_dir, out_path, meta, ref_full=None):
    """Q.summarize over the raw runs (the reference a_bf16.json must be in raw_dir),
    each mode augmented with its build metadata and ROM capacity."""
    tmp = Path(out_path).with_suffix(".tmp.json")
    res = Q.summarize(raw_dir, tmp, {})
    tmp.unlink()
    res["schema"] = "opentallas.qwen3-8b-weight-format-search.v1"
    for k, v in meta.items():
        res[k] = v
    for name, m in res["modes"].items():
        raw = json.loads((Path(raw_dir) / f"{name}.json").read_text())
        if ref_full and "mmlu_full" in raw:
            rf = json.loads(Path(ref_full).read_text())["mmlu_full"]
            c = np.array([x["correct"] for x in raw["mmlu_full"]], float)
            cr = np.array([x["correct"] for x in rf], float)
            m["mmlu_full_14042"] = {
                "questions": int(len(c)), "accuracy": float(c.mean()), "accuracy_ref": float(cr.mean()),
                "delta_pt": float(100 * (c.mean() - cr.mean())),
                "delta_pt_ci95": [100 * v for v in Q._boot(lambda i: c[i].mean() - cr[i].mean(), len(c))],
                "note": "supplementary: all 14,042 MMLU test questions (the verdict keeps the 1,000-question subset)"}
        b = raw.get("build")
        if not b:
            continue
        m["build"] = {k: v for k, v in b.items() if k != "hi_fraction_by_matrix"}
        if "hi_fraction_by_matrix" in b:
            h = b["hi_fraction_by_matrix"]
            m["build"]["hi_fraction_by_matrix_type"] = {
                t: float(np.mean([v for k, v in h.items() if k.endswith(t)])) for t in (".qkv", ".o", ".gu", ".down")}
            m["build"]["hi_fraction_lm_head"] = h.get("lm_head")
            m["build"]["hi_fraction_by_layer"] = [float(np.mean([h[f"{i}.{t}"] for t in ("qkv", "o", "gu", "down")]))
                                                   for i in range(36) if f"{i}.qkv" in h]
        if b.get("fmt_spec") and raw.get("weights", "").split("|")[0] != "bf16":
            fmt = Fmt(b["fmt_spec"])
            f_hi = None
            if fmt.mixed and "hi_fraction_by_matrix" in b:
                bits = b.get("bits_per_weight_matrices")
                f_hi = (bits - fmt.lo.b - 17.0 / fmt.g) / (fmt.hi.b - fmt.lo.b)
            m["rom"] = rom_capacity(fmt, f_hi, b.get("bits_per_weight_matrices"))
    # A verdict is a DEPLOYMENT verdict only in the deployment arithmetic (contract +
    # FP8 KV) with all three measurements; everything else is labelled a screen.
    for name, m in res["modes"].items():
        if name == "a_bf16" or name not in res["verdict"]:
            continue
        have = [k for k in ("wikitext2_2048", "wikitext2_8192", "mmlu") if k in m]
        ok = []
        if "wikitext2_2048" in m:
            ok.append(m["wikitext2_2048"]["rel_delta_ppl"] <= Q.THRESHOLD["ppl_rel_max"])
        if "wikitext2_8192" in m:
            ok.append(m["wikitext2_8192"]["rel_delta_ppl"] <= Q.THRESHOLD["ppl_rel_max"])
        if "mmlu" in m:
            ok.append(m["mmlu"]["delta_pt"] >= -Q.THRESHOLD["mmlu_drop_max_pt"])
        full = len(have) == 3 and m["arith"] == "contract" and m["kv"] == "fp8"
        if not have:
            res["verdict"][name] = "not measured"
        elif full:
            res["verdict"][name] = "acceptable" if all(ok) else "not acceptable"
        else:
            res["verdict"][name] = (f"screen ({m['arith']} arithmetic, {m['kv']} KV; measured "
                                    f"{', '.join(have)}): " + ("passes" if all(ok) else "fails")
                                    + " the measured criteria")
    Path(out_path).write_text(json.dumps(res, indent=1) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fmt", default="int3+int6@0.125:g128", help="format spec, or 'bf16' (transforms only)")
    ap.add_argument("--rot", default="none", help="none | res | res+vo | res+vo+down")
    ap.add_argument("--actorder", type=int, default=1)
    ap.add_argument("--alloc", default="weight", choices=["weight", "fisher"])
    ap.add_argument("--scope", default="matrix", choices=["matrix", "global"])
    ap.add_argument("--awq", default="none", choices=["none", "down", "all"])
    ap.add_argument("--nseq", type=int, default=128)
    ap.add_argument("--embed-fmt", default=None, help="also quantise the (ROM-resident) embedding table, RTN")
    ap.add_argument("--lazy-scales", type=int, default=0, help="GPTQ group scales from the error-updated weights")
    ap.add_argument("--method", default="gptq", choices=["gptq", "rtn"])
    ap.add_argument("--post-scale", type=int, default=0,
                    help="per-channel formats: apply the BF16 scale once to the FP32 dot product "
                         "of codes and activations (Codex's RTL contract) instead of per element")
    ap.add_argument("--fisher-cache", default=None, help="torch file of fisher_pass() output (small: per-channel vectors)")
    ap.add_argument("--arith", default="gpu", help="comma list of gpu,contract (each evaluated in turn)")
    ap.add_argument("--kv", default="bf16", help="comma list aligned with --arith")
    ap.add_argument("--tasks", default="ppl2k,mmlu")
    ap.add_argument("--ppl-windows-2k", type=int, default=1000)
    ap.add_argument("--ppl-windows-8k", type=int, default=1000)
    ap.add_argument("--ppl-windows-8k-contract", type=int, default=16,
                    help="8K windows in the contract arithmetic (the earlier study's 16 of 36)")
    ap.add_argument("--mmlu", type=int, default=1000)
    ap.add_argument("--ref", default=None, help="a_bf16 raw JSON, for a quick log line")
    ap.add_argument("--out", required=True, help="output raw JSON path; with several arith, suffixed _<arith>")
    ap.add_argument("--summarize", default=None, help="directory of raw JSONs (with a_bf16.json) -> --out summary")
    ap.add_argument("--meta", default=None, help="JSON file merged into the summary")
    ap.add_argument("--ref-full", default=None, help="vendor raw JSON with mmlu_full (for the supplementary MMLU)")
    args = ap.parse_args()
    if args.summarize:
        summarize_search(args.summarize, args.out, json.loads(Path(args.meta).read_text()) if args.meta else {},
                         args.ref_full)
        return
    snap = Q.find_snapshot()
    if args.fmt == "vendor":        # the a_bf16 reference through this tool's evaluator
        evaluate(snap, None, "gpu", "bf16", args.tasks.split(","), args.out, args.ppl_windows_2k,
                 args.ppl_windows_8k, args.mmlu)
        return
    quant = args.fmt != "bf16"
    fmt = Fmt(args.fmt if quant else "int8:g128")
    fisher = None
    if args.alloc == "fisher" and args.fisher_cache and Path(args.fisher_cache).exists():
        fisher = torch.load(args.fisher_cache)
    if args.alloc == "fisher" and fmt.mixed and fisher is None:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(str(snap))
        cfg = json.loads((Path(snap) / "config.json").read_text())
        prep = Prep(Q.load_state(snap, "cpu"), cfg, args.rot, torch.device("cuda"))
        t0 = time.time()
        fisher = fisher_pass(snap, prep, tok)
        print(f"  fisher pass {time.time() - t0:.0f}s", flush=True)
        del prep
        if args.fisher_cache:
            torch.save(fisher, args.fisher_cache)
    wsrc = build(snap, fmt, rot=args.rot, actorder=bool(args.actorder), alloc=args.alloc, scope=args.scope,
                 awq=args.awq, nseq=args.nseq, fisher=fisher, quantise=quant, embed_fmt=args.embed_fmt,
                 lazy=bool(args.lazy_scales), method=args.method, post_scale=bool(args.post_scale),
                 log=lambda m: print(m, flush=True))
    if not quant:
        wsrc["fmt"] = "bf16"
    print(f"built {args.fmt}: {json.dumps({k: v for k, v in wsrc['meta'].items() if k != 'hi_fraction_by_matrix'})[:600]}", flush=True)
    ref = json.loads(Path(args.ref).read_text()) if args.ref else None
    ariths, kvs = args.arith.split(","), args.kv.split(",")
    for a, kv in zip(ariths, kvs):
        op = args.out if len(ariths) == 1 else str(Path(args.out).with_name(Path(args.out).stem + f"_{a}_{kv}.json"))
        w8 = args.ppl_windows_8k_contract if a == "contract" else args.ppl_windows_8k
        tasks = [t for t in args.tasks.split(",") if not (t == "mmlu_full" and a == "contract")]
        out = evaluate(snap, wsrc, a, kv, tasks, op, args.ppl_windows_2k, w8, args.mmlu)
        if ref:
            print(f"RESULT {args.fmt} {args.method} rot={args.rot} act={args.actorder} alloc={args.alloc}/{args.scope} awq={args.awq} "
                  f"{a}/{kv}: {quick_stats(out, ref)}", flush=True)


if __name__ == "__main__":
    main()
