"""Dependency bounds must not improve by adding idle parallel lanes."""
import json
from pathlib import Path

def inputs():
    root=Path(__file__).resolve().parents[1]
    c=json.loads((root/"configs/architecture/rom_hbm_review_v3.json").read_text())
    return c,json.loads((root/c["model"]).read_text())
from tools.audit_redesign_recurrence_feasibility import audit


def test_more_output_lanes_cannot_shorten_sequential_dot_product():
    c,m=inputs();c.update(c['rom_performance_variant'])
    before=audit(c,m);c['tiles_per_cluster']*=2;after=audit(c,m)
    assert before['linear_dependency_floor_us_by_recurrence_cycles']==after['linear_dependency_floor_us_by_recurrence_cycles']
    assert not before['sequential_contract_meets_linear_budget']
    assert before['linear_dependency_floor_us_by_recurrence_cycles']['1']==888.832


def test_recurrence_latency_and_clock_scale_bound():
    c,m=inputs();c.update(c['rom_performance_variant'])
    baseline=audit(c,m);c['clock_hz']/=2;slow=audit(c,m)
    assert slow['linear_dependency_floor_us_by_recurrence_cycles']['1']==baseline['linear_dependency_floor_us_by_recurrence_cycles']['2']
