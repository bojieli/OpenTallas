#!/usr/bin/env python3
"""Price a cycle-identical registered-nonempty request sink before building it."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def model():
    return {
        'schema': 'opentallas.hbm.smh.front_s_fifo_model.v1',
        'baseline_source': 'f7f1a0ee4bfd331c9d6bb873d9a772a5fa88cb48',
        'measurement': {'job': 'hbm_smh_front_s_m3f_f7f1a0ee4_t8',
            'SS_setup_ps': 7.357004, 'FF_hold_ps': -21.096708,
            'FF_register_hold_ps': 13.878565, 'DRC': 0,
            'logic_area_um2': 5597.77, 'macro_um': [432, 241.92],
            'critical_setup_path': 'u_rch.cnt[3] -> u_rch.head[13]',
            'critical_hold_path': 'u_prd.g_s[1].g_n.u/q[39] -> fp_d[39]'},
        'candidate': 'request sink caches occupancy in a dual-rail fail-closed state',
        'default_enabled': False,
        'cached_mutable_state_protection_qualified': False,
        'implementation_contract': {
            'nonempty_reset': 0,
            'nonempty_next': 'push&&!pop:1; pop&&!push:cnt!=1; otherwise cnt!=0',
            'empty_next': 'complement of nonempty_next, stored in a separate kept FF',
            'valid_decode': 'nonempty && !empty; equal rails suppress pop',
            'state_error': 'equal rails feed the existing sticky front_s fault register',
            'single_cached_bit_fault_policy': 'detect, suppress transfer while invalid, resynchronize rails from occupancy; sticky fault remains until reset',
            'fault_visibility_latency_cycles': 3,
            'existing_count_pointer_protection_changed': False,
            'invariant': 'nonempty == (cnt != 0) for every legal credit trace',
            'head_and_memory_updates': 'unchanged',
            'fifo_width_bits': 42, 'fifo_depth': 9,
            'forward_landing_cycles': 1, 'credit_return_cycles': 2,
            'boundary_bits_per_cycle': {'input': 43, 'output': 43, 'credit': 1},
            'memory_bytes_per_cycle': {'local_fifo_write': 5.25, 'local_fifo_read': 5.25},
            'memory_capacity_bits': 378,
            'MACs_per_cycle': 0, 'arithmetic_operations_changed': 0,
            'compute_intensity_MAC_per_byte': 0,
            'communication_intensity_bits_per_request': 87,
            'replicas_per_SM': 1, 'SMs': 32,
            'added_resettable_state_bits_per_SM': 2,
            'added_comparators_per_SM': 2,
            'added_mux_bits_per_SM_upper_bound': 4,
            'added_protection_gates_per_SM': {'valid_AND': 1, 'error_XNOR': 1, 'sticky_fault_OR_input': 1},
            'state_fanout_sinks_upper_bound': 44,
            'removed_critical_logic': '4-bit occupancy zero-detect before pop/head enable',
            'added_logic_location': 'occupancy==1 decode feeds nonempty state only',
            'added_boundary_tracks': 0, 'routing_channel_capacity_changed': False,
            'area_upper_bound_um2': 2.0,
            'area_bound_basis': 'provisional conservative budget for 2 FF + comparators/mux/protection; synthesis must validate',
            'area_fraction_of_measured_front_s': 2.0 / 5597.77,
            'slot_changed': False,
            'added_latency_cycles': 0, 'request_acceptance_cycle_changed': False,
            'single_user_token_latency_delta_cycles': 0,
            'applicable_designs': ['Qwen3-8B HBM', 'DeepSeek-V4.1 HBM'],
            'ROM_design_delta': 0},
        'adoption': False,
        'requirements': [
            'Expose model through tools/uarch_model.py before RTL build',
            'Cycle comparison of valid/data/credits at full 42-bit depth-9 sink against pinned original',
            'Exercise empty, simultaneous push/pop, occupancy one, full, wraparound and reset; meaningful mutation must fail',
            'Full front_s elaboration and source-pinned admitted route under unchanged clocks/uncertainty',
            'Separate output/internal FF hold repair remains required; this setup optimization does not claim to fix hold',
            'Inject either rail in both occupancy states: no false transfer, sticky error survives rail repair, reset clears fault',
            'After synthesis prove two independent rail FFs remain; keep attributes alone do not qualify fault protection',
            'Time the added validity/error/sticky-fault paths at SS/FF; existing count/pointer fault protection is unchanged and not newly qualified',
            'Real SS/FF >=15 ps, DRC0 and composed in-context clock/port validation'],
        'model_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True)
    out = Path(p.parse_args().out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(model(), indent=2) + '\n')
