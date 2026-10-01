import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('whole', Path(__file__).resolve().parents[1] / 'tools/w17_whole_dsrom_candidate.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_candidate_fails_closed_and_preserves_units():
    r = module.build()
    assert r['candidate']['allocated_subproblem_die_count'] == 732
    assert r['candidate']['complete_product_die_count'] is None
    assert not r['engine_RTL_build_ready'] and not r['physical_admission']
    assert r['dispatch']['full_token_latency_cycles'] is None
    assert r['vocabulary_homes']['combined_one_BF_field_excess_words'] == 3907584
    assert all(not x['adopt'] for x in r['dispatch']['alternatives'])

def test_address_extents_and_serial_constant_port():
    r = module.build()
    h = r['constants']['selected_minimal_home']
    assert h['physical_4096x274_banks'] * 4096 * 3 >= r['constants']['resulting_required_words']
    assert 44 * 4096 * 3 < r['constants']['resulting_required_words']
    assert r['constants']['resulting_required_words'] > 2**19
    assert r['constants']['resulting_required_words'] <= 2**20
    assert h['scalar_read_ports'] == 1 and not h['simultaneous_unrelated_reads']
    service = r['constants']['source_bound_service_preflight']
    assert service['capacity']['banks_per_rank'] == h['physical_4096x274_banks']
    assert service['timing_preflight']['mandatory_capture_before_bank_lane_mux']
    assert service['timing_preflight']['measured_capture_select_cycles'] is None
    assert not service['admission']
    e = r['vocabulary_homes']['embedding']
    assert (32320 - 1) * 320 + 319 == e['physical_words_per_home'] - 1
    assert e['physical_words_per_home'] == e['physical_banks_per_home'] * 4096

def test_power_does_not_claim_unpinned_suppression():
    r = module.build()
    assert not r['power']['compatible_arc_values_source_pinned']
    from decimal import Decimal
    w2 = r['power']['phase_rows'][2]
    assert Decimal(w2['clock_plus_static_W']) > Decimal(r['power']['per_die_budget_W'])
    assert all(x['BF_hub_nonexpert_data_W'] is None for x in r['power']['phase_rows'])
