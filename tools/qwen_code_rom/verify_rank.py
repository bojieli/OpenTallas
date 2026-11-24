#!/usr/bin/env python3
"""Verify one built TP8 Qwen code-ROM rank end to end against the real checkpoint.

Three independent legs, each a hard FAIL on any mismatch:

  A. masks:  every one of the rank's 7,680 via maps exists with the manifest
     SHA-256, decodes through the physical bitline order (bitline = 8 * bit +
     word % 8, 10 dead bitlines must be dark) and the decoded 20,032 resident
     words equal the pinned released stage images (matrix_int8.hex, whose
     digests must equal the stage metadata pins) byte for byte -- full, not
     sampled; padding words 20,032..20,479 must be zero.
  B. checkpoint: for the selected layers the stage image is re-derived from
     the pinned Qwen3-8B safetensors rows (hdc_qwen_layer0_rom_w12.verify_sample,
     TP8 / 3,072 groups) and compared code by code, plus row scales.
  D. (--head-scratch) the HEAD stage (lm_head, 1,600 words) re-emitted from
     the checkpoint reproduces the built image byte for byte.
  C. identity: revision, checkpoint lock, rank, tile/bank coverage.

  verify_rank.py --snapshot <ckpt>/<rev> --banks <banks> --masks <masks_rN> --rank N \
      [--layers 0,17,35] [--rows 4] --out verify.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/qwen_code_rom')]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def decode_mask(path: Path) -> np.ndarray:
    """4096 x 32 code bytes from one 512-row x 266-byte via map (inverse of build.physical)."""
    rows = [bytes.fromhex(line.strip().decode())[::-1] for line in path.open('rb') if line.strip()]
    if len(rows) != 512 or any(len(r) != 266 for r in rows):
        raise ValueError(f'wrong via map shape: {path}')
    mask = np.frombuffer(b''.join(rows), dtype=np.uint8).reshape(512, 266)
    if np.any(mask[:, 256:]):
        raise ValueError(f'dead bitlines programmed: {path}')
    bits = np.unpackbits(mask[:, :256], axis=1, bitorder='little').reshape(512, 256, 8)
    return np.packbits(bits.transpose(0, 2, 1), axis=2, bitorder='little').reshape(4096, 32)


def leg_masks(masks: Path, rank: int, build) -> dict:
    rec_path = masks / f'rank{rank}' / 'manifest.json'
    rec = json.loads(rec_path.read_text())
    ident = (rec['rank'], rec['tp'], rec['macros'], rec['resident_words'], rec['checkpoint_revision'],
             rec['checkpoint_lock_sha256'], rec['source_bytes_requantized'], rec['partial_stages'])
    if ident != (rank, 8, 7680, build.ROWS, build.REV, build.LOCK, False, []):
        raise ValueError(f'rank identity mismatch: {ident}')
    pairs = {(p['tile'], p['bank']): p for p in rec['pairs']}
    if set(pairs) != {(t, b) for t in range(build.TILES) for b in range(build.BANKS)}:
        raise ValueError('tile/bank coverage incomplete')
    words = np.zeros((build.BANKS * 4096, build.WORD_BYTES), dtype=np.uint8)
    mdir = masks / f'rank{rank}' / 'masks'
    n = 0
    for (tile, bank), p in sorted(pairs.items()):
        for c in p['columns']:
            f = mdir / c['file']
            if c['instance'] != f'qtile_t{tile}_b{bank}_c{c["native_column"]}' or sha(f) != c['sha256']:
                raise ValueError(f'mask pin mismatch: {f}')
            col = c['native_column']
            words[4096 * bank:4096 * (bank + 1), 64 * tile + 32 * col:64 * tile + 32 * (col + 1)] = decode_mask(f)
            n += 1
    if np.any(words[build.ROWS:]):
        raise ValueError('padding words programmed')
    stages = 0
    for st in rec['stages']:
        path = Path(st['path'])
        meta = json.loads(Path(st['metadata_path']).read_text())
        if sha(path) != st['sha256'] or st['sha256'] != meta['image_sha256']['matrix_int8.hex']:
            raise ValueError(f'stage image pin mismatch: {path}')
        base, count = st['resident_base'], st['words']
        with path.open('rb') as f:
            for i, line in enumerate(f):
                ref = np.frombuffer(bytes.fromhex(line.strip().decode())[::-1], dtype=np.uint8)
                if not np.array_equal(words[base + i], ref):
                    raise ValueError(f'decoded mask word differs from stage image: stage {st["stage"]} word {i}')
        if i + 1 != count:
            raise ValueError(f'stage word count: {st["stage"]}')
        stages += 1
    return {'masks_decoded': n, 'stages_compared': stages, 'resident_words_compared': build.ROWS,
            'manifest_sha256': sha(rec_path)}


def leg_checkpoint(snapshot: Path, banks: Path, rank: int, layers: list[int], rows: int) -> list[dict]:
    os.environ['QWEN_O4_TP'] = '8'
    os.environ['QWEN_O4_GROUPS'] = '3072'
    import hdc_qwen_layer0_rom_w12 as layer
    out = []
    for L in layers:
        out.append(layer.verify_sample(snapshot, banks / f'images/layer{L}/die{rank}', rank,
                                       rows_per_matrix=rows, layer=L))
    return out


def leg_head(snapshot: Path, banks: Path, rank: int, scratch: Path) -> dict:
    """Re-emit the HEAD stage image from the checkpoint (fresh lm_head read + W8 quantize) and compare byte for byte."""
    os.environ['QWEN_O4_TP'] = '8'
    os.environ['QWEN_O4_GROUPS'] = '3072'
    import qwen_o4_head_rom_w12 as head
    built = banks / f'head_images/rank{rank}'
    ref = json.loads((built / 'head_rom.json').read_text())
    fresh = head.emit(snapshot, scratch, rank)
    for k in ('die', 'rows', 'row0', 'code_words', 'scale_words', 'checkpoint_revision', 'checkpoint_lock_sha256'):
        if fresh[k] != ref[k]:
            raise ValueError(f'head identity differs: {k}')
    for name in ('matrix_int8.hex', 'matrix_scale_bf16.hex'):
        if sha(built / name) != ref['image_sha256'][name] or sha(scratch / name) != ref['image_sha256'][name]:
            raise ValueError(f'head stage {name} not reproduced from the checkpoint')
    return {'rows': fresh['rows'], 'row0': fresh['row0'], 'code_words': fresh['code_words'],
            'scale_words': fresh['scale_words'], 'image_sha256': ref['image_sha256']}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--banks', type=Path, required=True)
    ap.add_argument('--masks', type=Path, required=True)
    ap.add_argument('--rank', type=int, choices=range(8), required=True)
    ap.add_argument('--layers', default='0,17,35')
    ap.add_argument('--rows', type=int, default=4)
    ap.add_argument('--skip-masks', action='store_true', help='checkpoint leg only')
    ap.add_argument('--head-scratch', type=Path, help='also re-emit the HEAD stage here and compare (leg D)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    import build
    res = {'schema': 'opentallas.qwen-tp8-code-rank-verify.v1', 'rank': a.rank, 'checkpoint_revision': build.REV}
    try:
        if not a.skip_masks:
            res['masks'] = leg_masks(a.masks, a.rank, build)
        res['checkpoint'] = leg_checkpoint(a.snapshot, a.banks, a.rank,
                                           [int(x) for x in a.layers.split(',') if x != ''], a.rows)
        if a.head_scratch:
            res['head'] = leg_head(a.snapshot, a.banks, a.rank, a.head_scratch)
        res['codes_checked'] = sum(x['codes_checked'] for x in res['checkpoint'])
        res['verdict'] = 'PASS'
    except Exception as e:  # noqa: BLE001 -- any mismatch is the verdict
        res['verdict'] = 'FAIL'
        res['error'] = f'{type(e).__name__}: {e}'
    a.out.write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps({k: res.get(k) for k in ('rank', 'verdict', 'codes_checked', 'error')}))
    return 0 if res['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
