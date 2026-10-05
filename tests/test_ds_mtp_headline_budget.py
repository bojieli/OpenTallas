import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ds_mtp_headline_budget as B


def test_prefix_acceptance_counts_bonus_and_walk_iterations():
    assert B.committed_tau({'histogram_accepted_0_5': [2, 0, 0, 0, 0, 1],
                            'n': 3, 'tau': 8/3}) == 8/3
    with pytest.raises(ValueError):
        B.committed_tau({'histogram_accepted_0_5': [2, 0, 0, 0, 0, 1],
                         'n': 3, 'tau': 5/3})


def test_reference_margin_is_workload_specific_not_qualification():
    m = B.build()
    assert m['workloads']['chat']['reference_remaining_overhead_budget_us'] < 60
    assert m['workloads']['pooled_36_prompts']['reference_remaining_overhead_budget_us'] > 400
    assert all(r['qualified_rate'] is None for r in m['workloads'].values())
    assert not m['missing_costs_are_zero']
    assert not m['acceptance_context_transfer_to_1M_proven']
    assert m['ROM_current_58stage_PAR2_iteration_us'] is None
