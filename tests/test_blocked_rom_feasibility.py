"""Static feasibility must charge recurrence and partial reduction work."""
import json
from pathlib import Path
from tools.audit_blocked_rom_feasibility import bounds, rounding_witness


def inputs():
    root=Path(__file__).resolve().parents[1]
    c=json.loads((root/'configs/architecture/rom_hbm_review_v3.json').read_text())
    c.update(c['rom_performance_variant'])
    return c,json.loads((root/c['model']).read_text())


def test_non_equivalence_is_a_concrete_finite_bf16_case():
    w=rounding_witness()
    assert w['whole_K_sequential_result']==0
    assert w['blocked_pairwise_result']==1


def test_smaller_blocks_exchange_recurrence_for_reduction_work():
    c,m=inputs();small=bounds(c,m,32);large=bounds(c,m,128)
    assert small['ideal_compute_dependency_floor_us']['3']<large['ideal_compute_dependency_floor_us']['3']
    assert small['reduction_adds_per_token']>large['reduction_adds_per_token']
    assert small['partial_bytes_per_token']==4*large['partial_bytes_per_token']


def test_configured_utilization_cannot_improve_ideal_bound():
    c,m=inputs();r=bounds(c,m)
    for L in ['1','2','3']:
        assert r['floor_us_with_configured_utilization_cap'][L]>=r['ideal_compute_dependency_floor_us'][L]
    assert r['floor_us_with_configured_utilization_cap']['1']>r['linear_budget_us']
