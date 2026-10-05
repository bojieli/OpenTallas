#!/usr/bin/env python3
"""Capacity-only bounds in the committed predictive ASAP7 macro view geometry.

No process scaling, throughput, routability or complete-die fit is inferred.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = [
    'physical/asap7_memory_macros/index.json',
    'results/arch/v41_die_placement.json',
    'results/arch/v41_die_assembly.json',
    'results/rtl/v41x_qe_local_tile_bank_l0.json',
    'results/rtl/hdc_v41x_qtile_pair_bank.json',
]


def uniform_allocation(required_bits, capacity_bits, area_um2):
    count = (required_bits + capacity_bits - 1) // capacity_bits
    return {'count': count, 'allocated_bits': count * capacity_bits,
            'padding_bits': count * capacity_bits - required_bits,
            'area_mm2': count * area_um2 / 1e6}


def derive(root=ROOT):
    data = [json.loads((root / f).read_text()) for f in INPUTS]
    catalog, placement, assembly, witness, replay = data
    macros = {n: m for n, m in catalog['macros'].items() if m['kind'] == 'rom'}
    required_bytes = math.ceil(placement['rom_bytes_per_die'])
    required_bits = required_bytes * 8
    cases = []
    for name, m in macros.items():
        c = uniform_allocation(required_bits, m['capacity_bits'], m['area_um2'])
        c.update(macro=name, capacity_bits=m['capacity_bits'],
                 width_um=m['width_um'], height_um=m['height_um'],
                 min_period_tt_ps=m['min_period_ps']['tt'],
                 macro_period_only_eligible_at_920ps=m['min_period_ps']['tt'] <= 920,
                 fraction_of_815mm2=c['area_mm2'] / 815)
        cases.append(c)
    # Fractional best-density bound applies to any mixture, but is not an
    # integer placement. Uniform candidates above are integer allocations.
    best = min(macros, key=lambda n: macros[n]['area_um2'] / macros[n]['capacity_bits'])
    m = macros[best]
    raw_bound = required_bits * m['area_um2'] / m['capacity_bits'] / 1e6
    q = macros['ot_rom_8192x274_m8']
    payload_cases = {}
    for label, payload in [('fp8_264bit_in_274', 264), ('fp4_pair_272bit_in_274', 272),
                           ('hypothetical_256data_18overhead', 256)]:
        payload_cases[label] = uniform_allocation(required_bits, 8192 * payload, q['area_um2'])
    # A scenario preserves the two-matrix witness's measured occupancy. It
    # is deliberately NOT called a universal lower bound or final mapping.
    sets = math.ceil(required_bytes / witness['source_checkpoint_bytes'])
    witness_scenario = dict(bank_sets=sets, macros=sets*16,
        area_mm2=sets*16*q['area_um2']/1e6,
        source_payload_per_set_bytes=witness['source_checkpoint_bytes'],
        physical_bytes_per_set=witness['physical_macro_bytes_allocated'],
        qualification='Hypothetical repetition of observed two-matrix occupancy; does not establish full-expert packing or identical tensor formats.')
    return dict(schema='opentallas.v41.floorplan_rom_capacity.v1',
        status='capacity_only_area_obstruction_not_found_complete_fit_unproved',
        source_sha256={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in INPUTS},
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        required_bytes=required_bytes, required_bytes_basis='ceil of adopted average ROM bytes per die; worst actual stage may differ',
        predictive_view_geometry=dict(technology='ASAP7 predictive macro compiler', die_test_area_mm2=815,
            scale_factor_applied=1, minimum_fractional_area_bound_mm2=raw_bound,
            bound_macro=best, uniform_integer_allocations=cases,
            local274_payload_allocations=payload_cases, local16macro_occupancy_scenario=witness_scenario),
        analytical_reference_only=dict(technology='N5 analytical density model; no equivalence to predictive ASAP7 macro view area',
            rom_area_mm2=assembly['ledger']['layer']['rom_mm2'],
            density_mbit_per_mm2=assembly['ledger']['layer']['rom_density_mbit_per_mm2'],
            comparison_ratio=None, substitution_into_analytical_total_permitted=False),
        excluded=['ECC implementation and its actual payload cost', 'all-expert per-stage integer bank packing',
            'replication to satisfy simultaneous ports', 'bank-select mux and data registers',
            'ROM-to-MAC wiring and channel whitespace', 'compute, SRAM, PHY, clock, PDN, DFT',
            'macro manufacturing qualification and extracted silicon timing'],
        conclusions=['Raw capacity alone fits an 815mm2 area envelope in these predictive macro views.',
            'That necessary capacity check neither proves rectangular placement nor complete die feasibility.',
            'The densest 16384x266 macro fails its own TT 920ps period test; feasible clock requires another macro or explicit multicycle service.',
            'No predictive-to-N5 area conversion or substitution is performed.'])


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output', type=Path, default=ROOT/'results/floorplan/v41_rom_capacity.json')
    args=ap.parse_args(); args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(derive(),indent=2)+'\n')

if __name__ == '__main__': main()
