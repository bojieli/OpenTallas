"""Direct-census proof availability only; active conditional footprint unproved."""
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import prove_dsrom_direct_generic_prefix_sat as proof

YOSYS = shutil.which('yosys')

@pytest.mark.parametrize('module,width',[(m,w) for m,widths in proof.SPECS.items() for w in widths])
def test_all_inputs_complete_add_or_increment_result(tmp_path,module,width):
    assert YOSYS, 'Yosys required for actual proofs'
    implementation=proof.module_text((ROOT/proof.SOURCE).read_text(),module)
    r=proof.prove_case(YOSYS,implementation,module,width,tmp_path/'sat')
    assert r['verdict']=='PASS' and r['returncode']==0
    assert r['witness_sha256'] is None

@pytest.mark.parametrize('mutation',proof.MUTATIONS)
def test_real_carry_and_low_bit_mutants_have_exact_numeric_counterexamples(tmp_path,mutation):
    assert YOSYS, 'Yosys required for negative controls'
    module,width,before,after=proof.MUTATIONS[mutation]
    implementation=proof.module_text((ROOT/proof.SOURCE).read_text(),module)
    assert implementation.count(before)==1
    r=proof.prove_case(YOSYS,implementation.replace(before,after),module,width,tmp_path/'sat')
    assert r['verdict']=='FAIL' and r['returncode']==0 and r['witness_sha256']
    witness=json.loads((tmp_path/'sat'/'witness.json').read_text())
    v={s['name']:int(s['data'][0],2) if 'data' in s else int(s['wave'][0]) for s in witness['signal']}
    assert v['equal']==0
    expected=v['a']+v['b']+v['cin'] if module=='ot_hdc_ksadd_k' else v['a']+v['inc']
    assert v['expected']==expected
    assert v['actual']^v['expected']==(1<<width if 'drop_carry' in mutation else 1)

@pytest.mark.parametrize('rc,log',[(1,'SAT proof finished - model found: FAIL!'),
    (0,'ERROR: parse failure'),(0,'SAT solving timed out!'),(None,'PROOF PROCESS TIMEOUT')])
def test_errors_are_not_successful_negative_controls(rc,log):
    assert proof.classify(rc,log)=='ERROR'

@pytest.mark.parametrize('module,width',[('ot_hdc_inc_k',16),('ot_hdc_ksadd_k',32),('ot_hdc_ksadd_k',True)])
def test_conditional_or_invalid_widths_are_outside_direct_scope(module,width):
    with pytest.raises(ValueError,match='scope'):proof.miter(module,width)

def test_retained_negative_cannot_be_overwritten(tmp_path):
    (tmp_path/'yosys.log').write_text('retained negative')
    with pytest.raises(FileExistsError):proof.prove_case('unused','unused','ot_hdc_inc_k',24,tmp_path)
    assert (tmp_path/'yosys.log').read_text()=='retained negative'

def test_first_package_remains_byte_identical():
    assert len(proof.first_package_pins())==25
