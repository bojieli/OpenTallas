#!/usr/bin/env python3
"""qwen_r25: the bit-exact golden of Qwen3-8B decode on the r25 HBM die (TP4), contract r25_prenorm_full_w8.

The arithmetic is the quality harness's `r25_prenorm_full_w8` mode (tools/qwen3_deployment_quality.py, Qwen3(order=
"r25", prenorm=True), weights "w8", KV "fp8") -- the mode the owner's quality run gates -- written as an independent
numpy model on the golden primitives (tools/hdc_golden.py add/mul/exp/rsqrt/to_bf16/to_fp8: IEEE binary32 RNE, every
zero result +0; tools/hdc_golden_v41.csum/div).  `tools/qwen_r25_golden_check.py` proves it equal, value for value,
to the harness on the released checkpoint.  The die decomposition (TP4) is explicit, because r25's summation order
depends on it:

  embedding   x = code[t] * scale[t] (INT8 x BF16, exact in FP32), FP32 residual stream
  RMSNorm     r = rsqrt(csum8(x*x) * fp32(1/4096) + fp32(eps)); h = (x * r) * g          (pre-matvec, FP32)
  matvec      t[n] = csum8_k(bf16(h)[k] * code[n, k])  (chunks of 8 contiguous products from +0, chunk sums a
              pairwise tree padded with +0); y = t * s[n] (one RNE multiply, BF16 row scale)
              qkv / gate-up / lm_head: output rows split over the 4 dies, whole K per die;
              o_proj / down: K split over the 4 dies (die d: its 8 q heads / its 3,072 FFN columns), each die's
              partial a csum8 over its slice, the 4 partials added ((p0 + p1) + (p2 + p3)) in rank order (TU owner
              tree), THEN the row scale
  QK-norm     per head of 128, gain FP32, as RMSNorm
  RoPE        rotate-half over 128 (theta 1e6): cos/sin = fp32(cos(f64(fp32(pos) * fp32(inv_freq))))
              y = [a*cos + b*(-sin), b*cos + a*sin]                                         (FP32)
  KV          K = fp8(rope(k)), V = fp8(v) (E4M3 RNE, saturating 448), appended at the position
  attention   q = bf16(rope(q)); s_p = csum8_d(q * K_p) * fp32(1/sqrt(128)); m = max_p s_p;
              e_p = exp(s_p - m); Z = csum8_p(e_p); pv = csum8_p(bf16(e_p) * V_p) (zero-padded to a power-of-two
              chunk count); o = pv / Z (IEEE divide)                         GQA: q head h reads KV head h // 4
  SwiGLU      act = g / (1 + exp(-g)) (IEEE divide), m = act * u (FP32), then the down matvec rounds bf16(m)
  head        final RMSNorm, lm_head rows split 4 x 37,984, logits FP32, argmax lowest index on ties

Weights: the INT8 image is the deployed quantiser's output (harness quantize_w8, CPU torch, per output row, whole
row one group), computed once per matrix and cached (`Image`); the golden consumes codes and scales as given.

    python3 tools/qwen_r25_golden.py --snapshot SNAP --cache DIR --layer 0 --position 8191 --out TRACE.npz
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import hdc_golden as G  # noqa: E402

F = np.float32
CHUNK = 8
TP = 4
EPS_DEFAULT = 1e-6


# ----------------------------------------------------------------------------------------------------------------
# primitives: the HGI-1 arithmetic library (tools/hgi_sim/lib.py), the only code the golden shares with the simulator
# ----------------------------------------------------------------------------------------------------------------
from hgi_sim import lib as A  # noqa: E402

csum, div, pairwise, rope_tables, rope = A.csum, A.div, A.pairwise, A.rope_tables, A.rope_half


def csum_rows(codes, xb, rows_per=2048):
    return A.sm_int8(codes, xb, rows_per)


def rmsnorm(x, w, eps):
    """x [..., d] -> row_norm per row of d (the FUSED.ROW_NORM order)."""
    x = np.asarray(x, dtype=F)
    return A.row_norm(x.reshape(-1), w, eps, seg=x.shape[-1]).reshape(x.shape)


def silu_mul(g, u):
    return A.glu(g, u)


# ----------------------------------------------------------------------------------------------------------------
# checkpoint and INT8 image
# ----------------------------------------------------------------------------------------------------------------
class Checkpoint:
    """The released BF16 safetensors, read lazily with numpy (BF16 -> FP32 exactly)."""

    def __init__(self, snap):
        self.snap = Path(snap)
        self.cfg = json.loads((self.snap / "config.json").read_text())
        idx = json.loads((self.snap / "model.safetensors.index.json").read_text())["weight_map"]
        self.where = idx
        self._hdr = {}

    def _header(self, fn):
        if fn not in self._hdr:
            with open(self.snap / fn, "rb") as f:
                n = struct.unpack("<Q", f.read(8))[0]
                self._hdr[fn] = (json.loads(f.read(n)), 8 + n)
        return self._hdr[fn]

    def get(self, name, rows=None):
        fn = self.where[name]
        hdr, base = self._header(fn)
        meta = hdr[name]
        assert meta["dtype"] == "BF16", meta
        shape = meta["shape"]
        a, b = meta["data_offsets"]
        mm = np.memmap(self.snap / fn, dtype=np.uint16, mode="r", offset=base + a, shape=((b - a) // 2,))
        u = mm.reshape(shape)
        if rows is not None:
            u = u[rows[0]:rows[1]]
        return (np.asarray(u, dtype=np.uint32) << 16).view(F)


class Image:
    """INT8 codes [N, K] and BF16 row scales (as FP32) per matrix, from the deployed quantiser (cached .npz)."""
    MATS = {"qkv": ("self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj"), "o": ("self_attn.o_proj",),
            "gu": ("mlp.gate_proj", "mlp.up_proj"), "down": ("mlp.down_proj",)}

    def __init__(self, ck: Checkpoint, cache):
        self.ck, self.cache = ck, Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)

    def _quant(self, w):
        import torch
        import qwen3_deployment_quality as Q
        codes, scales, _ = Q.quantize_w8(torch.from_numpy(np.ascontiguousarray(w)).to(torch.bfloat16))
        return codes.numpy().astype(np.int8), scales.to(torch.float32).numpy().reshape(-1).astype(F)

    def get(self, key):
        """key: 'L{i}.qkv' | 'L{i}.o' | 'L{i}.gu' | 'L{i}.down' | 'lm_head' | 'embed'."""
        p = self.cache / f"{key}.npz"
        if p.exists():
            z = np.load(p)
            return z["codes"], z["scales"]
        if key == "lm_head":
            w = self.ck.get("lm_head.weight")
        elif key == "embed":
            w = self.ck.get("model.embed_tokens.weight")
        else:
            li, m = key.split(".")
            i = int(li[1:])
            w = np.concatenate([self.ck.get(f"model.layers.{i}.{n}.weight") for n in self.MATS[m]], axis=0)
        codes, scales = self._quant(w)
        tmp = self.cache / f".{key}.{os.getpid()}.npz"
        np.savez(tmp, codes=codes, scales=scales)
        os.replace(tmp, p)
        return codes, scales


# ----------------------------------------------------------------------------------------------------------------
# the model
# ----------------------------------------------------------------------------------------------------------------
class QwenR25:
    def __init__(self, snap, cache):
        self.ck = Checkpoint(snap)
        self.img = Image(self.ck, cache)
        c = self.ck.cfg
        self.L, self.H, self.NH, self.KV, self.HD = (c["num_hidden_layers"], c["hidden_size"],
                                                      c["num_attention_heads"], c["num_key_value_heads"],
                                                      c["head_dim"])
        self.FF, self.V, self.eps, self.theta = c["intermediate_size"], c["vocab_size"], c["rms_norm_eps"], \
            c["rope_theta"]
        assert not c.get("tie_word_embeddings"), "lm_head is a separate matrix"
        self.scale = F(1.0 / np.sqrt(self.HD))
        self.grp = self.NH // self.KV

    # -- per-die geometry ---------------------------------------------------------------------------------------
    def die_rows(self, d):
        """qkv row indices of die d in the concatenated [q | k | v] matrix (its 8 q heads, 2 KV heads)."""
        nq, nk = self.NH // TP, self.KV // TP
        q = np.arange(d * nq * self.HD, (d + 1) * nq * self.HD)
        k = self.NH * self.HD + np.arange(d * nk * self.HD, (d + 1) * nk * self.HD)
        v = (self.NH + self.KV) * self.HD + np.arange(d * nk * self.HD, (d + 1) * nk * self.HD)
        return q, k, v

    def head_rows(self, d):
        return d * self.V // TP, (d + 1) * self.V // TP

    def lw(self, i, n):
        return self.ck.get(f"model.layers.{i}.{n}.weight")

    def embed(self, tok):
        codes, scales = self.img.get("embed")
        return G.mul(codes[tok].astype(F), scales[tok])

    def matvec(self, x, key, tp=1, rows=None):
        """y = scale * csum8 order; tp > 1: K split over tp dies, partials added by the pairwise tree."""
        codes, scales = self.img.get(key)
        if rows is not None:
            codes, scales = codes[rows], scales[rows]
        xb = G.to_bf16(x)
        K = codes.shape[1]
        if tp == 1:
            t = csum_rows(codes, xb)
            parts = None
        else:
            kd = K // tp
            parts = [csum_rows(codes[:, d * kd:(d + 1) * kd], xb[d * kd:(d + 1) * kd]) for d in range(tp)]
            t = pairwise(parts)
        return G.mul(t, scales), parts

    # -- one decoder layer at one position ------------------------------------------------------------------------
    def layer(self, i, x, pos, Kc, Vc, trace=None):
        """x [H] FP32 at `pos`; Kc, Vc [KV, >= pos+1, HD] FP8 values (positions < pos are the cache; row pos is
        written here).  Returns x_out.  trace (dict) receives every intermediate."""
        t = trace if trace is not None else {}
        NH, KV, HD = self.NH, self.KV, self.HD
        h = rmsnorm(x, self.lw(i, "input_layernorm"), self.eps)
        qkv, _ = self.matvec(h, f"L{i}.qkv")
        q = qkv[:NH * HD].reshape(NH, HD)
        k = qkv[NH * HD:(NH + KV) * HD].reshape(KV, HD)
        v = qkv[(NH + KV) * HD:].reshape(KV, HD)
        qn = rmsnorm(q, self.lw(i, "self_attn.q_norm"), self.eps)
        kn = rmsnorm(k, self.lw(i, "self_attn.k_norm"), self.eps)
        cos, sin = rope_tables(pos, HD, self.theta)
        cos, sin = cos[0], sin[0]
        qr = rope(qn, cos, sin)
        kr = G.to_fp8(rope(kn, cos, sin))
        vr = G.to_fp8(v)
        Kc[:, pos], Vc[:, pos] = kr, vr
        qb = G.to_bf16(qr)
        P = pos + 1
        attn = np.empty((NH, HD), dtype=F)
        sc_all, z_all, pv_all = [], [], []
        for hh in range(NH):
            kv = hh // self.grp
            Kp, Vp = Kc[kv, :P], Vc[kv, :P]
            e, Z, _ = A.softmax_e_z(A.att_qk(qb[hh], Kp), self.scale)
            s = G.mul(A.att_qk(qb[hh], Kp), self.scale)
            pv = A.att_pv(G.to_bf16(e), Vp)
            attn[hh] = div(pv, Z)
            sc_all.append(s)
            z_all.append(Z)
            pv_all.append(pv)
        o, o_parts = self.matvec(attn.reshape(-1), f"L{i}.o", tp=TP)
        x1 = G.add(x, o)
        h2 = rmsnorm(x1, self.lw(i, "post_attention_layernorm"), self.eps)
        gu, _ = self.matvec(h2, f"L{i}.gu")
        g, u = gu[:self.FF], gu[self.FF:]
        mm = silu_mul(g, u)
        dn, dn_parts = self.matvec(mm, f"L{i}.down", tp=TP)
        x2 = G.add(x1, dn)
        t.update({"x_in": x, "h_attn": h, "qkv": qkv, "q_norm": qn, "k_norm": kn, "q_rope": qr, "k_row": kr,
                  "v_row": vr, "scores": np.stack(sc_all), "Z": np.array(z_all, dtype=F), "pv": np.stack(pv_all),
                  "attn": attn, "o_parts": np.stack(o_parts), "o": o, "x_mid": x1, "h_ffn": h2, "gu": gu, "act": mm,
                  "down_parts": np.stack(dn_parts), "down": dn, "x_out": x2})
        return x2

    def head(self, x, trace=None):
        t = trace if trace is not None else {}
        h = rmsnorm(x, self.ck.get("model.norm.weight"), self.eps)
        logits, _ = self.matvec(h, "lm_head")
        tok = int(np.argmax(logits))                 # lowest index on ties (numpy argmax)
        t.update({"h_final": h, "logits": logits, "token": np.array([tok])})
        return logits, tok


# ----------------------------------------------------------------------------------------------------------------
# synthetic, format-valid decode state at a target position (owner rule measure-at-target-context)
# ----------------------------------------------------------------------------------------------------------------
def synthetic_kv(model: QwenR25, i, pos, seed=8191):
    """K/V cache of layer i for positions 0..pos-1: K rows are fp8(rope_p(rmsnorm(N(0,1)) * k_norm gain)) -- the
    format and scale the real cache holds -- and V rows fp8(N(0, sigma)); row `pos` is left for the layer."""
    rng = np.random.default_rng([seed, i, pos])
    KV, HD = model.KV, model.HD
    Kc = np.zeros((KV, pos + 1, HD), dtype=F)
    Vc = np.zeros((KV, pos + 1, HD), dtype=F)
    gk = model.lw(i, "self_attn.k_norm")
    inv = (1.0 / (model.theta ** (np.arange(0, HD, 2, dtype=np.float64) / HD))).astype(np.float32)
    ang = (np.arange(pos, dtype=np.float32)[:, None] * inv[None, :]).astype(np.float32)
    cos = np.cos(ang.astype(np.float64)).astype(F)
    sin = np.sin(ang.astype(np.float64)).astype(F)
    for kv in range(KV):
        k = rmsnorm(rng.standard_normal((pos, HD)).astype(F), gk, model.eps)
        Kc[kv, :pos] = G.to_fp8(rope(k, cos, sin))
        Vc[kv, :pos] = G.to_fp8((rng.standard_normal((pos, HD)) * 0.5).astype(F))
    return Kc, Vc


def synthetic_x(model: QwenR25, i, seed=8191, tok=9707):
    """Layer input: layer 0 takes the embedding of `tok`; deeper layers a residual of realistic per-channel scale
    (the embedding row plus N(0, 0.5) noise; a layer is a pure function of its inputs)."""
    x = model.embed(tok % model.V)
    if i == 0:
        return x
    rng = np.random.default_rng([seed, i, 1])
    return G.add(x, (rng.standard_normal(model.H) * 0.5).astype(F))


def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot", required=True, type=Path)
    ap.add_argument("--cache", required=True, type=Path)
    ap.add_argument("--layer", type=int, default=0)
    ap.add_argument("--position", type=int, default=8191)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    m = QwenR25(a.snapshot, a.cache)
    Kc, Vc = synthetic_kv(m, a.layer, a.position)
    x = synthetic_x(m, a.layer)
    tr = {}
    m.layer(a.layer, x, a.position, Kc, Vc, tr)
    np.savez(a.out, **tr)
    print(json.dumps({k: digest(v) for k, v in tr.items()}, indent=1))


if __name__ == "__main__":
    main()
