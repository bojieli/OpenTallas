import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('actual',ROOT/'tools/qwen_real_memory_measured_contexts.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


def test_actual_P1023_late_context_memory_price():
    r=m.build();rows=[x for x in r['rows'] if x['position']==1023]
    assert len(r['rows'])==9
    assert [x['ideal_cycles']for x in rows]==[4940]*3
    assert [x['real_cycles']for x in rows]==[5789,7171,7027]
    assert [x['observed_memory_service_extra_cycles']for x in rows]==[849,2231,2087]
    assert r['high_observed_overhead_percent']==pytest.approx(2231/4940*100)
    assert r['published_token_rate'] is None and r['full_token_latency_us'] is None
    assert r['posted_write_gain'] is None and not r['physical_clock_qualified']


def test_old_P0_P255_cycle_observations_remain_exact():
    r=m.build()
    assert [x['observed_memory_service_extra_cycles']for x in r['rows'][:6]]==[156,932,544,247,608,759]
    assert [p['observed_layer_sum_extra_cycles']for p in r['pairs']]==[1632,1614,5167]


@pytest.mark.parametrize('bad',['identity','KV','denominator','output'])
def test_latest_pair_refuses_unmatched_or_inexact_data(bad):
    h=m.load_helper();root=ROOT/m.INPUT
    a=json.loads((root/'ideal2_p1023.json').read_text());b=json.loads((root/'real2_p1023.json').read_text())
    if bad=='identity':b['binary_sha256']='wrong'
    if bad=='KV':next(iter(b['token_kv_writeback_checks'].values()))['k_mismatches']=1
    if bad=='denominator':a['stages']['L0']['cycles']=0
    if bad=='output':next(iter(b['layer_x_checks'].values()))['mismatches']=1
    with pytest.raises(ValueError):h.matched_pair(a,b,1023)


def test_byte_replay():
    assert json.loads((ROOT/m.OUT).read_text())==m.build()
