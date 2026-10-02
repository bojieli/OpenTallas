import copy,gzip,json,sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from ds_hbm_storage_home_binding_r41 import bind_storage,bound_class,canonical
from h3_ds_checkpoint_provider_r30 import Provider as Original
from hbm_bound_event_journal_r30 import JournalBudget
D=ROOT/'results/uarch/ds_hbm_connected_source_r37_20261002'

def load(p):return json.loads(gzip.decompress(p.read_bytes()))
@pytest.fixture(scope='module')
def bound():
    native=load(ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz')
    homes=load(D/'inputs/actual_DeepSeek_homes.json.gz')['homes']
    manifest=load(D/'inputs/prefix_input_manifest.json.gz')
    return native,homes,manifest,bind_storage(native,homes,manifest)

def test_exact_current_full_directory_arithmetic_unchanged(bound):
    original,homes,m,(n,h,d,r)=bound
    assert len(d['rows'])==4616 and len(h)==len(homes)+4616
    assert h[:len(homes)]==homes and r['arithmetic_unchanged']
    assert max(r['total_reserved_bytes_by_rank'].values())==29355520
    assert r['max_reserved_end']<=67108864
    row=next(x for x in d['rows'] if x['PC']==5 and x['rank']==0)
    assert row['version']=='DeepSeek.5.window.L0.62' and row['base']==33554432
    assert row['shape']==[128,512] and row['bytes']==262144
    assert n['templates']==original['templates']

def test_existing_initial_collision_refused_without_source_mutation(bound):
    n,h,m,_=bound;bad=copy.deepcopy(m)
    next(r for r in bad['initial_versions'] if 'home' in r)['home']['base']=33554432
    before=canonical(n),canonical(h)
    with pytest.raises(ValueError,match='overlap'):bind_storage(n,h,bad)
    assert before==(canonical(n),canonical(h))

@pytest.fixture
def endpoint(bound,tmp_path):
    _,_,m,(n,h,_,_)=bound
    c=bound_class();p=object.__new__(c)
    p.manifest=m;p.revision=m['checkpoint_revision'];p.native=n;p.homes=h;p.generation=m['generation'];p.seq=0;p.locations={};p.views={};p.state={};p.rf={};p.published={};p.source_images={};p.query_visible={}
    # Actual 128x512 F32 window:8192 sector writes+8192 reads,
    #8 events/sector *8 journal page reserve *(640B envelope+64B overhead).
    p.journal_budget=JournalBudget(tmp_path/'journal',131072+2*8192*8*8*(640+64))
    w=next(w for w in n['instructions'][5]['writes'] if not w['version'].endswith('.61') and w['native_result_binding']['result']=='window')
    identity=dict(PC=5,rank=0,generation=p.generation,version=w['version'],home_indices=[i for i in w['home_indices'] if 0 in h[i]['rank_group']])
    yield p,identity,w['native_result_binding']
    p.journal_budget.db.close()

@pytest.mark.parametrize('bad',['home','generation','view'])
def test_prevalidation_refusal_preserves_actual_backing_and_journal(endpoint,bad):
    p,i,v=endpoint;i=copy.deepcopy(i);v=copy.deepcopy(v)
    if bad=='home':i['home_indices']=[]
    if bad=='generation':i['generation']+=1
    if bad=='view':v['result']='win_new'
    before=p.journal_budget.db.total_changes
    with pytest.raises(ValueError):p.publish(i,{'data':np.zeros((128,512),np.float32)},v)
    assert p.state=={} and p.locations=={} and p.journal_budget.db.total_changes==before

def test_actual_state_window_backing_visible_read_lease_and_duplicate(endpoint,bound):
    p,i,v=endpoint
    data=np.arange(128*512,dtype=np.float32).reshape(128,512)
    receipt=p.publish(i,{'data':data},v)
    assert receipt['identity']==i and receipt['pending_obligations']==0
    assert [e['event'] for e in receipt['events']]==['software_backing_visible','consumer_accept','validated_reverse_grant']
    np.testing.assert_array_equal(Original.restore(p,i['version'],0).view(np.uint32),data.view(np.uint32))
    p.views[(8,0,p.generation,1)]={'rows':{'leased_versions':[i['version']]}}
    with pytest.raises(ValueError,match='leased'):Original.release_version(p,i['version'],p.generation)
    before=p.journal_budget.db.total_changes
    with pytest.raises(ValueError,match='duplicate'):p.publish(i,{'data':data},v)
    assert p.journal_budget.db.total_changes==before
    p.views.clear();Original.release_version(p,i['version'],p.generation)
    assert (i['version'],0) not in p.locations
    from ds_hbm_prefix_observed_outputs_r41 import Witness
    witness=Witness(p,bound[0],ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/independent_prefix_expected_outputs.json')
    # This labeled row-order fixture is deliberately not a trained output.
    with pytest.raises(ValueError,match='differs'):witness.observe(i,{'data':data},receipt)
    assert witness.events[-1]['byte_exact'] is False
    with pytest.raises(ValueError,match='no retry'):witness.observe(i,{'data':data},receipt)


def test_independent_full_prefix_reference_joins_every_output(bound,tmp_path):
    from ds_hbm_prefix_observed_outputs_r41 import Witness
    from ds_hbm_finite_state_homes_r30 import output_spec
    original,_,manifest,(native,homes,_,_)=bound
    class ReferenceOwner:pass
    p=ReferenceOwner();p.native=native;p.homes=homes;p.manifest=manifest;p.revision=manifest['checkpoint_revision'];p.generation=manifest['generation'];p.journal_budget=JournalBudget(tmp_path/'compare',131072)
    w=Witness(p,original,ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/independent_prefix_expected_outputs.json')
    assert len(w.expected)==1568
    for (pc,version,rank,generation,field),row in w.expected.items():
        op=native['instructions'][pc]
        owned=next(r for r in op['rank_bindings'] if r['rank']==rank)
        write=next(x for x in op['writes'] if x['version']==version)
        tid=next(b['template'] for b in owned['buffer_programs'] if b['write_version']==version) if owned.get('buffer_programs') else owned['template']
        spec=output_spec(native['templates'][tid],write['native_result_binding']['result'])
        assert spec['shape']==row['shape'] and row['dtype']=='<f4' and field=='data'
        assert generation==p.generation
        assert any(rank in homes[i]['rank_group'] for i in write['home_indices'])
    with pytest.raises(ValueError,match='incomplete'):w.finish()
    p.journal_budget.db.close()
