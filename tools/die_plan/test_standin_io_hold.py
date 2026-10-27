"""Optimised IO contracts cannot inherit the legacy synthetic seam hold guarantee."""
import copy
import json
from pathlib import Path
import pytest
import die_ci as C
import die_trial as T
import gen_phys as G
import schema as S
HERE=Path(__file__).resolve().parent
PAIR=json.loads((HERE/'examples/s81_pair/s81_pair_plan.json').read_text())

@pytest.mark.parametrize('mode',['sender_min','plan_demand'])
def test_ci_standin_requires_real_parent(mode):
    raw=copy.deepcopy(PAIR)
    raw['clock']['io_hold']=mode
    if mode=='plan_demand': raw['clock']['hold_demand']=dict(source='plan',default_ps=80)
    p=S.Plan(raw)
    row=C.standin('ft',p,C.DEFAULT_MARGINS,C.kit_budget(G,p))
    assert row['hold_policy_ps'] is None and row['hold_ps'] is None
    assert row['hold_status']=='NEEDS_PARENT'
    assert row['setup_policy_ps'] is not None

@pytest.mark.parametrize('mode',['sender_min','plan_demand'])
def test_trial_bare_optimised_input_never_inherits_legacy_bhold(mode):
    raw=copy.deepcopy(PAIR); raw['clock']['io_hold']=mode
    if mode=='plan_demand':raw['clock']['hold_demand']=dict(source='plan',default_ps=80)
    p=S.Plan(raw)
    v,_=T.standin_netlist(p,'fb')
    assert 'OT_IO_HOLD NEEDS_PARENT' in v
    for port in G.input_hold_min(p,'fb'):
        assert f'.A({port}[' not in v
        assert f'.D({port}[' in v
    # Die-edge fallback is still modelled by the old hold contract.
    fallback,_=T.standin_netlist(p,'fa')
    assert 'OT_BHOLD_' in fallback


def test_legacy_keeps_original_budget():
    p=S.Plan(copy.deepcopy(PAIR))
    row=C.standin('ft',p,C.DEFAULT_MARGINS,C.kit_budget(G,p))
    assert row['hold_policy_ps'] is not None and 'hold_status' not in row
    v,_=T.standin_netlist(p,'fb')
    assert 'OT_BHOLD_' in v and 'NEEDS_PARENT' not in v
