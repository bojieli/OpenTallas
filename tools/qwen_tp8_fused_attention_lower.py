#!/usr/bin/env python3
"""Explicit opt-in program lowering for an unqualified fused TP8 service."""
import argparse
import hashlib
import json
from pathlib import Path

import hdc_isa as I
import hdc_qwen_fullshape_isa_w12 as ISA
from qwen_tp8_native_dispatch_audit import audit


def lower(profile, image):
    original = audit(profile, image)
    fields = [row['encoded_fields'].copy() for row in original['instructions']]
    vm = profile['vm_map']
    removed = set(range(11, 16))
    dead = {'S': (vm['S'], vm['S'] + 4 * 8192),
            'M': (vm['M'], vm['M'] + 4), 'Z': (vm['Z'], vm['Z'] + 4),
            'RZ': (vm['RZ'], vm['RZ'] + 4), 'ATT': (vm['ATT'], vm['ATT'] + 512)}
    access_proof = []
    def check(pc, role, addresses):
        addresses = set(addresses)
        for name, (lo, hi) in dead.items():
            if any(lo <= addr < hi for addr in addresses):
                raise ValueError(f'PC{pc} {role} aliases removed attention intermediate {name}')
        if addresses:
            access_proof.append({'original_pc': pc, 'role': role, 'elements': len(addresses),
                                 'minimum': min(addresses), 'maximum': max(addresses)})
    for pc, f in enumerate(fields):
        if pc in removed:
            continue
        if f['unit'] == I.UNIT_SU:
            if f['su_d_nin']:
                raise ValueError('unexpected dynamic SU count outside removed operators')
            used = ['a']
            if f['ma'] == I.MA_AB or f['md'] == I.MD_B or f['ad'] == I.AD_NEGB:
                used.append('b')
            if f['ad'] in (I.AD_Q, I.AD_C) or f['mc'] == I.MC_C:
                used.append('c')
            for src in used:
                if not f[src + '_src']:
                    if f[src + '_d']:
                        raise ValueError('unexpected dynamic VM source outside removed operators')
                    check(pc, 'read_' + src, (f[src + '_base'] + o*f[src + '_so'] + n*f[src + '_si']
                          for o in range(f['su_nout']) for n in range(f['su_nin'])))
            if f['dst'] == I.DST_VM:
                if f['d_d']:
                    raise ValueError('unexpected dynamic VM destination')
                check(pc, 'VM_write', (f['d_base'] + o*f['d_so'] + n*f['d_si']
                      for o in range(f['su_nout']) for n in range(f['su_nin'])))
            if f['red']:
                check(pc, 'reduction_write', (f['r_base'] + o*f['r_so'] for o in range(f['su_nout'])))
        elif f['unit'] == I.UNIT_ME:
            if f['me_wsrc'] or f['me_d_k'] or f['me_d_nout'] or f['me_d_tiles']:
                raise ValueError('unexpected dynamic matrix provider outside removed operators')
            # All retained ROM operations use contiguous X with xjs0/xks1;
            # derive the whole K from actual K-split, not output count.
            if f['me_xjs'] or f['me_xks'] != 1:
                raise ValueError('unsupported retained ROM X addressing')
            check(pc, 'ROM_X_read', range(f['me_xbase'], f['me_xbase'] + f['me_k']*(1 << f['me_split'])))
            check(pc, 'ROM_VM_write', range(f['me_obase']*16, f['me_obase']*16 + f['me_nout']))
    for descriptor in profile['descriptor_hex']:
        d = ISA.decode_descriptor(int(descriptor, 16))
        if d['kind'] == 1:
            check(-1, 'collective_VM_read_write', range(d['vm_word']*16, (d['vm_word']+d['words'])*16))
    # This is a NEW provider contract and image, not a legacy QK instruction.
    # Program SHA + capability select binds this native-only interpretation.
    fused = {key: 0 for key in I.LAYOUT}
    fused.update(unit=I.UNIT_ME, barrier=1, me_wsrc=1, me_nout=512,
                 me_tiles=1, me_k=128, me_xbase=vm['QR'], me_xks=1,
                 me_obase=vm['ATTN']//16, me_oen=1, me_ots=1,
                 me_ojs=1, me_mmode=1)
    result, pc_map = [], {}
    for pc, f in enumerate(fields):
        if pc in removed:
            if pc == 11:
                pc_map[pc] = len(result)
                result.append(fused)
            continue
        pc_map[pc] = len(result)
        if pc == 16:
            # O projection cannot chase the removed SU normalization. Wait
            # for actual native ATTN VM commits and prior KV write drain.
            f.update(barrier=1, chase=0, chase_n=0, chase_rows=0, wait_me=0, wait_su=0)
        result.append(f)
    descriptors = []
    for word in profile['descriptor_hex']:
        d = ISA.decode_descriptor(int(word, 16))
        descriptors.append(ISA.encode_descriptor(d['kind'], d['vm_word'], d['words'],
                            pc_map[d['program_base']], d['row0']))
    encoded = [ISA.encode_instruction(f) for f in result]
    raw = ''.join(f'{w:0256x}\n' for w in encoded).encode()
    return {'schema': 'opentallas.qwen-tp8-fused-attention-lowering.v1',
            'status': 'OPT_IN_PROGRAM_CONTRACT_NOT_NATIVE_EXECUTED',
            'source_program_sha256': original['program_sha256'],
            'candidate_program_sha256': hashlib.sha256(raw).hexdigest(),
            'source_profile_sha256': hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest(),
            'program_words': len(encoded), 'program_hex': [f'{w:0256x}' for w in encoded],
            'descriptor_hex': [f'{w:016x}' for w in descriptors],
            'original_to_candidate_pc': pc_map, 'removed_original_pcs': sorted(removed),
            'fused_request_pc': pc_map[11], 'fused_output_element_base': vm['ATTN'],
            'fused_output_elements': 512, 'required_Q_element_base': vm['QR'],
            'native_transport': {'Q_words': 32, 'result_words': 32, 'word_bits': 512,
                                 'word_elements': 16, 'epoch_bits': 16, 'layer_bits': 6,
                                 'position_bits': 18, 'maximum_position': 8191,
                                 'Q_word_order': 'head=beat//8, dim0=16*(beat%8); lossless FP32 transport; BF16 RNE only inside actual attention consumer',
                                 'result_word_address': 'ATTN_BASE//16+beat',
                                 'kernel_result_handshake_is_VM_commit': False},
            'provider_contract': 'ONE fused native QK/scale/exp/Z/PV/reciprocal/normalize operation, four Q heads sharing one KV head, canonical S128/PV256 exact reduction order. Native capability is bound to this candidate image SHA; legacy QK/PV ABI is incompatible.',
            'completion_contract': 'idle/progress describe actual ATTN receiver VM commits; all512 elements must commit before following barrier permits O projection; every preceding K/V write committed before request admission.',
            'removed_intermediate_intervals': dead, 'retained_instruction_access_proof': access_proof,
            'external_visibility_requirement': 'No debug, telemetry, memory reader or host DMA may require materialized S/M/Z/RZ/ATT during this candidate. Program-only alias proof does not prove absence of external consumers.',
            'architecture_adopted': False, 'native_executed': False, 'performance_measured': False,
            'source_sha256': {str(Path(__file__).name): hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            'claim_boundary': 'Explicit candidate instruction lowering and source-derived internal alias audit only. No actual attention service integration, immutable operand/golden pass, clock closure, or token latency claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--hex-out', type=Path, required=True)
    args = parser.parse_args()
    report = lower(json.loads(args.profile.read_text()), args.image)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    args.hex_out.write_text(''.join(word + '\n' for word in report['program_hex']))
    print(f"candidate {report['program_words']} words: {report['candidate_program_sha256']}")

if __name__ == '__main__':
    main()
