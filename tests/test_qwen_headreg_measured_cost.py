import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('head',ROOT/'tools/qwen_headreg_measured_cost.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


def test_actual_slow_count_cost_and_rate_debit():
    r=m.build()
    for x in r['rows']:
        assert x['added_sclk_cycles']==126
        assert x['functional_added_ns']==140
        assert 0<x['same_clock_context_rate_debit_percent']<.057
        assert x['same_clock_context_rate_ratio']==pytest.approx(x['reference_cycles']/x['measured_cycles'])
        assert x['full_token_rate'] is None and x['physical_clock_gain'] is None
    assert r['rate_bonus']==0 and not r['async_adopted'] and not r['clock_fix_adopted']


@pytest.mark.parametrize('bad',['72','failed','multiuser','unstable'])
def test_refuse_estimated_cost_and_other_scope(bad):
    r=json.loads((ROOT/m.BASE/'result.json').read_text())
    if bad=='72':r['runs']['c1p1ah_u1']['added_cycles']=72
    if bad=='failed':r['runs']['c1p1ah_u1']['returncode']=1
    if bad=='multiuser':r['runs']['c1p1ah_u1']['args']=['+CLK=split','+USERS=2']
    if bad=='unstable':r['source_stable']=False
    with pytest.raises(ValueError):m.price(r)


def test_source_pinned_byte_replay():
    assert json.loads((ROOT/m.OUT).read_text())==m.build()
