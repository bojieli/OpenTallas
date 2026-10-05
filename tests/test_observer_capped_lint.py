"""Run supervisor cap checks using tiny Python children; never run Verilator."""
import copy,hashlib,json,os,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import prepare_observer_lint_gate as prep
import run_observer_capped_lint as runner
import plan_observer_hierarchy_gate as old
OUT=ROOT/prep.OUT
DATA=(OUT/'plan.json').read_bytes()
PLAN=json.loads(DATA)


def child(tmp_path,code,seconds=2,memory=runner.MEMORY,log_max=runner.LOG):
    return runner.supervise([sys.executable,'-c',code],tmp_path,dict(os.environ),tmp_path/'child.log',seconds,memory,log_max)


def test_prepared_plan_valid():runner.validate_plan(PLAN)


def test_go_template_is_inert():
    with pytest.raises(ValueError):runner.require_go(DATA,json.loads((OUT/'GO.template.json').read_bytes()))


@pytest.mark.parametrize('mutate',[lambda g:g.update(plan_sha256='0'*64),lambda g:g.update(decision='PENDING'),lambda g:g.update(reviewer=''),lambda g:g.update(resource_caps_reviewed=False),lambda g:g.update(extra=True)])
def test_go_requires_exact_reviewed_hash_and_fields(mutate):
    g=json.loads((OUT/'GO.template.json').read_bytes())
    g.update(decision='GO',reviewer='synthetic test only',resource_caps_reviewed=True,source_ownership_and_guard_provenance_reviewed=True)
    mutate(g)
    with pytest.raises(ValueError):runner.require_go(DATA,g)


def test_synthetic_go_schema_only_no_execution():
    g=json.loads((OUT/'GO.template.json').read_bytes())
    g.update(decision='GO',reviewer='synthetic schema test',resource_caps_reviewed=True,source_ownership_and_guard_provenance_reviewed=True)
    runner.require_go(DATA,g)


def test_whitespace_scanner_does_not_invent_enc3():
    assert prep.instances('qenc = ot_hdc_v41x_idx_enc32(qrow);')==[]
    assert prep.instances('ot_real #(.W(32), .N(2)) u_child (.*);')==[('ot_real','u_child')]


def test_both_modes_single_ownership_guarded_missing_only():
    for mode in PLAN['modes']:
        assert not mode['closure']['ambiguous']
        assert set(mode['closure']['unresolved'])==prep.GUARDS
        assert all(mode['guard_resolution'][g]['false'] for g in prep.GUARDS)
        assert 'ot_hdc_v41x_idx_enc3' not in mode['closure']['ownership']
        assert mode['parameters']['SUN']==256 and mode['parameters']['CL_DEPTH']==512 and mode['parameters']['ROM_PHW']==6


def test_ckv_driver_exact_indexed_binding():
    m=PLAN['modes'][1]
    assert {k:m['parameters'][k] for k in ['X_IDX','X_SEL','IDX_RING','CKV_SELECTED']}==dict(X_IDX=2,X_SEL=1,IDX_RING=1,CKV_SELECTED=1)
    assert m['copy']==prep.CKV_COPY
    copy=(ROOT/prep.CKV_COPY).read_text()
    assert prep.inverse_ckv(copy,(ROOT/old.COPY).read_text())==old.blob(ROOT,prep.CKV_ORIGINAL).decode()
    assert 'parameter bit SIM_OBS_ENABLE = 0' in copy
    assert 'CKV observation requires opt-in' not in copy
    for p in ['ckv_ag_tx_ready','ckv_ag_rx_valid','ckv_ag_rx_rank','ckv_ag_rx_gid']:
        assert '.'+p+'('+p+')' in copy


def test_original_sources_and_supplements_pinned():
    for m in PLAN['modes']:
        for path,sha in m['source_sha256'].items():
            data=(ROOT/path).read_bytes() if path in [old.L0_COPY,prep.CKV_COPY] else old.blob(ROOT,path)
            assert hashlib.sha256(data).hexdigest()==sha


def test_tool_version_read_from_pinned_metadata_no_execution():
    assert PLAN['tool']['metadata_version']=='5.050 2026-07-01'
    assert PLAN['tool']['version_executed'] is False
    for path,sha in PLAN['tool']['pins'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha


def test_actual_cpu_and_address_space_cap_in_child(tmp_path):
    r=child(tmp_path,'import os,resource,json; print(json.dumps([len(os.sched_getaffinity(0)),resource.getrlimit(resource.RLIMIT_AS),resource.getrlimit(resource.RLIMIT_CORE)]))')
    assert r['success']
    n,mem,core=json.loads((tmp_path/'child.log').read_text())
    assert n==2 and mem==[runner.MEMORY,runner.MEMORY] and core==[0,0]


def test_wall_cap_terminates_child(tmp_path):
    r=child(tmp_path,'import time; time.sleep(20)',seconds=0.15)
    assert r['cap_reason']=='WALL_CAP' and not r['success'] and r['seconds']<2


def test_log_cap_keeps_finite_receipt(tmp_path):
    r=child(tmp_path,'import os; os.write(1,b"x"*65536)',log_max=1024)
    assert r['cap_reason']=='LOG_CAP' and not r['success']
    assert (tmp_path/'child.log').stat().st_size<=1024


def test_memory_limit_real_failure_control(tmp_path):
    r=child(tmp_path,'a=bytearray(128*1024**2)',memory=64*1024**2)
    assert not r['success'] and r['returncode']!=0
    assert b'MemoryError' in (tmp_path/'child.log').read_bytes()


def test_failure_receipt_cannot_be_overwritten(tmp_path):
    (tmp_path/'child.log').write_bytes(b'oldfailure')
    with pytest.raises(FileExistsError):child(tmp_path,'print(1)')
    assert (tmp_path/'child.log').read_bytes()==b'oldfailure'


@pytest.mark.parametrize('mutate',[lambda p:p['caps'].update(mode_wall_seconds=61),lambda p:p['modes'][0]['argv'].append('--build'),lambda p:p['modes'][0]['parameters'].update(SUN=16),lambda p:p['modes'][0]['closure']['unresolved'].append('ot_missing')])
def test_runner_rejects_relaxation_build_and_unresolved(mutate):
    p=copy.deepcopy(PLAN);mutate(p)
    with pytest.raises(ValueError):runner.validate_plan(p)


def test_plan_only_cli_never_runs_compiler():
    r=subprocess.run([sys.executable,str(ROOT/'tools/run_observer_capped_lint.py'),'--plan',str(OUT/'plan.json')],capture_output=True,text=True,timeout=5)
    assert r.returncode==0 and 'PLAN ONLY' in r.stdout


def test_mutants_exact_one_occurrence_and_finite_caps():
    for mode in PLAN['modes']:
        text=(ROOT/mode['copy']).read_text()
        for mutant in mode['mutants']:
            assert text.count(mutant['find'])==1
            assert mutant['timeout_seconds']==30
            changed=text.replace(mutant['find'],mutant['replace'])
            assert changed!=text and mutant['expected_diagnostic'] in changed
