#!/usr/bin/env python3
"""Pack real shipped Qwen3-8B layer-0 TP2 INT8 rows into G6144 ROM words.

The o/down code ROM carries unscaled partials. Their true full-row BF16 scales
are placed in constant ROM for one SU multiply after both TP half-reductions.
This emits images and ISA words; it does not claim RTL execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from safetensors import safe_open

import hdc_golden as G
import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_program as FP
from hdc_qwen_fullshape_placement import CONFIG, LOCK, GROUPS, matrix
from hdc_qwen_int8_image import first_layer_tp2_matrices

W, IL = I.W_LANES, I.INTERLEAVE
ROOT = Path(__file__).resolve().parents[1]


def pinned_snapshot(snapshot: Path):
    lock = json.loads(LOCK.read_text())
    snapshot = Path(snapshot)
    if snapshot.name != lock['revision']:
        raise ValueError('snapshot revision differs from shipped source lock')
    for item in lock['expected_files']:
        if item['path'].endswith('.safetensors') or item['path'] in ('config.json', 'model.safetensors.index.json'):
            path = snapshot / item['path']
            if not path.is_file() or path.stat().st_size != item['size_bytes']:
                raise ValueError(f'missing/size-mismatched shipped checkpoint file: {path}')
            if path.is_symlink() and item['path'].endswith('.safetensors'):
                if path.resolve().name != item['sha256']:
                    raise ValueError(f'blob pin mismatch: {path}')
            elif hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError(f'content pin mismatch: {path}')
    return lock


def joined_matrices(source):
    """Apply the same qkv and gate/up row order as hdc_program.Layout."""
    def arrays(key):
        x = source[key]
        return x['codes'].numpy(), x['scales'].view(__import__('torch').int16).numpy().view(np.uint16).reshape(-1)
    q, qs = arrays('q'); k, ks = arrays('k'); v, vs = arrays('v')
    gate, gs = arrays('gate'); up, us = arrays('up')
    if gate.shape != up.shape or gate.shape[0] % 128:
        raise ValueError('gate/up rows must have matching 128-row tiles')
    gu = np.concatenate([part for i in range(0, len(gate), 128)
                         for part in (gate[i:i + 128], up[i:i + 128])])
    gus = np.concatenate([part for i in range(0, len(gs), 128)
                          for part in (gs[i:i + 128], us[i:i + 128])])
    return {'qkv': (np.concatenate((q, k, v)), np.concatenate((qs, ks, vs))),
            'o': arrays('o'), 'gu': (gu, gus), 'down': arrays('down')}


def engine_word_arrays(codes, scales, *, split, groups=GROUPS, raw_partial=False):
    """Yield code/scale words at identical addresses; pad the shorter bank."""
    codes = np.asarray(codes, dtype=np.int8)
    scales = np.asarray(scales, dtype=np.uint16).reshape(-1)
    n, k = codes.shape
    if len(scales) != n or groups % split or k % split:
        raise ValueError('matrix scale or K-split shape mismatch')
    per_round, kc = groups // split, k // split
    rounds = (n + W * IL * per_round - 1) // (W * IL * per_round)
    code_count, scale_count = rounds * kc * IL, rounds * per_round * IL
    span = max(code_count, scale_count)
    pad = np.zeros((rounds * per_round * W * IL, k), dtype=np.int8)
    pad[:n] = codes
    blk = pad.reshape(rounds, per_round, IL, W, split, kc)
    spad = np.full(rounds * per_round * W * IL, 0x3F80, dtype=np.uint16)
    spad[:n] = 0x3F80 if raw_partial else scales
    scale_rows = spad.reshape(-1, W)
    for addr in range(span):
        if addr < code_count:
            r, rem = divmod(addr, kc * IL)
            kk, j = divmod(rem, IL)
            code = blk[r, :, j, :, :, kk].transpose(0, 2, 1).reshape(-1).view(np.uint8)
        else:
            code = np.zeros(groups * W, dtype=np.uint8)
        scale = scale_rows[addr] if addr < scale_count else np.full(W, 0x3F80, dtype=np.uint16)
        yield code, scale


def word_hex(lanes, width):
    if width == 8:
        return np.asarray(lanes, dtype=np.uint8)[::-1].tobytes().hex()
    return ''.join(f'{int(v):04x}' for v in np.asarray(lanes, dtype=np.uint16)[::-1])


def matrix_plan(matrices):
    rows, base = [], 0
    for name in ('qkv', 'o', 'gu', 'down'):
        codes, scales = matrices[name]
        row = matrix(base, name, *codes.shape)
        row['scale_base'] = base
        row['scale_span_words'] = row['rounds'] * (GROUPS // row['split']) * IL
        row['code_span_words'] = row['words']
        row['allocated_words'] = max(row['code_span_words'], row['scale_span_words'])
        row['end'] = base + row['allocated_words']
        if len(scales) != row['rows']:
            raise ValueError(f'{name}: missing one scale per row')
        rows.append(row)
        base = row['end']
    return rows


def constant_words(snapshot, true_o_scales, true_down_scales, lay):
    """Build the exact first-layer constant addresses used by the ISA profile."""
    index = json.loads((snapshot / 'model.safetensors.index.json').read_text())['weight_map']
    def tensor(name):
        with safe_open(str(snapshot / index[name]), framework='pt', device='cpu') as sf:
            return sf.get_tensor(name).float().numpy()
    cb = lay.cb
    data = [(np.float32(0), np.float32(0)) for _ in range(cb['rope'])]
    qn = tensor('model.layers.0.self_attn.q_norm.weight')
    kn = tensor('model.layers.0.self_attn.k_norm.weight')
    norms = np.concatenate((np.tile(qn, lay.NH), np.tile(kn, lay.KV)))
    for i, value in enumerate(norms):
        data[cb[(0, 'qk')] + i] = (np.float32(value), np.float32(0))
    data[cb['qscale']] = (np.float32(0), np.float32(1 / np.sqrt(lay.HD)))
    for position in range(FP.TMAX):
        cos, sin, _ = G.rope_tables(position, lay.HD, 1_000_000)
        data.extend(zip(cos, sin))
    o_base = len(data)
    data.extend((np.uint32(int(x) << 16).view(np.float32), np.float32(0)) for x in true_o_scales)
    down_base = len(data)
    data.extend((np.uint32(int(x) << 16).view(np.float32), np.float32(0)) for x in true_down_scales)
    return data, (o_base, down_base)


def emit(snapshot: Path, out: Path, die: int):
    pinned_snapshot(snapshot)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    source = first_layer_tp2_matrices(snapshot, die)
    matrices = joined_matrices(source)
    rows = matrix_plan(matrices)
    lay = FP.LayerZero(None, die, rows)
    crom, scale_bases = constant_words(snapshot, matrices['o'][1], matrices['down'][1], lay)
    prog = FP.profile(die, matrix_rows=rows, post_scale_bases=scale_bases)
    code_path, scale_path = out / 'matrix_int8.hex', out / 'matrix_scale_bf16.hex'
    scale_depth = max(row['base'] + (row['rounds'] - 1) * (GROUPS // row['split']) * IL
                      + (GROUPS - 1) * IL + IL for row in rows)
    with code_path.open('w') as code_file, scale_path.open('w') as scale_file:
        for row in rows:
            codes, scales = matrices[row['name']]
            words = engine_word_arrays(codes, scales, split=row['split'],
                                       raw_partial=row['name'] in ('o', 'down'))
            for code, scale in words:
                code_file.write(word_hex(code, 8) + '\n')
                scale_file.write(word_hex(scale, 16) + '\n')
        # The current core requests a scale word for every physical group,
        # including groups outside G/S valid output tiles. Those words still
        # need a defined finite ROM response until RTL masks the requests.
        for _ in range(rows[-1]['end'], scale_depth):
            scale_file.write('3f80' * W + '\n')
    (out / 'crom.hex').write_text(P.hexwords(((int(G.bits(hi)) << 32) | int(G.bits(lo))
                                             for lo, hi in crom), 64))
    (out / 'program.hex').write_text('\n'.join(prog['program_hex']) + '\n')
    (out / 'segments.hex').write_text('\n'.join(prog['descriptor_hex']) + '\n')
    images = [code_path, scale_path, out / 'crom.hex', out / 'program.hex', out / 'segments.hex']
    source_files = ('tools/hdc_qwen_layer0_rom.py', 'tools/hdc_qwen_int8_image.py',
                    'tools/hdc_qwen_fullshape_program.py', 'tools/hdc_qwen_fullshape_placement.py',
                    'tools/hdc_program.py', 'tools/hdc_isa.py', 'tools/qwen3_deployment_quality.py')
    source_pins = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_files}
    manifest = {'schema': 'opentallas.qwen-o4-layer0-tp2-rom.v1', 'status': 'image_and_isa_emitted',
                'die': die, 'tp': 2, 'checkpoint_revision': snapshot.name,
                'checkpoint_lock_sha256': hashlib.sha256(LOCK.read_bytes()).hexdigest(),
                'config_sha256': hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
                'checkpoint_index_sha256': hashlib.sha256((snapshot / 'model.safetensors.index.json').read_bytes()).hexdigest(),
                'source_sha256': source_pins,
                'matrix_word_bits': GROUPS * W * 8,
                'matrix_words': rows[-1]['end'], 'matrix_layout': rows,
                'scale_rom_words': scale_depth,
                'constant_words': len(crom), 'post_tp_scale_bases': scale_bases,
                'program_words': prog['program_words'], 'segments': prog['segment_count'],
                'image_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in images},
                'blockers': [item for item in prog['blockers']
                             if 'TP2 norm-folded INT8 matrix payloads and constant payloads' not in item]
                            + ['first-layer RTL execution and bit-exact TP2 shard comparison remain unrun',
                               'embedding/lm_head and all 36 layer payloads are not emitted'],
                'claim_boundary': 'Real checkpoint layer-0 ROM/ISA mapping only; RTL bit exactness and full token unproved.'}
    (out / 'layer0_rom.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def verify_sample(snapshot: Path, out: Path, die: int, rows_per_matrix=8):
    """Compare packed ROM addresses with independently re-read real W8 rows."""
    pinned_snapshot(snapshot)
    out = Path(out)
    manifest = json.loads((out / 'layer0_rom.json').read_text())
    if manifest['die'] != die or manifest['checkpoint_revision'] != Path(snapshot).name:
        raise ValueError('image source/die identity mismatch')
    if manifest['checkpoint_lock_sha256'] != hashlib.sha256(LOCK.read_bytes()).hexdigest():
        raise ValueError('checkpoint lock pin mismatch')
    for name, digest in manifest['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'stale source pin: {name}')
    for name, digest in manifest['image_sha256'].items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'image digest mismatch: {name}')
    source = first_layer_tp2_matrices(snapshot, die, rows_per_matrix=rows_per_matrix)
    layout = {item['name']: item for item in manifest['matrix_layout']}
    encoded = [I.decode(int(word, 16)) for word in (out / 'program.hex').read_text().splitlines()]
    post_su = [f for f in encoded if f['unit'] == I.UNIT_SU and f['c_src'] == I.SRC_ALT
               and f['c_base'] in manifest['post_tp_scale_bases'] and f['d_base'] == FP.vm_map()[0]['T1']]
    if len(post_su) != 2 or [f['c_base'] for f in post_su] != manifest['post_tp_scale_bases']:
        raise ValueError('post-TP scale schedule mismatch')
    descriptors = [int(word, 16) for word in (out / 'segments.hex').read_text().splitlines()]
    if len(descriptors) != 5 or sum((word & 3) == P.COLL_ALLREDUCE for word in descriptors) != 4:
        raise ValueError('TP half-collective schedule mismatch')
    code_width = GROUPS * W * 2 + 1
    scale_width = W * 4 + 1
    checks = 0
    with (out / 'matrix_int8.hex').open('rb') as cf, (out / 'matrix_scale_bf16.hex').open('rb') as sf, \
            (out / 'crom.hex').open('rb') as crom:
        @lru_cache(maxsize=64)
        def code_word(addr):
            cf.seek(addr * code_width)
            line = cf.read(code_width)
            if len(line) != code_width:
                raise ValueError('short code ROM image')
            return line

        @lru_cache(maxsize=64)
        def scale_word(addr):
            sf.seek(addr * scale_width)
            line = sf.read(scale_width)
            if len(line) != scale_width:
                raise ValueError('short scale ROM image')
            return line

        def code_at(meta, row, col):
            split, kc = meta['split'], meta['k_per_split']
            per_round = GROUPS // split
            tile, slot, lane = row // (W * IL), (row // W) % IL, row % W
            round_idx, q = divmod(tile, per_round)
            chunk, kk = divmod(col, kc)
            address = meta['base'] + round_idx * kc * IL + kk * IL + slot
            group = q * split + chunk
            offset = 2 * (GROUPS * W - 1 - (group * W + lane))
            return int(code_word(address)[offset:offset + 2], 16)

        def scale_at(meta, row):
            per_round = GROUPS // meta['split']
            tile, slot, lane = row // (W * IL), (row // W) % IL, row % W
            round_idx, q = divmod(tile, per_round)
            address = meta['base'] + (round_idx * per_round + q) * IL + slot
            offset = 4 * (W - 1 - lane)
            return int(scale_word(address)[offset:offset + 4], 16)

        offsets = {'q': ('qkv', 0), 'k': ('qkv', 2048), 'v': ('qkv', 2560),
                   'o': ('o', 0), 'gate': ('gu', 0), 'up': ('gu', 128), 'down': ('down', 0)}
        for name, (mapped, row0) in offsets.items():
            item, meta = source[name], layout[mapped]
            codes = item['codes'].numpy().view(np.uint8)
            scales = item['scales'].view(__import__('torch').int16).numpy().view(np.uint16).reshape(-1)
            for row in range(codes.shape[0]):
                for col in range(codes.shape[1]):
                    if code_at(meta, row0 + row, col) != int(codes[row, col]):
                        raise ValueError(f'{name} code mismatch at row={row} col={col}')
                    checks += 1
                actual_scale = scale_at(meta, row0 + row)
                if actual_scale != (0x3F80 if name in ('o', 'down') else int(scales[row])):
                    raise ValueError(f'{name} matrix scale mismatch at row={row}')
                if name in ('o', 'down'):
                    base = manifest['post_tp_scale_bases'][0 if name == 'o' else 1]
                    crom.seek((base + row) * 17)
                    word = crom.read(17)
                    if len(word) != 17 or int(word[8:16], 16) != int(scales[row]) << 16:
                        raise ValueError(f'{name} post-TP scale mismatch at row={row}')
    return {'schema': 'opentallas.qwen-o4-layer0-rom-sample-gate.v1',
            'status': 'exact_sampled_rows', 'die': die, 'rows_per_matrix': rows_per_matrix,
            'codes_checked': checks, 'full_row_scale_after_tp': True,
            'claim_boundary': 'Real checkpoint sampled ROM code/scale address gate; no RTL layer or full token pass.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--die', type=int, choices=(0, 1), required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--verify-sample', type=int, metavar='ROWS',
                    help='Verify existing image against this many complete real rows per source matrix')
    args = ap.parse_args()
    if args.verify_sample is not None:
        print(json.dumps(verify_sample(args.snapshot, args.out, args.die, args.verify_sample)))
    else:
        result = emit(args.snapshot, args.out, args.die)
        print(json.dumps({k: result[k] for k in ('status', 'die', 'matrix_words', 'program_words', 'segments')}))


if __name__ == '__main__':
    main()
