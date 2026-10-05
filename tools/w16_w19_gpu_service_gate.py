#!/usr/bin/env python3
"""Source-bound GPU SIMD/RF/shared-memory qualification of W19's fixed allocation."""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

import w16_w19_resident_bounds as B
import w19_resident_contract as W

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = 'results/rtl/w19_checkpoint_production_20261001/resident-service-candidate-r1.json'
SCOPE = 'results/quality/w16_w19_gpu_mapping_scope_20261001/gpu_scope.json'
PARTIAL = 'results/quality/w16_w19_resident_service_price_20261001/partial_price.json'
OUT = 'results/uarch/w16_w19_gpu_service_gate_20261001'


def residency_arithmetic(region_sizes, sm_count, scratch_bytes):
    B.require(type(sm_count) is int and sm_count > 0 and type(scratch_bytes) is int and scratch_bytes > 0,
              'unknown SIMD/shared-memory geometry')
    B.require(region_sizes and all(type(v) is int and v > 0 for v in region_sizes.values()),
              'unknown/zero resident working-set credit')
    total = sum(region_sizes.values())
    return dict(candidate_HBM_region_bytes=region_sizes, sum_bytes=total,
        ideal_even_split_bytes_per_sm=math.ceil(total / sm_count),
        modeled_scratch_bytes_per_die=sm_count * scratch_bytes,
        remaining_bytes_arithmetic=sm_count * scratch_bytes - total,
        actual_per_SM_bank_mapping=None, actual_RF_allocation=None, actual_liveness=None,
        fit=False, scope='Conditional byte accounting only; HBM reservations do not allocate SM scratch/RF or supply ports')


def copy_port_arithmetic(size, readers):
    B.require(type(size) is int and size > 0 and type(readers) is int and readers > 0,
              'unknown copy replication')
    return math.ceil(size / (readers * 128))


def require_gpu_schedule(schedule):
    fields = ('instruction_lowering', 'multiply_add_rounding', 'instruction_latencies', 'warp_issue_schedule',
              'available_SIMT_lanes', 'RF_allocation_and_ports', 'shared_bank_allocation_and_ports',
              'collective_chunk_tree', 'SU_SFU_Sinkhorn_schedule', 'DMA_tag_credit_arbitration',
              'controller_commit_fence', 'critical_chain', 'source_bindings')
    B.require(isinstance(schedule, dict) and all(schedule.get(f) is not None for f in fields),
              'GPU lowering/RF/shared-memory/service critical-chain contract missing')
    B.require(schedule.get('dedicated_HCP') is False, 'dedicated HCP cannot substitute for GPU SIMD sharing')
    B.require(type(schedule['available_SIMT_lanes']) is int and schedule['available_SIMT_lanes'] > 0,
              'unknown available SIMD lanes')
    return True  # Necessary schema only; executable source/physical validation remains separate.


