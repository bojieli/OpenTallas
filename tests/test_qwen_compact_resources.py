import json
from pathlib import Path

import pytest

from tools.audit_qwen_compact_resources import ROOT, INPUTS, break_even_rom_tb_s, candidate, dies_to_hold, model_work

M, C, R, EV = [json.loads((ROOT / n).read_text()) for n in INPUTS[:4]]
REC = R['linear_dependency_floor_us_by_recurrence_cycles']


def test_kv_and_work_follow_published_topology():
    w = model_work(M)
    assert w['kv_bytes'] == 8192 * 36 * 8 * 128 * 2 * 2
    assert w['weight_bytes'] == 15136811008
    assert w['attention_ops'] == 4 * 36 * 32 * 128 * 8192


def test_area_budget_is_conserved_and_overfull_die_is_refused():
    row = candidate(M, C, REC, 5, 400, 18)
    b = row['die_budget']
    assert b['fixed_mm2'] + b['kv_sram_mm2'] + b['compute_mm2'] + 400 == pytest.approx(815)
    assert row['holds_full_checkpoint']
    assert 'infeasible' in candidate(M, C, REC, 4, 500, 18)


def test_sequential_contract_binds_both_machines_equally():
    for rate in (18, 72):
        s = candidate(M, C, REC, 5, 400, rate)['contracts']['sequential_rne_recurrence_1']
        assert s['rom']['binding'] == s['hbm_equal_area']['binding'] == 'recurrence'
        assert s['rom_over_hbm_single_sequence'] == 1


def test_floor_is_maximum_of_terms_and_rom_rate_never_exceeds_lanes():
    row = candidate(M, C, REC, 6, 300, 1e6)
    assert row['rom_rate_used_TB_s'] == pytest.approx(row['lane_consumable_weight_TB_s'])
    for s in row['contracts'].values():
        for side in ('rom', 'hbm_equal_area'):
            assert s[side]['floor_us'] == max(s[side]['terms_us'].values())


def test_break_even_rate_equalizes_relaxed_floors():
    rate = break_even_rom_tb_s(M, C, 5, 400)
    s = candidate(M, C, REC, 5, 400, rate)['contracts']['unqualified_relaxed_association']
    assert s['rom_over_hbm_single_sequence'] == pytest.approx(1)


def test_committed_record_matches_inputs():
    import hashlib
    out = json.loads((ROOT / 'results/architecture/qwen_compact_resources.json').read_text())
    for name, digest in out['input_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest


def test_optimized_hbm_split_is_never_worse_than_the_twin():
    for cls, d in EV['density_classes_for_sweeps'].items():
        if cls.startswith('hc1'):
            continue
        n = dies_to_hold(M, C, 300, d)
        for s in candidate(M, C, REC, n, 300, 'sram_matched', d)['contracts'].values():
            assert s['hbm_equal_area_optimized_split']['floor_us'] <= s['hbm_equal_area']['floor_us'] + 1e-9


def test_derived_die_count_holds_the_checkpoint_and_one_fewer_does_not():
    for cls, d in EV['density_classes_for_sweeps'].items():
        if cls.startswith('hc1'):
            continue
        n = dies_to_hold(M, C, 400, d)
        assert candidate(M, C, REC, n, 400, 18, d)['holds_full_checkpoint']
        assert not candidate(M, C, REC, n - 1, 400, 18, d)['holds_full_checkpoint']


def test_compiler_class_density_gives_no_several_fold_advantage():
    out = json.loads((ROOT / 'results/architecture/qwen_compact_resources.json').read_text())
    ratios = [r['contracts']['unqualified_relaxed_association']['rom_over_optimized_hbm_single_sequence']
              for r in out['candidates'] if 'contracts' in r and r['density_class'].startswith('compiler_class')]
    assert ratios and max(ratios) < 2
