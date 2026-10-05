import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w17_D1_core_cost_handoff as m

def test_unobserved_runtime_has_no_invented_rate_or_wall_budget():
    x=m.build();assert x['expected_wall_seconds'] is None
    assert x['actual_runtime']['actual_cycles'] is None and x['actual_runtime']['seconds_per_cycle'] is None
    assert not x['native_only_observability_option']['GO'] and not x['native_only_observability_option']['selected']
    assert x['causal_gate']['service_status']=='BOUND_MISSING'

def test_expected_cycles_separate_from_seconds():
    x=m.build();t=x['expected_conditional_cycle_targets'];assert [r['pre_NBA_cycle'] for r in t]==[12302,12355,136667,136669,136800]
    assert x['expected_elapsed_cycles']['descriptor_to_stage']==124369
    assert all(r['expected_wall_seconds'] is None for r in t)

def test_cost_calculation_only_with_finite_measured_inputs():
    assert m.finite_cost(cycles=100,init_seconds=2,seconds_per_cycle=.03,logging_seconds=.2)==5.2
    for k in ['init_seconds','seconds_per_cycle','logging_seconds']:
        args=dict(cycles=100,init_seconds=2,seconds_per_cycle=.03,logging_seconds=.2);args[k]=None;assert m.finite_cost(**args) is None

@pytest.mark.parametrize('bad',[True,-1,float('nan'),float('inf'),'3'])
def test_invalid_measurement_never_prices_launch(bad):
    with pytest.raises(ValueError):m.finite_cost(cycles=100,init_seconds=bad,seconds_per_cycle=.03,logging_seconds=.2)
