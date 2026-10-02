import copy,gzip,json,sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_source_inputs_r34 as S
import ds_hbm_group_provider_r34 as G
D=ROOT/'results/uarch/ds_hbm_source_inputs_views_r34_20261002'
D33=ROOT/'results/uarch/ds_hbm_window_retirement_r33_20261002'

def native():return json.loads(gzip.decompress((D/'inputs/group_source_projection.json.gz').read_bytes()))
def template(n):return n['templates'][next(o for o in n['instructions'] if o['pc']==10)['rank_bindings'][0]['template']]
def machine():return S.load('r34_test_machine',D33/'inputs/native_machine_class.py.source').Machine

def test_all40_source_groups_are_bound():
    n=native();new,w=G.lower_native(n);assert len(w)==40
    for r in w:
        t=new['templates'][r['new_template']];assert t['providers']['parts']['shape']==[8,8,1024]
        assert t['resources']['materialized_tensor_workspace_bytes']==524288
        assert t['resources']['streaming_tiling_fit_proved'] is False
        old=n['templates'][r['old_template']]
        assert [(x['op'],x['src'],x['attrs']) for x in old['code']]==[(x['op'],x['src'],x['attrs']) for x in t['code'][:-1]]

@pytest.mark.parametrize('seed',[0,7,42])
def test_bitexact_eight_independent_source_reduction_trees(seed):
    n=native();old=template(n);new=G.lower_template(old);M=machine()
    a=np.random.default_rng(seed).standard_normal((8,8,1024)).astype(np.float32)
    expected=np.concatenate([M(old,{'parts':a[:,g]},None).run()['out'] for g in range(8)])
    actual=M(new,{'parts':a},None).run()['out']
    assert actual.shape==(8192,) and np.array_equal(actual.view(np.uint32),expected.view(np.uint32))
    # Historical single-group output cannot fill the8192-word source destination.
    assert M(old,{'parts':a[:,0]},None).run()['out'].shape==(1024,)

def test_rank_group_contributor_order_and_missing_refusal():
    n=native();producer=next(o for o in n['instructions'] if o['pc']==9);t=G.lower_template(template(n))
    values={r:np.full(1024,r,np.float32) for r in range(64)}
    a=G.gather_parts(lambda v,r:values[r],'v',producer,t['providers']['parts'])
    assert all(np.all(a[j,g]==8*g+j) for j in range(8) for g in range(8))
    assert not a.flags.writeable
    del values[63]
    with pytest.raises(KeyError):G.gather_parts(lambda v,r:values[r],'v',producer,t['providers']['parts'])

def test_wrong_source_row_owner_refused():
    n=native();p=copy.deepcopy(next(o for o in n['instructions'] if o['pc']==9));p['source_op']['rows'][8]=[0,1024]
    with pytest.raises(ValueError):G.gather_parts(lambda v,r:np.zeros(1024,np.float32),'v',p,G.lower_template(template(n))['providers']['parts'])

def test_exact_checkpoint_gained_initializer_no_extra_historical_row(tmp_path):
    class Checkpoint:
        def tensor(self,name):return np.arange(1,513,dtype=np.float32)/512,'BF16'
    images=S.materialize(Checkpoint(),tmp_path/'images');ref,G0,V,init=S.codecs()
    assert len(images)==40
    for layer,r in enumerate(images):
        gain=np.arange(1,513,dtype=np.float32)/512
        rng=np.random.default_rng([20260930,1048576,0,layer])
        expected=V.qdq_fp8(G0.to_bf16(rng.standard_normal((127,512)).astype(np.float32)*gain).reshape(-1)).reshape(127,512)
        actual=np.load(r['path'],allow_pickle=False)
        assert np.array_equal(actual.view(np.uint32),expected.view(np.uint32))
        assert r['whole_reference_state_digest_verified'] is False
    with pytest.raises(ValueError):S.materialize(Checkpoint(),tmp_path/'images')

def homes():return json.loads(gzip.decompress((D33/'initial_window_homes.json.gz').read_bytes()))
def images():return [dict(layer=i,path='external',shape=[127,512],dtype='F32') for i in range(40)]

def test_complete_3840_home_capacity_binding():
    r=S.bind_initial_windows(images(),homes());assert len(r)==3840
    assert sum(x['home']['bytes'] for x in r)==10403840*96

@pytest.mark.parametrize('fault',['overlap','position','generation','extra_row'])
def test_window_home_identity_and_shape_failclosed(fault):
    h=homes()
    if fault=='overlap':h['rows'][96]['base']=h['rows'][0]['base']
    elif fault=='position':h['rows'][0]['logical_positions'][0]-=1
    elif fault=='generation':h['rows'][0]['generation']=2
    else:h['rows'][0]['shape']=[128,512]
    with pytest.raises(ValueError):S.bind_initial_windows(images(),h)

