import sys,json,shutil
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ds_mtp_accept_rtl_receipt_verify as V
P=V.P.OUT/'runtime_r1'

def test_actual_receipt_strict():assert V.verify(P)['directed_runs']==43

def copy(tmp):
 for p in P.iterdir():
  if p.is_file():shutil.copyfile(p,tmp/p.name)
 return tmp

@pytest.mark.parametrize('kind',['missing_case','fake_positive_marker','fake_negative_marker','mutant_compile_failure','changed_binary','lint_warning'])
def test_receipt_controls_refuse_false_pass(tmp_path,kind):
 d=copy(tmp_path);r=json.loads((d/'record.json').read_text())
 if kind=='missing_case':r['cases'].pop()
 elif kind=='fake_positive_marker':(d/'case_-1.log').write_text('COMPONENT_PASS cycles=2709 cohorts=40\n')
 elif kind=='fake_negative_marker':(d/'case_31.log').write_text('COMPONENT_PASS\n')
 elif kind=='mutant_compile_failure':r['mutant_compile']['rc']=1
 elif kind=='changed_binary':r['binary_sha256']='0'*64
 elif kind=='lint_warning':(d/'lint.log').write_text('%Warning\n')
 (d/'record.json').write_text(json.dumps(r))
 with pytest.raises(AssertionError):V.verify(d)
