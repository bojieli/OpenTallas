import copy,gzip,json,sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from ds_hbm_history_codec_r36 import encode,decode
from ds_hbm_source_inputs_r34 import codecs,load,sha
from ds_hbm_history_store_r36 import History
import h3_ds_history_provider_r36 as P
D=ROOT/'results/uarch/ds_hbm_history_provider_r36_20261002'
D30=ROOT/'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002'
D33=ROOT/'results/uarch/ds_hbm_window_retirement_r33_20261002'

@pytest.mark.parametrize('mode,width',[('FP4E4',512),('FP4E8',128)])
def test_source_qdq_codec_roundtrip_zero_sign_extremes(mode,width):
    _,_,V,_=codecs();rng=np.random.default_rng(77);x=rng.standard_normal((64,width)).astype(np.float32)
    q=(V.qdq_fp4_e4m3(x.reshape(-1),16) if mode=='FP4E4' else V.qdq_fp4_e8m0(x.reshape(-1))).reshape(x.shape)
    packed,s=encode(q,mode);assert np.array_equal(decode(packed,s,mode).view(np.uint32),q.view(np.uint32))
    z=np.zeros((1,width),np.float32);z[0,1]=-0.;p,s=encode(z,mode);assert np.array_equal(decode(p,s,mode).view(np.uint32),z.view(np.uint32))
    with pytest.raises(ValueError):encode(np.full((1,width),np.nan,np.float32),mode)
    with pytest.raises(ValueError):encode(np.full((1,width),np.float32(.1234567)),mode)

def native():return json.loads(gzip.decompress((D/'inputs/native_history_projection.json.gz').read_bytes()))

def setup(tmp_path,query=False):
    n=native();m=json.loads((D30/'checkpoint_input_manifest.json').read_bytes());m.update(journal_root=str(tmp_path/'journal'),journal_capacity_bytes=(2096*65536+2*131072 if query else 16<<20),history_source_receipt=dict(status='PASS_EXACT_ENTERING_STATE_DIGEST',actual_state_sha256='b59a99c8294625778d28306924067d5bbf706979068579280d6ee40cb24e6782',expected_state_sha256='b59a99c8294625778d28306924067d5bbf706979068579280d6ee40cb24e6782'))
    import os
    state=Path(os.environ.get('DS_HBM_STATE_ROOT','/tmp/kepler-ds-hbm-r35-entering-state'))
    records=json.loads((ROOT/'results/uarch/ds_hbm_checkpoint_payloads_r35_20261002/entering_state_image_hashes.json').read_bytes())
    records=[dict(r,path=str(state/Path(r['path']).name)) for r in records if r['layer']==2 and r['kind'] in (1,2)]
    if not all(Path(r['path']).exists() for r in records):raise FileNotFoundError('regenerate real source state with pinned r35 initializer; no synthetic substitution')
    m['history_images']=records
    rows=json.loads((D30/'finite_state_homes.json').read_bytes())['rows'];homes=[];op=next(o for o in n['instructions'] if o['pc']==121)
    for kind,field in [(1,'compressed'),(2,'index_keys')]:
        r=next(r for r in rows if r['PC']==121 and f'.{field}.L2.' in r['version']);index=len(homes);homes.append(dict(version=r['version'],rank_group=[63],home={'class':'HBM_NATIVE_STATE'},binding=r));w=next(w for w in op['writes'] if w['version']==r['version']);w['home_indices']=[index]
    if query:
        from h3_ds_query_provider_r36 import create_provider
        m['query_field_homes']=json.loads(gzip.decompress((D/'query_field_homes.json.gz').read_bytes()))
        hs=json.loads((D/'inputs/source_query_RF_homes.json').read_bytes());o=next(o for o in n['instructions'] if o['pc']==124)
        for w in o['writes']:
            inds=[]
            for h in hs[w['version']]:inds.append(len(homes));homes.append(h)
            w['home_indices']=inds
        return create_provider(m,n,{},homes),n
    return P.create_provider(m,n,{},homes),n

