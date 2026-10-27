#!/usr/bin/env python3
"""TOK-QK-KVL 10-27: declared deterministic FP8 K/V history for the history-seeded TP4 ISA golden.

The per-layer KV-die attention vectors come from tools/qwen_layerbench/kv_attn_gold.py, which runs
tools/qwen_hbmacc_position_oracle_gpu.py --run --kv-history.  The weights are the real checkpoint, the token is the
real prompt token, and x is chained layer to layer.  The 36-layer real-prefill history (fx/gold/tp4) was never
produced: the GPU regeneration failed on 10-09, and none of the fleet or archive trees holds it.  So each layer's K/V
store is seeded with a declared, format-valid FP8 history.  The oracle states that this is admissible ("a layer is a
pure function of its inputs").

The history code law is the one tools/qwen_tp8_native_layer_oracle.py uses for its prior cache: safe finite signed
E4M3 codes with a distinct layer, die and KV-head seed:
  K code = ((t*11 + dim*7 + die*13 + layer*19 + g*29) % 48 + 24) | ((t + dim + die + g) % 2) << 7
  V code = ((t*3 + dim*5 + die*17 + layer*23 + g*31) % 48 + 24) | ((t + 2*dim + die + g) % 2) << 7
Rows 0..P-1 are filled.  Row P is written by the oracle (the decoded token's own K/V).  The layout is the oracle's
store, the u32 view of the fp32 store that LayerZero.k_elem / v_elem use (tools/hdc_qwen_fullshape_program_w12.py,
the same indexing kv_attn_vectors.py reads):
  K[g, t, d] at ((g*(TMAX/W) + t//W)*HD + d)*W + t%W     V[g, t, d] at KVD*TMAX*HD + (g*TMAX + t)*HD + d
    kvl_history.py --out DIR [--pos 8191] [--layers 36] [--tp 4]  -> DIR/L<n>_die<d>.bin + manifest.json
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

TMAX, HD, KVD, W = 8192, 128, 2, 16


def fp8_decode(codes):
    codes = np.asarray(codes, dtype=np.uint8)
    exp = ((codes >> 3) & 15).astype(np.int32)
    mant = (codes & 7).astype(np.float32)
    value = np.where(exp == 0, mant * np.float32(2 ** -9), (1 + mant / 8) * np.exp2(exp - 7)).astype(np.float32)
    return np.where(codes & 128, -value, value).astype(np.float32)


def store(layer, die, pos):
    st = np.zeros(2 * KVD * TMAX * HD, dtype=np.float32)
    t, d = np.meshgrid(np.arange(pos), np.arange(HD), indexing='ij')
    for g in range(KVD):
        kc = (((t * 11 + d * 7 + die * 13 + layer * 19 + g * 29) % 48) + 24).astype(np.uint8) | \
             (((t + d + die + g) % 2) * 128).astype(np.uint8)
        vc = (((t * 3 + d * 5 + die * 17 + layer * 23 + g * 31) % 48) + 24).astype(np.uint8) | \
             (((t + 2 * d + die + g) % 2) * 128).astype(np.uint8)
        kidx = ((g * (TMAX // W) + t // W) * HD + d) * W + t % W
        vidx = KVD * TMAX * HD + (g * TMAX + t) * HD + d
        st[kidx] = fp8_decode(kc)
        st[vidx] = fp8_decode(vc)
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--pos', type=int, default=8191)
    ap.add_argument('--layers', type=int, default=36)
    ap.add_argument('--tp', type=int, default=4)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    man = {}
    for n in range(a.layers):
        for die in range(a.tp):
            p = a.out / f'L{n}_die{die}.bin'
            store(n, die, a.pos).view('<u4').tofile(p)
            man[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (a.out / 'manifest.json').write_text(json.dumps({
        'schema': 'opentallas.tok-qk-kvl.declared-history.v1', 'pos': a.pos, 'layers': a.layers, 'tp': a.tp,
        'law': __doc__.split('\n\n')[2], 'sha256': man}, indent=1) + '\n')
    print(f'kvl_history: {len(man)} stores, rows 0..{a.pos - 1}')


if __name__ == '__main__':
    main()
