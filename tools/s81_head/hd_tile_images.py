#!/usr/bin/env python3
"""S81-HEAD HD-TILE (10-21): ROM images + x streams for the ot_s81hd_tile mini-array bench.

Writes into OUT, for each bundle base row R in ROWS (128 rows of the released DeepSeek-V4.1 head.weight each), the
skewed ROM images of ot_dsrom_head_bundle exactly as tools/dsrom_1m_head.py cmd_bundle does (instance prefix P:
P a0..a3 / P b, _0/_1 banks), plus xa.hex / xb.hex (golden final-norm x of the 1M token) and golden.json (per-bundle
and joint argmax {row, bits} from the golden logits, lowest id on ties).

    python3 tools/s81_head/hd_tile_images.py OUT [--sk 7] h:21888 g:22016
SK = the element adder latency (ot_s81hd_elem NC 1: ot_hdc_fp32_add_lat_fan32 LAT 7 -> 7; ot_v41_fadd CUT 0x17b -> 8).
Also writes <P>lg.hex: the 128 golden logits (FP32 bits, local row order) of each bundle.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsrom_1m_head as H  # noqa: E402

args = sys.argv[1:]
sk = 7
if '--sk' in args:
    i = args.index('--sk'); sk = int(args[i + 1]); del args[i:i + 2]
out = Path(args[0]); out.mkdir(parents=True, exist_ok=True)
H.setup_gate()
H.SK = sk
xf, logits = H.golden_x()
x16 = (H.G.bits(xf).astype(np.uint32) >> 16).astype(np.uint64)
ck = H.Ckpt(H.SNAP)
gold = {}
for arg in args[1:]:
    pre, r0 = arg.split(":"); r0 = int(r0)
    m = H.gate.Mat(ck, "head", "bf16", H.BUNDLE_ROWS, H.K, r0=r0)
    u = np.asarray(m.u16, dtype=np.uint64)
    for q in range(4):
        H.write_macro(H.skewed_image(u[32 * q:32 * q + 32, :4096].reshape(H.NW, 16)), out, f"{pre}a{q}")
    perm = np.array([32 * (n % 4) + n // 4 for n in range(H.BUNDLE_ROWS)])
    H.write_macro(H.skewed_image(u[perm, 4096:].reshape(H.NW, 16)), out, f"{pre}b")
    lg = logits[r0:r0 + H.BUNDLE_ROWS]
    b = int(np.argmax(lg))
    gold[pre] = dict(row0=r0, row=r0 + b, bits=f"{int(H.G.bits(lg[b:b+1])[0]):08x}")
    (out / f"{pre}lg.hex").write_text("".join(f"{int(v):08x}\n" for v in H.G.bits(lg)))


def slices(xx, n):
    return "".join("".join(f"{int(v):04x}" for v in xx[16 * i:16 * i + 16][::-1]) + "\n" for i in range(n))


(out / "xa.hex").write_text(slices(x16[:4096], 256))
(out / "xb.hex").write_text(slices(x16[4096:], 64))
gold["checkpoint_header_sha256"] = ck.pins
gold["sk"] = sk
(out / "golden.json").write_text(json.dumps(gold, indent=1) + "\n")
print(json.dumps(gold))
