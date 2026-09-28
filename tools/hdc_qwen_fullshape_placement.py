#!/usr/bin/env python3
"""Checkpoint-free address preflight for the shipped Qwen3-8B TP2 INT8 image.

This computes the matrix ROM geometry used by hdc_program.Layout.place_matrix.
It does not emit weights, a program, or a golden/RTL shard verdict.
"""
import argparse
import hashlib
import json
from pathlib import Path

import hdc_golden as G
import hdc_isa as I
import hdc_program as P

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'compiler/models/qwen3-8b/config.json'
LOCK = ROOT / 'compiler/models/qwen3-8b/checkpoint_source.json'
GROUPS, W, IL = 6144, I.W_LANES, I.INTERLEAVE


def matrix(base, name, n, k, groups=GROUPS):
    if n <= 0 or k <= 0 or groups <= 0 or k % W:
        raise ValueError(f'{name}: invalid matrix/group dimensions')
    split = G.split_for(n, k, groups, W, IL)
    if groups % split:
        raise ValueError(f'{name}: K split {split} does not divide {groups} groups')
    kc = k // split
    per_round = groups // split
    tiles = (n + W * IL - 1) // (W * IL)
    rounds = (tiles + per_round - 1) // per_round
    words = rounds * kc * IL
    return {'name': name, 'base': base, 'end': base + words, 'words': words,
            'rows': n, 'columns': k, 'split': split, 'k_per_split': kc,
            'tiles_per_round': per_round, 'rounds': rounds,
            'scale_rows': n, 'scale_words': (n + W - 1) // W}


def placement(config=None, groups=GROUPS):
    config = json.loads(CONFIG.read_text()) if config is None else config
    shape = (config['hidden_size'], config['num_hidden_layers'], config['num_attention_heads'],
             config['num_key_value_heads'], config['head_dim'], config['intermediate_size'],
             config['vocab_size'])
    if shape != (4096, 36, 32, 8, 128, 12288, 151936):
        raise ValueError(f'not shipped Qwen3-8B config: {shape}')
    h, layers, nh, kv, hd, ff, vocab = shape
    matrices = []
    base = scale_base = 0
    # Both TP2 dies have the same matrix geometry; row contents and vocab
    # indices differ.  Code ROM words are 8*W*G bits, exactly as the reduced
    # INT8 image writer; each output row gets one BF16 post-tree scale.
    dims = [('qkv', (nh // 2 + 2 * kv // 2) * hd, h),
            ('o', h, nh // 2 * hd), ('gu', ff, h), ('down', h, ff // 2)]
    for layer in range(layers):
        for name, n, k in dims:
            row = matrix(base, f'L{layer:02d}.{name}', n, k, groups)
            row['scale_base'] = scale_base
            row['scale_end'] = scale_base + row['scale_words']
            matrices.append(row)
            base = row['end']
            scale_base = row['scale_end']
    head = matrix(base, 'lm_head', vocab // 2, h, groups)
    head['scale_base'] = scale_base
    head['scale_end'] = scale_base + head['scale_words']
    matrices.append(head)
    base = head['end']
    scale_base = head['scale_end']
    embed_words = (vocab * h + W * groups - 1) // (W * groups)
    embedding_element_base = base * W * groups
    a_limit = 1 << I.A
    n_limit = 1 << I.N
    blockers = []
    if base + embed_words > a_limit:
        blockers.append('matrix+embedding BF16-compatible word address exceeds ISA AW24')
    if embedding_element_base + vocab * h > a_limit:
        blockers.append('legacy hdc_program embedding element address exceeds ISA AW24; separate INT8 embed ROM requires a new base contract')
    if vocab > n_limit:
        blockers.append('vocabulary token and argmax index exceed NW16')
    if vocab // 2 > n_limit:
        blockers.append('lm_head me_nout exceeds ISA NW16; emit row chunks with argmax continuation')
    if max(P.VM['GU'] + ff, P.VM['ACT'] + ff // 2, P.VM['QKV'] + (nh // 2 + kv) * hd) > I.VM_ELEMS:
        blockers.append('fixed vector-memory placement exceeds VM_ELEMS=4096')
    if config['max_position_embeddings'] > I.T_MAX:
        blockers.append('shipped context exceeds T_MAX=64 KV provision')
    blockers.append('TP2 norm fold is absent from hdc_program.Layout/build_program')
    blockers.append('reduced INT8 scale image aliases matrix-word bases; shipped image needs independent dense scale-base addressing')
    blockers.append('DFlash drafter fc S4096 / verify-slot ISA image is not emitted')
    blockers.append('fullshape stage program/ROM depth and deployed INT8 golden are not validated')
    return {'schema': 'opentallas.qwen-o4-fullshape-placement.v1',
            'status': 'blocked' if blockers else 'ready_for_image',
            'config_sha256': hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
            'checkpoint_lock_sha256': hashlib.sha256(LOCK.read_bytes()).hexdigest(),
            'tp': 2, 'identical_geometry_per_die': True,
            'groups': groups, 'lanes': W, 'interleave': IL,
            'matrix_code_words_per_die': base,
            'matrix_code_word_bits': 8 * W * groups,
            'matrix_scale_words_per_die': scale_base,
            'embedding_code_words_per_die': embed_words,
            'embedding_element_address_base': embedding_element_base,
            'embedding_scale_rows_per_die': vocab,
            'matrix_scale_rows_per_die': sum(x['scale_rows'] for x in matrices),
            'matrices_per_die': matrices, 'blockers': blockers,
            'claim_boundary': 'Analytical INT8 ROM placement only; no checkpoint image, ISA program, or RTL comparison.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    report = placement()
    data = json.dumps(report, indent=2) + '\n'
    if args.out:
        args.out.write_text(data)
    else:
        print(data, end='')


if __name__ == '__main__':
    main()
