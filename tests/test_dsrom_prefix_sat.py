"""Actual SAT checks of pinned prefix outputs; no FP/sequential qualification."""
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import prove_dsrom_prefix_sat as proof

YOSYS = shutil.which('yosys')

@pytest.mark.parametrize('module,width',[
    (module,width) for module,(_,widths) in proof.SPECS.items() for width in widths
])
def test_all_input_widened_result_including_every_output_bit(tmp_path,module,width):
    assert YOSYS, 'Yosys required for actual combinational proofs'
    source=(ROOT/proof.SPECS[module][0]).read_text()
    result=proof.prove_case(YOSYS,proof.module_text(source,module),module,width,tmp_path/'sat')
    assert result['verdict']=='PASS'
    assert result['returncode']==0
    assert result['witness_sha256'] is None

@pytest.mark.parametrize('mutation',proof.MUTATIONS)
def test_deliberate_carry_and_output_mutants_have_real_SAT_counterexamples(tmp_path,mutation):
    assert YOSYS, 'Yosys required for actual negative controls'
    module,width,before,after=proof.MUTATIONS[mutation]
    original=proof.module_text((ROOT/proof.SPECS[module][0]).read_text(),module)
    assert original.count(before)==1
    result=proof.prove_case(YOSYS,original.replace(before,after),module,width,tmp_path/'sat')
    assert result['verdict']=='FAIL'
    assert result['returncode']==0  # a real SAT counterexample, not a tool crash
    assert result['witness_sha256']
    assert (tmp_path/'sat'/'witness.json').is_file()

@pytest.mark.parametrize('returncode,log',[
    (1,'SAT proof finished - model found: FAIL!'),
    (0,'ERROR: frontend rejected input'),(0,'SAT solving timed out!'),(None,'PROOF PROCESS TIMEOUT'),
])
def test_tool_errors_or_timeouts_never_count_as_mutant_rejection(returncode,log):
    assert proof.classify(returncode,log)=='ERROR'

@pytest.mark.parametrize('module,width',[('ot_hdc_ksa',True),('ot_hdc_ksa',7),('ot_hdc_sk_mul',53)])
def test_no_unrequested_module_or_width_is_silently_qualified(module,width):
    with pytest.raises(ValueError,match='scope'):proof.miter(module,width)

def test_existing_receipt_directory_is_never_overwritten(tmp_path):
    (tmp_path/'yosys.log').write_text('retained failure')
    with pytest.raises(FileExistsError):
        proof.prove_case('unused','unused','ot_hdc_ksa',8,tmp_path)
    assert (tmp_path/'yosys.log').read_text()=='retained failure'
