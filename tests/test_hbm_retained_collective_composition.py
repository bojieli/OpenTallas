import ast
import importlib.util
import json
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('retained', ROOT/'tools/hbm_retained_collective_composition.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_retained_measured_fit_terms_no_candidate_savings():
    r = m.build()
    assert r['verify_passes'][0]['retained_collective_us'] == 240.46
    assert r['verify_passes'][5]['retained_collective_us'] == 326.81
    assert r['retained_draft_collective_us'] == 23.89
    assert r['verify_passes'][0]['baseline_total_us'] == pytest.approx(442.14)
    assert r['retained_fixed_terms']['gather_ns'] == pytest.approx(932.8/1200480192.08*1e9)
    assert r['retained_fixed_terms']['allreduce_ns'] == pytest.approx(988.74/1200480192.08*1e9)
    for p in r['verify_passes']:
        assert p['HA2_saving_us'] == p['dependent_R3a_saving_us'] == 0
        assert p['conditional_service_corrected_total_us'] > p['baseline_total_us']
    assert not r['adopted'] and r['published_accelerator_rate'] is None
    assert not r['rejected_HA2']['estimated_459ns_eligible']
    assert not r['rejected_HA2']['candidate_550ns_benefit_eligible']


def test_MTP_preserves_full_draft_collectives_and_no_rate_bonus():
    r = m.build()
    for row in r['conditional_rows']:
        p = r['verify_passes'][row['gamma']]
        scale = 1 if row['context'] == '1M' else 441.3/442.14
        assert row['retained_draft_us'] == pytest.approx(sum(r['retained_draft_parts_us'].values())*scale)
        assert row['conditional_MTP_step_us'] == pytest.approx(row['conditional_verify_us'] + row['retained_draft_us'])
        assert row['conditional_MTP_step_us'] >= (p['baseline_total_us'] + sum(r['retained_draft_parts_us'].values()))*scale


@pytest.mark.parametrize('mutation', ['source','adopted','credit','measurement','packet','whole'])
def test_rejected_candidate_cannot_reenter(mutation):
    t=json.loads((ROOT/m.TERMINAL).read_text());v=json.loads((ROOT/m.VERDICT).read_text())
    if mutation=='source':v['source_commit']='bad'
    if mutation=='adopted':v['rows'][0]['adopted']=True
    if mutation=='credit':v['rows'][0]['contribution_to_adopted_composition']=1
    if mutation=='measurement':v['rows'][0]['measured_gather_last_ns'][0]=550
    if mutation=='packet':t['exact']['gather_packet_checks']=1
    if mutation=='whole':t['measurements']['whole_allreduce_ns']=550
    with pytest.raises(ValueError):m.validate_rejection(t,v)


def test_record_byte_replay():
    assert json.loads((ROOT/m.OUT).read_text())==m.build()


def test_default_calculation_bodies_unchanged():
    old=subprocess.check_output(['git','show','b3537e174:tools/uarch_model.py'],cwd=ROOT,text=True)
    def funcs(s):return {n.name:ast.dump(n) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
    a,b=funcs(old),funcs((ROOT/'tools/uarch_model.py').read_text())
    assert set(b)-set(a)=={'hbm_retained_collective_rows','qwen_headreg_measured_rows'}
    assert all(b[k]==v for k,v in a.items() if k!='main')
