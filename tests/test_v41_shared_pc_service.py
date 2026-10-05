"""Timing-model sector reservation, not complete shared PHY or fixed-QE safety."""
import subprocess
from pathlib import Path
import pytest
from tools.rtl_chip_v41x_die_smoke import VERILATOR
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('num,den',[(0,5),(3,5),(5,8)])
def test_shared_pc_service(tmp_path,num,den):
    cmd=[VERILATOR,'--binary','--timing','-Wno-fatal','--top-module','tb_v41_shared_pc_service',
         f'-GWNUM={num}',f'-GDEN={den}','--Mdir',str(tmp_path/'obj'),'-j','2',
         str(ROOT/'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv'),str(ROOT/'rtl/test/tb_v41_shared_pc_service.sv')]
    b=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
    assert b.returncode==0,b.stdout+b.stderr
    for mode in (0,1,2):
        r=subprocess.run([str(tmp_path/'obj/Vtb_v41_shared_pc_service'),f'+MODE={mode}'],capture_output=True,text=True,timeout=30)
        assert r.returncode==0,r.stdout+r.stderr
        assert f'SHARED_PC_PASS MODE={mode}' in r.stdout
        print(r.stdout.splitlines()[0])
