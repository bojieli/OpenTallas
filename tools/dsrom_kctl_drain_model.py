#!/usr/bin/env python3
"""Price only the ring drain flag cut; no throughput or clock qualification."""
import hashlib
import json
from pathlib import Path
import ast
ROOT = Path(__file__).resolve().parents[1]
dff = next(ast.literal_eval(n.value) for n in ast.parse((ROOT/'tools/uarch_model.py').read_text()).body
           if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'DFF_UM2' for t in n.targets))
source = 'rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_ring.sv'
hw, stacks = 23, 4
bits = 2 * hw + 2
record = {
    'schema': 'dsrom.kctl_drain.v1', 'baseline_sha256': hashlib.sha256((ROOT/source).read_bytes()).hexdigest(),
    'scope': 'DS ROM IDX_RING=1: four existing ring readers; singleton scan, no extra context',
    'method': 'registered remaining-block and next-wrap flags, updated on actual d_step only',
    'history': {'registered_flags': '6694bcd18', 'broad_successor_not_intaken': 'a274edd41'},
    'parameters': {'HW': hw, 'AW': 30, 'NPC': 32, 'WB': 32, 'GA': 24, 'replicas': stacks},
    'macs_per_cycle': 0, 'new_memory_bytes_per_cycle': 0, 'new_external_boundary_bits_per_cycle': 0,
    'unchanged_ports_per_stack_bits': {'request': 32*(1+1+30+4+16), 'response': 32*(1+1+16+4+256), 'keys': 16*544+16+2},
    'unchanged_peak_response_bytes_per_cycle_per_stack': 32*32,
    'new_control_register_bits_per_stack': bits,
    'mutable_protection': {'required': True, 'parity_lower_bound_bits_per_stack': 2, 'qualified': False},
    'register_area_lower_bound_um2_all_four': (bits+2)*stacks*dff,
    'area_basis': 'unified DFF_UM2 only; decrementers, compare, mux, protection handling, CTS and routing unmeasured',
    'local_muxes': 'two HW-bit counter enable muxes + two flag enables per stack; no replicated data mux',
    'fanout': 'd_step updates two counters and two flags; d_more drives d_live; d_wrap_next selects existing head wrap update',
    'track_floor': {'external_added': 0, 'local_state_bits_per_stack': bits, 'legal_channel_capacity': None, 'slot_fit_qualified': False},
    'clock': {'target_GHz': 1.2, 'setup_uncertainty_ps': 60, 'hold_uncertainty_ps': 25, 'SS_FF_qualified': False},
    'latency': {'added_cycles_per_scan_expected': 0, 'added_cycles_per_block_expected': 0,
                'token_extra_ns_expected': 0, 'condition': 'every accepted request/response, drain pulse, payload and busy edge remains cycle-identical',
                'measurement': None, 'gain_claim': None},
    'adoption': False, 'default_enable': 0,
    'integration': 'Archimedes replaces only ring reader module with additive _drain wrapper, explicitly ENABLE=1 after gates; non-ring readers unchanged',
}
print(json.dumps(record, indent=2, sort_keys=True))
