from pathlib import Path
import sys
import ast
import subprocess
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ds_hbm_checkpoint_phases_r69 as P

def test_live_phase_max_not_serial_sum():
    ledger={'retained_candidate_base_bytes':1000,'original_R68_constructor_RAM_bytes':900}
    proof={k:10 for k in P.FIELDS};proof['complete_source_phase_bounds']=True
    value=P.compose(ledger,proof)
    assert value['required_runtime_RAM_bytes']==1050
    assert not value['physical_admission']

@pytest.mark.parametrize('bad',[None,0,-1,1.0,True])
def test_missing_or_guessed_zero_phase_refuses(bad):
    proof={k:10 for k in P.FIELDS};proof['complete_source_phase_bounds']=True
    proof[P.FIELDS[0]]=bad
    with pytest.raises(ValueError,match='positive'):P.compose({},proof)

def test_unreviewed_phase_bounds_refuse():
    with pytest.raises(ValueError,match='complete'):P.compose({}, {})

def test_successor_child_retains_original_execution_and_admission():
    root=Path(__file__).resolve().parents[1]
    new=ast.parse((root/'tools/ds_hbm_pc01_child_r69.py').read_text())
    calls=[ast.unparse(n.func) for n in ast.walk(new) if isinstance(n,ast.Call)]
    for name in ('validate','constructors','e.execute_operation','R.memory_admission',
                 'R.restore_cold','verify_actual_restore','atomic.require_fresh_restore'):
        assert name in calls
    assert calls.count('constructors')==2
    assert 'selected.capture_atomic' in calls and 'helper.capture_quiescent' not in calls
    source=ast.unparse(new)
    assert "len(e.native['instructions']) != 2213" in source
    assert 'len(p.homes) != 290730' in source
    assert "model['inherited_workspace_bytes']" in source

def test_successor_defaultoff_before_any_source_or_provider_read(tmp_path):
    root=Path(__file__).resolve().parents[1]
    value=subprocess.run([sys.executable,str(root/'tools/ds_hbm_pc01_child_r69.py'),
        '--plan',str(tmp_path/'absent-plan'),'--phase-proof',str(tmp_path/'absent-proof')],
        capture_output=True,text=True)
    assert value.returncode!=0 and 'R69 streamed child is default off' in value.stderr
    assert not list(tmp_path.iterdir())