def test_actual_writer_receipts_to_selectedKV_native_consumer(tmp_path):
    p,n=setup(tmp_path);op=next(o for o in n['instructions'] if o['pc']==121);rank=63;g=1;grp=524287
    written={};identities={};receipts={}
    for kind,field in [(1,'compressed'),(2,'index_keys')]:
        w=next(w for w in op['writes'] if f'.{field}.L2.' in w['version']);row=p.history.images[2,kind].data[0].copy()
        identity=dict(PC=121,template=op['rank_bindings'][0]['template'],rank=rank,SMs=list(range(32)),version=w['version'],generation=g,home_indices=w['home_indices'])
        written[kind]=row;identities[kind]=identity
        if kind==1:
            before=dict(p.history.pending)
            with pytest.raises(ValueError):p.publish(dict(identity,generation=2),{'data':row},w['native_result_binding'])
            assert p.history.pending==before and not p.state
        receipts[kind]=p.publish(identity,{'data':row},w['native_result_binding'])
        assert [e['event'] for e in receipts[kind]['events']]==['software_backing_visible','consumer_accept','validated_reverse_grant']
        if kind==1:
            assert 2 not in p.history.visible
            with pytest.raises(ValueError):p.history.read(2,1,np.array([grp],np.int64),identity['version'],1)
    assert not p.history.pending and 2 in p.history.visible
    # Duplicate must refuse before changing actual backing or journal.
    state=p.state[63];before=state.events.summary();backing={k:bytes(v) for k,v in state.backing.items()};used=state.events.budget.used
    w=next(w for w in op['writes'] if '.compressed.L2.' in w['version'])
    with pytest.raises(ValueError):p.publish(identities[1],{'data':written[1]},w['native_result_binding'])
    assert state.events.summary()==before and state.events.budget.used==used and {k:bytes(v) for k,v in state.backing.items()}==backing
    # Actual512-row native LOAD, with old rows and the newly visible owner row.
    consumer=next(o for o in n['instructions'] if o['pc']==128);owned=consumer['rank_bindings'][0];key=owned['template'];b=consumer['provider_bindings'][key]
    ids=np.r_[np.arange(511,dtype=np.int64),np.int64(grp)];p.published[b['sel']['version'],0]=ids
    views=p.read_views(consumer,owned,1);assert p.history.leases
    vm=load('r36_native_machine',D33/'inputs/native_machine_class.py.source').Machine
    result=vm(n['templates'][key],{name:r['data'] for name,r in views.items()},None).run()['selected']
    expected=np.concatenate([p.history.images[2,1].data[:511],written[1][None,:]])
    assert np.array_equal(result.view(np.uint32),expected.view(np.uint32))
    with pytest.raises(ValueError):p.release_version(identities[1]['version'],1)
    with pytest.raises(ValueError):p.history.release(next(iter(p.history.leases)),identities[1]['version'],2)
    p.release_views(128,0,1,views);assert not p.history.leases
    # Full source rank0 owned index rows include no invented extra key.
    index=next(o for o in n['instructions'] if o['pc']==125);rb=index['rank_bindings'][0];ik=rb['template'];bind=index['provider_bindings'][ik]
    q=p.history.images[2,2].data[:32].copy();qc,qe=encode(q,'FP4E8')
    # Query bundle is a caller-provided already accepted compound view; this
    # gate does not claim the pending full-program compound-home implementation.
    remaining={name:bind[name] for name in ('key_codes','key_exp','keys')}
    out=p._read_one(index,rb,ik,remaining,1)
    assert out['keys']['data'].shape==(5464,128)
    assert np.array_equal(decode(out['key_codes']['data'],out['key_exp']['data'],'FP4E8').view(np.uint32),out['keys']['data'].view(np.uint32))
    p.release_views(125,0,1,out);assert not p.history.leases
    for engine in p.state.values():engine.events.flush()

def test_actual_compound_query_writes_and_signed_consumer_read(tmp_path):
    p,n=setup(tmp_path,query=True);op=next(o for o in n['instructions'] if o['pc']==124);q=p.history.images[2,2].data[:32].copy();codes,exp=encode(q,'FP4E8');raw_exp=exp.astype(np.int32).view(np.uint32)
    w=next(w for w in op['writes'] if w['native_result_binding']['result']=='iqf');identity=dict(PC=124,version=w['version'],rank=0,generation=1,home_indices=w['home_indices']);fields={'data':q,'query_codes':codes,'query_exp':raw_exp}
    wrong=dict(fields,query_exp=exp)
    with pytest.raises(ValueError):p.publish(identity,wrong,w['native_result_binding'])
    assert not p.state and not p.rf and not p.query_visible
    wrong_id=dict(identity,home_indices=[])
    with pytest.raises(ValueError):p.publish(wrong_id,fields,w['native_result_binding'])
    assert not p.state and not p.rf
    original=p.homes[identity['home_indices'][0]]['word_count']
    p.homes[identity['home_indices'][0]]['word_count']=original+1
    with pytest.raises(ValueError):p.publish(identity,fields,w['native_result_binding'])
    assert not p.state and not p.rf
    p.homes[identity['home_indices'][0]]['word_count']=original
    receipt=p.publish(identity,fields,w['native_result_binding'])
    assert set(receipt['payload_sha256'])==set(fields) and receipt['pending_obligations']==0
    assert [e['event'] for e in receipt['events']]==['software_backing_visible','consumer_accept','validated_reverse_grant']
    assert p.query_homes[identity['version'],0,'query_exp']['dtype']=='U32'
    assert np.array_equal(p._query_access(identity,'query_exp'),raw_exp)
    before=p.state[0].events.summary();used=p.state[0].events.budget.used
    with pytest.raises(ValueError):p.publish(identity,fields,w['native_result_binding'])
    assert p.state[0].events.summary()==before and p.state[0].events.budget.used==used
    consumer=next(o for o in n['instructions'] if o['pc']==125);rb=consumer['rank_bindings'][0];key=rb['template'];bs=consumer['provider_bindings'][key]
    # Exact typed compound subview gate; complete index op awaits all operands.
    views=p._read_one(consumer,rb,key,{name:bs[name] for name in ('query_codes','query_exp')},1)
    assert np.array_equal(views['query_codes']['data'],codes)
    assert views['query_exp']['data'].dtype==np.int64 and np.array_equal(views['query_exp']['data'],exp)
    assert np.any(exp<0) and not views['query_exp']['data'].flags.writeable
    with pytest.raises(ValueError):p.release_version(identity['version'],1)
    p.release_views(125,0,1,views);p.release_version(identity['version'],1)
    with pytest.raises(ValueError):p._read_one(consumer,rb,key,{name:bs[name] for name in ('query_codes','query_exp')},1)
    p.drain(1)

