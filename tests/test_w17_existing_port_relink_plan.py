import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from w17_existing_port_relink_plan import build,mapped,BASE

def test_relink_changes_only_source_binding_optin_and_output():
    p=build(ROOT);old=json.loads((ROOT/BASE).read_text())['argv']
    assert p['compiler_argv'][:-1]==[mapped(x) for x in old[:-1]]
    assert p['compiler_argv'][-1]=='/output/v41_existing_port_trace'
    assert sum(x.endswith('.a') for x in p['compiler_argv'])==13
    assert not p['runtime_allowed'] and p['full_frontend_runs']==0

def test_aggregate_caps_and_readonly_bound_inputs():
    p=build(ROOT);cmd=p['future_container_argv']
    assert cmd[cmd.index('--memory')+1]=='4g'
    assert cmd[cmd.index('--memory-swap')+1]=='4g'
    assert cmd[cmd.index('--cpus')+1]=='2'
    assert 'VERIFIED_INPUT_BUNDLE:/inputs:ro' in cmd
    assert p['caps']['wall_seconds']==60 and p['caps']['log_MiB']==2

def test_no_payload_injection_or_new_getters():
    p=build(ROOT)
    assert not p['execution_allowed'] and not p['qualified_provider_counts_available']
    assert all(name.endswith(('.a','.h','.hpp','.inc','.tpp','.cpp')) for name in p['input_sha256'])
    assert all('/images/' not in name and 'checkpoint' not in name for name in p['input_sha256'])


def test_GO_rejects_before_input_reads_or_compiler(tmp_path):
    import run_w17_bounded_existing_port_relink as run
    pp=tmp_path/'plan.json';pp.write_text(json.dumps(build(ROOT)))
    gp=tmp_path/'GO.json';gp.write_text(json.dumps({'execution_allowed':False}))
    import pytest
    with pytest.raises(ValueError,match='GO'):run.validate(pp,gp,tmp_path/'missing')
