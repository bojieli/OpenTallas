"""Explicit endpoints break reset-placement feedback without skipping budgets."""
import copy
import json
from pathlib import Path
import pytest
import schema
import taps
import reset_tree as RT


def plan():
    raw=json.loads((Path(__file__).parent/'examples/tiny_plan.json').read_text())
    raw['reset'].update(release='wavefront',start='broadcast')
    for t in raw['partition_types'].values():
        t['clock'].update(tap_mode='explicit',control_sinks=True,
                          taps=[dict(name='clk',xy=[432.,432.])],
                          tap_max_sinks=10000,tap_radius_um=1500.)
    return schema.Plan(raw)


def test_reset_geometry_then_complete_actual_control_budget():
    P=plan()
    # Previously this entered wf_solve -> face_sites -> tap_grid forever.
    got=schema.tap_grid(P,'src')
    assert got==[('clk',432.,432.)]
    W=RT.wf_solve(P)
    assert W['unreachable']==[]
    controls=taps.control_pin_sinks(P,'src')
    assert controls and any(n=='start_i' for n,*_ in controls)
    base=taps.sink_sites(P,'src',control=False)
    final=taps.explicit_taps(P,'src')
    assert sum(t[3] for t in final)==sum(p[2] for p in base)+len(controls)


def test_planning_endpoint_lookup_never_reads_sink_budget(monkeypatch):
    P=plan()
    monkeypatch.setattr(taps,'sink_sites',lambda *a,**k:pytest.fail('recursive full sink lookup'))
    assert RT._plan_taps(P,'src')==[('clk',432.,432.)]


def test_full_control_capacity_and_radius_still_fail_closed():
    P=plan()
    base=sum(p[2] for p in taps.sink_sites(P,'src',control=False))
    assert len(taps.control_pin_sinks(P,'src'))>1
    P.types['src']['clock']['tap_max_sinks']=int(base)+1
    with pytest.raises(ValueError,match='load='):
        taps.explicit_taps(P,'src')
    P.types['src']['clock']['tap_max_sinks']=10000
    P.types['src']['clock']['tap_radius_um']=1
    with pytest.raises(ValueError,match='radius='):
        schema.tap_grid(P,'src')


def test_endpoint_geometry_is_not_a_waiver():
    P=plan();P.types['src']['clock']['taps'][0]['xy']=[0.,0.]
    with pytest.raises(ValueError,match='outline/halo'):
        RT._plan_taps(P,'src')
