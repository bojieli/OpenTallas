"""Exact r37 str failure plus actual finite r34 provider/V3 restore component.
Compact source-class fixture; not full NativeExecution constructor admission.
"""
from pathlib import Path
import sys
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_checkpoint_boundary_r62 as R


def test_exact_old_failure_and_stage_traceback(tmp_path):
    receipt=tmp_path/'stage.json'
    with pytest.raises(AttributeError,match='read_bytes'):
        R.boundary_call(receipt,'source_contract.runner_hash',lambda:R.sha(str(ROOT/'tools/ds_hbm_checkpointed_prefix_r55.py')))
    import json
    got=json.loads(receipt.read_bytes())
    assert got['last_call_stage']=='source_contract.runner_hash'
    assert got['stage_status']=='FAILED'
    assert 'p.read_bytes()' in got['traceback']


@pytest.mark.parametrize('representation',['str','Path'])
def test_source_contract_project_capture_cold_restore(tmp_path,representation):
    # Reuse the original actual endpoint component setup and strict restore controls.
    source=(ROOT/'tests/test_ds_hbm_checkpointed_prefix_r55.py').read_text()
    import ast
    script=next(ast.literal_eval(n.value) for n in ast.parse(source).body
                if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SCRIPT' for t in n.targets))
    old="contract={'identity':C.identity(p,e),'runner_extension':'priced arbitrary source metadata'*8}"
    replacement="""import ds_hbm_checkpoint_boundary_r62 as B
runner=Path(R.__file__);plan=Path.cwd()/'results/uarch/ds_hbm_checkpoint_execution_r58_20261003/runtime_plan.json'
if sys.argv[3]=='str': runner=str(runner);plan=str(plan)
contract=B.boundary_call(root/'boundary.json','source_contract',lambda:B.source_contract(C,p,e,runner_source=runner,source_plan=plan))
assert contract['runner_source_sha256']==R.sha(Path(R.__file__))
assert contract['source_plan_sha256']==R.sha(Path(plan))"""
    assert old in script
    script=script.replace(old,replacement)
    # Track every actual boundary invocation, including the unchanged cold adapter.
    script=script.replace('projection=C.project_checkpoint(e,p,w,boundary_pc=0,destination=dest)',
        "projection=B.boundary_call(root/'boundary.json','project_checkpoint',lambda:C.project_checkpoint(e,p,w,boundary_pc=0,destination=dest))")
    script=script.replace('receipt=C.capture_quiescent(e,p,w,boundary_pc=0,destination=dest,source_contract=contract)',
        "receipt=B.boundary_call(root/'boundary.json','capture_quiescent',lambda:C.capture_quiescent(e,p,w,boundary_pc=0,destination=dest,source_contract=contract))")
    script=script.replace("verified,restored=R.restore_cold(C,checkpoint=dest,source_contract=contract,checkpoint_receipt=receipt,\n provider=p2,engine=e2,witness=w2,next_pc=1)",
        "verified,restored=B.boundary_call(root/'boundary.json','restore_cold',lambda:R.restore_cold(C,checkpoint=dest,source_contract=contract,checkpoint_receipt=receipt,provider=p2,engine=e2,witness=w2,next_pc=1))")
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path),'success',representation],cwd=ROOT,capture_output=True,text=True)
    (tmp_path/'component_receipt.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stdout+result.stderr
    import json
    assert json.loads((tmp_path/'boundary.json').read_bytes())['last_call_stage']=='restore_cold'
    assert json.loads((tmp_path/'boundary.json').read_bytes())['stage_status']=='COMPLETED'


def test_changed_runner_source_not_normalized_away(tmp_path):
    class Helper:
        @staticmethod
        def identity(provider,engine):return {'test_identity':True}
    a=tmp_path/'runner.py';b=tmp_path/'plan.json'
    a.write_text('old');b.write_text('{}')
    first=R.source_contract(Helper,None,None,runner_source=str(a),source_plan=str(b))
    a.write_text('changed')
    second=R.source_contract(Helper,None,None,runner_source=a,source_plan=b)
    assert first['runner_source_sha256']!=second['runner_source_sha256']
    assert first['source_plan_sha256']==second['source_plan_sha256']


def test_exact_runner_hash_adapter_before_prefix():
    script="""import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools'))
import ds_hbm_checkpointed_prefix_r55 as original
import ds_hbm_checkpoint_boundary_r62 as successor
assert type(original.__file__) is str
try: original.sha(original.__file__)
except AttributeError: pass
else: raise AssertionError('old failure missing')
receipt=successor.install_runner_hash_adapter(original)
assert original.sha(original.__file__)==successor.ORIGINAL_R55_SHA256
assert receipt['numerical_launch'] is False
try: successor.install_runner_hash_adapter(original)
except ValueError: pass
else: raise AssertionError('repeat/mutated enrollment accepted')
"""
    result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
