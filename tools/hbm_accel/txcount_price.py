#!/usr/bin/env python3
"""HA1 additive sizing extension of the unified microarchitecture model.
No default architecture row is changed. Unknown physical constants block adoption.
"""
import ast
import math
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
# Load the exact unified-model constants/function without importing unrelated
# physical-result dependencies in this sparse checkout.
_tree = ast.parse((ROOT / 'tools/uarch_model.py').read_text())
_names = {'DFF_UM2', 'WIRE_PS_PER_UM', 'UNCERTAINTY_PS', 'WIRE_OVERHEAD_PS'}
_nodes = [n for n in _tree.body if
          (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in _names for t in n.targets))
          or (isinstance(n, ast.FunctionDef) and n.name == 'wire_cycles')]
exec(compile(ast.Module(body=_nodes, type_ignores=[]), 'uarch_model.py:HA1', 'exec'))

def price():
    slots, sms = 32, 32
    # 32 protected 55-bit owner/slot identities; protected context, counters,
    # and two 32-bit seen masks. Two simultaneous event read ports, one manifest write.
    bits = slots * 72 + 3 * 72
    return {
        'schema': 'opentallas.ha1.txcount.portbook.v1', 'status': 'ESTIMATE',
        'clock_hz': 1.2e9, 'setup_uncertainty_ps': 60, 'hold_uncertainty_ps': 25,
        'MACs_per_cycle': 0, 'payload_memory_bytes_per_cycle': 0,
        'max_transactions_per_SM': slots, 'SMs_per_die': sms,
        'protected_bits_per_SM': bits, 'storage_cell_um2_per_SM': bits * DFF_UM2,
        'storage_cell_um2_per_die': bits * DFF_UM2 * sms,
        'ports': {
            'manifest': {'bits_per_cycle': 60, 'fanout': 1},
            'begin_context': {'bits_per_cycle': 49, 'fanout': 1},
            'W4_accepted_common_ACK': {'bits_per_cycle': 104, 'fanout': 1},
            'W6_accepted_visibility': {'bits_per_cycle': 104, 'fanout': 1},
            'scheduler_completion': {'bits_per_cycle': 44, 'fanout': 1}},
        'table': {'identity_bits': 55, 'protected_word_bits': 72, 'read_ports': 2,
                  'write_ports': 1, 'read_muxes': 2, 'read_mux_fanin': slots,
                  'comparators_bits': 2 * (55 + 43), 'manifest_uniqueness_comparators_bits': slots * 55, 'counters': 3, 'counter_bits': 6,
                  'seen_masks_bits': 64, 'codec_instances': 2 * slots + 6},
        'routing_tracks': 'ESTIMATE: local event buses 208 + completion44; channel capacity unmeasured',
        'area_and_slot_fit': 'ESTIMATE: storage only; mux, SECDED, counters, clock and routing unmeasured',
        'tree': {'qwen': {'leaf_cycles': 9, 'trunk_cycles': 13},
                 'v41': {'leaf_cycles': 7, 'trunk_cycles': 22}},
        'latency': {'priced_boundary_cycles': 78, 'target_boundary_cycles': 47,
                    'v41_AR_saved_us': 8.9, 'v41_AR_gain_estimate_percent': 2.0,
                    'qwen_AR_gain': 'ESTIMATE: canonical boundary count not measured',
                    'qwen3.8_27B': 'ESTIMATE: model-level owner must supply boundary count'},
        'wire_crosscheck_1p2GHz': {
            'qwen': [wire_cycles(4253.5, 1.2e9), wire_cycles(6489.3, 1.2e9)],
            'v41': [wire_cycles(3248.2, 1.2e9), wire_cycles(11033.7, 1.2e9)]},
        'W6_successor': {
            'status': 'ESTIMATE', 'original_clock_MHz': 429,
            'original_protected_bits': 144, 'additional_live_replicated_bits': 213,
            'additional_cell_um2': 213 * DFF_UM2,
            'approach': 'triplicated live state, parallel original SECDED witness; decode removed from state-data feedback',
            'positive_pipeline_cycles': 0, 'II_change_cycles': 0,
            'quarantine': 'immediate UE or witness/live mismatch; no delayed release using unchecked state',
            'limit': 'syndrome/quarantine remains in control-enable paths; clock gain unmeasured, not a 1.2GHz claim'},
        'adopt': False,
        'semantics': 'Counts scheduler visibility only. Does not release RF leases, consumer debt, issuer workspace, or W6 drain.'}
if __name__ == '__main__':
    print(json.dumps(price(), indent=2))
