#!/usr/bin/env python3
"""Build the full36 numerical successor using independent protected PC lanes.

Reuses the retained exact compute archives; only the transport-bearing top is
rebuilt. Run run_full.py --stage build, then --stage runtime under admission.
The runtime compares all 300 layer/KV/head outputs with the retained truth.
"""
import argparse
import json
from pathlib import Path

from full_build import prepare


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--authority-job', type=Path, required=True)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--backend-dependency', type=Path, action='append', default=[])
    p.add_argument('--kv-map', type=int, choices=[0, 1], default=0,
                   help='1: option-M quadrant-local KV stripe end to end (default 0)')
    a = p.parse_args()
    source = a.source_root.resolve()
    exp = source / 'rtl/experimental/qwen_rom_combined_p0_20261005'
    top = exp / 'ot_qwen_p0_full_numeric.sv'
    context = exp / 'ot_qwen_p0_parallel_transport_context.sv'
    adapter = source / 'rtl/hdc/kv/ot_qwen_s4_parallel_protected_pc.sv'
    # Refuse silent fallback to the historically serialized P0 root.
    for f in (top, exp / 'ot_qwen_p0_full_transport_join.sv'):
        if 'PARALLEL_TRANSPORT' not in f.read_text():
            raise ValueError(f'{f}: full-width opt-in parameter missing')
    if 'ot_qwen_s4_parallel_protected_pc' not in adapter.read_text():
        raise ValueError('actual protected sector-lane implementation required')
    # The owner adapter delegates landing storage through protected_pc/ring.
    # Inspect that implementation too; the raw CDC need not be a direct child.
    landing_sources = [adapter, source / 'rtl/hdc/kv/ot_qwen_s4_protected_pc.sv',
                       source / 'rtl/hdc/kv/ot_qwen_s4_protected_ring.sv']
    if not any('ot_qwen_stream4_cdc_pc #' in f.read_text() for f in landing_sources):
        raise ValueError('protected landing implementation lacks actual raw CDC')
    deps = [context, adapter,
            source / 'rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv',
            source / 'rtl/hdc/v41x/ot_hdc_v41x_kreg.sv']
    bank = exp / 'ot_qwen_p0_parallel_bank.sv'
    if bank.exists():
        deps.append(bank)
    deps += a.backend_dependency
    r = prepare(a.authority_job, source, top,
                source / 'rtl/hdc/kv/ot_qwen_s4_numeric_memory.sv',
                a.output, backend_dependencies=deps,
                cdc_consumer_join=True, landing_rsel=1, parallel_transport=True,
                kv_map=a.kv_map)
    r['parallel_transport'] = True
    r['cdc_binding_scope'] = ('128 independent protected 32-byte sector lanes; '
                              'actual ot_qwen_stream4_cdc_pc RSEL=1; '
                              'physical qualification remains separate')
    # The old candidate record describes the serialized full504 ring only.
    r.pop('owner_cdc_leaf_candidate', None)
    r['reference_cycles'] = 193955
    r['expected_input_token'] = 24
    r['expected_next_token'] = 18
    r['expected_winning_logit_bits'] = '42282b99'
    (a.output / 'prepared.json').write_text(json.dumps(r, indent=2) + '\n')
    print(json.dumps({'top': r['top'], 'parallel_transport': True,
                      'status': r['status']}))


if __name__ == '__main__':
    main()
