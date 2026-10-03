import ast
import importlib.util
import json
import subprocess
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('clockregion',ROOT/'tools/clock_region_candidate_composition.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


def test_source_cycles_and_optional_terms():
    r=m.build();p=r['profiles']
    assert [p[n]['Qwen_base_cycles']for n in ('central','bound')]==[506,2024]
    assert [p[n]['DS_base_cycles']for n in ('central','bound')]==[661,2642]
    assert [p[n]['Qwen_banded_extra_cycles']for n in ('central','bound')]==[217,868]
    assert [p[n]['Qwen_unmerged_IO_extra_cycles']for n in ('central','bound')]==[144,576]
    assert [p[n]['DS_source_S73_unmerged_IO_extra_cycles']for n in ('central','bound')]==[306,1228]
    assert len(r['rows'])==48


def test_combined_prices_never_remove_baseline_wire_or_grant_MTP_free_cost():
    for x in m.build()['rows']:
        assert x['combined_conditional_AR_us']==pytest.approx(x['base_conditional_AR_us']+x['CLOCK_REGION_us'])
        assert x['CLOCK_REGION_us']==pytest.approx(x['CLOCK_REGION_cycles']/1200)
        assert x['rate_debit_percent']>0
        assert x['combined_MTP_step_us'] is None and x['combined_MTP_tokens_s'] is None
        if x['model'].endswith('S82'):
            assert x['base_conditional_AR_us']>418
            if x['unmerged_IO']:
                assert x['provisional_extra_S82_IO_cycles']==(16 if x['profile']=='central' else 64)
    r=m.build()
    assert not r['adopted'] and not r['default_enabled']
    assert r['published_rate'] is None and r['measured_primitive_delta'] is None


@pytest.mark.parametrize('bad',['measured','cycles','S73','RD4','zero','IOgain'])
def test_wrong_authority_or_scope_refused(bad):
    a=[json.loads((ROOT/p).read_text())for p in (m.DECISION,m.QWEN,m.DS)]
    if bad=='measured':a[0]['status']='MEASURED'
    if bad=='cycles':a[0]['recommendation']['price_to_model']['deepseek']['bound_cycles']=2644
    if bad=='S73':a[2]['stages']=73
    if bad=='RD4':a[2]['return_RD']=4
    if bad=='zero':a[0]['derivation']['latency']['central_thick_metal']['deepseek']['C']['cycles']=0
    if bad=='IOgain':a[0]['derivation']['latency']['central_thick_metal']['deepseek']['C_unmerged']['cycles']=600
    with pytest.raises(ValueError):m.compose(*a)


def test_record_replays_and_old_model_calculations_are_unchanged():
    assert json.loads((ROOT/m.OUT).read_text())==m.build()
    old=subprocess.check_output(['git','show','d99237f667bd526b787f993f009113ba3444c080:tools/uarch_model.py'],cwd=ROOT,text=True)
    def f(s):return {n.name:ast.dump(n)for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
    a,b=f(old),f((ROOT/'tools/uarch_model.py').read_text())
    assert set(b)-set(a)=={'clock_region_rows'}
    assert all(b[k]==v for k,v in a.items()if k!='main')
