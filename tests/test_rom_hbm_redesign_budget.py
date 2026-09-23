"""Guard architectural accounting against optimistic comparison shortcuts."""
from copy import deepcopy
import json
from pathlib import Path

from tools.evaluate_rom_hbm_redesign import evaluate

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    c = json.loads((ROOT/'configs/architecture/rom_hbm_review_v3.json').read_text())
    m = json.loads((ROOT/c['model']).read_text())
    return c,m


def test_hbm_cache_is_credited_and_kv_is_not_forced_to_hbm():
    c,m=inputs()
    p=evaluate(c,m)
    assert p['hbm_twin_weight_only_lower_bound_us'] < p['hbm_twin_shared_weight_kv_lower_bound_us']
    no_cache=deepcopy(c);no_cache['hbm_twin_extra_sram_bytes_per_die']=0
    assert p['hbm_twin_weight_only_lower_bound_us'] < evaluate(no_cache,m)['hbm_twin_weight_only_lower_bound_us']
    assert not p['conditions']['threefold_vs_hbm_weight_floor_with_extra_cache']


def test_performance_pass_is_not_a_claim_of_measured_or_universal_speedup():
    c,m=inputs();c.update(c['rom_performance_variant'])
    p=evaluate(c,m)
    assert p['all_necessary_conditions_pass']
    assert p['qualified_token_latency_us'] is None and p['qualified_speedup'] is None
    assert p['required_rom_us_for_3x_vs_full_spare_cache'] < p['rom_token_latency_target_us_not_prediction']


def test_long_context_requires_capacity_and_arithmetic_not_just_bandwidth():
    c,m=inputs();base=evaluate(c,m)
    c['context_positions']*=4;c['capacity_positions']*=4
    p=evaluate(c,m)
    assert p['qk_av_operations']==4*base['qk_av_operations']
    assert p['attention_scores']==4*base['attention_scores']
    assert not p['conditions']['kv_capacity']
    assert not p['conditions']['score_and_exp_scratch']


def test_fallback_and_collective_failure_cannot_hide_in_peak_compute():
    c,m=inputs();c.update(c['rom_performance_variant'])
    c['fallback_fraction_target']=0.001;c['collective_latency_budget_ns']=1000
    p=evaluate(c,m)
    assert not p['conditions']['fallback_average_capacity']
    assert not p['conditions']['collective_budget']
    assert not p['all_necessary_conditions_pass']


def test_rom_density_cannot_increase_ports_or_create_free_capacity():
    c,m=inputs();c.update(c['rom_performance_variant']);p=evaluate(c,m)
    c['rom_bytes_per_mm2_assumed']/=2;q=evaluate(c,m)
    assert q['system_weight_bytes_s_target']==p['system_weight_bytes_s_target']
    assert q['raw_rom_bytes_per_die']==p['raw_rom_bytes_per_die']
    assert not q['conditions']['rom_area_within_cap']
