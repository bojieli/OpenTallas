#!/usr/bin/env python3
"""el1013-hbm-hc: vectors for the B2 chunk-collector transaction bench (tb_hgi_hc_coll_b2).
Per row: x (D 5,120 FP32) -> squares -> 640 chunk leaves (8 sequential FP32 adds, as the lanes) -> the golden sum of
squares = hdc_golden_v41.split_sum(mul(x, x), RMS_SPLIT) under chunk8 (the reduction inside rmsnorm_bf16).
--out DIR: coll_chunk.mem (rows x 640 words, tag order), coll_ss.mem (one word a row), coll_sizes.svh.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_golden_v41 as GV  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_hc_coll_b2_tb')
    ap.add_argument('--rows', type=int, default=12)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    D = 5120
    GV.set_arith("chunk8")
    rng = np.random.default_rng(1013)
    ch, ss = [], []
    for r in range(a.rows):
        x = (rng.standard_normal(D) * (0.5 + r)).astype(np.float32)
        sq = GV.mul(x, x)
        for c in range(D // 8):
            acc = np.float32(sq[8 * c])
            for k in range(1, 8):
                acc = GV.add(acc, sq[8 * c + k])
            ch.append(int(np.asarray(acc, dtype=np.float32).view(np.uint32)))
        ss.append(int(np.asarray(GV.split_sum(sq, GV.RMS_SPLIT), dtype=np.float32).view(np.uint32)))
    (out / 'coll_chunk.mem').write_text(''.join(f'{v:08X}\n' for v in ch))
    (out / 'coll_ss.mem').write_text(''.join(f'{v:08X}\n' for v in ss))
    (out / 'coll_sizes.svh').write_text(f'localparam integer NROW = {a.rows};\n')
    print(f"{a.rows} rows, {len(ch)} chunks")


if __name__ == '__main__':
    main()