def test_all60_source_static_auxiliaries_and_group_first_rope(tmp_path):
    n=json.loads(gzip.decompress((D/'inputs/static_auxiliary_projection.json.gz').read_bytes()))
    cfg=json.loads((D33/'inputs/inference_config.json').read_bytes())
    b=S.static_auxiliary(n,cfg,tmp_path/'static');assert len(b)==60
    _,_,V,_=S.codecs()
    from h3_ds_checkpoint_provider_r34 import LockedArray
    for key,r in b.items():
        a=LockedArray(r).check();assert list(a.shape)==r['shape'] and a.dtype==np.float32
        name=key.rsplit('/',1)[1]
        if name.startswith('index_rope'):
            first=1048576-cfg['compress_ratios'][r['source_binding']['layer']]
            assert r['source_group_first_position']==first
            f=V.rope_freqs(64,65536,160000,16,32,1)
            expected=V.rope_cs(f,first)[name=='index_rope_sin']
            assert np.array_equal(a.view(np.uint32),expected.view(np.uint32))
            if first!=1048575:assert not np.array_equal(a.view(np.uint32),V.rope_cs(f,1048575)[name=='index_rope_sin'].view(np.uint32))

def test_actual_group_provider_retains_all64_source_leases(tmp_path):
    n,w=G.lower_native(native());m=json.loads((ROOT/'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002/checkpoint_input_manifest.json').read_bytes())
    m.update(journal_root=str(tmp_path),journal_capacity_bytes=16<<20)
    from h3_ds_checkpoint_provider_r34 import create_provider
    p=create_provider(m,n,{},[]);op=next(o for o in n['instructions'] if o['pc']==10);owned=op['rank_bindings'][0];key=owned['template'];b=op['provider_bindings'][key];v=b['parts']['version']
    for rank in range(64):p.published[v,rank]=np.full(1024,rank,np.float32)
    views=p.read_views(op,owned,1)
    assert views['parts']['source_ranks']==list(range(64)) and p._leased(v)
    assert np.all(views['parts']['data'][7,7]==63)
    with pytest.raises(ValueError):p.release_version(v,1)
    p.release_views(op['pc'],owned['rank'],1,views);assert not p._leased(v)

def test_actual_scalar_auxiliary_provider_and_historical_scalar_failure(tmp_path):
    n=json.loads(gzip.decompress((D/'inputs/static_auxiliary_projection.json.gz').read_bytes()))
    cfg=json.loads((D33/'inputs/inference_config.json').read_bytes());bindings=S.static_auxiliary(n,cfg,tmp_path/'images')
    m=json.loads((ROOT/'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002/checkpoint_input_manifest.json').read_bytes());m.update(journal_root=str(tmp_path/'journal'),journal_capacity_bytes=16<<20,view_bindings=bindings)
    from h3_ds_checkpoint_provider_r34 import create_provider
    from h3_ds_checkpoint_provider_r30 import LockedArray as Old
    p=create_provider(m,n,{},[]);op=next(o for o in n['instructions'] if o['pc']==8);owned=op['rank_bindings'][0];key=owned['template'];b={'attn_scale':op['provider_bindings'][key]['attn_scale']}
    views=p._read_one(op,owned,key,b,1);a=views['attn_scale']['data']
    assert a.shape==() and a.dtype==np.float32 and a.view(np.uint32)==np.float32(512**-0.5).view(np.uint32)
    assert not a.flags.writeable
    p.release_views(8,0,1,views)
    with pytest.raises(ValueError):Old(bindings[f'8/{key}/attn_scale'])

@pytest.mark.parametrize('fault',['wrong_generation','missing_home','wrong_shape','outside_aperture'])
def test_actual_provider_prevalidates_initial_home_before_opening_images(tmp_path,fault):
    from h3_ds_checkpoint_provider_r34 import create_provider
    h=homes()['rows'][0];r=dict(h,path=str(tmp_path/'must_not_open.npy'),sha256='absent',home=dict(h))
    if fault=='wrong_generation':r['home']['generation']=2
    elif fault=='missing_home':del r['home']
    elif fault=='wrong_shape':r['home']['shape']=[128,512]
    else:r['home']['base']=67108864
    m=dict(generation=1,initial_versions=[r])
    with pytest.raises(ValueError):create_provider(m,native(),{},[])
    assert not (tmp_path/'must_not_open.npy').exists()

def test_actual_retained_source_image_retires_after_lease_only(tmp_path):
    from h3_ds_checkpoint_provider_r34 import create_provider
    h=homes()['rows'][0];a=np.zeros((127,512),np.float32);path=tmp_path/'retained.npy';np.save(path,a,allow_pickle=False)
    r=dict(h,path=str(path),sha256=S.sha(path),home=dict(h))
    m=json.loads((ROOT/'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002/checkpoint_input_manifest.json').read_bytes());m.update(journal_root=str(tmp_path/'journal'),journal_capacity_bytes=16<<20,initial_versions=[r])
    p=create_provider(m,native(),{},[]);v=r['version'];view={'data':p.restore(v,0),'leased_versions':[v]}
    p.views[5,0,1,0]={'window':view}
    with pytest.raises(ValueError):p.release_version(v,1)
    assert (v,0) in p.source_images and path.exists()
    p.views.clear();p.release_version(v,1)
    assert (v,0) not in p.source_images and (v,0) not in p.published
    with pytest.raises(KeyError):p.restore(v,0)
    assert S.sha(path)==r['sha256']
