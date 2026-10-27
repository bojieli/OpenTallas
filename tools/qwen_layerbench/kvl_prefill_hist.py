#!/usr/bin/env python3
"""TOK-QK-KVL 10-27: the REAL 36-layer prefill K/V history of the released Qwen3-8B checkpoint over the real prompt.

The KV die's per-layer attention needs, for every layer, the K/V of positions 0..P-1 of the prompt.  This tool makes
them from the released checkpoint (HF Qwen/Qwen3-8B safetensors) with the deployed weights and KV format:
  * weights: the O4 W8 contract exactly as the die's ROM images hold them (norm-folded q/k/v and gate/up, W8 codes +
    one BF16 scale per row, qwen3_deployment_quality.quantize_w8; --check-prep compares the codes / scales with the
    pinned TP4 stage images bit for bit);
  * KV: golden to_fp8 (E4M3 RNE, saturating, no scale) on K after q/k-norm + RoPE and on V;
  * arithmetic: the vendor (HF transformers) BF16 inference arithmetic (qwen3_deployment_quality mode "gpu", here on
    the CPU).  The ISA-golden prefill itself is sequential decode, ~10 s (P0) .. ~57 s (P8191) per position on 32
    CPU threads, i.e. ~76 h for 8,191 positions, so it is NOT the history source; the decode of the token under test
    (P) stays the bit-exact ISA golden, seeded with this history (qwen_hbmacc_position_oracle_gpu --kv-history).
Output: OUT/L<n>_die<d>.bin = the oracle's u32 view of the fp32 K/V store (TP4 die d holds KV heads 2d, 2d+1; layout
of LayerZero.k_elem / v_elem as in kvl_history.py), rows 0..P-1 filled; OUT/manifest.json (sha256, prep check).
    kvl_prefill_hist.py --snapshot DIR --tokens prompt_tokens_8192.txt --pos 8191 --out DIR [--prep-dir fx/tp4]
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch

import qwen3_deployment_quality as DQ

TMAX, HD, KVD, W, TP = 8192, 128, 2, 16, 4


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--tokens', type=Path, required=True)
    ap.add_argument('--pos', type=int, default=8191)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--prep-dir', type=Path)
    ap.add_argument('--chunk', type=int, default=1024)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    m = DQ.Qwen3(a.snapshot, "gpu", "w8", "fp8", device="cpu", fold=True)
    print(f'loaded in {time.time() - t0:.0f} s', flush=True)
    man = {'schema': 'opentallas.tok-qk-kvl.real-prefill-history.v1', 'pos': a.pos,
           'snapshot_files_sha256': {f.name: sha(f) for f in sorted(a.snapshot.glob('*.safetensors'))},
           'tokens_sha256': sha(a.tokens), 'arith': 'gpu (HF BF16) on cpu', 'weights': 'w8 folded', 'kv': 'fp8',
           'tool_sha256': {p: sha(Path(__file__).parent / p) for p in ('kvl_prefill_hist.py', 'qwen3_deployment_quality.py')}}
    if a.prep_dir:   # the W8 codes / scales of every layer and die vs the pinned TP4 stage images (prep npz)
        chk = {}
        for n in range(m.L):
            lay = m.layers[n]
            q, s = lay['qkv']['q'], lay['qkv']['s'][:, 0]
            for d in range(TP):
                z = np.load(a.prep_dir / f'L{n:02d}_d{d}.npz')
                rows = np.r_[np.arange(1024 * d, 1024 * d + 1024), 4096 + np.arange(256 * d, 256 * d + 256),
                             5120 + np.arange(256 * d, 256 * d + 256)]
                cq = np.array_equal(q[rows].numpy(), z['codes_qkv'])
                cs = np.array_equal(s[rows].to(torch.float32).numpy(), z['scales_qkv'])
                chk[f'L{n}_die{d}'] = {'codes_qkv_equal': bool(cq), 'scales_qkv_equal': bool(cs)}
        man['prep_check'] = chk
        man['prep_check_all_equal'] = all(v['codes_qkv_equal'] and v['scales_qkv_equal'] for v in chk.values())
        print('prep check (qkv codes+scales == pinned TP4 images):', man['prep_check_all_equal'], flush=True)
    toks = [int(t) for t in a.tokens.read_text().split()][:a.pos]
    cache = m.new_cache(1, TMAX)
    tt = torch.tensor(toks)
    for i in range(0, len(toks), a.chunk):
        m.forward(tt[i:i + a.chunk], cache)
        print(f'prefill {min(len(toks), i + a.chunk)}/{len(toks)} ({time.time() - t0:.0f} s)', flush=True)
    P = a.pos
    t = np.arange(P)[:, None]; dim = np.arange(HD)[None, :]
    for n in range(m.L):
        K, V = cache['kv'][n]
        K = K[0, :, :P].to(torch.float32).numpy(); V = V[0, :, :P].to(torch.float32).numpy()   # [8, P, HD]
        for d in range(TP):
            st = np.zeros(2 * KVD * TMAX * HD, dtype=np.float32)
            for g in range(KVD):
                st[((g * (TMAX // W) + t // W) * HD + dim) * W + t % W] = K[2 * d + g]
                st[KVD * TMAX * HD + (g * TMAX + t) * HD + dim] = V[2 * d + g]
            p = a.out / f'L{n}_die{d}.bin'
            st.view('<u4').tofile(p)
            man.setdefault('sha256', {})[p.name] = sha(p)
    man['wall_seconds'] = round(time.time() - t0, 1)
    (a.out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print('KVL_PREFILL_HIST done', man['wall_seconds'], 's')


if __name__ == '__main__':
    main()
