import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
sp=importlib.util.spec_from_file_location('recovery_run',Path(__file__).parents[1]/'tools/w17_window_recovery_gate_run.py')
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)


def test_exact_go_template_rejects_missing_mismatched_fields(tmp_path):
    p=tmp_path/'plan.json';p.write_text('{}')
    plan={k:k for k in ('runner_sha256','model_sha256','record_sha256','manifest_sha256','command_sha256')}
    plan.update(caps=m.CAPS,budget=m.BUDGET,model_composition={'storage_bits':259})
    go={'status':m.STATUS,'plan_sha256':m.sha(p),**{k:plan[k] for k in ('runner_sha256','model_sha256','record_sha256','manifest_sha256','command_sha256','caps','budget')},
        'reviewed_model_composition_sha256':m.digest(plan['model_composition']),
        'reviewed_source_diff_budget':True,'reviewed_connected_oracle_and_negative_controls':True}
    m.validate_go(go,plan,p)
    for key in go:
        bad=dict(go);bad.pop(key)
        with pytest.raises(ValueError):m.validate_go(bad,plan,p)
    for key,value in [('status','OTHER_GO'),('reviewed_source_diff_budget',False),('plan_sha256','0'*64),('caps',{}),('command_sha256','1'*64)]:
        bad=dict(go);bad[key]=value
        with pytest.raises(ValueError):m.validate_go(bad,plan,p)


def test_missing_go_launches_no_service_or_output(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'validate_plan',lambda path:{})
    invoked=[]
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**kw:invoked.append(a))
    args=SimpleNamespace(plan='ignored',probe=False,go_commit=None,go_path='missing',unit='w17-recovery-no-go',out=str(tmp_path/'out'))
    with pytest.raises(ValueError):m.launch(args)
    assert not invoked and not Path(args.out).exists()


def test_actual_schedule_fits_single_aggregate_budget():
    record=json.loads(m.RECORD.read_text());jobs=m.schedule(record)
    assert len(jobs)==5 and sum(j['compile_seconds'] for j in jobs)==130
    assert sum(c['seconds'] for j in jobs for c in j['cases'])==26
    assert 130+26+m.BUDGET['supervision_reserve_seconds']==m.CAPS['RuntimeMaxSec']==180
    assert len(jobs[0]['cases'])==3
    assert sum(c['expected']=='FAIL' for j in jobs for c in j['cases'])==4
    assert m.CAPS['MemoryMax']==4*1024**3 and m.CAPS['MemorySwapMax']==0
    assert m.CAPS['CPUAffinity']==[30,31]
    assert m.BUDGET['automatic_retries']==0


@pytest.mark.parametrize('code,text',[(0,'expected fatal'),(-9,'expected fatal'),(-6,'wrong failure'),(-6,'')])
def test_negative_only_accepts_declared_semantic_failure(code,text):
    with pytest.raises(ValueError):m.verify_runtime({'expected':'FAIL','marker':'expected fatal'},code,text)


def test_expected_negative_and_positive_receipts():
    m.verify_runtime({'expected':'FAIL','marker':'expected fatal'},-6,'expected fatal')
    m.verify_runtime({'expected':'PASS','marker':'case PASS'},0,'case PASS')
    for code,text in [(1,'case PASS'),(0,'case PASS\n%Error: unrelated assertion')]:
        with pytest.raises(ValueError):m.verify_runtime({'expected':'PASS','marker':'case PASS'},code,text)


def test_pins_wrong_source_rejected_before_compiler(monkeypatch):
    original=m.sha
    monkeypatch.setattr(m,'sha',lambda p:'0'*64 if str(p).endswith('idx_hbm_recovery.sv') else original(p))
    with pytest.raises(ValueError,match='source pin mismatch'):m.source_manifest()


def test_compiler_environment_override_rejected(monkeypatch):
    monkeypatch.setenv('VERILATOR_ROOT','/wrong/helper')
    with pytest.raises(ValueError):m.compiler()


def test_aggregate_caps_reject_before_compile(monkeypatch):
    monkeypatch.setattr(m.subprocess,'check_output',lambda *a,**kw:'MemoryMax=1\nMemorySwapMax=0\n')
    with pytest.raises(ValueError):m.caps_receipt('w17-recovery-mutant-cap')


def test_bench_revision_keeps_sourcepins_and_real_fresh_operation():
    old=(m.PACKAGE/'tb.sv').read_text();new=m.BENCH.read_text()
    assert 'integer init_word' in new and 'for(init_word=' in new
    assert 'fresh post-fence refill/publication failed' in new
    assert 'force ' not in new and '.WIN_STACK(2)' in new
    assert 'observer unrelated owner conservation' in old and 'observer unrelated owner conservation' in new
    record=json.loads(m.RECORD.read_text())
    assert record['unified_uarch_addendum']['prepared_added_state_bits']==259


@pytest.mark.parametrize('field,value',[
 ('MemoryMax','2147483648'),('MemorySwapMax','1073741824'),
 ('CPUAffinity','0 1'),('LimitFSIZE','536870912'),
 ('RuntimeMaxUSec','4min'),('KillMode','process')])
def test_each_cap_mismatch_rejected(field,value,monkeypatch):
    values={k:' '.join(map(str,v)) if isinstance(v,list) else str(v)
            for k,v in m.CAPS.items() if k!='RuntimeMaxSec'}
    values.update(ControlGroup='/fake',RuntimeMaxUSec='3min')
    values[field]=value
    monkeypatch.setattr(m.subprocess,'check_output',lambda *a,**kw:'\n'.join(k+'='+v for k,v in values.items()))
    with pytest.raises(ValueError):m.caps_receipt('w17-recovery-bad-cap')


def test_systemd_cpu_range_normalizes_exact_cap_without_relaxation():
    assert m.parse_cpu_set('30-31')==m.CAPS['CPUAffinity']
    assert m.parse_cpu_set('30 31')==m.CAPS['CPUAffinity']
    assert m.parse_cpu_set('30-32')!=m.CAPS['CPUAffinity']
    with pytest.raises(ValueError):m.parse_cpu_set('31-30')


def test_go_consumption_prevents_same_authorization_retry(tmp_path):
    claim=m.claim_go('a'*40,tmp_path)
    assert claim.is_dir()
    with pytest.raises(FileExistsError):m.claim_go('a'*40,tmp_path)


def test_projected_visibility_never_phy_or_service_admission():
    text=Path(m.__file__).read_text()
    assert 'retrospective relative to actual dispatch' in text
    assert "'service_provider_admission':False" in text
    assert "'physical_drain_admission':False" in text
