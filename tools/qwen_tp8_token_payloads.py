#!/usr/bin/env python3
"""Emit remaining actual TP8 layers and all head banks; execution stays unproved."""
import argparse
import copy
import gc
import hashlib
import json
from pathlib import Path

from hdc_qwen_layer0_rom_w12 import emit as emit_layer
from qwen_o4_head_rom_w12 import emit as emit_head
from qwen_tp8_payload_fused_lower import lower_image
from qwen_tp8_fulltoken_plan import validate_heads


def write_lower(directory, candidate):
    directory.mkdir(parents=True, exist_ok=True)
    for name, key in [('program.hex', 'program_hex'), ('segments.hex', 'descriptor_hex')]:
        (directory / name).write_text(''.join(w + '\n' for w in candidate[key]))
    (directory / 'lowering.json').write_text(json.dumps(candidate, indent=2) + '\n')


def run(snapshot, base, plan_path):
    source_plan = json.loads(plan_path.read_text())
    if source_plan['tp'] != 8 or source_plan['groups'] != 3072 or source_plan['layers'] != 36:
        raise ValueError('not a native source plan')
    validate_heads(source_plan['head_profiles'])
    for mutant in ('missing_rank', 'rank_offset'):
        heads = copy.deepcopy(source_plan['head_profiles'])
        if mutant == 'missing_rank':
            heads.pop()
        else:
            # Transported descriptor high row bit, not a metadata-only change.
            heads[7]['descriptor_hex'][0] = f"{int(heads[7]['descriptor_hex'][0], 16) ^ (1 << 18):016x}"
        try:
            validate_heads(heads)
        except ValueError:
            print('MUTANT_REJECTED', mutant, flush=True)
        else:
            raise AssertionError('head binding mutant escaped: ' + mutant)
    receipts = {'schema': 'opentallas.qwen-tp8-token-payloads.v1',
                'plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                'checkpoint_revision': snapshot.name, 'layers': [], 'heads': [],
                'scope': 'Actual immutable checkpoint images only; no execution, token or timing proof'}
    receipt_path = base / 'token_payload_progress.json'
    for layer in range(36):
        for rank in range(8):
            image = base / 'images' / f'layer{layer}' / f'die{rank}'
            manifest_path = image / f'layer{layer}_rom.json'
            if not manifest_path.exists():
                emit_layer(snapshot, image, rank, layer=layer, compact_banks=True)
            candidate = lower_image(image, layer=layer)
            write_lower(base / 'fused_images' / f'layer{layer}' / f'die{rank}', candidate)
            receipts['layers'].append({'layer': layer, 'rank': rank,
                                       'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                                       'program_sha256': candidate['candidate_program_sha256']})
            receipt_path.write_text(json.dumps(receipts, indent=2) + '\n')
            print('LAYER_IMAGE_BOUND', layer, rank, flush=True)
            gc.collect()
    for rank in range(8):
        directory = base / 'head_images' / f'rank{rank}'
        manifest = emit_head(snapshot, directory, rank)
        if manifest['code_words'] != source_plan['head_geometry']['words'] or manifest['rows'] != 18992:
            raise ValueError('actual head emitter differs from source plan')
        receipts['heads'].append({'rank': rank, 'manifest': manifest})
        receipt_path.write_text(json.dumps(receipts, indent=2) + '\n')
        print('HEAD_IMAGE_BOUND', rank, flush=True)
        gc.collect()
    receipts['status'] = 'ALL36_LAYERS_ALL8_HEAD_IMAGES_SOURCE_BOUND_NOT_EXECUTED'
    receipt_path.write_text(json.dumps(receipts, indent=2) + '\n')
    print(receipts['status'], flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--base', type=Path, required=True)
    ap.add_argument('--plan', type=Path, required=True)
    args = ap.parse_args()
    run(args.snapshot, args.base, args.plan)
