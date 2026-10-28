"""Exercise actual generated kit contracts and known failure classes without P&R."""
import json
import re
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys
import schema
import kit_preflight as KP


@pytest.fixture
def kit(tmp_path):
    raw = json.loads((Path(__file__).parent/'examples/tiny_plan.json').read_text())
    kd = gen_phys.write_type_kit(schema.Plan(raw), 'src', tmp_path, [])
    # The generated source filelist normally comes from write_phys; supply the
    # actual minimal boundary-register module for this direct write_type fixture.
    # The module is named after the kit DESIGN_NAME: kit_preflight module_closure requires the top to be defined by a
    # VERILOG_FILES source (the old fixed name "top" failed that existing check; HBM-CORES-REBAL-5 10-28).
    cfg=kd/'config.mk'
    top=re.search(r"^export DESIGN_NAME\s*=\s*(\S+)", cfg.read_text(), re.M).group(1)
    (kd/'rtl/top.sv').parent.mkdir(exist_ok=True)
    (kd/'rtl/top.sv').write_text(f'module {top}(input clk, a, output reg y); always @(posedge clk) y<=a; endmodule\n')
    cfg.write_text(cfg.read_text()+'\nexport VERILOG_FILES = /work/rtl/top.sv\n')
    return kd


def test_generated_kit_and_isolated_cli(kit, tmp_path):
    record=KP.check(kit)
    assert record['verdict']=='PASS', record['issues']
    import subprocess
    p=subprocess.run([sys.executable, '-I', str(kit/'kit_preflight.py'), str(kit),
                      '--out',str(tmp_path/'receipt.json')],capture_output=True,text=True)
    assert p.returncode==0, p.stdout+p.stderr
    assert json.loads((tmp_path/'receipt.json').read_text())['deferred']


def test_missing_staged_source_fails(kit):
    (kit/'rtl/top.sv').unlink()
    assert any('unstaged /work/rtl/top.sv' in x for x in KP.check(kit)['issues'])


def test_ff_reference_mismatch_fails_before_route(kit):
    cfg=kit/'config.mk'
    cfg.write_text(cfg.read_text()+'\nexport OT_VCLK_FF = 101.25\n')
    assert any('FF' in x or 'insertion_ff_ps' in x for x in KP.check(kit)['issues'])


def test_cast_mutant_fails(kit):
    (kit/'rtl/top.sv').write_text("module top(input [7:0] a, output [7:0] y); assign y={2'b11,(2'(a+1)^2'(a))}; endmodule")
    assert KP.check(kit)['checks']['yosys_cast_forms']['verdict']=='FAIL'


def test_removed_helper_and_invalid_slice_fail(kit):
    (kit/'lec.py').unlink()
    (kit/'master_slice.json').write_text('{}')
    r=KP.check(kit)
    assert r['checks']['staged_tools']['verdict']=='FAIL'
    assert r['checks']['master_slice']['verdict']=='FAIL'


def test_existing_receipt_never_overwritten(kit,tmp_path):
    out=tmp_path/'old.json';out.write_text('{"verdict":"FAIL"}')
    with pytest.raises(FileExistsError): KP.main([str(kit),'--out',str(out)])
    assert out.read_text()=='{"verdict":"FAIL"}'
