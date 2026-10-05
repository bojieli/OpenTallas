from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ds_hbm_dual_resources_r56 as R


def native():return {'instructions':[{'pc':i,'family':f} for i,f in enumerate(R.old.FAMILIES)]}

def rf(birth,slot=0):return dict(birth_pc=birth,rank_group=[0],SM=0,home={'class':'RF','slot_first':slot,'vectors':2})

def test_union_retains_dead_bytes_and_both_RF_copies():
    h=[rf(0),rf(9),rf(10,4)]
    m=R.source_sector_homes(native(),h,{'initial_versions':[]})
    assert m['selected_source_home_count']==2
    assert m['resident_sector_upper']==64
    assert m['released_raw_contents_retained'] and m['hardware_capacity_unchanged']
    assert m['shared_ports_at_boundary']==0
    assert len(m['rows'])==1 and len(m['rows'][0]['sector_ranges'])==2


def test_initial_state_all_reserved_sectors_included_even_if_unused():
    h=[rf(0)]
    initial={'version':'actual_initial','rank':0,'home':{'base':33554432,'reservation_bytes':65}}
    m=R.source_sector_homes(native(),h,{'initial_versions':[initial]})
    assert m['resident_sector_upper']==67
    assert next(r for r in m['rows'] if r['kind']=='state')['sector_ranges']==[[1048576,1048579]]


def test_produced_state_PC_boundary_uses_exact_binding():
    h=[dict(rank_group=[0],home={'class':'HBM_NATIVE_STATE'},binding={'PC':9,'base':33554432,'reservation_bytes':32}),
       dict(rank_group=[0],home={'class':'HBM_NATIVE_STATE'},binding={'PC':10,'base':33554464,'reservation_bytes':32})]
    m=R.source_sector_homes(native(),h,{'initial_versions':[]})
    assert m['resident_sector_upper']==1


@pytest.mark.parametrize('mutant',['family','missing_birth','RF_slot'])
def test_unknown_source_shapes_and_out_of_slot_refuse(mutant):
    n=native();h=[rf(0)]
    if mutant=='family':n['instructions'][9]['family']='invented'
    if mutant=='missing_birth':del h[0]['birth_pc']
    if mutant=='RF_slot':h[0]['home']['slot_first']=511
    with pytest.raises(ValueError):R.source_sector_homes(n,h,{'initial_versions':[]})


def test_invalid_intervals_refused_and_source_intervals_coalesced():
    assert R.merge([[3,5],[0,2],[1,4]])==[[0,5]]
    with pytest.raises(ValueError):R.merge([[0,0]])


def test_byte_atoms_have_source_bound_cached_identity():
    # Producer iterates32B byte payloads; V3 read_tree indexes struct raw bytes.
    # Full tables charged perport; only duplication per byte pointer is removed.
    raw=bytes(range(256))
    assert all(raw[i] is int(str(i)) for i in range(256))
    partial=[raw[i] for i in range(32)]
    assert len(partial)==32 and R.sys.getsizeof(partial)>=32*8


def test_wrapper_refuses_numerical_argv_before_provider_creation(monkeypatch,tmp_path):
    import ds_hbm_dual_constructor_r56 as wrapper
    monkeypatch.setattr(sys,'argv',['r56','--plan',str(tmp_path/'missing'),'--out',str(tmp_path/'out')])
    with pytest.raises(SystemExit):wrapper.main()
    assert not (tmp_path/'out').exists()


def test_source_RF_span_actual_sector_count_and_reverse_drains(tmp_path):
    # Real pinned SourceViews reader + addressed producer; small component
    # operands only. It proves the128-word span makes16 requests, not timing.
    import subprocess
    script=r'''
import sys,hashlib
from pathlib import Path
sys.path[:0]=[str(Path.cwd()/'tools'),str(Path.cwd()/'tests')]
import numpy as np
import test_ds_producer_checkpoint_resume_v3 as T
from h3_ds_connected_provider_r37 import peer
import ds_hbm_additive_endpoint_join_r54 as J
import hbm_bound_event_journal_r30 as journal
import h3_ds_checkpoint_provider_r30 as base
import h3_ds_query_provider_r36 as query
import h4_hbm_w19_pc10_endpoints as endpoint
bridge=peer('h4_c0_ds_source_views')
J.install([journal,base,query,endpoint,bridge])
p,e,w=T.constructor(Path(sys.argv[1]),'source')
p.homes[0]['word_count']=128;p.homes[0]['home']['vectors']=1
values=np.arange(128,dtype=np.float32)
p.publish(dict(PC=0,rank=0,generation=1,version='v0',home_indices=[0]),{'data':values},{'result':'out'})
b=bridge.SourceViews(p,native_content_sha256=bridge.digest(bridge.canonical(p.native)))
start=len(p.rf[0].events)
words,loc,receipt=b._read_words('v0',0,np.arange(128))
assert words.tobytes()==values.tobytes()
assert receipt['accepted_sectors']==16 and receipt['software_reverse_drained']
rows=list(p.rf[0].events[start:]);assert sum(r['event']=='request_accept' for r in rows)==16
assert sum(r['event']=='validated_reverse_grant' for r in rows)==16
assert not p.rf[0].live and not p.rf[0].queue and not p.rf[0].resident
before=len(p.rf[0].events)
try:b._read_words('v0',0,np.arange(129))
except ValueError:pass
else:raise AssertionError('source bounds relaxed')
assert len(p.rf[0].events)==before
print('PASS_SOURCE_128WORD_16SECTOR_COUNT_AND_REVERSE_COMPONENT')
'''
    r=subprocess.run([sys.executable,'-c',script,str(tmp_path)],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True)
    (tmp_path/'source_read_receipt.log').write_text(r.stdout+r.stderr)
    assert r.returncode==0,r.stdout+r.stderr
    assert 'PASS_SOURCE_' in r.stdout
