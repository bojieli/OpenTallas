#!/usr/bin/env python3
"""Cached HCpost inputs and original scheduled words for the DS20 SU join.

No scheduling, operator evaluation, expected-as-input, or authority synthesis.
The caller must supply the retained, SHA-pinned original prog.hex. The 64-bit
loader words are transport chunks of those 690-bit words, never native ISA.
"""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np

from gpu_sys.mem_image import write_images
from hbm_accel_su_fused_compile import compile_saved
from hbm_accel_su_fused_compile_cases import load_cases
from hbm_accel_su_fused_runtime import bind, bits

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = dict(VM=0, KV=0x100000, CRlo=0x300000,
                 CRhi=0x320000, WR=0x340000)


def prepare(cases, original_program, out):
    cases, original_program, out = map(Path, (cases, original_program, out))
    blob, case_sha = load_cases(cases)
    case = blob['cases'][4]
    compiler = compile_saved(cases)['cases'][4]
    group = compiler['candidates'][0]
    if (case['name'] != 'L0.hc_post.attn' or group['kind'] != 'hc_post'
            or not group['selected'] or group['original_op_indexes'] != [0, 1, 2, 3]
            or compiler['retained_op_indexes'] or len(case['ops']) != 4):
        raise ValueError('only the actual full original four-op HCpost chain is bound')
    contract_path = ROOT/'results/rtl/hbm_su_fused_20261005/native_abi/native_contract.json'
    contract = json.loads(contract_path.read_text())
    payload = original_program.read_bytes()
    expected_pin = contract['scheduled_programs'][case['name']]['sha256']
    if hashlib.sha256(payload).hexdigest() != expected_pin:
        raise ValueError('original scheduled prog.hex source pin mismatch; do not reschedule')
    words = [int(t, 16) for t in payload.decode('ascii').split()]
    if len(words) != 4 or any(w >> 690 for w in words):
        raise ValueError('actual original native word count/width')
    controls = {'ch_src', 'ch_seq', 'ch_lead', 'ch_mul', 'w_idle',
                'w_rseq_en', 'w_rseq', 'w_dseq_en', 'w_dseq', 'x_start'}
    for op, word in zip(case['ops'], words):
        offset = 0
        for name, width in contract['word_fields'].items():
            value = (word >> offset) & ((1 << width)-1)
            if name not in controls and value != int(op[name]):
                raise ValueError(f'original arithmetic/address field differs: {name}')
            if name == 'x_start' and value:
                raise ValueError('external X producer is not in this minimum installed join')
            offset += width
    if any(bits(case[key]).size > (1 << 15) for key in ('cr_lo', 'cr_hi')):
        raise ValueError('original CR namespace bounds; do not overlap source banks')
    # bind reuses the actual compiler/operand loader; no second descriptor parser.
    plan = bind(cases, 4, 0, out)
    (out/'prog.hex').write_bytes(payload)
    loader = []
    for slot, word in enumerate(words):
        for chunk in range(11):
            loader.append(dict(im_addr=(1 << 13) | (slot << 4) | chunk,
                               im_data=f'{(word >> (64*chunk)) & ((1 << 64)-1):016x}'))
    # The namespace has the original logical capacities. Initial backing contains
    # only actual init/CR words; saved comparison output is a separate file.
    vm = np.zeros(1 << 18, dtype=np.uint32)
    available = np.zeros(vm.size, dtype=np.bool_)
    for address, values in case['init']:
        data = bits(values)
        if address < 0 or address+len(data) > vm.size:
            raise ValueError('original VM initialization bounds')
        vm[address:address+len(data)] = data
        available[address:address+len(data)] = True
    o = group['operands']
    for key, count in [('residual_VM_word_address', 20480),
                       ('Y_VM_word_address', 5120),
                       ('comb_VM_word_address', 16), ('post_VM_word_address', 4)]:
        a = o[key]
        if not available[a:a+count].all():
            raise ValueError(f'actual source unavailable: {key}')
    write_images({NAMESPACE['VM']:vm.astype('<u4').tobytes(),
                  NAMESPACE['CRlo']:bits(case['cr_lo']).astype('<u4').tobytes(),
                  NAMESPACE['CRhi']:bits(case['cr_hi']).astype('<u4').tobytes()},
                 2, 65536, out, prefix='memory')
    record = dict(schema='opentallas.ds20-su-parent-fixture.v1',
                  case_sha256=case_sha, original_program_sha256=expected_pin,
                  compiler='hbm_accel_su_fused_compile.compile_saved',
                  source_case=case['name'], original_op_indexes=[0,1,2,3],
                  source_word_width=690, loader_transport_width=64,
                  loader=loader, namespace_byte_base=NAMESPACE,
                  component_memory=dict(NS=2,NPC=2,MEM_WORDS=65536,USE_W2=0),
                  installed_parent_memory_unchanged=True,
                  VM_operands=o, expected_words=plan['check_words'],
                  expected_used_only_for_comparison=True,
                  parent_owner_hardware_required=True,
                  original_schedule_preserved=True, adopted=False)
    record['files_sha256'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in out.iterdir() if p.is_file()}
    (out/'parent_fixture.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases', type=Path, required=True)
    ap.add_argument('--original-program', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    print(json.dumps(prepare(a.cases, a.original_program, a.out), indent=2))