def test_all_compound_homes_count_actual_widths_and_capacity():
    h=json.loads(gzip.decompress((D/'query_field_homes.json.gz').read_bytes()))
    assert len(h['rows'])==1536 and set(h['per_rank_added_bytes'].values())=={69632}
    assert max(h['final_reserved_bytes_per_rank'].values())==29355520<33554432
    for rank in range(96):
        rs=sorted([r for r in h['rows'] if r['rank']==rank],key=lambda r:r['base'])
        assert all(a['base']+a['reservation_bytes']<=b['base'] for a,b in zip(rs,rs[1:]))
        assert all(r['dtype']=='U32' for r in rs)


def test_all_query_home_regeneration_byteexact():
    from ds_hbm_query_homes_r36 import compile_homes
    n=json.loads(gzip.decompress((D/'inputs/all_query_projection.json.gz').read_bytes()))
    initial=json.loads(gzip.decompress((D33/'initial_window_homes.json.gz').read_bytes()))
    expected=json.loads(gzip.decompress((D/'query_field_homes.json.gz').read_bytes()))
    assert compile_homes(n,initial)==expected

def test_streamed_slice_length_without_materialization():
    from h3_ds_query_provider_r36 import SizedEvents
    from hbm_bound_event_journal_r30 import DiskEvents,JournalBudget
    import tempfile
    with tempfile.TemporaryDirectory() as root:
        j=SizedEvents(DiskEvents(JournalBudget(root,131072+65536)))
        for k in range(3):j.append(dict(event='control',sequence=k))
        assert len(j[1:])==2 and [r['sequence'] for r in j[1:]]==[1,2]
        assert len(j[-1:])==1 and j[0]['sequence']==0


def test_manifest_reconciliation_retains_false_admission(tmp_path):
    from ds_hbm_history_manifest_r36 import compose
    base=json.loads((D30/'provider_manifest.json').read_bytes())
    base.update(full_token_launch_ready=True,full_token_inputs_bound=True,full_token_GO=True,hardware_admitted=True)
    receipt=json.loads((ROOT/'results/uarch/ds_hbm_checkpoint_payloads_r35_20261002/entering_state_terminal.json').read_bytes())
    state=tmp_path/'state';state.mkdir()
    records=json.loads((ROOT/'results/uarch/ds_hbm_checkpoint_payloads_r35_20261002/entering_state_image_hashes.json').read_bytes())
    (state/'images.json').write_text(json.dumps(records))
    for r in records:(state/Path(r['path']).name).touch()
    homes=json.loads(gzip.decompress((D/'query_field_homes.json.gz').read_bytes()))
    base['native_program_sha256']=homes['source_native_sha256']
    with pytest.raises(ValueError):compose(dict(base,native_program_sha256='wrong'),receipt,state,homes,tmp_path/'fresh-journal')
    result=compose(base,receipt,state,homes,tmp_path/'fresh-journal')
    assert len(result['history_images'])==8
    assert not any(result[f] for f in ('full_token_launch_ready','full_token_inputs_bound','full_token_GO','hardware_admitted'))
    assert result['journal_root']==str(tmp_path/'fresh-journal') and not (tmp_path/'fresh-journal').exists()
    # Preparation checks presence only; immutable source hashes are enforced by
    # actual provider construction. An empty stand-in can NEVER instantiate it.
    with pytest.raises(Exception):P.create_provider(result,native(),{},[])
