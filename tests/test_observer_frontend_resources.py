"""Resource model and finite supervisor controls; no compiler invocation."""
import copy,json,sys,os
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import model_observer_frontend_resources as model
import run_observer_resource_priced_lint as runner
OUT=ROOT/model.OUT
DATA=(OUT/'plan.json').read_bytes();PLAN=json.loads(DATA)

def healthy():
    return dict(memory={'MemAvailable':128*model.GiB,'SwapFree':1024*model.GiB},disk_available_bytes=32*model.GiB,cpu_affinity=list(range(32)),load=[8,8,8],cgroup_ancestors=[{'memory.max':'max','cpu.max':'max 100000'}])

def test_exact_current_original_frontends_pinned():
    records=model.validate_evidence(ROOT)
    assert len(records)==4
    assert max(r['peak_rss_kib'] for r in records)==33379644
    assert max(r['wall_seconds'] for r in records)==244.39
    assert all(r['address_space_peak_unavailable'] and r['tool_at_run_hash_unavailable'] for r in records)

def test_plan_unchanged_real_hierarchy_commands():
    runner.validate_plan(PLAN)
    old=json.loads((ROOT/PLAN['unchanged_plan_path']).read_bytes())
    assert PLAN['modes']==old['modes'] and PLAN['tool']==old['tool']
    assert PLAN['caps']['total_compiler_wall_budget_seconds']==2*600+4*30+5

@pytest.mark.parametrize('mutation',[
 lambda h:h['memory'].update(MemAvailable=95*model.GiB),
 lambda h:h.update(disk_available_bytes=17*model.GiB),
 lambda h:h.update(cpu_affinity=list(range(9))),
 lambda h:h.update(load=[23,0,0]),
 lambda h:h.update(cgroup_ancestors=[{'memory.max':str(100*model.GiB),'memory.current':str(5*model.GiB)}]),
 lambda h:h.update(cgroup_ancestors=[{'cpu.max':'900000 100000'}]),
])
def test_negative_admission_no_swap_credit(mutation):
    h=healthy();mutation(h)
    with pytest.raises(ValueError):model.admit(h)

def test_admission_boundary_and_ancestor():
    h=healthy();h['memory']['MemAvailable']=96*model.GiB;h['disk_available_bytes']=18*model.GiB
    h['cgroup_ancestors'].append({'memory.max':str(100*model.GiB),'memory.current':str(4*model.GiB),'cpu.max':'1000000 100000'})
    assert model.admit(h)

def test_old_go_cannot_authorize_new_budget():
    old=json.loads((ROOT/'results/rtl/parent_observer_structural_GO_20261002/GO.json').read_bytes())
    with pytest.raises(ValueError):runner.require_go(DATA,old)

def test_pending_go_inert():
    with pytest.raises(ValueError):runner.require_go(DATA,json.loads((OUT/'GO.template.json').read_bytes()))

@pytest.mark.parametrize('mutation',[
 lambda p:p['caps'].update(memory_bytes=65*model.GiB),
 lambda p:p['caps'].update(mode_wall_seconds=601),
 lambda p:p['modes'][0]['parameters'].update(SUN=16),
 lambda p:p['modes'][0]['argv'].append('--cc'),
 lambda p:p['modes'][1]['source_sha256'].pop(next(iter(p['modes'][1]['source_sha256']))),
])
def test_unreviewed_change_rejected(mutation):
    p=copy.deepcopy(PLAN);mutation(p)
    with pytest.raises(ValueError):runner.validate_plan(p)

def child(tmp,code,**kw):
    return runner.supervise([sys.executable,'-c',code],tmp,dict(os.environ),tmp/'child.log',kw.pop('seconds',2),**kw)

def test_real_cap_settings_only_small_child(tmp_path):
    r=child(tmp_path,'import os,resource,json;print(json.dumps([len(os.sched_getaffinity(0)),resource.getrlimit(resource.RLIMIT_AS),resource.getrlimit(resource.RLIMIT_CORE)]))')
    assert r['success']; n,mem,core=json.loads((tmp_path/'child.log').read_text())
    assert n==2 and mem==[64*model.GiB]*2 and core==[0,0]

def test_real_memory_failure_small_negative(tmp_path):
    r=child(tmp_path,'a=bytearray(128*1024**2)',memory=64*1024**2)
    assert not r['success'] and b'MemoryError' in (tmp_path/'child.log').read_bytes()

def test_wall_stop(tmp_path):
    r=child(tmp_path,'import time;time.sleep(20)',seconds=.15)
    assert r['cap_reason']=='WALL_CAP' and not r['success']

def test_log_stop(tmp_path):
    r=child(tmp_path,'import os;os.write(1,b"x"*65536)',log_max=1024)
    assert r['cap_reason']=='LOG_CAP' and (tmp_path/'child.log').stat().st_size<=1024

def test_failure_log_preserved(tmp_path):
    (tmp_path/'child.log').write_bytes(b'oldfailure')
    with pytest.raises(FileExistsError):child(tmp_path,'print(1)')
    assert (tmp_path/'child.log').read_bytes()==b'oldfailure'

def test_missing_go_rejects_before_scratch_or_compiler(tmp_path):
    go=tmp_path/'go.json';go.write_text((OUT/'GO.template.json').read_text());scratch=tmp_path/'scratch'
    with pytest.raises(ValueError):runner.execute(ROOT,OUT/'plan.json',go,scratch)
    assert not scratch.exists()

@pytest.mark.parametrize('mutation',[
 lambda r:r[0].update(source_commit='65e2785'),
 lambda r:r[0]['parameters'].update(SUN=16),
 lambda r:r[0].update(peak_rss_kib=1),
 lambda r:r[0]['source_sha256'].update({'rtl/test/v41_runtime/ot_v41_rt_die.sv':'0'*64}),
])
def test_old_geometry_forged_measurement_authority_rejected(tmp_path,mutation):
    import shutil
    dst=tmp_path/model.OUT;shutil.copytree(OUT,dst)
    records=json.loads((dst/'retained_frontends.json').read_bytes());mutation(records)
    (dst/'retained_frontends.json').write_text(json.dumps(records))
    with pytest.raises(ValueError):model.validate_evidence(tmp_path)

def test_insufficient_admission_cannot_invoke_compiler(tmp_path,monkeypatch):
    go=json.loads((OUT/'GO.template.json').read_bytes())
    go.update(decision='GO',reviewer='synthetic admission test',source_cost_and_calibration_limits_reviewed=True,source_ownership_and_guard_provenance_reviewed=True,resource_caps_reviewed=True)
    g=tmp_path/'go.json';g.write_text(json.dumps(go));scratch=tmp_path/'scratch'
    low=healthy();low['memory']['MemAvailable']=1
    monkeypatch.setattr(model,'headroom',lambda:low)
    def unexpected(*a,**k):pytest.fail('compiler must not be invoked')
    monkeypatch.setattr(runner,'supervise',unexpected)
    with pytest.raises(ValueError,match='memory reserve'):runner.execute(ROOT,OUT/'plan.json',g,scratch)
    assert not scratch.exists()

def test_source_bound_selected_unrolled_groups():
    assert model.validate_selected_counts(ROOT)['base_qmul_instances']==1280
    record=json.loads((OUT/'hierarchy_cost.json').read_bytes())
    assert not record['ckv_difference']['exact_same_binding_frontend_measurement']
    assert record['observer']['complete_ast_cost_unavailable']
