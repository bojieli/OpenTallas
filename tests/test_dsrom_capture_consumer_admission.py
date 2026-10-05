import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_consumer_admission as A
@pytest.fixture(scope='module')
def model():return A.build()
def test_source_wait_masks_are_not_producer_read_fences(model):
 c=model['first_W1_W3_consumers']
 assert len(c)==12
 assert sum(x['wait']==2 for x in c)==2 and sum(x['wait']==0 for x in c)==10
 assert not any(x['explicit_ME_wait'] or x['explicit_QE_wait'] for x in c)
def test_distinct_bank_and_address_leases(model):
 assert model['bank_and_VMlease_distinct']
 assert model['one_bank_generation_until_SUread_deadlocks_I66_I67_I70']
 assert model['source_census']['capture_frames_lower_bound']==4
 assert model['source_census']['all_matrix_frames_lower_bound']>=4
 assert model['selected_VMlease_capacity'] is None
 assert model['no_new_payloadseat_or_VM512_lease_assumed']
def test_suppression_and_nonfree_metadata(model):
 assert model['suppress_native_ROM_slots']==list(range(128))
 assert model['capture_minimum_metadata']['metadata_FF']==4*209
 assert model['capture_minimum_metadata']['metadata_50pct_floor_mm2']>0
 assert model['two_metadata_scopes_alternatives_not_additive']
 assert not model['guard_implemented'] and not model['contextual_PR_admitted']
def test_lower_bound_not_fixture_deadline(model):
 assert model['source_core_pc66_to_pc70_native_accept_lower_bound_edges']==24
 assert model['lower_bound_not_deadline']
 assert model['actual_consumer_first_edge'] is None
 assert model['actual_consumer_last_edge'] is None
 assert model['source_census']['exact_peak_accepted_read_and_Rplus2_tail'] is None

def versions():return {66:dict(base=398720,end_exclusive=399296,same_identity=True,VMvisible=True,VMversion_lease_live=True)}
def request():return [dict(producer_pc=66,src=0,address=398720)]
def test_actual_identity_admission():
 assert A.consumer_guard(versions(),request(),True)
 assert not A.consumer_guard(versions(),request(),False)
@pytest.mark.parametrize('field',['same_identity','VMvisible','VMversion_lease_live'])
def test_idle_cannot_replace_read_fence(field):
 v=versions();v[66][field]=False
 assert not A.consumer_guard(v,request(),True)
@pytest.mark.parametrize('change,value',[('producer_pc',67),('src',1),('address',399296),('address',398719),('address',(1<<19)+398720)])
def test_alias_or_nonVM_read_cannot_close_lease(change,value):
 r=request();r[0][change]=value
 assert not A.consumer_guard(versions(),r,True)


def test_positive_ordering_guard_bound_not_zero():
 assert A.guarded_native_accept_lower(24,[420,800])==802
 with pytest.raises(ValueError):A.guarded_native_accept_lower(24,[None])
 with pytest.raises(ValueError):A.guarded_native_accept_lower(None,[420])
