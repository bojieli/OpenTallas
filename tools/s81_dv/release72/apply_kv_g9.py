#!/usr/bin/env python3
"""Prepare the exact G9 op15 hardware binding; no physical view is inherited.

Apply to copies of the completed G8 overlays, before strict bind. The G9 normal
slice source already instantiates xgt/xrt unconditionally. Producer transport,
programme dates, native fanout and physical qualification remain open.
"""
import argparse
import copy
import json
from pathlib import Path


def apply(plan, table, source_ref):
    blocks = [b for b in plan['blocks'] if b['name'] == 's_3N']
    assert len(blocks) == 1, 'expected one actual s_3N'
    block = blocks[0]
    original = table['masters'][block['master']]
    assert original['module'] == 'ot_s81sl_slice', original['module']
    assert not original.get('view'), 'cannot inherit a default-off slice view'
    key = 'dsdv_slice_kv512'
    assert key not in table['masters'], 'KV source overlay already applied'
    row = copy.deepcopy(original)
    row.setdefault('params', {})['KV_ENABLE'] = 1
    row['ref'] = source_ref
    row['view'] = None
    row['view_note'] = ('UNBOUND G9 KV_ENABLE1 source variant; leaf0 op15 uses production D512 bank/adapter. '
                        'Default-off VS/slice/native views do not qualify this hardware.')
    table['masters'][key] = row
    block['master'] = key
    sources = ['rtl/dsrom_sys/s81_dv/slice/' + n for n in
               ('ot_s81sl_slice.sv', 'ot_s81sl_kv_leaf.sv', 'ot_s81sl_kv_bank.sv',
                'ot_s81sl_xgt.sv', 'ot_s81sl_rstopt.sv', 'ot_s81sl_xrt.sv')]
    refs = table.setdefault('rtl_refs', {}).setdefault(source_ref, [])
    prefer = table.setdefault('prefer', [])
    for path in sources:
        if path not in refs:
            refs.append(path)
        selected = source_ref + '/' + path
        if selected not in prefer:
            prefer.append(selected)
    plan['facts']['kv_bank_source_binding'] = dict(
        instance='u_s_3N.lf[0].u_lf.g_kv.u_kv', master='ot_s81sl_kv_leaf', source_ref=source_ref,
        params={'KV_ENABLE': 1}, opcode=15, gain_kind=7, kv_kind=1,
        model='tools/s81_dv/kv_bank_1021/MODEL.json',
        status='SOURCE_ONLY_NATIVE_AND_PHYSICAL_QUALIFICATION_OWED',
        vm_input_rows=[672, 819], vm_output_rows=[672, 771],
        fixed_drain_age=1024, fixed_drain_edges=104, write_events=26, unique_spine_addresses=25,
        mechanism_receipt='6e4c28b27:results/token_pass/s81_kv_real_vp_1021/r3/result.json',
        producer_hold='Actual CAP gather, TP4 exchange, VM lifetime and issue programme are not supplied by this overlay',
        qualification_hold='KV_ENABLE1 changes leaf hardware; no VS/default-off slice view or prior native census alias')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--table', required=True, type=Path)
    parser.add_argument('--source-ref', required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    table = json.loads(args.table.read_text())
    apply(plan, table, args.source_ref)
    args.plan.write_text(json.dumps(plan, indent=1) + '\n')
    args.table.write_text(json.dumps(table, indent=1) + '\n')
    print('G9_KV_SOURCE_BIND u_s_3N leaf0 KV_ENABLE1; native/physical/producer qualification owed')


if __name__ == '__main__':
    main()
