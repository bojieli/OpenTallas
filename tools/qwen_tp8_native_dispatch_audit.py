#!/usr/bin/env python3
"""Catalog the pinned TP8 instruction image without claiming its execution."""
import argparse
import hashlib
import json
from pathlib import Path

import hdc_qwen_fullshape_isa_w12 as ISA

LABELS = [
    'hidden sum of squares', 'QKV projection', 'hidden reciprocal RMS',
    'V scale and cache write', 'QK scale and sums of squares',
    'QK reciprocal RMS', 'QK weighted normalization', 'Q lower RoPE',
    'K lower RoPE and cache write', 'Q upper RoPE',
    'K upper RoPE and cache write', 'QK scores and row maxima',
    'scaled exponentials and ordered Z reduction', 'PV weighted sum',
    'Z reciprocal', 'attention normalization', 'O projection',
    'O all-reduce fence', 'attention residual and hidden sum of squares',
    'gate/up projection', 'post-attention reciprocal RMS',
    'gate/up scale', 'SiLU times up', 'down projection',
    'down all-reduce fence', 'MLP residual and hidden sum of squares',
    'layer completion fence',
]

def audit(profile, image):
    raw = image.read_bytes()
    words = [int(line, 16) for line in raw.decode().splitlines() if line.strip()]
    if words != [int(word, 16) for word in profile['program_hex']]:
        raise ValueError('actual image differs from profile instruction bits')
    if profile['tp'] != 8 or profile['groups'] != 3072 or len(words) != len(LABELS):
        raise ValueError('this operation catalog requires the pinned TP8/GT3072 layer-zero profile')
    vm = profile['vm_map']
    def region(address):
        return max(((base, name) for name, base in vm.items() if base <= address), default=(0, '?'))[1]
    rows = []
    for pc, word in enumerate(words):
        f = ISA.decode_instruction(word)
        if f['unit'] == 1:
            provider = 'native_attention_QK' if f['me_wsrc'] and f['me_d_tiles'] else ('native_attention_PV' if f['me_wsrc'] else 'ROM_matvec')
            memory = {'x_element_base': f['me_xbase'], 'x_region': region(f['me_xbase']),
                      'output_word_base': f['me_obase'], 'output_region': region(f['me_obase'] * 16),
                      'weight_source': 'KV' if f['me_wsrc'] else 'ROM', 'weight_base': f['me_wbase']}
        elif f['unit'] == 2:
            provider = 'SU64_and_native_KV_formatter' if f['dst'] == 2 else 'SU64'
            memory = {key: {'base': f[key + '_base'], 'source': 'constant_ROM' if f[key + '_src'] else 'VM',
                            'region': None if f[key + '_src'] else region(f[key + '_base'])} for key in ('a', 'b', 'c')}
            memory['destination'] = {'kind': ('none', 'VM', 'KV')[f['dst']], 'base': f['d_base'],
                                     'region': region(f['d_base']) if f['dst'] == 1 else None}
            memory['reduction'] = {'kind': f['red'], 'base': f['r_base'], 'region': region(f['r_base']) if f['red'] else None}
        else:
            provider = 'TP8_collective' if pc in (17, 24) else 'layer_completion'
            memory = {}
        rows.append({'pc': pc, 'operation': LABELS[pc], 'required_provider': provider,
                     'encoded_fields': f, 'memory_operands': memory,
                     'dependency': {key: f[key] for key in ('barrier', 'wait_me', 'wait_su', 'chase', 'chase_n', 'chase_rows')},
                     'integration_status': 'NOT_WHOLE_LAYER_BOUND_OR_EXECUTED'})
    return {'schema': 'opentallas.qwen-tp8-native-dispatch-audit.v1',
            'claim': 'Source-derived instruction ownership and interface requirements only; no whole-layer arithmetic or latency proof.',
            'program_sha256': hashlib.sha256(raw).hexdigest(), 'tp': 8, 'groups': 3072,
            'vm_elems': profile['vm_elems'], 'kv_window_elems': profile['kv_window_elems'],
            'instructions': rows,
            'required_contracts': {
                'ROM_matvec': 'Accept only WSRC0; preserve actual X-address stalls and registered root ordering. Completion includes every output VM write commit.',
                'native_attention': 'Accept PCs11/13 from actual instruction bits and token position. Read actual Q/K/V, write actual S/M and ATT; preserve four Q heads sharing one KV head and golden reduction order. Report accepted operation, ready, idle, progress and faults to ME controller.',
                'SU64': 'Use actual VM operands, coefficient/RoPE ROM and exact rounding; advance progress only after actual published VM/reduction outputs. PCs12/14/15 remain SU-owned unless explicit replacement binds equivalent effects to instruction retirement.',
                'KV_formatter': 'Buffer non-stallable SU vector writes; drained means receiver memory commits including partial V sector flush, not just enqueue or transmission. PCs11/13 wait for prior K/V commits.',
                'TP8_collective': 'At PCs17/24 drain both units and KV writes, reduce actual 256-word T1 vector in golden rank order, publish all return VM writes before next segment starts.',
                'layer_completion': 'At PC26 require all arithmetic, mutable writes, collective returns and link credits drained; this image omits embedding/lm_head and does not prove a token.',
            }}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = audit(json.loads(args.profile.read_text()), args.image)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(f"cataloged {len(report['instructions'])} actual instructions: {report['program_sha256']}")

if __name__ == '__main__':
    main()
