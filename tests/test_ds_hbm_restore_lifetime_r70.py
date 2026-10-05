"""All-port source budget gate + actual production R63 restore callsite fixture.
Component inputs only; no released full-size constructor or numerical smoke.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests'))
import ds_hbm_checkpoint_phases_r69 as old
import ds_hbm_checkpoint_phases_r70 as phase
import ds_producer_checkpoint_resume_v3 as base
import ds_hbm_checkpointed_prefix_r63 as production
import ds_hbm_streamed_checkpoint_r69 as selected
import ds_hbm_atomic_checkpoint_r67 as atomic
import test_ds_producer_checkpoint_resume_v3 as fixture

def proof():
    p={k:10 for k in old.FIELDS}
    p.update(complete_source_phase_bounds=True,restore_proof_schema=phase.SCHEMA,
        restore_dictionary_tables_complete=True,restored_sector_entry_upper=738048,
        restored_port_count_upper=96,restore_all_port_table_extra_upper_bytes=257100544)
    return p

def test_all_port_table_copy_charged_in_cold_phase_only():
    ledger=phase.source_ledger(ROOT);p=proof();before=dict(p)
    value=phase.compose(ledger,p)
    assert value['phase_increment_peaks']['cold']==257100564
    assert value['phase_increment_peaks']['save']==30
    assert value['required_runtime_RAM_bytes']==43899508682+257100564+20
    assert value['old_largest_only_bytes_not_charged_twice']
    assert not value['physical_admission'] and p==before

def test_old_complete_flag_without_port_proof_refuses():
    p={k:10 for k in old.FIELDS};p['complete_source_phase_bounds']=True
    with pytest.raises(ValueError,match='all-port'):phase.compose(phase.source_ledger(ROOT),p)

@pytest.mark.parametrize('field,value', [('restored_sector_entry_upper',738047),
    ('restored_port_count_upper',95),('restore_all_port_table_extra_upper_bytes',2706176),
    ('restore_dictionary_tables_complete',False)])
def test_incomplete_or_largest_only_refuses(field,value):
    p=proof();p[field]=value
    with pytest.raises(ValueError):phase.compose(phase.source_ledger(ROOT),p)

def test_more_ports_require_more_table_capacity():
    p=proof();p['restored_port_count_upper']=97
    with pytest.raises(ValueError,match='insufficient'):phase.compose(phase.source_ledger(ROOT),p)

def test_actual_child_restores_through_original_production_helper():
    tree=ast.parse((ROOT/'tools/ds_hbm_pc01_child_r70.py').read_text())
    calls=[ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call)]
    assert 'R.restore_cold' in calls and 'selected.restore_cold' not in calls
    assert 'atomic.require_fresh_restore' in calls and 'verify_actual_restore' in calls
    assert 'phases.compose' in calls and 'R.memory_admission' in calls
    assert 'constructors' in calls and 'e.execute_operation' in calls

def test_original_production_restore_actual_subprocess(tmp_path):
    p,e,w=fixture.constructor(tmp_path,'producer',run_stop=2)
    e.last_use={'v0':2212,'v1':2212};e.execute_operation(e.native['instructions'][0])
    w.seen.add((0,'v0',0,1,'data'))
    expected_sha=hashlib.sha256(p.restore('v0',0).tobytes()).hexdigest()
    contract=dict(identity=base.identity(p,e),checkpoint_selection=selected.selection(base))
    cp=tmp_path/'checkpoint'
    selected.capture_atomic(base,e,p,w,boundary_pc=0,destination=cp,
        source_contract=contract,enabled=True)
    closure=json.loads((cp/'state.json').read_text())
    history=closure['historical_journal_inventory']
    base.verify_journal_inventory(history)
    child=subprocess.run([sys.executable,str(Path(__file__)), '--restore-fixture',str(tmp_path),str(cp)],
                         text=True,capture_output=True)
    assert child.returncode==0,child.stdout+child.stderr
    result=json.loads((tmp_path/'production_restore_receipt.json').read_text())
    assert result['actual_RF_sha256']==expected_sha and result['retired']==[0,1]
    assert result['callsite']=='R63.restore_cold -> original V3 verify/restore'
    assert result['last_use_v0']==2212
    base.verify_journal_inventory(history) # no reads/writes on old sealed provider

def restore_fixture(root,cp):
    p,e,w=fixture.constructor(root,'cold',run_stop=2)
    e.last_use={'v0':2212,'v1':2212}
    publication=json.loads((cp/'ATOMIC_COMPLETE.json').read_text())
    atomic.require_fresh_restore(publication)
    actual=json.loads((cp/'actual_observations.json').read_text())
    selected.selection(base) # same hard R2 pin required by actual child enrollment
    verified,restored=production.restore_cold(base,checkpoint=cp,
        source_contract=actual['source_contract'],checkpoint_receipt=publication['producer_receipt'],
        provider=p,engine=e,witness=w,next_pc=1)
    source_sha=hashlib.sha256(p.restore('v0',0).tobytes()).hexdigest()
    e.execute_operation(e.native['instructions'][1])
    (root/'production_restore_receipt.json').write_text(json.dumps(dict(retired=sorted(e.retired),
        actual_RF_sha256=source_sha,last_use_v0=e.last_use['v0'],restore=restored,
        callsite='R63.restore_cold -> original V3 verify/restore',fixture_only=True)))

if __name__=='__main__':
    if sys.argv[1]!='--restore-fixture':raise ValueError('fixture only')
    restore_fixture(Path(sys.argv[2]),Path(sys.argv[3]))
