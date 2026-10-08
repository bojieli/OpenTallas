#!/usr/bin/env python3
"""Pre-RTL model: opt-in duplicate native owner plus fail-closed boundary compare."""
import json
from hbm_sm_serial_owner_model import model as baseline

def model():
    base=baseline()
    bits=base['total_flop_lower_bound_bits']
    return dict(status='prebuild_candidate_not_adopted',baseline=base,
        scheme='two independent registered owners; compare every output and independent per-owner critical-state parity; mismatch immediately gates all effect handshakes and latches abort',
        protected_fields=['320-bit record','program address/limit','record count/index','word/group/ordinal pointers','weight base','operand resident identity','FSM/arrive/publication/start flags','registered X payload/address/enable','ingress outputs before issue'],
        duplicate_owner_flops=bits,sticky_abort_flops=1,total_flops=2*bits+1,
        flop_area_lower_bound_um2=(2*bits+1)*.2916,
        slot_lower_bound_um2_at_55pct=(2*bits+1)*.2916/.55,
        replicas=32,nominal_added_cycles=0,
        payload_compare_bits=2268, handshake_compare_bits=13, state_parity_compare_bits=1,
        parity_tree_inputs_per_owner=2572, balanced_parity_binary_levels=12,
        local_generic_mapped_observation=dict(tool='Yosys0.9; not fleet ORFS',state_flops=5343,compare_and_gate_levels=20,owner_parity_levels=12,blocked_direct_pin_fanout=13),
        logic_cost='second copy of baseline logic; XOR output compare plus two parity reductions over2572 owner-statebits; OR reduction and side-effect gates, not area measured',
        communication='unchanged external widths; independent cores consume identical accepted source transactions; mismatch cannot acknowledge input or assert external writes/start/completion',
        fault_scope='single state-bit upset or output disagreement; common-mode faults and coordinated equal parity multi-bit changes not claimed',
        physical_obligation='no combinational timing assumed: compare tree and gate fanout require actual SS/FF closure; must pipeline/price if needed',
        open_gates=['parent memory/allocation/result binding','source/clock separation for independent physical copies','timing and compare-network physical qualification','actual ORFS mapped duplicate-bank preservation gate'],selected=False)
if __name__=='__main__':print(json.dumps(model(),indent=2))
