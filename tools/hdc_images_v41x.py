#!/usr/bin/env python3
"""Weight and constant images of the re-specified V4.1 decode core (rtl/hdc/v41x/ot_hdc_core_v41x.sv).

    python3 tools/hdc_images_v41x.py --out DIR [--mtp GAMMA] [--hhw 8]

The program, the instruction fields and the ISA-level simulator (tools/hdc_program_v41.py) keep the as-built
layout (Layout).  Each re-specified engine reads its weights from memories in ITS OWN layout; this tool builds
those images from the same Layout, and fixes, per engine, the translation from an as-built base (the value the
instruction field carries) to the engine's base -- the adapter applies it (rtl/hdc/v41x/ot_hdc_v41x_*_adapt.sv).

* HE -> ot_hdc_v41x_hcp: 8 weight banks of HHW binary32 lanes.  Matrix fn [nout, K] (K = 8 * he_k) at as-built
  HE ROM word b is placed at bank word b + o*R + r (R = ceil(he_k / HHW)), bank k, lane l = fn[o][8*(r*HHW+l)+k]:
  the IDENTITY translation, legal because the engine's footprint nout*R words fits the as-built he_k*IL
  (asserted).  File hbank.hex: line a*8 + k = bank k word a, lanes 0..HHW-1 (lane 0 in the low bits).

MTP builds (--mtp GAMMA) use tools/hdc_program_v41.mtp_layout, so the MTP-only weights (mtp.0-2 layers, their
hyper-connection projections) are covered by the same placement rule.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402
import hdc_program_v41 as P  # noqa: E402

IL = I.INTERLEAVE


def he_matrices(lay):
    """(as-built base, fn [nout, K] binary32) of every HE matrix, recovered from the as-built HE ROM words:
    word b + k'*IL + j holds, in lane c*NL + l, row j*NL + l at column c*kc + k'."""
    S, NL = V.HC_SPLIT, I.HE_LANES
    hw = np.stack(lay.hwords)                       # [words, S*NL]
    out = []
    for key, mat in lay.mat.items():
        if not (isinstance(key, tuple) and key[-1] == "fn"):
            continue
        b, n, kc = mat["base"], mat["n"], mat["k"]
        blk = hw[b:b + kc * IL].reshape(kc, IL, S, NL)          # [k', j, c, l]
        w = blk.transpose(1, 3, 2, 0).reshape(IL * NL, S * kc)   # [j*NL + l, c*kc + k']
        out.append((b, w[:n].astype(np.float32), kc))
    return out


def hbank_image(lay, hhw):
    """{word*8 + bank: [hhw] uint32} of the HCP weight banks, identity-translated."""
    img = {}
    for b, w, kc in he_matrices(lay):
        n, K = w.shape
        R = -(-kc // hhw)
        assert n * R <= kc * IL, (b, n, R, kc)       # the engine's footprint fits the as-built one
        bits = G.bits(w).astype(np.uint32)
        for o in range(n):
            for r in range(R):
                for k in range(8):
                    lanes = np.zeros(hhw, dtype=np.uint32)
                    for l in range(hhw):
                        col = 8 * (r * hhw + l) + k
                        if col < K:
                            lanes[l] = bits[o, col]
                    img[(b + o * R + r) * 8 + k] = lanes
    return img


def write_banked(path, img, lane_bits, lanes):
    """A $readmemh image with explicit @addresses (sparse)."""
    digits = lane_bits * lanes // 4
    with open(path, "w") as fh:
        prev = None
        for a in sorted(img):
            if prev is None or a != prev + 1:
                fh.write(f"@{a:x}\n")
            fh.write(f"{P.pack_lanes(img[a], lane_bits):0{digits}x}\n")
            prev = a


def write(out, lay, hhw=8):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    hb = hbank_image(lay, hhw)
    write_banked(out / "hbank.hex", hb, 32, hhw)
    meta = {"hhw": hhw, "hbank_lines": len(hb), "hbank_top": max(hb) + 1 if hb else 0}
    (out / "v41x_images.json").write_text(json.dumps(meta))
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mtp", type=int, help="MTP layout with this gamma (tools/hdc_program_v41.mtp_layout)")
    ap.add_argument("--hhw", type=int, default=8)
    a = ap.parse_args()
    model = V.Model()
    lay = P.mtp_layout(model, a.mtp) if a.mtp else P.Layout(model)
    print(json.dumps(write(a.out, lay, a.hhw)))


if __name__ == "__main__":
    main()
