#!/usr/bin/env python3
"""Additive persistent-product construction; logical hits are not hardware credit."""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
from tools.w10_crom_control_reservation import read, block

def inventory(warm):
    if warm['schema'] != 'opentallas.CROM-immutable-warm-residency.v1':
        raise ValueError('unsupported residency source')
    stages = [s for s in warm['stages'] if s['product_words']]
    if sorted(s['layer'] for s in stages) != [1, 14]:
        raise ValueError('unexpected product stages')
    if any(s['product_words'] != 20480 or s['extra_persistent_product_bits'] != 655360 for s in stages):
        raise ValueError('product storage mismatch')
    owners = warm['topology_cases']['stage_local_candidate']['absolute_owner_keys']
    keys = [(o['rank'], o['layer']) for o in owners if o['layer'] in (1, 14)]
    expected = {(r, layer) for r in range(4) for layer in (1, 14)}
    if len(keys) != 8 or set(keys) != expected:
        raise ValueError('missing or duplicated product owner')
    if (warm['extra_product_reference_home_count'], warm['extra_product_bits_per_Engram_home'],
        warm['product_20entry_lane_select_MUX2_bits']) != (8, 655360, 622592):
        raise ValueError('typed allocation mismatch')
    if any(s['gamma_families'] != 2 or s['gamma_words'] != 10240 for s in stages):
        raise ValueError('primary warm dual gamma allocation changed')
    return sorted(keys)

def build(warm, power, clock, area):
    keys = inventory(warm)
    cost = block(655360, 622592, 0, power, clock, area)
    aggregate = {k: str(D(cost[k]) * len(keys)) for k in (
        'conditional_cell_plus_macro_area_mm2', 'ungated_clock_W',
        'all_state_leakage_upper_W', 'data_internal_upper_W',
        'data_input_pin_upper_W', 'unresolved_output_load_ceiling_W')}
    return {
        'schema': 'w10_crom_warm_product_additive_budget_v1',
        'source_mapping_digest': warm['mapping_digest'],
        'affected_reference_owners': [{'rank': r, 'layer': l} for r, l in keys],
        'allocation_scope': 'Conditional stage-local candidate, not instantiated DUT storage or accepted whole geometry.',
        'extra_persistent_product_words_per_home': 20480,
        'extra_persistent_product_FF_per_home': 655360,
        'candidate_20entry_read_MUX2_bits_per_home': 622592,
        'primary_dual_gamma_bits_per_regular_home_retained': 327680,
        'per_affected_home': cost,
        'eight_reference_home_allocation_sum': aggregate,
        'sum_is_not_phase_simultaneous_power_or_whole_product_power': True,
        'clock_assumption': 'All added FF clocked at 1.2GHz; independent reserved CTS tree, guard2 wire hypothesis. No root stop or warm idle gating credit.',
        'data_assumption': 'Activity1 compatible FF data events plus conservative NAND events/pin loads; output max-load ceiling separate. Not actual power or physical minimum.',
        'cold_init_source_calendar': warm['cold_init']['SS17_cold_candidates'],
        'cold_calendar_not_per_warm_token_charge': True,
        'warm_logical_hit_not_execution_cycle_credit': True,
        'additional_control_FF_bits': None,
        'additional_control_area_power': None,
        'unpriced': ['init/reset/epoch/valid/address/selector control and lease publication',
                     'actual read ports/fanout/load/RC and selected data activation trace',
                     'actual128bitCDC and1152bus route reach',
                     'whole geometry/phase overlap/PG/IR and contextualSSFF'],
        'source_L1_invalid': warm['cold_init']['source_L1_invalid'],
        'actual_provider_instantiated': False, 'complete_inventory': False,
        'actual_power_qualified': False, 'whole_power_W': None,
        'actual_warm_cycles': None, 'root_stop_credit': 0,
        'generic_buffer_reuse_credit': 0, 'single_gamma_savings_credit': 0,
        'physical_admission': False, 'jobs_launched': 0,
        'verdict': 'SOURCE_BOUND_ADDITIVE_PRODUCT_CONSTRUCTION_NO_WARM_GAIN_OR_PHYSICAL_ADMISSION'}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    a = p.parse_args()
    specs = {
        'warm': ('9bd2ccdf0', 'results/quality/w16_engram_initializer_20261001/warm_residency.json'),
        'power': ('e79394b1c', 'results/uarch/w10_q_power_envelope_r1/power.json'),
        'clock': ('fea811df4', 'results/uarch/w10_q_existing_icg_r1/clock.json'),
        'area': ('6da3c7a60', 'results/uarch/w10_q_elaboration_inventory_r1/construction.json')}
    inputs, pins = {}, {}
    for name, (commit, path) in specs.items():
        inputs[name], pins[name] = read(commit, path)
    x = build(**inputs)
    x['source_pins'] = pins
    x['standard_cell_library_inputs'] = inputs['power']['sources']
    Path(a.output).write_text(json.dumps(x, sort_keys=True, indent=2) + '\n')

if __name__ == '__main__':
    main()
