"""Actual frozen W2/W6 source interfaces; backend/drain are control fixtures."""
from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/h3_complete_native_calendar_20261002/c0_command_r8'
RTL=ROOT/'rtl/gpu/hbm_w5_c0_candidate'
@pytest.fixture(scope='module')
def binaries(tmp_path_factory):
    out=tmp_path_factory.mktemp('c0_connected');result={}
    w6=[BASE/'inputs/ot_gpu_w6_secded_pkg.sv',BASE/'inputs/ot_gpu_rf_visibility_fence_w6.sv']
    for top,tb,extra in [('tb','tb_c0_command.sv',[]),('tb_join','tb_c0_w2_w6_join.sv',[BASE/'inputs/ot_hdc_qwen_pc_exact_completion.sv',RTL/'ot_hbm_w5_w2_pc_adapter.sv'])]:
        binary=out/top
        subprocess.run(['iverilog','-g2012','-s',top,'-o',str(binary),*map(str,w6),str(RTL/'ot_hbm_w5_c0_command.sv'),*map(str,extra),str(RTL/tb)],check=True,capture_output=True,text=True)
        result[top]=binary
    return result
@pytest.mark.parametrize('mode',range(9))
def test_command_retention_and_reset(binaries,mode):
    result=subprocess.run(['vvp',str(binaries['tb']),f'+mode={mode}'],check=True,capture_output=True,text=True)
    assert 'PASS' in result.stdout
@pytest.mark.parametrize('mode',range(5))
def test_actual_W2_W6_interface_join(binaries,mode):
    result=subprocess.run(['vvp',str(binaries['tb_join']),f'+mode={mode}'],check=True,capture_output=True,text=True)
    assert 'PASS' in result.stdout

@pytest.mark.parametrize('top,tb,join',[('tb','tb_c0_command.sv',False),('tb_join','tb_c0_w2_w6_join.sv',True)])
def test_disabled_components(tmp_path,top,tb,join):
    paths=[BASE/'inputs/ot_gpu_w6_secded_pkg.sv',BASE/'inputs/ot_gpu_rf_visibility_fence_w6.sv',RTL/'ot_hbm_w5_c0_command.sv']
    if join:paths += [BASE/'inputs/ot_hdc_qwen_pc_exact_completion.sv',RTL/'ot_hbm_w5_w2_pc_adapter.sv']
    binary=tmp_path/top
    subprocess.run(['iverilog','-g2012','-s',top,'-P',f'{top}.ENABLE=0','-o',str(binary),*map(str,paths),str(RTL/tb)],check=True,capture_output=True,text=True)
    result=subprocess.run(['vvp',str(binary)],check=True,capture_output=True,text=True)
    assert 'PASS disabled' in result.stdout
