"""Bounded source/protocol regressions; not actual released-checkpoint smoke."""
import ast,copy,hashlib,json,os,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_pc01_controller_r68 as C


def test_unenrolled_scope_refuses_before_provider_constructor(tmp_path):
    p=tmp_path/'plan';p.write_text('{}')
    with pytest.raises(ValueError,match='enrollment'):C.validate(p,stage='runtime',pc=0)
    assert len(list(tmp_path.iterdir()))==1


def test_full_scope_count_cannot_be_shrunk():
    for n,h,last in ((2,290730,1),(2213,3,1),(2213,290730,10)):
        with pytest.raises(ValueError,match='full-source PC01'):
            C.scope(dict(schema='DS_FULL_SOURCE_PC01_PLAN_R68',full_native_PCs=n,full_homes=h,terminal_PC=last))


def test_child_reuses_literal_constructor_and_inherited_execute():
    tree=ast.parse((ROOT/'tools/ds_hbm_pc01_child_r68.py').read_bytes())
    imports=[n for n in tree.body if isinstance(n,ast.ImportFrom) and n.module=='ds_hbm_per_pc_r67']
    assert len(imports)==1 and {n.name for n in imports[0].names}=={'constructors','verify_actual_restore'}
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    run=[n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='execute_operation']
    assert len(run)==1 and ast.unparse(run[0])=='e.execute_operation(op)'
    text=ast.unparse(main)
    assert 'helper.scope_role_proof' in text and 'helper.data_identity' in text and 'R.restore_cold' in text
    assert 'atomic.require_fresh_restore' in text and 'atomic.capture_atomic' in text
    assert 'w.expected' not in text and 'expected_outputs' not in text


def receipts():
    a=dict(pid=101,retired_PCs=[0],observed_outputs=384)
    b=dict(pid=102,retired_PCs=[0,1],observed_outputs=576,restored_from_actual_producer_pid=101)
    v=dict(pid=103,restored_from_actual_producer_pid=102,actual_restore_exactness=dict(retired_PCs=[0,1],actual_payload_exact=True,live_debts=0,all_owners_drained=True))
    return a,b,v


def test_synthetic_receipt_validator_demands_all_outputs_and_actual_lineage():
    a,b,v=receipts();assert C.finish_smoke(a,b,v,'source')['full_native_PCs']==2213
    b['observed_outputs']=575
    with pytest.raises(ValueError,match='publications'):C.finish_smoke(a,b,v,'source')
    a,b,v=receipts();v['restored_from_actual_producer_pid']=101
    with pytest.raises(ValueError,match='lineage'):C.finish_smoke(a,b,v,'source')
    a,b,v=receipts();v['pid']=a['pid']
    with pytest.raises(ValueError,match='fresh process'):C.finish_smoke(a,b,v,'source')


def proof_case(tmp_path):
    price=dict(required_RAM_bytes=100,required_disk_bytes=200,projection_complete=True)
    model=dict(runtime_projection=price)
    plan=dict(runtime_parent_proof=str(tmp_path/'proof.json'),resolved_output_root='/home/ubuntu/ds-hbm-pc01-r68-run-20261003',component_model_sha256='model',output_root='/home/ubuntu/ds-hbm-pc01-r68-run-20261003')
    p=dict(actual_output_root=plan['resolved_output_root'],physical_membership_verified=True,write_set_source_model_sha256='model',write_set_COW_overlap_reviewed=True,
        allocator_page_upper_bytes=100,filecache_page_upper_bytes=20,page_tables_and_kernel_upper_bytes=5,guest_extra_page_upper_bytes=10,
        physical_new_page_union_upper_bytes=125,other_owned_reservations_and_live_growth_bytes=10,MemAvailable_bytes=135)
    Path(plan['runtime_parent_proof']).write_text(json.dumps(p));return plan,model,p


def test_COW_counted_once_and_guest_parent_not_summed(tmp_path,monkeypatch):
    plan,model,p=proof_case(tmp_path)
    monkeypatch.setattr(C.remote,'fresh_admission',lambda x:dict(available_RAM_bytes=110))
    got=C.page_proof(plan,model,'runtime');assert got['physical_new_page_union_upper_bytes']==125 and got['COW_counted_once']
    p['MemAvailable_bytes']=134;Path(plan['runtime_parent_proof']).write_text(json.dumps(p))
    with pytest.raises(ValueError,match='physical touched-page aggregate'):C.page_proof(plan,model,'runtime')


@pytest.mark.parametrize('field,value,pattern', [('write_set_COW_overlap_reviewed',False,'COW-overlap'),('physical_membership_verified',False,'membership'),('allocator_page_upper_bytes',99,'cannot be lowered'),('physical_new_page_union_upper_bytes',124,'exclusion'),('filecache_page_upper_bytes',None,'inventory')])
def test_missing_page_fields_and_unproved_discount_refused(tmp_path,monkeypatch,field,value,pattern):
    plan,model,p=proof_case(tmp_path);p[field]=value;Path(plan['runtime_parent_proof']).write_text(json.dumps(p))
    monkeypatch.setattr(C.remote,'fresh_admission',lambda x:dict(available_RAM_bytes=99999))
    with pytest.raises(ValueError,match=pattern):C.page_proof(plan,model,'runtime')


def test_restore_with_live_ownership_debt_never_passes():
    a,b,v=receipts();v['actual_restore_exactness']['live_debts']=1
    with pytest.raises(ValueError,match='debts'):C.finish_smoke(a,b,v,'source')


def test_no_runtime_caps_or_retry_fallback():
    tree=ast.parse((ROOT/'tools/ds_hbm_pc01_controller_r68.py').read_bytes())
    waits=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='wait']
    assert len(waits)==1 and not waits[0].args and not waits[0].keywords
    assert 'sched_setaffinity' not in ast.unparse(tree)
    assert 'RLIMIT_AS' not in ast.unparse(tree) and 'RLIMIT_FSIZE' not in ast.unparse(tree)


def test_actual_compact_source_control_codec_keeps_every_frame_and_checksum(tmp_path):
    # Actual source codec, directed control records. No trained operator smoke.
    import h3_complete_native_calendar_successor_r1 as calendar
    budget=calendar.CompactJournalBudget(tmp_path/'journal',4*1024*1024)
    events=calendar.CompactDiskEvents(budget)
    rows=[]
    for rank in range(200):
        event=dict(event='C0_actual_native_numeric_call',record=dict(PC=rank%2,rank=rank%96,
            source_native_stages=32,home_indices=[0,19,512],dtype='<f4',shape=[4,5120],
            generation=1,arithmetic='source',physical_qualified=False),payload_sha256=hashlib.sha256(bytes([rank%256])).hexdigest())
        before=events.path.stat().st_size
        events.append(event);rows.append(event)
    events.flush()
    assert list(events[:])==rows and len(events)==200
    assert events.index_path.stat().st_size==32
    assert events.summary()['event_counts']=={'C0_actual_native_numeric_call':200}
    events.close();budget.db.close()
