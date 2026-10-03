"""Local RTL gate; no installed parent or endpoint latency qualification."""
import subprocess
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture(scope='module')
def simulator(tmp_path_factory):
    target=tmp_path_factory.mktemp('w5')/'simulation'
    paths=[ROOT/'rtl/gpu/hbm_w5_candidate'/p for p in ('ot_hbm_w5_read_frame.sv','tb_read_frame.sv')]
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(target),*map(str,paths)],check=True,capture_output=True,text=True)
    return target
@pytest.mark.parametrize('mode',range(7))
def test_local_component(simulator,mode):
    result=subprocess.run(['vvp',str(simulator),f'+mode={mode}'],check=True,capture_output=True,text=True)
    assert 'PASS' in result.stdout

def test_disabled(tmp_path):
    paths=[ROOT/'rtl/gpu/hbm_w5_candidate'/p for p in ('ot_hbm_w5_read_frame.sv','tb_read_frame.sv')]
    binary=tmp_path/'disabled'
    subprocess.run(['iverilog','-g2012','-s','tb','-P','tb.ENABLE=0','-o',str(binary),*map(str,paths)],check=True,capture_output=True,text=True)
    result=subprocess.run(['vvp',str(binary)],check=True,capture_output=True,text=True)
    assert 'PASS default-off' in result.stdout
