#!/usr/bin/env python3
"""Source-pinned command cost requirements; no RTL or inferred timing."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = 'results/uarch/h3_distributed_norm_endpoint_20261002'
COMPONENTS = ('admission', 'RF_read', 'execute', 'mirrored_write_ACK', 'done_retire')

def compose(commands, costs):
    """Serialize the actual command list. Unknown costs cannot become zero."""
    total = 0
    for command in commands:
        op = command['op']
        values = costs.get(op)
        if not isinstance(values, dict) or set(values) != set(COMPONENTS):
            raise ValueError('missing or extra cost components: ' + op)
        for name in COMPONENTS:
            value = values[name]
            if type(value) is not int or value < 0:
                raise ValueError('cost must be an explicit nonnegative integer')
            total += value
        if sum(values.values()) == 0:
            raise ValueError('zero command service is forbidden')
    return total

def generate():
    pins = [__file__]
    targets = {}
    for target in ('Qwen', 'DeepSeek'):
        path = ROOT / INPUT / (target + '.json.gz')
        pins.append(str(path))
        data = json.loads(gzip.decompress(path.read_bytes()))
        flow = data['selected_command_bindings']
        templates = {}
        for key, commands in flow['command_templates'].items():
            templates[key] = {'commands': len(commands),
                'opcode_counts': dict(sorted(Counter(c['op'] for c in commands).items())),
                'serialized_service_edges': None}
        opcodes = sorted({op for t in templates.values() for op in t['opcode_counts']})
        targets[target] = {'selected_PCs': len(flow['bindings']), 'templates': templates,
            'cost_request': {op: dict.fromkeys(COMPONENTS) for op in opcodes},
            'scope': 'local participant templates only; collector/tail/output/provider service required separately',
            'remaining_services': ['input/coefficient/gamma/constant staging',
                'source root extraction and forward CDC', 'collector decode and ROOT_INSERT mirrored ACK',
                'reverse commit ACK and closed delivery fence', 'ordered collector tree and scalar tail',
                'scalar broadcast and downstream scale', 'each output home copy and mirrored ACK',
                'PACK_BF16 and bounded packing queue', 'matrix xw CDC/staging/barrier/weight readiness',
                'spill reserve/sector transport/causal visibility/read retirement'],
            'critical_path_rule': 'max participant service only after priced independent ports; serialized shared collector; no ideal overlap',
            'full_kernel_edges': None}
    sources = ['tools/w19_gpu_norm_calendar.py', 'tools/hdc_golden_v41.py',
        'tools/qwen_hbm_complete_executor.py', 'rtl/hdc/v41/ot_hdc_fdiv.sv',
        'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv', 'rtl/abi3/ot_a3_fp32_div_rne_pipe.sv',
        'rtl/gpu/ot_gpu_full_sm_service.sv', 'rtl/gpu/ot_gpu_rf_service.sv']
    pins += [str(ROOT / p) for p in sources]
    return {'schema': 'H3_NATIVE_COMMAND_COST_CONTRACT_V1', 'targets': targets,
        'DIV': {'specification_owner': 'Peirce H3 lowering',
            'model_composition_owner': 'Maxwell', 'implementation_owner': None,
            'assignment': 'No implementation owner assignment evidenced in pinned package; independent exact-DIV work assignable',
            'selected_call': 'tools/w19_gpu_norm_calendar.py:scalar_norm_program DIV(sum,@F5120)',
            'divisor_binary32_hex': '45a00000',
            'arithmetic': 'binary32 RN-even exact quotient, gradual underflow, canonical +0; add epsilon only after rounded division',
            'fault_contract': 'nonfinite operand, zero divisor or overflow: fault and +0; no valid successful publication',
            'reference': 'tools/hdc_golden_v41.py:div; numerical golden is not a service-time oracle',
            'candidate_bodies': [{'source': sources[3], 'declared_depth': 31, 'declared_II': 1},
                {'source': sources[4], 'module': 'ot_hdc_v41x_fdiv', 'declared_depth': 19, 'declared_II': 1}],
            'native_GPU_binding': False, 'end_to_end_service_edges': None,
            'cost_to_add': list(COMPONENTS) + ['reset/valid/fault alignment', 'scalar result publication/broadcast'],
            'calendar_21_is_proposal_not_measurement': True,
            'reciprocal_multiply_substitution_allowed': False},
        'Qwen': {'RSTD_mean': 'FMUL(sum,F32(1/4096)); not DIV',
            'reciprocal': 'executor reciprocal seed 0x7ef311c7 with source saturation rule; three separately rounded y*(2-a*y) iterations',
            'rsqrt': 'separate bit-seeded three-Newton rsqrt; reciprocal is not rsqrt',
            'exact_IEEE_DIV_is_not_a_substitute_for_Qwen_reciprocal': True},
        'admission': {'RTL_allowed': False, 'Maxwell_required': ['internal_RF_12339_tracks',
            'root_route_41_tracks', 'replica_slot_fit', 'composed_all_component_latency'],
            'native_clock_transfer': False, 'physical_causal_visibility': False,
            'Qwen_spill_required_bytes': 33554432, 'Qwen_source_extent_bytes': 704512},
        'source_sha256': {str(Path(p).relative_to(ROOT)): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in pins}}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    path = Path(args.out)
    result = generate()
    if args.verify:
        if json.loads(path.read_text()) != result:
            raise SystemExit('cost contract replay mismatch')
        print('PASS_SOURCE_PINNED_COST_CONTRACT_REPLAY')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')

if __name__ == '__main__':
    main()
