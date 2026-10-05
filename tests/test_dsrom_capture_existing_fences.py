import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_existing_fences as F
@pytest.fixture(scope='module')
def nodes():return json.loads(F.A.inputs()['program.json.gz'])['nodes']
def test_twelve_existing_ready_chains(nodes):
 p=F.proof(nodes)
 assert p['all12_proved']
 assert [(r['producer_pc'],r['existing_later_LINQ_ready_fence_pc'],r['consumer_pc']) for r in p['rows']]==[(66,67,70),(67,68,70),(68,69,80),(69,72,80),(72,73,85),(73,79,85),(82,83,90),(83,84,90),(87,88,95),(88,89,95),(92,93,98),(93,94,98)]
def test_final_GU5_fences(nodes):
 r=next(r for r in F.proof(nodes)['rows'] if r['producer_pc']==93)
 assert r['existing_later_LINQ_ready_fence_pc']==94
 assert 97 in r['all_later_LINQ_fences_before_consumer']
 assert 96 in r['collective_allidle_fences']
@pytest.mark.parametrize('kwargs',[{'common_transaction_slot':False},{'ready_gated_by_publication_and_credits':False},{'X_ROM_enabled':False}])
def test_contract_mutants_do_not_inherit_proof(nodes,kwargs):
 assert not F.proof(nodes,**kwargs)['all12_proved']
def test_bypass_final_LINQ_fences_fails(nodes):
 n=copy.deepcopy(nodes)
 for r in n:
  if r.get('scope')==0 and r.get('instruction_index') in (94,97):r['instruction']['qe_mode']=1
 p=F.proof(n)
 assert not next(r for r in p['rows'] if r['producer_pc']==93)['conditional_publication_order_proved']
def test_no_guard_adoption_or_actual_deadline():
 m=F.build()
 assert not m['prospective_SU_guard_selected'] and m['selected_SU_guard_charge_mm2']==0
 assert m['first_consumer_upper_edge'] is None and not m['contextual_PR_admitted']
 assert m['VMlease_retained_through_accepted_read_and_Rplus2']
def context():
 return dict(stage=0,rank=0,expert=383,phase=285,key_word=2151149568,generation=1,user=65536,xversion=7,pc=93)
def eventset():
 keys=['last_owned_VMvisible','last_owned_credit_capture','bank_rearm','core_LINQ_admit','native_LINQ_accept','core_SU_admit','native_SU_accept','first_VM_read_accept']
 pcs=[93,93,93,94,94,98,98,98]
 return {k:dict(logical_provider='one-ROM-transaction',pc=p,edge=i,owned_producer_context=context()) for i,(k,p) in enumerate(zip(keys,pcs))}
def test_enrolled_callback_order_schema():
 assert F.check_accepted_order(eventset(),93,94,98,context())
@pytest.mark.parametrize('mutation',['earlyread','wrongprovider','missingcallback','sameedgecredit','wrongPC','upperuseralias'])
def test_bad_callback_orders_rejected(mutation):
 e=eventset()
 if mutation=='earlyread':e['first_VM_read_accept']['edge']=0
 if mutation=='wrongprovider':e['native_LINQ_accept']['logical_provider']='per-target-bank-only'
 if mutation=='missingcallback':del e['bank_rearm']
 if mutation=='sameedgecredit':e['last_owned_credit_capture']['edge']=0
 if mutation=='wrongPC':e['native_SU_accept']['pc']=95
 if mutation=='upperuseralias':e['bank_rearm']['owned_producer_context']['user']=0
 with pytest.raises(ValueError):F.check_accepted_order(e,93,94,98,context())
