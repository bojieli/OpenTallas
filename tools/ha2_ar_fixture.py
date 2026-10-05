#!/usr/bin/env python3
"""HA2 all-reduce fixture: per-contributor FP32 partials and the golden result image for tb_ha2_ar.

    python3 tools/ha2_ar_fixture.py OUTDIR --shape ds|qwen [--seed S]

The golden is the W19 executor's own operation (tools/w19_hbm_tp96_isa.py op_reduce): for each reduction group the
NC contributors' partials in rank order, reduced pairwise ((p0 + p1) + (p2 + p3)) + ... with hdc_golden.add, then
(DS) hdc_golden.to_bf16.  Operands are an arithmetic STRESS fixture (wide exponents, exact cancellations to zero,
subnormal sums, near-ties for the BF16 rounding), not a model token.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402

F = np.float32
SHAPES = {
    # DS-V4.1 TP-96 o-group all-reduce (variant oreduce): 8 groups x 8 contributors x 1,024 FP32, BF16 out
    "ds": dict(GS=16, NG=6, NC=8, NOG=8, E=1024, LANES=16, ONESHOT=0, BF16=1),
    # Qwen3-8B TP-2: H = 4,096 FP32 partials, one-shot over the in-package link, FP32 out (W15 q256 width)
    # DS-V4.1 TP-96 all-gather through the same endpoint (NC = 1: no reduction): every die's 64 BF16 values
    # (128 B, the W19 per-rank segment class: y 5,120 x 2 B / 96 = 107 B) to every die
    "dsgather": dict(GS=16, NG=6, NC=1, NOG=96, E=64, LANES=16, ONESHOT=0, BF16=1),
    # the same gather at 4x the payload (256 BF16 = 512 B a rank), for the slope
    "dsgather512": dict(GS=16, NG=6, NC=1, NOG=96, E=256, LANES=16, ONESHOT=0, BF16=1),
    # debug shape: 2 groups of 4, 2 reduction groups of 4 contributors
    "tiny": dict(GS=4, NG=2, NC=4, NOG=2, E=256, LANES=16, ONESHOT=0, BF16=1),
    "qwen": dict(GS=2, NG=1, NC=2, NOG=1, E=4096, LANES=256, ONESHOT=1, BF16=0),
}


def stress(rng, n):
    x = (rng.standard_normal(n) * np.exp2(rng.integers(-24, 24, n))).astype(F)
    k = rng.random(n)
    x[k < 0.03] = (rng.standard_normal(int((k < 0.03).sum())) * 2.0 ** -130).astype(F)        # subnormals
    x[(k >= 0.03) & (k < 0.05)] = F(0.0)
    return x


def build(shape: str, seed: int):
    s = SHAPES[shape]
    rng = np.random.default_rng(seed)
    nc, nog, e = s["NC"], s["NOG"], s["E"]
    parts = np.stack([stress(rng, e) for _ in range(nc * nog)])
    if nc == 1:
        parts = G.to_bf16(parts).astype(F)          # a gather moves BF16 values: exact in the BF16 image
    # exact cancellations: contributor 1 = -contributor 0 on a band, contributor 3 = -contributor 2 elsewhere
    for og in range(nog if nc > 1 else 0):
        b = og * nc
        parts[b + 1, 0:64] = -parts[b, 0:64]
        if nc > 2:
            parts[b + 3, 64:128] = -parts[b + 2, 64:128]
            # BF16 exact ties: contributor 0 carries low-16 = 0x8000 (bit 16 odd and even), the others are zero
            parts[b + 1:b + nc, 160:192] = F(0.0)
            t = (rng.integers(0x3F00, 0x4100, 32).astype(np.uint32) << 16) | np.uint32(0x8000)
            parts[b, 160:192] = t.view(F)
            # whole-tree cancellation to zero (canonical +0) and all-subnormal sums
            for j in range(0, nc, 2):
                parts[b + j + 1, 0:16] = -parts[b + j, 0:16]
            parts[b:b + nc, 192:224] = (rng.standard_normal((nc, 32)) * 2.0 ** -133).astype(F)
    z = np.zeros((nog, e), dtype=F)
    for og in range(nog):
        p = [parts[og * nc + j].copy() for j in range(nc)]
        while len(p) > 1:
            p = [G.add(p[i], p[i + 1]) for i in range(0, len(p), 2)]
        z[og] = p[0]
    zr = G.to_bf16(z) if s["BF16"] else z
    return s, parts, zr


def hexword(vals_u: list[int], bits: int) -> str:
    w = 0
    for i, v in enumerate(vals_u):
        w |= int(v) << (bits * i)
    n = len(vals_u) * bits // 4
    return f"{w:0{n}x}"


def write(outdir: Path, shape: str, seed: int):
    s, parts, zr = build(shape, seed)
    outdir.mkdir(parents=True, exist_ok=True)
    L, e, nc, nog = s["LANES"], s["E"], s["NC"], s["NOG"]
    pf = e // L
    of = pf if s["ONESHOT"] else pf // nc
    rpf = 2 if s["BF16"] else 1
    rof = of // rpf
    with open(outdir / "part.hex", "w") as fh:
        for r in range(nc * nog):
            u = parts[r].view(np.uint32)
            for f in range(pf):
                fh.write(hexword(list(u[f * L:(f + 1) * L]), 32) + "\n")
    lines = []
    owners = 1 if s["ONESHOT"] else nc
    for og in range(nog if not s["ONESHOT"] else 1):
        for so in range(owners):
            for m in range(rof):
                base = so * of * L + m * rpf * L
                v = zr[og, base:base + rpf * L]
                if s["BF16"]:
                    u = (v.view(np.uint32) >> 16).astype(np.uint32)
                    lines.append(hexword(list(u), 16))
                else:
                    lines.append(hexword(list(v.view(np.uint32)), 32))
    (outdir / "expected.hex").write_text("\n".join(lines) + "\n")
    meta = dict(shape=shape, seed=seed, params=s, partial_flits=pf, result_flits=len(lines),
                golden="hdc_golden.add pairwise tree in contributor rank order" + (" + hdc_golden.to_bf16" if s["BF16"] else ""),
                sha256={f: hashlib.sha256((outdir / f).read_bytes()).hexdigest() for f in ("part.hex", "expected.hex")},
                zero_results=int((zr == 0).sum()), subnormal_results=int(((zr != 0) & (np.abs(zr) < 2 ** -126)).sum()))
    (outdir / "fixture.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--shape", choices=sorted(SHAPES), required=True)
    ap.add_argument("--seed", type=int, default=20261004)
    a = ap.parse_args()
    print(json.dumps(write(a.outdir, a.shape, a.seed)))
