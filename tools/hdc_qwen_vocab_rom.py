#!/usr/bin/env python3
"""Source-pinned shipped Qwen embedding and TP2 lm_head ROM windows.

Sparse ``@address`` memh images preserve full-model addresses while bounding
real-checkpoint tests to a few complete rows. Unlisted scale words read BF16
+1; a full image or RTL testbench must initialize that default explicitly.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from hdc_qwen_fullshape_placement import CONFIG, LOCK, GROUPS, matrix
from hdc_qwen_int8_image import shipped_vocab_rows
from hdc_qwen_layer0_rom import pinned_snapshot, word_hex

ROOT = Path(__file__).resolve().parents[1]
W, IL = 16, 8


def embed_window(codes, scales, global_start):
    out_code, out_scale = {}, {}
    for row, (code, scale) in enumerate(zip(codes, scales)):
        token = global_start + row
        for chunk in range(64):
            out_code[token * 64 + chunk] = np.asarray(code[chunk * 64:(chunk + 1) * 64], dtype=np.uint8)
        out_scale[token] = np.uint16(scale)
    return out_code, out_scale, {'codes_per_word': 64, 'full_code_words': 151936 * 64,
                                 'full_scale_rows': 151936}


def head_window(codes, scales, local_start):
    geometry = matrix(0, 'lm_head', 75968, 4096)
    split, kc, per_round = geometry['split'], geometry['k_per_split'], GROUPS // geometry['split']
    out_code, out_scale = {}, {}
    for offset, (code, scale) in enumerate(zip(codes, scales)):
        row = local_start + offset
        tile, slot, lane = row // (W * IL), row // W % IL, row % W
        round_idx, q = divmod(tile, per_round)
        saddr = (round_idx * per_round + q) * IL + slot
        out_scale.setdefault(saddr, np.full(W, 0x3F80, dtype=np.uint16))[lane] = scale
        for col, value in enumerate(code):
            chunk, kk = divmod(col, kc)
            address = round_idx * kc * IL + kk * IL + slot
            group = q * split + chunk
            out_code.setdefault(address, np.zeros(GROUPS * W, dtype=np.uint8))[group * W + lane] = value
    return out_code, out_scale, geometry


def write_window(snapshot: Path, out: Path, kind: str, start: int, count: int, die=None):
    pinned_snapshot(snapshot)
    source = shipped_vocab_rows(snapshot, kind, start=start, count=count, die=die)
    codes = source['codes'].numpy().view(np.uint8)
    scales = source['scales'].view(__import__('torch').int16).numpy().view(np.uint16).reshape(-1)
    if kind == 'embedding':
        code, scale, geometry = embed_window(codes, scales, source['global_start'])
        code_width = 8
    else:
        code, scale, geometry = head_window(codes, scales, start)
        code_width = 8
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    code_path, scale_path = out / f'{kind}_int8_window.hex', out / f'{kind}_scale_bf16_window.hex'
    with code_path.open('w') as stream:
        for address, value in sorted(code.items()):
            stream.write(f'@{address:x}\n{word_hex(value, code_width)}\n')
    with scale_path.open('w') as stream:
        for address, value in sorted(scale.items()):
            lanes = [int(value)] if kind == 'embedding' else value
            stream.write(f'@{address:x}\n{word_hex(lanes, 16)}\n')
    pins = ('tools/hdc_qwen_vocab_rom.py', 'tools/hdc_qwen_int8_image.py',
            'tools/qwen3_deployment_quality.py', 'tools/hdc_qwen_layer0_rom.py')
    manifest = {'schema': 'opentallas.qwen-o4-vocab-rom-window.v1', 'kind': kind,
                'die': die, 'local_start': start, 'global_start': source['global_start'],
                'rows': count, 'complete': count == (151936 if kind == 'embedding' else 75968) and start == 0,
                'checkpoint_revision': Path(snapshot).name,
                'checkpoint_lock_sha256': hashlib.sha256(LOCK.read_bytes()).hexdigest(),
                'config_sha256': hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
                'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in pins},
                'geometry': geometry, 'code_word_count': len(code), 'scale_word_count': len(scale),
                'default_unlisted_scale_bf16': '3f80',
                'image_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in (code_path, scale_path)},
                'claim_boundary': 'Checkpoint-quantized complete rows at full-shape addresses; no RTL token pass.'}
    (out / f'{kind}_window.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--kind', choices=('embedding', 'lm_head'), required=True)
    ap.add_argument('--die', type=int, choices=(0, 1))
    ap.add_argument('--start', type=int, required=True)
    ap.add_argument('--count', type=int, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    print(json.dumps(write_window(args.snapshot, args.out, args.kind, args.start, args.count, args.die)))


if __name__ == '__main__':
    main()
