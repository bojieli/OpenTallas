import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reticle_audit', ROOT / 'tools/dsrom_reticle_fixed_debit_reconciliation.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


@pytest.fixture(scope='module')
def model():
    return M.build()


def test_union_nested_overlap():
    assert M.union_area([[0, 0, 10, 10], [2, 2, 5, 5], [5, 0, 15, 10]]) == 150


def test_union_disconnected_abutting():
    assert M.union_area([[0, 0, 3, 3], [3, 0, 5, 3], [0, 7, 3, 9]]) == 21


def test_union_rejects_inverted():
    with pytest.raises(ValueError):
        M.union_area([[5, 0, 4, 10]])


def test_complement_not_service_silicon(model):
    d = model['fixed_debit_algebra_mm2']
    assert sum(d.values()) == pytest.approx(418.26916414007)
    assert d['historical_10pct_slot_fill_loss'] == pytest.approx(49.201319651)
    assert d['inherited_C_rotate_hub_replacement'] == pytest.approx(25.5696)
    assert model['decomposition_is_accounting_not_disjoint_physical_regions']


def test_actual_reservation_rectangles_no_credit(model):
    u = model['rectangle_union']
    assert u['union_mm2'] == pytest.approx(131.24731428864)
    assert u['duplicate_overlap_mm2'] == 0
    assert not u['outside_rectangle_area_is_free_packable']
    assert model['containment']['proven_removable_double_count_mm2'] == 0


def test_conservative_fail_unchanged(model):
    b = model['composed_conservative_branch']
    assert b['total_mm2'] == pytest.approx(924.2886185238459)
    assert not b['area_condition_pass'] and not b['physical_fit_proven']
    assert model['containment']['all_current_charges_retained']


def test_condition_requires_exclusions_and_extra_hardware(model):
    c = model['corrected_4096_branch_contract']
    limit = c['max_extra_exclusions_plus_unpriced_hardware_mm2']
    assert limit == pytest.approx(220.7332313275841)
    pass_area = M.budget_branch(c['priced_field_mm2'], 47.208013178655904, 131.24731428864, limit-2, 1)
    fail_area = M.budget_branch(c['priced_field_mm2'], 47.208013178655904, 131.24731428864, limit, 1)
    assert pass_area['area_condition_pass'] and not pass_area['build_admitted']
    assert not fail_area['area_condition_pass']


def test_negative_cost_rejected():
    with pytest.raises(ValueError):
        M.budget_branch(400, 47, 131, -100, 0)


def test_bijection_preserves_all_sites_and_regions(model):
    c = model['single_parallel_successor']
    rows = c['source_site_mapping']
    assert len({(r['shard'], r['local_site']) for r in rows}) == 4096
    assert {r['source_site'] for r in rows} == set(range(4096))
    for r in rows:
        assert r['source_site'] == 2048*r['shard']+r['local_site']
        assert r['source_return_region'] == 64*r['shard']+r['local_return_region']
    assert c['source_reduction_region_cut_count'] == 0


def test_BF_dual_mask_exact_both_halves():
    source = {i*4096//724 for i in range(724)}
    local = {i*2048//362 for i in range(362)}
    assert source == local | {g+2048 for g in local}


def test_conservative_successor_duplicates_full_fixed_cost(model):
    c = model['single_parallel_successor']
    assert c['conservative_priced_per_shard_mm2'] == pytest.approx(694.8828979212859)
    assert c['per_shard_margin_for_extra_IO_link_adapter_hardware_mm2'] == pytest.approx(163.1171020787141)
    assert c['full_inherited_fixed_debit_retained_per_shard_mm2'] == pytest.approx(418.26916414007)
    assert c['full47p208_residual_retained_per_shard_mm2'] == pytest.approx(47.208013178655904)
    assert c['fixed_services_replicated_not_silently_shared']


def test_uniform_cfg_storage_and_weight_capacity_not_dropped(model):
    c = model['single_parallel_successor']
    assert c['uniform_cfg_logical_payload_bits_per_rank_owner'] == 5033164800
    assert c['uniform_cfg_physical_storage_bits_per_rank_owner'] == 8455716864
    assert c['aggregate_weight_bits_per_old_owner'] == 18387828736
    assert c['aggregate_weight_macros_per_old_owner'] == 16384
    assert 2*c['return_bits_per_shard'] == 69771008
    assert c['aggregate_adjacent_compute_unchanged']
    assert sum(s['active_pairs'] for s in c['actual_622_shard_site_census']) == 3375
    assert sum(s['padding_q_pairs'] for s in c['actual_622_shard_site_census']) == 721


def test_more_dies_are_parallel_not_TP_reassociation(model):
    c = model['single_parallel_successor']
    assert c['layer_dies_after'] == 464 and c['serial_stage_owners'] == 58
    assert c['logical_TP_ranks'] == 4
    assert c['added_serial_stage_hops'] == c['added_TP_collective_tree_levels'] == 0
    assert c['added_intraowner_boundary']
    assert not c['critical_path']['no_single_token_loss_proven']


def test_finite_boundary_cost_not_zero_or_rate(model):
    c = model['single_parallel_successor']
    assert c['boundary']['unbackpressured_remote_result_port_width_bits_per_stream_cycle'] == 4416
    assert c['critical_path']['sensitivity_us_if_all1149_layer_weight_calls_exposed'] == [114.9,229.8,574.5]
    assert not c['performance_adopted'] and not c['build_admitted']
    assert not model['calendar']['full_token_calendar_complete']
    assert len(model['calendar']['native_failures']) == 7


def test_policy_track_margin_not_discount(model):
    r = model['route_policy']
    assert r['corridor_margin_tracks']['collector_combined'] == 4
    assert r['corridor_margin_tracks']['index_quarter_join_to_batch'] == 46
    assert r['corridor_margin_tracks']['index_HBM_all128responses'] == 72
    assert r['no_discount_from_margin_or_free_whitespace']


def test_replay_exact(model):
    record = M.OUT / 'model-r4.json'
    assert record.read_text() == json.dumps(model, indent=2, sort_keys=True)+'\n'
