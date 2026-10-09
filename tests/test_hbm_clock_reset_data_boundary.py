from pathlib import Path
import subprocess
import shutil
import pytest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'rtl/hbm_accel/control/ot_hbm_clock_reset_data_boundary.sv'

@pytest.mark.skipif(not shutil.which('iverilog'),reason='iverilog unavailable')
@pytest.mark.parametrize('mutant',[None,'raw_intent','direct_ready'])
def test_data_boundary_and_negative_controls(tmp_path,mutant):
    source=SOURCE.read_text()
    if mutant=='raw_intent':
        source=source.replace('assign reset_n[i]=local_reset_n;',
                              'assign reset_n[i]=reset_intent_n[i] & pll_lock & cold_por_n;')
    if mutant=='direct_ready':
        source=source.replace('assign ready=ready_registered;', 'assign ready=sequence_ready;')
    candidate=tmp_path/'candidate.sv';candidate.write_text(source)
    executable=tmp_path/'bench.vvp'
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(executable),str(candidate),
                    str(ROOT/'tests/rtl/tb_hbm_clock_reset_data_boundary.sv')],
                   check=True,capture_output=True,text=True)
    r=subprocess.run(['vvp',str(executable)],capture_output=True,text=True)
    if mutant:
        assert r.returncode!=0,r.stdout+r.stderr
        assert 'oracle' in r.stdout or 'bypass' in r.stdout,r.stdout
    else:
        assert r.returncode==0,r.stdout+r.stderr
        assert 'PASS DATA boundary: 17 endpoints' in r.stdout

@pytest.mark.skipif(not shutil.which('iverilog'),reason='iverilog unavailable')
def test_actual_analog_macro_wrapper_elaborates(tmp_path):
    subprocess.run(['iverilog','-g2012','-s','ot_hbm_clock_reset_data_pll',
                    '-P','ot_hbm_clock_reset_data_pll.ENABLE=1',
                    '-o',str(tmp_path/'production.vvp'),str(SOURCE),
                    str(ROOT/'rtl/hbm_accel/control/ot_hbm_pll_bb.sv')],
                   check=True,capture_output=True,text=True)
