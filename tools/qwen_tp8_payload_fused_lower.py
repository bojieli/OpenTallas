#!/usr/bin/env python3
"""Bind explicit fused lowering to an actual checkpoint ROM/scale program."""
import argparse
import hashlib
import json
from pathlib import Path

import hdc_qwen_fullshape_program_w12 as FP
import hdc_qwen_fullshape_isa_w12 as ISA
from hdc_qwen_fullshape_placement_w12 import TP, GROUPS, LOCK, CONFIG
from qwen_tp8_fused_attention_lower import lower_validated

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lower_image(directory):
    manifest = json.loads((directory / 'layer0_rom.json').read_text())
    if TP != 8 or GROUPS != 3072 or manifest['tp'] != 8 or manifest['layer'] != 0:
        raise ValueError('requires actual TP8/GT3072 layer-zero image environment')
    if manifest['checkpoint_lock_sha256'] != sha(LOCK) or manifest['config_sha256'] != sha(CONFIG):
        raise ValueError('checkpoint/config source pin mismatch')
    for path, digest in manifest['source_sha256'].items():
        if sha(ROOT / path) != digest:
            raise ValueError(f'emitter source pin mismatch: {path}')
    for path, digest in manifest['image_sha256'].items():
        if sha(directory / path) != digest:
            raise ValueError(f'actual payload/image hash mismatch: {path}')
    profile = FP.profile(manifest['die'], matrix_rows=manifest['matrix_layout'],
                         post_scale_bases=manifest['post_tp_scale_bases'])
    source_words = (directory / 'program.hex').read_text().split()
    if source_words != profile['program_hex'] or (directory / 'segments.hex').read_text().split() != profile['descriptor_hex']:
        raise ValueError('actual emitted instruction/descriptor bits differ from source-derived profile')
    fields = [ISA.decode_instruction(int(word, 16)) for word in source_words]
    if len(fields) != 29 or fields[11]['me_wsrc'] != 1 or fields[13]['me_wsrc'] != 1:
        raise ValueError('expected source-derived QK/exp/PV/reciprocal/normalize block')
    scales = [pc for pc, f in enumerate(fields) if f['unit'] == 2 and f['c_src'] == 1
              and f['c_base'] in manifest['post_tp_scale_bases'] and f['d_base'] == profile['vm_map']['T1']]
    if scales != [18, 26]:
        raise ValueError('both actual post-collective O/down scales must survive lowering')
    original = {'program_sha256': sha(directory / 'program.hex'),
                'instructions': [{'encoded_fields': f} for f in fields]}
    candidate = lower_validated(profile, original)
    candidate['schema'] = 'opentallas.qwen-tp8-payload-fused-lowering.v1'
    candidate['actual_image_sha256'] = manifest['image_sha256']
    candidate['actual_emitter_source_sha256'] = manifest['source_sha256']
    candidate['payload_layer'] = manifest['layer']
    candidate['payload_die'] = manifest['die']
    candidate['checkpoint_revision'] = manifest['checkpoint_revision']
    candidate['post_collective_scales'] = [{'source_pc': pc, 'candidate_pc': candidate['original_to_candidate_pc'][pc],
                                         'constant_base': fields[pc]['c_base']} for pc in scales]
    candidate['source_sha256'][Path(__file__).name] = sha(__file__)
    return candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    candidate = lower_image(args.image)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'program.hex').write_text(''.join(w + '\n' for w in candidate['program_hex']))
    (args.out / 'segments.hex').write_text(''.join(w + '\n' for w in candidate['descriptor_hex']))
    (args.out / 'lowering.json').write_text(json.dumps(candidate, indent=2) + '\n')
    print(f"actual payload die{candidate['payload_die']} -> {candidate['program_words']} fused instructions; "
          f"both post-collective scales retained; SHA {candidate['candidate_program_sha256']}")

if __name__ == '__main__':
    main()
