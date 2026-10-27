import copy
import pytest
from hbm_hub_clock_retarget import retarget_type


def fixture():
    return dict(clock=dict(core_taps='early', taps=[
        dict(kind='core', name='u.hc.clk', xy=[8, 9], insertion_ps=250,
             insertion_ff_ps=202.5, budget_owner='hc'),
        dict(kind='core', name='v', xy=[1, 2], insertion_ps=250, budget_owner='vmod')]),
        hard_cores=[dict(inst='u.hc__q0', module='hc', origin_um=[0, 10], outline_um=[20, 40]),
                    dict(inst='u.hc__q1', module='hc', origin_um=[100, 30], outline_um=[20, 40]),
                    dict(inst='v', module='vmod', origin_um=[9, 20], outline_um=[2, 8])])


def test_replica_and_nested_instance_clock_contract():
    t = fixture()
    h = copy.deepcopy(t['hard_cores'])
    r = retarget_type(t)
    assert (r['old_taps'], r['new_taps']) == (2, 3)
    assert [(x['name'], x['xy']) for x in t['clock']['taps']] == [
        ('u.hc__q0.clk', [10, 30]), ('u.hc__q1.clk', [110, 50]), ('v', [10, 24])]
    assert t['clock']['taps'][1]['insertion_ff_ps'] == 202.5
    assert t['hard_cores'] == h
    before = copy.deepcopy(t)
    retarget_type(t)
    # Reapplication preserves the physically meaningful clock contract.
    assert [(x['name'], x['xy'], x['insertion_ps']) for x in t['clock']['taps']] == [
        (x['name'], x['xy'], x['insertion_ps']) for x in before['clock']['taps']]


def test_missing_contract_fails_without_dropping_core():
    t = fixture()
    t['hard_cores'].append(dict(inst='missing', module='hc', origin_um=[0, 0], outline_um=[1, 1]))
    before = copy.deepcopy(t)
    with pytest.raises(ValueError, match='no source clock contract'):
        retarget_type(t)
    assert t == before


def test_wrong_module_contract_rejected():
    t = fixture()
    t['hard_cores'][0]['module'] = 'different'
    with pytest.raises(ValueError, match='module differs'):
        retarget_type(t)
