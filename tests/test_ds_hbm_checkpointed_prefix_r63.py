"""Production successor source and compact actual endpoint boundary tests.
No released-checkpoint prefix execution. Exact original constructors retained.
"""
from pathlib import Path
import ast,sys,subprocess,pytest
ROOT=Path(__file__).resolve().parents[1]
@pytest.mark.parametrize('representation',['str','Path'])
def test_successor_source_contract_project_capture_cold_restore(tmp_path,representation):
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
    script=script.replace('import ds_hbm_checkpointed_prefix_r55 as R','import ds_hbm_checkpointed_prefix_r63 as R')
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


def test_successor_preserves_runtime_guards_and_arithmetic():
    old=ast.parse((ROOT/'tools/ds_hbm_checkpointed_prefix_r55.py').read_bytes())
    new=ast.parse((ROOT/'tools/ds_hbm_checkpointed_prefix_r63.py').read_bytes())
    def functions(tree):return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    a,b=functions(old),functions(new)
    assert set(a)==set(b)
    for name in set(a)-{'main','source_gate'}:assert a[name]==b[name],name
    # The native execution loop remains exactly unchanged.
    def loop(tree):
        main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        return next(n for n in ast.walk(main) if isinstance(n,ast.For) and ast.unparse(n.iter)=="native['instructions'][:10]")
    assert ast.dump(loop(old),include_attributes=False)==ast.dump(loop(new),include_attributes=False)
    text=(ROOT/'tools/ds_hbm_checkpointed_prefix_r63.py').read_text()
    assert 'sha(Path(__file__))' in text and 'traceback.format_exc()' in text
    assert "'checkpoint_boundary_stage.json','preflight_source_contract'" in text
    for stage in ['source_contract','project_checkpoint','capture_quiescent','cold_constructors','restore_cold']:
        assert "'checkpoint_boundary_stage.json','"+stage+"'" in text


def test_successor_has_exact_output_root_gate_and_loader():
    text=(ROOT/'tools/ds_hbm_checkpoint_execution_r63.py').read_text()
    assert 'validate_output_root(args.out,plan,projection)' in text
    assert 'enrollment.install()' in text
    assert 'import ds_hbm_checkpointed_prefix_r63 as original' in text
