"""Static gate preparation only; no RTL compiler invoked."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import plan_observer_hierarchy_gate as gate
import prepare_simulation_observation_wrapper as observer
OUT=ROOT/gate.OUT
PLAN=json.loads((OUT/'plan.json').read_text())


def test_real_l0_parent_rejects_named_ckv_parameter_statically():
    negative=json.loads((OUT/'static_binding_negative_r2.json').read_text())
    assert 'CKV_SELECTED' not in negative['l0_parameter_names']
    assert negative['verdict']=='STATIC_BINDING_BLOCKER_NOT_COMPILER_VERDICT'
    assert negative['compiler_run'] is False
    assert '.CKV_SELECTED(SIM_OBS_CKV_SELECTED)' in ''.join(negative['source_excerpt'])
    assert negative['old_copy_changed'] is False


def test_protected_observer_exact_original_inverse():
    copy=(ROOT/gate.COPY).read_bytes()
    retained=subprocess.check_output(['git','show','2c867b19139de1086b522cb15213dec80435af33:'+gate.COPY],cwd=ROOT)
    assert copy==retained
    assert hashlib.sha256(copy).hexdigest()==PLAN['observer_sha256']
    assert observer.inverse(copy.decode())==observer.original(ROOT)


@pytest.mark.parametrize('mode',PLAN['modes'],ids=lambda m:m['name'])
def test_both_real_source_closures_are_pinned(mode):
    for path,digest in mode['source_sha256'].items():
        data=(ROOT/path).read_bytes() if path in (gate.COPY,gate.L0_COPY) else gate.blob(ROOT,path)
        assert hashlib.sha256(data).hexdigest()==digest
    assert not mode['closure']['duplicate_definitions']
    assert mode['status']=='NOT_EXECUTED'
    assert mode['cost']['minimum_elaborated_instances']=='UNAVAILABLE_BEFORE_COMPILER'


@pytest.mark.parametrize('mode',PLAN['modes'],ids=lambda m:m['name'])
def test_modes_do_not_mix_parent_definitions(mode):
    files=mode['closure']['files']
    if mode['name']=='WINDOW_actual_L0':
        assert gate.L0_PARENT in files and gate.CKV_PARENT not in files
        assert mode['parameters']['SIM_OBS_CKV_SELECTED']==0
    else:
        assert gate.CKV_PARENT in files and gate.L0_PARENT not in files
        assert mode['parameters']['SIM_OBS_CKV_SELECTED']==1
    assert mode['parameters']['CL_DEPTH']==512  # driver binding, not wrapper default256
    assert mode['parameters']['ROM_PHW']==6
    assert mode['branch_params']['CLK_PS']==1000


@pytest.mark.parametrize('mode',PLAN['modes'],ids=lambda m:m['name'])
def test_frontend_only_command_and_bounded_budget(mode):
    command=mode['command_spec']
    assert '--lint-only' in command
    assert not {'--cc','--build','make','--binary'} & set(command)
    assert '-DV41_ATT_CUT' in command
    budget=PLAN['resource_budget']
    assert budget['memory_max_bytes']==4*1024**3
    assert budget['cpu_affinity_count']==2
    assert budget['per_mode_wall_seconds']==60


def test_minimum_service_closures_use_real_modules():
    window=PLAN['necessary_service_closures']['ot_chip_v41x_window_attn_source']
    ckv=PLAN['necessary_service_closures']['ot_chip_v41x_ckv_die_service']
    assert 'ot_chip_v41x_window_kv_prefetch' in window['modules']
    assert 'ot_chip_v41x_window_refill_schedule' in window['modules']
    assert 'ot_chip_v41x_ckv_sel_fetch' in ckv['modules']
    assert 'ot_chip_v41x_ckv_selected_dma' in ckv['modules']
    assert not window['unresolved_modules']
    assert not ckv['unresolved_modules']


def test_missing_real_dependency_not_silently_stubbed():
    result=gate.closure({'parent.sv':'module root; ot_real_child u(); endmodule'},'root')
    assert result['unresolved_modules']==['ot_real_child']


def test_ambiguous_parent_module_is_reported():
    result=gate.closure({'a.sv':'module root; endmodule','b.sv':'module root; endmodule'},'root')
    assert result['duplicate_definitions']=={'root':['a.sv','b.sv']}


def test_dependencies_do_not_include_comments_or_strings():
    result=gate.closure({'p.sv':'module root; // ot_fake foo();\n initial $display("ot_bad bar()"); endmodule'},'root')
    assert not result['unresolved_modules']


def test_no_compiler_launch_in_plan_tool():
    source=(ROOT/'tools/plan_observer_hierarchy_gate.py').read_text()
    assert "['git','show',SOURCE+':'+path]" in source
    assert 'subprocess.run' not in source
    assert 'Popen' not in source


def test_new_l0_derivative_inverse_and_no_unsupported_actual():
    derivative=(ROOT/gate.L0_COPY).read_text()
    old=(ROOT/gate.COPY).read_text()
    assert gate.inverse_l0(derivative)==old
    assert observer.inverse(gate.inverse_l0(derivative))==observer.original(ROOT)
    assert '.CKV_SELECTED(SIM_OBS_CKV_SELECTED)' not in derivative
    assert 'parameter bit SIM_OBS_ENABLE = 0' in derivative
    assert 'parameter bit SIM_OBS_CKV_SELECTED = 0' in derivative


@pytest.mark.parametrize('mode',PLAN['modes'],ids=lambda m:m['name'])
def test_compile_filelist_excludes_localparam_include_header(mode):
    assert not any(p.endswith('.svh') for p in mode['compile_files'])
    assert (OUT/mode['filelist']).read_text().splitlines()==mode['compile_files']
