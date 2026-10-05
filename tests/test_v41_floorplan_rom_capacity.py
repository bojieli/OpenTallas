import importlib.util
from pathlib import Path

P=Path(__file__).resolve().parents[1]/'tools/v41_floorplan_rom_capacity.py'
spec=importlib.util.spec_from_file_location('capacity',P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_integer_counts_cover_exact_requirement_without_an_extra_macro():
    d=m.derive(); bits=d['required_bytes']*8
    for row in d['predictive_view_geometry']['uniform_integer_allocations']:
        assert row['allocated_bits'] >= bits
        assert (row['count']-1)*row['capacity_bits'] < bits
        assert row['padding_bits']==row['allocated_bits']-bits


def test_capacity_is_not_timing_or_complete_fit():
    d=m.derive();g=d['predictive_view_geometry']
    assert g['minimum_fractional_area_bound_mm2'] < 815
    rows={r['macro']:r for r in g['uniform_integer_allocations']}
    assert not rows['ot_rom_16384x266_m16']['macro_period_only_eligible_at_920ps']
    assert rows['ot_rom_8192x274_m8']['macro_period_only_eligible_at_920ps']
    assert d['analytical_reference_only']['comparison_ratio'] is None
    assert not d['analytical_reference_only']['substitution_into_analytical_total_permitted']
    assert d['status'].endswith('complete_fit_unproved')


def test_observed_witness_is_not_raw_bit_density():
    g=m.derive()['predictive_view_geometry']
    assert g['local16macro_occupancy_scenario']['area_mm2'] > g['local274_payload_allocations']['fp8_264bit_in_274']['area_mm2']
    assert g['local16macro_occupancy_scenario']['macros'] % 16 == 0
