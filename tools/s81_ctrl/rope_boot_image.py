#!/usr/bin/env python3
"""RoPE boot image of an S81 die (stream ds-control, 2026-10-08): the plain and YaRN cos/sin tables of the released
DeepSeek-V4.1-Flash config (rope_head_dim 64 -> 32 pairs; rope_theta 10000; YaRN: compress_rope_theta 160000,
factor 16, original_seq_len 65536, beta 32/1) computed by the arithmetic golden's own functions (tools/hdc_golden_v41.py
rope_freqs / rope_cs, binary32), laid out as ot_s81_boot_seq's static region: sector E = kind*8*MAX_POS + 8*pos + 2*s + j
holds pairs 8s+4j .. 8s+4j+3, pair p at bits 64*(p%4) as {sin[31:0], cos[31:0]} (ot_chip_v41x_rope_hbm_cache).
Writes <out>/rope.hex (one 256-b sector a line, E order) and <out>/rope_meta.txt (sectors, checksum = sum mod 2^32 of
zlib.crc32(E 4 B LE + 32 data bytes)).  Positions: 0 .. MAX_POS-1 by default, or the top MAX_POS positions of the 1M
context with --top (so the bench also covers positions near 1,048,575)."""
import argparse, json, sys, zlib
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--max-pos", type=int, default=64)
ap.add_argument("--top", action="store_true")
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()
c = json.loads((ROOT / "compiler/models/deepseek-v4.1-flash/inference_config.json").read_text())
rd = c["rope_head_dim"]
fr = [G.rope_freqs(rd, 0, c["rope_theta"], c["rope_factor"], c["beta_fast"], c["beta_slow"]),
      G.rope_freqs(rd, c["original_seq_len"], c["compress_rope_theta"], c["rope_factor"], c["beta_fast"], c["beta_slow"])]
P = a.max_pos
base_pos = (1 << 20) - P if a.top else 0
lines, csum = [], 0
for k in range(2):
    for i in range(P):
        cs, sn = G.rope_cs(fr[k], base_pos + i)
        cw = np.asarray(cs, dtype=np.float32).view(np.uint32); sw = np.asarray(sn, dtype=np.float32).view(np.uint32)
        for s in range(4):
            for j in range(2):
                v = 0
                for q in range(4):
                    p = 8 * s + 4 * j + q
                    v |= ((int(sw[p]) << 32) | int(cw[p])) << (64 * q)
                E = k * 8 * P + 8 * i + 2 * s + j
                lines.append(f"{v:064x}")
                csum = (csum + zlib.crc32(E.to_bytes(4, "little") + v.to_bytes(32, "little"))) & 0xFFFFFFFF
a.out.mkdir(parents=True, exist_ok=True)
(a.out / "rope.hex").write_text("\n".join(lines) + "\n")
(a.out / "rope_meta.txt").write_text(f"{len(lines)} {csum:08x} {base_pos}\n")
print(len(lines), f"{csum:08x}", base_pos)
