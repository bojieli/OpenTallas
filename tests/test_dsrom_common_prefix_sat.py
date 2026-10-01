"""New common-family proofs only; existing HDC proofs are not repeated."""
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import prove_dsrom_common_prefix_sat as proof

YOSYS=shutil.which('yosys')

@pytest.mark.parametrize('module,width',[(m,w) for m,widths in proof.SPECS.items() for w in widths])
def test_every_result_bit_and_carry_for_all_binary_inputs(tmp_path,module,width):
    assert YOSYS,'Yosys required for actual proofs'
    implementation=proof.module_text((ROOT/proof.SOURCE).read_text(),module)
    r=proof.prove_case(YOSYS,implementation,module,width,tmp_path/'sat')
    assert r['verdict']=='PASS' and r['returncode']==0
    assert r['witness_sha256'] is None

@pytest.mark.parametrize('mutation',proof.MUTATIONS)
def test_carry_and_low_result_mutants_have_real_numeric_counterexamples(tmp_path,mutation):
    assert YOSYS,'Yosys required for real negative controls'
    module,width,before,after=proof.MUTATIONS[mutation]
    implementation=proof.module_text((ROOT/proof.SOURCE).read_text(),module)
    assert implementation.count(before)==1
    r=proof.prove_case(YOSYS,implementation.replace(before,after),module,width,tmp_path/'sat')
    assert r['verdict']=='FAIL' and r['returncode']==0 and r['witness_sha256']
    witness=json.loads((tmp_path/'sat'/'witness.json').read_text())
    v={s['name']:int(s['data'][0],2) if 'data' in s else int(s['wave'][0]) for s in witness['signal']}
    assert v['equal']==0
    expected=v['a']+v['b']+v['cin'] if module=='ot_v41_ksadd' else v['a']+v['inc']
    assert v['expected']==expected
    assert v['actual']^v['expected']==(1<<width if 'drop_carry' in mutation else 1)

@pytest.mark.parametrize('rc,log',[(1,'SAT proof finished - model found: FAIL!'),
    (0,'ERROR: parse failure'),(0,'SAT solving timed out!'),(None,'PROOF PROCESS TIMEOUT')])
def test_errors_are_not_successful_negative_controls(rc,log):
    assert proof.classify(rc,log)=='ERROR'

@pytest.mark.parametrize('module,width',[('ot_v41_inc',16),('ot_hdc_ksadd_k',24),('ot_v41_ksadd',True)])
def test_outside_scope_is_not_silently_qualified(module,width):
    with pytest.raises(ValueError,match='scope'):proof.miter(module,width)

def test_retained_negative_cannot_be_overwritten(tmp_path):
    (tmp_path/'yosys.log').write_text('retained negative')
    with pytest.raises(FileExistsError):proof.prove_case('unused','unused','ot_v41_inc',24,tmp_path)
    assert (tmp_path/'yosys.log').read_text()=='retained negative'

def test_manifest_census_and_exact_common_source_are_bound():
    authority=proof.authorities()
    assert authority['manifest_pin']['source_count']==145
    assert authority['source_pin']['sha256']==proof.SOURCE_SHA
    assert authority['compile_binding']['CUT']==379
    assert authority['compile_binding']['actual_fadd_LATENCY']==8
