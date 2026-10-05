"""Resource/schema tests only; do not run full native design builds."""
import sys,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from price_w17_owned_progress_parallel_compile import price,BASE

def test_sixteen_workers_measured_margin_with_fleet_reserve():
    p=price(ROOT)
    assert p['workers']==16 and p['CXX_aggregate_cap_GiB']==88
    assert p['fresh_free_RAM_required_GiB']==112
    assert p['two_mode_CPU_only_projection_seconds']<13000
    assert p['compile_cap_sum_seconds']==33600
    assert not p['projection_is_service_or_wall_bound'] and not p['execution_authorized']

def test_only_make_concurrency_and_caps_change():
    old=json.loads((ROOT/BASE/'native_commands.json').read_text())['phases'];new=price(ROOT)['phases']
    assert len(new)==len(old)==16
    for a,b in zip(old,new):
        if a['kind']=='frontend':assert a==b
        else:
            assert [x.replace('-j16','-j2') for x in b['argv']]==a['argv']
            assert b['CPU']==16 and b['aggregate_memory_GiB']==88
    assert price(ROOT)['functional_RTL_changes']==0

@pytest.mark.parametrize('workers',[20,24,48])
def test_larger_concurrency_rejected_with_same_measured_margin(workers):
    with pytest.raises(ValueError):price(ROOT,workers)

def test_target_scope_cannot_transfer_native_helper_credit():
    p=price(ROOT)
    assert len(p['target_mapping_requirements'])==6
    assert not p['native_helper_transfer_credit']
    assert 'aggregate cgroup cap' in p['enforcement']['memory']


def test_actual_supervisor_caps_entire_container_and_readonly_sources(tmp_path):
    import run_w17_owned_progress_compile_phase as run
    plan=price(ROOT);p=plan['phases'][1]
    cmd=run.docker_argv(ROOT,tmp_path,p,plan['container_image'],'test-owned')
    assert cmd[cmd.index('--memory')+1]=='88g'
    assert cmd[cmd.index('--memory-swap')+1]=='88g'
    assert cmd[cmd.index('--cpus')+1]=='16'
    assert '--read-only' in cmd and f'{ROOT}:/source:ro' in cmd
    assert cmd[-len(p['argv']):]==p['argv']
    assert '--lint-only' not in cmd and '--cc' in plan['phases'][0]['argv']


def test_frontend_cap_unchanged(tmp_path):
    import run_w17_owned_progress_compile_phase as run
    p=price(ROOT)['phases'][0];cmd=run.docker_argv(ROOT,tmp_path,p,'sha256:pin','test-owned')
    assert cmd[cmd.index('--memory')+1]=='64g' and cmd[cmd.index('--cpus')+1]=='2'
    assert cmd[cmd.index('--ulimit')+1]==f'as={64<<30}:{64<<30}'


@pytest.mark.parametrize('change',[{'execution_allowed':False},{'scope':'RUNTIME'},{'plan_sha256':'0'*64},{'owner_interface_policy':'SELECT_UNREVIEWED_CANCEL_COPY'}])
def test_fresh_GO_rejects_scope_pin_or_unreviewed_owner_before_compile(tmp_path,change):
    import hashlib
    import run_w17_owned_progress_compile_phase as run
    plan=price(ROOT);pp=tmp_path/'plan.json';pp.write_text(json.dumps(plan))
    go=dict(schema='w17.owned_progress.native_compile_GO.v1',plan_sha256=hashlib.sha256(pp.read_bytes()).hexdigest(),source_commit=plan['source_commit'],scope='NATIVE_COMPILE_ONLY',execution_allowed=True,phase_indices=[0],owner_interface_policy='ORIGINAL_4E_OBSERVATION_ONLY_NO_CANCELLATION_SELECTION')
    go.update(change);gp=tmp_path/'GO.json';gp.write_text(json.dumps(go))
    with pytest.raises(ValueError):run.reviewed(pp,gp,0)
