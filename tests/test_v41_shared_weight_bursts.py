from pathlib import Path
import subprocess
from tools.rtl_chip_v41x_die_smoke import VERILATOR
ROOT=Path(__file__).resolve().parents[1]

def test_shared_weight_bursts_and_ledger(tmp_path):
    paths=['rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv','rtl/chip/ot_chip_v41x_weight_pc_adapter.sv',
           'rtl/chip/ot_chip_v41x_shared_hbm_model.sv','rtl/test/tb_v41_shared_weight_bursts.sv']
    c=subprocess.run([VERILATOR,'--binary','--timing','-Wno-fatal','--top-module','tb_v41_shared_weight_bursts',
                      '--Mdir',str(tmp_path/'obj'),'-j','2',*[str(ROOT/p) for p in paths]],capture_output=True,text=True,timeout=240)
    assert c.returncode==0,c.stdout+c.stderr
    assert '%Warning-LATCH' not in c.stderr,c.stderr
    for bad in (0,1):
        r=subprocess.run([str(tmp_path/'obj/Vtb_v41_shared_weight_bursts'),f'+BADLEDGER={bad}'],capture_output=True,text=True,timeout=30)
        assert r.returncode==0,r.stdout+r.stderr
        assert ('SHARED_BURST_BAD_LEDGER_PASS' if bad else 'SHARED_BURST_PASS') in r.stdout
        print(r.stdout.splitlines()[0])