def build():
    import uarch_model as U
    c, scope = B.read(CANDIDATE), B.read(SCOPE)
    W.validate(c)
    for path, digest in c['source_pins'].items():
        B.require(B.sha(path) == digest, 'candidate source drift: ' + path)
    for path, pin in scope['source_pins'].items():
        B.require(B.sha(path) == pin['sha256'], 'GPU scope source drift: ' + path)
    B.require(scope['verdict'] == 'GPU_SIMT_MAPPING_REQUIRED_BEFORE_SERVICE_FREEZE', 'GPU scope changed')
    B.require(c['max_stack_end'] == 3175215616 and c['required_sector_bits_candidate'] == 27
              and c['required_bulk_line_bits_candidate'] == 25, 'candidate allocation changed')
    element = U.SM_ELEM['v41']
    budget = scope['current_model_budget']
    B.require(element['simt_lanes'] == budget['simt_fp32_lanes_per_sm'] == 128
              and element['scratch_kb'] * 1024 == budget['scratch_bytes_per_sm'] == 65536,
              'GPU budget mismatch')
    sm_count = budget['sm_count_per_die']
    B.require(sm_count == 32 and sm_count * element['simt_lanes'] == 4096, 'SM replication changed')
    sizes = {}
    for name in ('hc.operator_staging', 'hc.activation_staging', 'hc.scalar_scratch'):
        values = [next(r['bytes'] for r in rank['regions'] if r['family'] == name) for rank in c['ranks']]
        B.require(len(set(values)) == 1, 'HC working set differs by rank')
        sizes[name] = values[0]
    residency = residency_arithmetic(sizes, sm_count, budget['scratch_bytes_per_sm'])
    _, built = U.arch_graph(c['initial_context'])
    hc_nodes = [n for n, nd in built.g.nodes.items() if n.endswith('hc.fn')]
    B.require(len(hc_nodes) == 80 and all(built.g.nodes[n]['sweep']['bytes'] == 1966080
              and built.g.nodes[n]['sweep']['macs'] == 491520 for n in hc_nodes),
              'unified HC workload mismatch')
    # Existing unified DAG and area remain unchanged. Its dedicated-HC/SU
    # organization is explicitly excluded by the GPU scope record.
    coeff = sizes['hc.operator_staging']
    illustrations = [dict(assumed_generic_128B_copy_ports=n,
        ideal_line_delivery_rounds=copy_port_arithmetic(coeff, n),
        instantiated_nonSM_port_count=None, completed_service_cycles=None)
        for n in (1, 4, 16)]
    missing = {f: None for f in ('instruction_lowering', 'multiply_add_rounding', 'instruction_latencies',
        'warp_issue_schedule', 'available_SIMT_lanes', 'RF_allocation_and_ports',
        'shared_bank_allocation_and_ports', 'collective_chunk_tree', 'SU_SFU_Sinkhorn_schedule',
        'DMA_tag_credit_arbitration', 'controller_commit_fence', 'critical_chain', 'source_bindings')}
    missing['dedicated_HCP'] = False
    try:
        require_gpu_schedule(missing)
    except B.Refusal as exc:
        refusal = str(exc)
    else:
        raise B.Refusal('unexpected GPU schedule qualification')
    paths = [CANDIDATE, SCOPE, PARTIAL, 'tools/w19_resident_contract.py', 'tools/uarch_model.py',
        'tools/arch_budget_v41.py', 'tools/decode_critical_path.py', 'results/arch/arch_budget_v41.json',
        'results/floorplan/hbm_gpu/v41_hbm_die.json', 'configs/hardware/technology.json',
        'rtl/gpu/ot_gpu_sm_v.sv', 'rtl/gpu/ot_gpu_bulk_copy.sv',
        'tools/w16_w19_resident_bounds.py', 'tools/w16_w19_address_prerequisite.py',
        'tools/w16_measured_calibration.py', 'tools/w16_w19_gpu_service_gate.py',
        'tests/test_w16_w19_gpu_service_gate.py']
    return dict(schema='opentallas.w16.w19.GPU_service_qualification.v1',
        base_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        allocation_source=CANDIDATE, GPU_authority=SCOPE, prior_reference_partial_price=PARTIAL,
        allocation=dict(max_stack_bytes=c['max_stack_end'], sector_bits=27, bulk_line_bits=25,
            aperture_remaining_bytes=(1 << 32) - c['max_stack_end'],
            qualification='Fixed owner HBM allocation; GPU compute/storage/route integration pending'),
        unified_work=dict(HC_operators=80, FP32_products_per_operator=491520,
            coefficient_bytes_per_operator=1966080, coefficient_bytes_per_rank_token=157286400,
            coefficient_bytes_all96_rank_token=157286400 * 96,
            FP32_products_rank_token=80 * 491520,
            separate_multiply_and_add_scalar_operations_rank_token=2 * 80 * 491520,
            SIMD_instruction_issue_cycles=None, operand_rounding='Separate multiply and chunk8 sequential add; no fused-MAC or BF16 coefficient conversion credit'),
        GPU_budget=dict(sm_count_per_die=sm_count, modeled_SIMT_lanes_per_die=4096,
            modeled_SIMT_logic_mm2_already_budgeted=4096 * U.GPU_UNIT_UM2['simt_lane'] / 1e6,
            actual_general_FP32_instruction_path=False, actual_general_RF_service=False,
            available_HC_lanes_after_shared_schedule=None, incremental_area_mm2=None,
            note='Existing GPU model budget only; no new block or free implementation/area credit'),
        residency_arithmetic=residency, copy_port_illustrations=illustrations,
        finite_service=dict(controller_count=4, candidate_queue_classes_per_controller=4,
            class_queue_depth=None, class_queue_entry_bits=None, queue_storage_area_mm2=None,
            actual_nonSM_copy_replication=None, scatter_tag_credit_bridge=None,
            controller_write_completion=None, actual_service_cycles=None),
        routing=dict(actual_SM_shared_bank_read_bits_per_cycle=None, actual_RF_port_bits_per_cycle=None,
            DMA_mux_demux_fanout=None, route_tracks=None, channel_capacity_tracks=None,
            actual_simultaneous_port_ownership=None),
        excluded_reference_credits=['W32 dedicated HCP timing or area adoption',
            '247.885us reference as a GPU lower bound',
            'historical ROM-derived dedicated HC/SU hub as GPU composition',
            'ideal byte splitting as bank/port/liveness fit', 'controller ingress as completed DMA service'],
        required_gpu_schedule=missing, verdict='REFUSED_PENDING_GPU_LOWERING_AND_RESOURCES', refusal_reason=refusal,
        W19_handoff=dict(owner='Euler / GPU allocation and service', acknowledgement=False,
            next_boundary='Pin standard GPU SIMT instruction/warp lowering and RF/shared-memory bank liveness for full-F32 HC plus SU/SFU/Sinkhorn. Bind DMA replication/credits and commit/fence before graph timing; retain allocation unchanged.'),
        candidate_composed_latency_us=None, candidate_rate=None, candidate_area_and_routes_qualified=False,
        model_ready_to_build=False, hardware_adopted=False, model_generator_changed=False,
        pins={p: B.sha(p) for p in paths})


def check(record):
    for path, digest in record['pins'].items():
        B.require(B.sha(path) == digest, 'pin drift: ' + path)
    fresh = build()
    fresh['base_commit'] = record['base_commit']
    B.require(fresh == record, 'GPU service qualification does not reproduce')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--out', type=Path)
    mode.add_argument('--check', type=Path)
    args = ap.parse_args()
    try:
        if args.check:
            check(json.loads(args.check.read_text()))
        else:
            data = build()
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open('x') as f:
                json.dump(data, f, indent=2, sort_keys=True)
                f.write('\n')
        print('PASS: exact allocation/unified GPU workload; composition and build readiness remain REFUSED')
    except (B.Refusal, FileExistsError) as exc:
        ap.exit(2, 'REFUSED: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
