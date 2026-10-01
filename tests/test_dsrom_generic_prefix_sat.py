"""Separate generic-adder SAT checks; no stand-ins or sequential qualification."""
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import prove_dsrom_generic_prefix_sat as proof

YOSYS = shutil.which('yosys')

@pytest.mark.parametrize('width',proof.WIDTHS)
def test_all_inputs_every_sum_bit_and_carry(tmp_path,width):
    assert YOSYS, 'Yosys required for actual proofs'
    implementation=proof.module_text((ROOT/proof.SOURCE).read_text())
    result=proof.prove_case(YOSYS,implementation,width,tmp_path/'sat')
    assert result['verdict']=='PASS' and result['returncode']==0
    assert result['witness_sha256'] is None

@pytest.mark.parametrize('mutation',proof.MUTATIONS)
def test_carry_and_sum_mutants_fail_with_numerically_verified_witnesses(tmp_path,mutation):
    assert YOSYS, 'Yosys required for actual negative controls'
    before,after=proof.MUTATIONS[mutation]
    implementation=proof.module_text((ROOT/proof.SOURCE).read_text())
    assert implementation.count(before)==1
    result=proof.prove_case(YOSYS,implementation.replace(before,after),48,tmp_path/'sat')
    assert result['verdict']=='FAIL' and result['returncode']==0
    assert result['witness_sha256']
    witness=json.loads((tmp_path/'sat'/'witness.json').read_text())
    values={s['name']:int(s['data'][0],2) if 'data' in s else int(s['wave'][0]) for s in witness['signal']}
    assert values['equal']==0
    assert values['expected']==values['a']+values['b']+values['cin']
    assert values['actual']^values['expected']==(1<<48 if mutation=='generic_drop_carry' else 1)

@pytest.mark.parametrize('rc,log',[(1,'SAT proof finished - model found: FAIL!'),
    (0,'ERROR: parse failure'),(0,'SAT solving timed out!'),(None,'PROOF PROCESS TIMEOUT')])
def test_tool_failures_do_not_count_as_mutant_rejection(rc,log):
    assert proof.classify(rc,log)=='ERROR'

@pytest.mark.parametrize('width',(True,7,53))
def test_unrequested_widths_are_not_qualified(width):
    with pytest.raises(ValueError,match='scope'):proof.miter(width)

def test_retained_logs_cannot_be_overwritten(tmp_path):
    (tmp_path/'yosys.log').write_text('retained negative')
    with pytest.raises(FileExistsError):proof.prove_case('unused','unused',8,tmp_path)
    assert (tmp_path/'yosys.log').read_text()=='retained negative'

def test_first_proof_package_is_byte_identical_to_committed_pin():
    assert len(proof.first_package_pins())==25
