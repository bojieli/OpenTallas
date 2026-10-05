"""Actual behavioral W service; no shared K/W contention or capacity claim."""
from pathlib import Path
import subprocess
import pytest
from tools.rtl_chip_v41x_die_smoke import VERILATOR
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('width',[24,30])
def test_weight_range_guard(tmp_path,width):
    sources=['rtl/hdc/kv/ot_hdc_hbm_model.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv',
             'rtl/chip/ot_chip_v41x_hbm3e_phy.sv','rtl/test/tb_chip_v41x_weight_range.sv']
    cmd=[VERILATOR,'--binary','--timing','-Wno-fatal','--top-module','tb_chip_v41x_weight_range',
         f'-GW_AW={width}','--Mdir',str(tmp_path/'obj'),'-j','2',*[str(ROOT/p) for p in sources]]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+result.stderr
    result=subprocess.run([str(tmp_path/'obj/Vtb_chip_v41x_weight_range')],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    assert f'WEIGHT_RANGE_PASS width={width}' in result.stdout
