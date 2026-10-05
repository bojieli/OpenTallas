#!/usr/bin/env python3
"""Emit the complete TP-2 lm_head INT8 code and BF16 scale ROM images of one die.

Stage-local compact banks for the head program of
tools/qwen_o4_fulltoken_binding_w12.py (code base 0, scale base 0, 99 rounds of
split 1024): code word a holds round/k/slot a as hdc_qwen_layer0_rom_w12's
engine_word_arrays lays it out (the same order hdc_qwen_vocab_rom.head_window
uses for sparse windows); scale word a holds the 16 BF16 row scales of
(round, tile, slot).  Rows are W8-quantized from the pinned checkpoint by
hdc_qwen_int8_image_w12.shipped_vocab_rows in windows, which that function
documents as composing into the complete image.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from hdc_qwen_fullshape_placement_w12 import CONFIG, GROUPS, LOCK, TP, matrix
from hdc_qwen_int8_image_w12 import shipped_vocab_rows
from hdc_qwen_layer0_rom_w12 import engine_word_arrays, pinned_snapshot, word_hex

ROOT = Path(__file__).resolve().parents[1]
ROWS = 151936 // TP
PINS = ('tools/qwen_o4_head_rom_w12.py', 'tools/hdc_qwen_int8_image_w12.py', 'tools/hdc_qwen_layer0_rom_w12.py',
        'tools/hdc_qwen_fullshape_placement_w12.py', 'tools/qwen3_deployment_quality.py')


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def emit(snapshot: Path, out: Path, die: int, window: int = 8192) -> dict:
    pinned_snapshot(snapshot)
    geo = matrix(0, 'lm_head', ROWS, 4096)
    codes = np.empty((ROWS, 4096), dtype=np.int8)
    scales = np.empty(ROWS, dtype=np.uint16)
    import torch
    for start in range(0, ROWS, window):
        count = min(window, ROWS - start)
        src = shipped_vocab_rows(snapshot, 'lm_head', start=start, count=count, die=die)
        codes[start:start + count] = src['codes'].numpy().view(np.int8)
        scales[start:start + count] = src['scales'].view(torch.int16).numpy().view(np.uint16).reshape(-1)
    out.mkdir(parents=True, exist_ok=True)
    per_round, kc = GROUPS // geo['split'], geo['k_per_split']
    code_count, scale_count = geo['rounds'] * kc * 8, geo['rounds'] * per_round * 8
    code_path, scale_path = out / 'matrix_int8.hex', out / 'matrix_scale_bf16.hex'
    with code_path.open('w') as cf, scale_path.open('w') as sf:
        for addr, (code, scale) in enumerate(engine_word_arrays(codes, scales, split=geo['split'])):
            if addr < code_count:
                cf.write(word_hex(code, 8) + '\n')
            if addr < scale_count:
                sf.write(word_hex(scale, 16) + '\n')
    manifest = {'schema': 'opentallas.qwen-o4-head-rom.v1', 'die': die, 'rows': ROWS, 'row0': die * ROWS,
                'geometry': geo, 'groups': GROUPS, 'tp': TP, 'code_words': code_count, 'scale_words': scale_count,
                'code_base': 0, 'scale_base': 0, 'checkpoint_revision': Path(snapshot).name,
                'checkpoint_lock_sha256': sha(LOCK), 'config_sha256': sha(CONFIG),
                'source_sha256': {p: sha(ROOT / p) for p in PINS},
                'image_sha256': {p.name: sha(p) for p in (code_path, scale_path)},
                'claim_boundary': 'Complete checkpoint-quantized lm_head TP-2 die image; no RTL result by itself.'}
    (out / 'head_rom.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--die', type=int, choices=range(TP), required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    m = emit(args.snapshot, args.out, args.die)
    print(json.dumps({k: m[k] for k in ('die', 'code_words', 'scale_words', 'image_sha256')}, indent=2))


if __name__ == '__main__':
    main()
