#!/usr/bin/env python3
"""RTL-BUILD-S81 (2026-10-18): fixtures for tb_s81sl_slice_eng -- the Engram mix of one DeepSeek-V4.1 layer
(tools/hdc_golden_v41.py Model.engram_layer arithmetic, chunk8) on ONE real DV slice (sid SID: elements
[320 SID, 320 SID + 320)), the other 15 slices' exchange flits injected as golden beat partials.

The mix is evaluated by mix_ref(), the statements of Model.engram_layer (j loop) verbatim; main() refuses to run when
those statements are no longer in engram_layer's source (the fixture tracks the reference).

Outputs (hex, one word / row per line) in OUTDIR:
  img_k.mem   (k = 0..4) leaf k's 88 row pairs: h half rows 0..15 at rows 0.. (vn layout: copy j element 4 i + e at
              bits (4 j + e) * 16), then the 72 row pairs of the Engram region at A0 (kv_rowmap.json: K_j at A0 + 16 j,
              W_j at A0 + 64 + 16 j, V at A0 + 128)
  flit.mem    the 15 x 12 foreign NX flits {b 8 = {v 4, sid 4} (xfin ENG tag), d 160} (source slice order, then vector v = kind * 4 + copy in the
              source's injection order: copy-major, kind hh, kk, dd), d = the source's 5 beat partials (leaf 0 in [31:0])
  fv.mem      the vector index of each flit line
  sum.mem     12 golden copy sums (v = kind * 4 + copy): hh, kk, dd over the full D = 5120
  gate.mem    4 golden gates
  y.mem       leaf k half row i of the result (5 x 16 lines, the vn layout, bf16(h + gate * v))
  par.mem     eps, scale (FP32 bits)
Usage: eng_slice_gold.py OUTDIR [--seed N] [--sid S]"""
import argparse
import inspect
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdc_golden_v41 as g  # noqa: E402

g.set_arith("chunk8")
F = np.float32
D, HC, NS, NVL = 5120, 4, 16, 5
REF_LINES = [
    "rstd = mul(rsqrt(add(div(reduce_sum_c(mul(hj, hj)), n), self.eps)),",
    "rsqrt(add(div(reduce_sum_c(mul(kj, kj)), n), self.eps)))",
    "dot = mul(mul(reduce_sum_c(mul(mul(hj, wgt[j]), kj)), rstd), self.engram_scale)",
    "mag = sqrt(np.maximum(np.abs(dot), F(1e-6)).astype(F))",
    "gate = sigmoid(np.where(dot < 0, neg(mag), mag).astype(F))",
    "out.append(add(hj, mul(gate, value)))",
]


def mix_ref(h, key, value, wgt, eps, scale):
    """Model.engram_layer's per-copy statements (self.eps -> eps, self.engram_scale -> scale)."""
    mul, add, div, rsqrt, sqrt, sigmoid, neg, reduce_sum_c = g.mul, g.add, g.div, g.rsqrt, g.sqrt, g.sigmoid, g.neg, g.reduce_sum_c
    out, gates = [], []
    for j in range(HC):
        hj, kj = h[j], key[j]
        n = F(D)
        rstd = mul(rsqrt(add(div(reduce_sum_c(mul(hj, hj)), n), eps)),
                   rsqrt(add(div(reduce_sum_c(mul(kj, kj)), n), eps)))
        dot = mul(mul(reduce_sum_c(mul(mul(hj, wgt[j]), kj)), rstd), scale)
        mag = sqrt(np.maximum(np.abs(dot), F(1e-6)).astype(F))
        gate = sigmoid(np.where(dot < 0, neg(mag), mag).astype(F))
        gates.append(F(gate))
        out.append(add(hj, mul(gate, value)))
    return g.to_bf16(np.stack(out)), np.array(gates, dtype=F)


def hx(x):
    return f"{int(np.asarray(x, dtype=F).view(np.uint32)):08x}"


def words(ws):
    """FP32 words, word 0 in the low bits -> one hex line."""
    return "".join(hx(w) for w in reversed(list(ws)))


def bf(x):
    return int(np.asarray(x, dtype=F).view(np.uint32)) >> 16


def hrow(a, hi):
    """vn half row hi of a [4, 64] BF16 block: copy j element 4 hi + e at bits (4 j + e) * 16."""
    v = 0
    for j in range(4):
        for e in range(4):
            v |= bf(a[j, 4 * hi + e]) << ((4 * j + e) * 16)
    return f"{v:064x}"


def main():
    src = inspect.getsource(g.Model.engram_layer)
    miss = [l for l in REF_LINES if l not in src]
    if miss:
        sys.exit(f"engram_layer no longer contains {miss}: update mix_ref")
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--sid", type=int, default=3)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    h = g.to_bf16(rng.standard_normal((HC, D)).astype(F) * F(2.0))
    h[0, 5] = F(0.0); h[2, 17] = F(-0.0)
    key = (rng.standard_normal((HC, D)) * 0.7).astype(F)
    wgt = g.mul((rng.standard_normal((HC, D)) * 0.3).astype(F), (rng.standard_normal((HC, D)) * 0.3).astype(F))
    value = rng.standard_normal(D).astype(F)
    eps, scale = F(1e-6), F(D ** -0.5)
    y, gates = mix_ref(h, key, value, wgt, eps, scale)
    o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    prod = [g.mul(h, h), g.mul(key, key), g.mul(g.mul(h, wgt), key)]       # [kind][copy][e]
    sums = [g.reduce_sum_c(prod[k][j]) for k in range(3) for j in range(HC)]
    (o / "sum.mem").write_text("\n".join(hx(s) for s in sums) + "\n")
    (o / "gate.mem").write_text("\n".join(hx(x) for x in gates) + "\n")
    (o / "par.mem").write_text(f"{hx(eps)}\n{hx(scale)}\n")

    def bp(k, j, beat):                                                    # beat partial (aligned 64-element subtree)
        return g.reduce_sum_c(prod[k][j][64 * beat:64 * beat + 64])

    fl, fv = [], []
    for s in range(NS):
        if s == a.sid:
            continue
        for j in range(HC):
            for k in range(3):
                d = words(bp(k, j, s * NVL + l) for l in range(NVL))
                fl.append(f"{(((k * 4 + j) << 4) | s):02x}{d}")          # ENG tag b = {v, sid} (xfin ENG)
                fv.append(f"{k * 4 + j:x}")
    (o / "flit.mem").write_text("\n".join(fl) + "\n")
    (o / "fv.mem").write_text("\n".join(fv) + "\n")
    ys = []
    for lf in range(NVL):
        e0 = 320 * a.sid + 64 * lf
        hb, kb, wb, vb, yb = h[:, e0:e0 + 64], key[:, e0:e0 + 64], wgt[:, e0:e0 + 64], value[e0:e0 + 64], y[:, e0:e0 + 64]
        img = [hrow(hb, i) for i in range(16)]
        # the K / W / V region of the compiler row map (kv_rowmap.json): 72 row pairs from A0
        img += [words(kb[j, 8 * i:8 * i + 8]) for j in range(4) for i in range(8)]
        img += [words(wb[j, 8 * i:8 * i + 8]) for j in range(4) for i in range(8)]
        img += [words(vb[8 * s:8 * s + 8]) for s in range(8)]
        (o / f"img_{lf}.mem").write_text("\n".join(img) + "\n")
        ys += [hrow(yb, i) for i in range(16)]
    (o / "y.mem").write_text("\n".join(ys) + "\n")
    print("wrote", o, "sid", a.sid, "gates", [hx(x) for x in gates])


if __name__ == "__main__":
    main()
