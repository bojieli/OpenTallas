"""HA0/HA10 numerical replay, frozen default behavior and fairness refusals."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import uarch_model as u
import hbm_accelerator_model as h

BEFORE = json.loads((ROOT / 'results/uarch/hbm_accelerator_integration_20261003/defaults_before.json').read_text())


@pytest.fixture(scope='module')
def model():
    return u.hbm_accel_rows()


@pytest.mark.parametrize('group_slot', [False, True])
@pytest.mark.parametrize('positions', [1, 6])
def test_no_service_default_is_exact_preintegration(group_slot, positions):
    # JSON turns the tuple into a list; every numeric part and boundary is exact.
    assert list(u.v41_hbm_chain(group_slot, positions)) == BEFORE['v41_hbm_chain'][f'{group_slot}/{positions}']
    assert list(u.v41_hbm_chain(group_slot, positions, service='off')) == BEFORE['v41_hbm_chain'][f'{group_slot}/{positions}']


@pytest.mark.parametrize('fn', ['qwen_hbm_rows', 'v41_hbm_rows', 'gpu_tier2'])
def test_default_rows_are_unchanged(fn):
    assert getattr(u, fn)() == BEFORE[fn]


def test_frozen_ladder_exact_not_point_one_percent_fitting(model):
    old = json.loads((ROOT / (h.STUDY + 'ladder.json')).read_text())
    assert model['hypotheses']['ds'] == old['ds']
    assert model['hypotheses']['qwen'] == old['qwen']


def test_hypotheses_cannot_publish_or_adopt(model):
    assert model['status'] == 'UNVALIDATED_MODEL_HYPOTHESES'
    assert model['adopted'] is False and model['default_enabled'] is False
    assert model['published_accelerator_rates'] == []
    assert model['measured_composition'] is None
    for rung in model['gates'].values():
        assert list(rung['ordered_gates']) == h.GATES
        assert all(x == 'NOT_PASSED' for x in rung['ordered_gates'].values())
        assert rung['adopted'] is False
    assert model['clock_blocker']['admission'] is False
    assert model['clock_blocker']['throughput_halving_allowed'] is False


def test_service_authorities_do_not_double_count_W19_first_access(model):
    legacy = model['labeled_baselines']['legacy_service_rows']
    assert {x['boundaries'] for x in legacy} == {329}
    central = legacy[2]
    assert central['parts_us']['routed_fetch'] == pytest.approx(40 * 476 * 1e-3)
    assert central['token_us'] == pytest.approx(sum(central['parts_us'].values()))
    w19 = model['hypotheses']['ds']['1M']['firm']['ladder']
    r0c = next(x for x in w19 if x['rung'] == 'R0c')
    assert r0c['ar_us'] == pytest.approx(457.0, abs=0.02)
    assert r0c['ar_us'] > w19[1]['ar_us']
    assert w19[0]['rung'] == 'R0' and w19[0]['ar_tok_s'] == pytest.approx(1098.6)
    assert 'not measured B200' in model['labeled_baselines']['gpu_grid']


def test_eight_scans_and_literal_fullscore_remain_explicit(model):
    gpu = model['labeled_baselines']['corrected_B200']
    assert len(gpu['index_scan']['scanning_layers']) == 8
    assert gpu['index_scan']['candidate_gather'] is True
    assert gpu['tokens_s'] == 282.4 and gpu['spec_tokens_s'] == 547.8
    assert model['labeled_baselines']['full_score_AR_tok_s'] == pytest.approx(281.84379348323137)
    assert model['fairness']['comparable_workload_precision_context_and_acceptance_qualified'] is False


def test_area_includes_core_dies_and_base_not_only_logic(model):
    assert h.silicon(1630, 8, 1000)['total_silicon_mm2'] == 9630
    for case in ('low', 'central', 'high'):
        areas = model['fairness']['qwen_area']['iso_total_silicon_with_rom']['area_sensitivities']
        assert areas[case] == model['fairness']['qwen_ROM_option_C_area'][case]
    for point in model['fairness']['ds_system_counts']:
        for a in point['area_sensitivities'].values():
            assert a['total_silicon_mm2'] == a['logic_mm2'] + a['dram_core_and_base_mm2']


def test_iso_area_sweep_does_not_transfer_96rank_gains(model):
    for row in model['fairness']['iso_total_silicon_budget_ablation']:
        assert row['area']['total_silicon_mm2'] <= row['budget_total_silicon_mm2']
        assert row['accelerator_rate'] is None
        assert row['historical_ablation']


def test_power_cannot_claim_unrestricted_rate_under_smaller_budget(model):
    point = model['fairness']['iso_power_average_bounds'][0]
    assert point['source_unrestricted_rate_hypothesis_tok_s'] == 3015.2
    assert point['average_rate_upper_bound_tok_s'] < 100
    for p in model['fairness']['iso_power_average_bounds']:
        rate = p['average_rate_upper_bound_tok_s']
        assert rate <= p['source_unrestricted_rate_hypothesis_tok_s']
        if not p['static_floor_exceeds_budget']:
            assert p['static_w'] + p['dynamic_J_per_token'] * rate <= p['budget_w'] + 1e-8
        assert p['instantaneous_power_and_throttling_schedule_qualified'] is False
    assert model['fairness']['saturated_accelerator_J_per_token'] is None


@pytest.mark.parametrize('budget', [10, 20])
def test_static_power_floor_is_not_free_sleep(budget):
    p = h.iso_power(100, 20, 1, budget)
    assert p['average_rate_upper_bound_tok_s'] == 0
    assert p['minimum_mean_intertoken_us'] is None
    assert p['static_floor_exceeds_budget'] is True


@pytest.mark.parametrize('bad', [0, -1, float('nan'), float('inf')])
def test_unknown_or_invalid_power_is_not_zero_cost(bad):
    with pytest.raises(ValueError):
        h.iso_power(100, 20, bad, 50)


def test_transferred_wire_fit_is_not_charged_as_10ns(model):
    a = model['wire_accounting']
    assert a['endpoint_stages_per_side'] == 34
    assert a['wire_only_two_endpoint_ns'] > 56
    assert a['C5hc_increment_ns'] == pytest.approx(83.4)
    assert '96-rank topology remains unvalidated' in a['transfer_scope']


def test_study_tamper_is_rejected_before_loading(tmp_path):
    for name in h.STUDY_PINS:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / name).read_bytes())
    p.write_bytes(p.read_bytes() + b' ')
    with pytest.raises(ValueError, match='frozen study changed'):
        h._load_study(tmp_path)


def test_source_pins_match_current_inputs(model):
    for name, expected in model['input_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected


def test_cli_optin_and_json_receipt(tmp_path, capsys):
    out = tmp_path / 'accel.json'
    u.main(['--hbm-accel', '--out', str(out)])
    assert json.loads(out.read_text()) == json.loads(capsys.readouterr().out)
    assert json.loads(out.read_text())['default_enabled'] is False


def test_legacy_energy_selects_true_saturation_not_last_batch(model):
    e = json.loads((ROOT / 'results/uarch/economics.json').read_text())
    for design, modes in model['fairness']['historical_ablation_energy'].items():
        for mode, row in modes.items():
            expected = e[design][mode]
            assert row['saturated']['batch'] == expected['sat_batch']
            assert row['saturated']['energy_mJ_per_token'] > 0
            assert row['batch1'] == expected['rows'][0]


def test_successor_guard_rejects_arbitrary_predecessor():
    with pytest.raises(ValueError, match='unrecognized prior'):
        h.verify_preserved_default_source(ROOT, '0' * 64)
