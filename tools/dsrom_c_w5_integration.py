#!/usr/bin/env python3
"""Production W5 dependency intake: retained return debt, no fixture reruns.

Pins W2 placement as placement only. A matrix's source/destination sites are
not a production wake calendar or a claim about stage-neighbor timing.
"""
import argparse
import hashlib
import json
from pathlib import Path


def build(inputs):
    read = lambda n: json.loads((inputs / n).read_text())
    selected = read('W2_return_baseline.json')
    physical = read('W2_physical_contract.json')
    w2 = read('W2_model.json')
    rejection = read('RD4_rejection.json')
    w4 = read('W4_model.json')
    assert selected['selected'] == 'EXISTING_RETURN_RD64_ROOT128'
    assert selected['RD'] == 64 and selected['ROOTD'] == 128
    assert selected['existing_storage_NP'] == 4096 and selected['existing_roots'] == 128
    assert selected['latency_credit_cycles'] == 0
    assert selected['area_credit_for_unconnected_return_nodes_mm2'] == 0
    assert not selected['RD4_credit_area_or_gain_claim']
    assert physical['return_contract'] == selected
    assert rejection['results']['nodes']['measured_saturated_slot_reuse_cycles'] == 9
    assert selected['target_cycles'] == 4 and not rejection['adopted']
    bounds = physical['region_bounds']
    assert len(bounds) == 129 and bounds[0] == 0 and bounds[-1] == selected['field_pairs']
    mapping = []
    for region, (start, end) in enumerate(zip(bounds, bounds[1:])):
        assert 0 < end-start <= 32
        for pair in range(start, end):
            retained_pair = 32*region + pair-start
            mapping.append({'field_pair': pair, 'region': region, 'retained_return_pair': retained_pair,
                            'retained_leaf_inputs': [2*retained_pair, 2*retained_pair+1]})
    assert len(mapping) == selected['field_pairs']
    used = {row['retained_return_pair'] for row in mapping}
    assert len(used) == len(mapping) and max(used) < 4096
    inactive = sorted(set(range(4096))-used)
    assert len(inactive) == selected['unused_return_input_pairs']
    # Audit the actual retained source signals before naming debt predicates.
    node = (inputs/'retained_return.sv').read_text()
    wrapper = (inputs/'retained_return_wrapper.sv').read_text()
    field = (inputs/'retained_field.sv').read_text()
    adder = (inputs/'retained_adder.sv').read_text()
    for needle in ('reg [AW:0] ac, bc;', 'reg [4:0] ap;', 'reg [4:0] vp;',
                   'reg [QW:0] qc;', 'reg        bv [0:D-1];', 'reg add;', 'output reg         r_v,'):
        assert needle in node, needle
    assert 'assign busy = |p_busy;' in field
    assert '.D(ROOTD), .QD(ROOTD)' in field
    assert '`ifdef V41_RT' in wrapper and "assign quiet = 1'b0;" in wrapper
    assert all(name in adder for name in ('s1_v', 's2_v', 's3_v', 's4_v', 'valid_out'))
    debt = [
        {'bit': 0, 'class': 'producer_and_ingress', 'required': 'all p_busy and accepted/live partial inputs; no producer pulse lost at isolation'},
        {'bit': 1, 'class': 'return_node_queues', 'required': 'OR over retained nodes of (ac != 0 || bc != 0)'},
        {'bit': 2, 'class': 'return_node_pipelines', 'required': 'OR of vp, ap, by_v, wrapper rv[RST:1], ingress/output valids; forwarding and tag alignment included'},
        {'bit': 3, 'class': 'root_input_queues', 'required': 'OR over all 128 roots of (qc != 0 || i_v)'},
        {'bit': 4, 'class': 'root_held_siblings', 'required': 'OR over all roots and all ROOTD=128 bv entries'},
        {'bit': 5, 'class': 'root_add_pipeline', 'required': 'OR over all roots of add, u_add.s1_v, s2_v, s3_v, s4_v, valid_out; include tag validity through the same lifetime'},
        {'bit': 6, 'class': 'root_delivery_and_consumption', 'required': 'r_v plus delivery/capture, masked-write visibility and reader debt until actual ownership retirement'},
        {'bit': 7, 'class': 'fault_identity_and_reverse_retirement', 'required': 'sticky return/link faults, outstanding identities, CDC cohorts, reverse ACK and TX/RX/replay obligations; unknown bindings assert debt'}]
    for row in debt:
        row['production_signal_bound'] = False
        row['unknown_is_debt'] = True
    return {'schema': 'dsrom_c_w5_production_integration_v1',
        'status': 'DEBT_MAPPING_PREPARED_PRODUCTION_CALENDAR_PDN_PENDING',
        'return': selected,
        'return_binding': {'field_pairs': len(mapping), 'inactive_input_pairs': inactive,
                           'map': mapping, 'inactive_storage_removed': False,
                           'successor_exactness_and_contextual_timing_qualified': False},
        'debt_map': debt,
        'source_findings': {'field_busy_omits_return_state': True,
            'root_add_inflight_cannot_use_add_or_sv_alone': True,
            'wrapper_quiet_is_simulation_only_and_not_exported_by_field': True,
            'hardware_quiet_default_zero_means_no_gating_credit': True,
            'qualified_predecessor_is_not_a_qualified_S73_ragged_successor': True},
        'W2': {'packing_gates': w2['gates'], 'provider_homes_are_not_wake_adjacency': True,
               'actual_production_successor_edges': None, 'actual_AR_MTP_residence_calendar': None,
               'required': ['source-owned directed operation edges with stage/rank/link IDs',
                            'prewake route/CDC delay and arrival deadlines per edge',
                            'retained return FIFO/root/adder/output/consumer/reverse retirement timestamps',
                            'qualified return and indexer/split-delivery costs in the same calendar']},
        'MaxwellPDN': {'existing_W4_physical_admitted': w4['physical_admitted'],
            'replacement_PG_rectangles': None, 'off_rail_Standby_W': None,
            'wake_energy_J': None, 'wake_relock_cycles': None, 'inrush_peak_A': None, 'droop_V': None,
            'required': ['always-on debt/control island and powered off-domain interface slots',
                         'source-pinned switch/clamp/retention and link standby Liberty',
                         'per-domain switched capacitance, ramp/current and simultaneous wake grants',
                         'droop budget and PDN/clock/routing checks with SS/FF 60/25 ps uncertainties']},
        'Engram_always_on': True, 'RTL_changed': False, 'fixture_or_proof_repeated': False,
        'adopted': False, 'intake_ready': False,
        'parent_priority': 'realmem records and actual combined HBM factory; source intake waits for ready context',
        'delta_qualified': {'dies': 0, 'return_area_credit_mm2': 0, 'latency_credit_cycles': 0,
                            'PG_kW': None, 'PG_tok_s': None}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    for origin in json.loads((args.inputs/'origins.json').read_text()):
        path = args.inputs/Path(origin['snapshot']).name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == origin['sha256'], path
    model = build(args.inputs)
    model['input_sha256'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in sorted(args.inputs.iterdir())}
    model['tool_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out/'model.json').write_text(json.dumps(model, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'status': model['status'], 'mapped_pairs': len(model['return_binding']['map']),
                      'retained_storage_pairs': model['return']['existing_storage_NP'],
                      'intake_ready': model['intake_ready'], 'fixture_repeated': False}))


if __name__ == '__main__':
    main()
