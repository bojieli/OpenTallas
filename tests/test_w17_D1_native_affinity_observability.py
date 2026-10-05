import importlib.util,json,re
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('native',ROOT/'tools/w17_D1_native_affinity_observability.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_exact_inverse():
    assert m.inverse((m.EV/'observed_main.cpp').read_text())==(m.EV/'original_main.cpp').read_text()
    m.validate_package()
@pytest.mark.parametrize('change',['topp->eval();|topp->eval(); topp->eval();','contextp->time(topp->nextTimeSlot());|contextp->time(1);','contextp->threads(1);|contextp->threads(2);','contextp->commandArgs(argc, argv);|contextp->commandArgs(0, nullptr);','topp->final();|','if (!topp->eventsPending()) break;|break;'])
def test_schedule_mutants(change):
    old,new=change.split('|')
    s=(m.EV/'observed_main.cpp').read_text()
    assert old in s
    assert m.inverse(s.replace(old,new))!=(m.EV/'original_main.cpp').read_text()
def test_pilot_caps_and_scope():
    p=m.validate_package()
    assert p['caps']==dict(memory=4294967296,swap=0,cpus=[1,2],whole_seconds=90,relink_seconds=60,runtime_seconds=20,reserve_seconds=10,output_bytes=536870912,file_bytes=268435456,log_bytes=16777216)
    assert p['argv']==['+CASE=HEALTHY'] and p['runtime_threads']==1 and p['no_frontend']
    assert p['claim']=='STARTUP_EVAL_COST_ONLY_NO_CORE_CALLBACK_TOKEN_QUALIFICATION'
@pytest.mark.parametrize('field,value',[('approved',False),('single_use',False),('plan_sha256','wrong'),('execution_commit','old'),('scope','CORE_PASS')])
def test_stale_or_broadened_GO(field,value):
    go=dict(approved=True,plan_sha256=m.sha(m.EV/'plan.json'),scope=m.validate_package()['claim'],single_use=True,execution_commit='head')
    go[field]=value
    with pytest.raises(ValueError):m.validate_go(go,'head')
def test_exact_GO():
    m.validate_go(dict(approved=True,plan_sha256=m.sha(m.EV/'plan.json'),scope=m.validate_package()['claim'],single_use=True,execution_commit='head'),'head')
def test_template_disabled():
    assert json.loads((m.EV/'GO.template.json').read_text())['approved'] is False
def test_marker_only_blocks():
    s=(m.EV/'observed_main.cpp').read_text()
    for b in re.findall(r'// D1_OBSERVE_BEGIN\n(.*?)// D1_OBSERVE_END',s,re.S):
        assert not any(x in b for x in ['topp->eval','nextTimeSlot','commandArgs','rst_n','contextp->time(topp','threads('])
def test_archive_preserves_model_member():
    s=(ROOT/'tools/w17_D1_native_affinity_observability.py').read_text()
    assert "'--redefine-sym','main=D1_retained_main'" in s
    assert not any(x in s for x in ['--cc','--build','make -f','shutil.rmtree'])
def test_input_manifest_pins_required_ABI():
    pins=m.load(m.EV/'input_pins.json')
    for name in ['Vtb_D1__ALL.a','observer_dpi.o','verilated.o','verilated_timing.o','Vtb_D1.h','verilated.h','Vtb_D1__main.cpp']:
        assert any(Path(p).name==name for p in pins)
    assert all(len(v['sha256'])==64 and v['bytes']>0 for v in pins.values())
def test_empty_log_unknown_cost():
    v=m.parse_markers('')
    assert v['observed_seconds_per_eval'] is None and v['cycles_per_second'] is None and not v['qualification']
def test_partial_constructor():
    v=m.parse_markers('D1_HOST phase=CONSTRUCTOR_ENTER mono_s=1 mono_ns=0 simtime=0 evals=0\n')
    assert v['phase_seconds']['constructor_seconds'] is None
def test_measured_eval_cost_not_cycle_rate():
    s='D1_HOST phase=EVAL_RETURN mono_s=1 mono_ns=0 simtime=500 evals=1\nD1_HOST phase=EVAL_RETURN mono_s=2 mono_ns=0 simtime=500 evals=2\n'
    v=m.parse_markers(s)
    assert v['observed_seconds_per_eval']==1 and v['cycles_per_second'] is None
@pytest.mark.parametrize('tail',['D1_HOST phase=EVAL_RETURN mono_s=0 mono_ns=0 simtime=500 evals=2','D1_HOST phase=EVAL_RETURN mono_s=2 mono_ns=0 simtime=499 evals=2','D1_HOST phase=EVAL_RETURN mono_s=2 mono_ns=0 simtime=600 evals=0','D1_HOST truncated','D1_HOST phase=EVAL_RETURN mono_s=1 mono_ns=1000000000 simtime=0 evals=1'])
def test_invalid_markers(tail):
    with pytest.raises(ValueError):m.parse_markers('D1_HOST phase=EVAL_RETURN mono_s=1 mono_ns=0 simtime=500 evals=1\n'+tail)
def test_no_delegated_CPU_quota_dependency():
    source=(ROOT/'tools/w17_D1_native_affinity_observability.py').read_text()
    assert "cg/'cpu.max'" not in source
    assert "sorted(os.sched_getaffinity(0))!=[1,2]" in source
    recipe=(m.EV/'review_and_launch.txt').read_text()
    assert 'CPUQuota=' not in recipe and "CPUAffinity='1 2'" in recipe
    assert "kernel_affinity_only_no_quota" in source
def test_original_model_and_ABI_byteidentical():
    old=ROOT/'results/uarch/w17_D1_native_observability_20261002'
    for name in ['original_main.cpp','observed_main.cpp','input_pins.json','tool_versions.json']:
        assert (old/name).read_bytes()==(m.EV/name).read_bytes()
def test_c827_failure_and_plan_preserved():
    protected=m.load(m.EV/'protected_c827_sha256.json')
    for p,h in protected.items():assert m.sha(ROOT/p)==h
    receipt=m.load(m.EV/'c827_rejected_admission_preserved.json')
    assert receipt['compiler_invocations']==receipt['simulations']==0
    assert receipt['status']=='PARENT_REJECTED_ADMISSION_CANDIDATE_NO_RUNTIME'
def test_no_cap_relaxation():
    old=m.load(ROOT/'results/uarch/w17_D1_native_observability_20261002/plan.json')
    new=m.validate_package()
    for k,v in old['caps'].items():
        if k!='cpus':assert new['caps'][k]==v
    assert new['compile_flags']==old['compile_flags'] and new['argv']==old['argv']
def test_full_object_inventory_covers_reused_inputs():
    plan=m.validate_package();inventory=m.load(m.EV/'full_object_inventory.json');pins=m.load(m.EV/'input_pins.json')
    obj=Path(plan['obj'])
    assert len(inventory)==1027
    assert sum(v['bytes'] for v in inventory.values())==1264545073
    for p,v in pins.items():
        if Path(p).is_relative_to(obj):assert inventory[p]==v
    assert m.sha(m.EV/'full_object_inventory.json')==plan['full_object_inventory_sha256']
