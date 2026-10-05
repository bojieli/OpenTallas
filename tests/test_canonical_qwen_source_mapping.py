import pytest
from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement,uint,PhysicalRFSourceAuthority
from tools.gpu_sys.canonical_qwen_transport import TransportError
from tools.h4_qwen_released_provider_delivery import PROGRAM_SHA

@pytest.fixture(scope='module')
def placement():
    return SourcePlacement.released()

def request(home):
    return dict(program_sha256=PROGRAM_SHA,source_key=['RF',home.rank,home.sm,home.first],
                version=home.version,lease='value:'+home.version,source_PC=max(0,home.birth))

def test_complete_census(placement):
    assert len(placement.version_ids)==2027
    assert len(placement.rf)+len(placement.spill)==31232
    assert len(placement.extents)==2*(36*11+7)  # source-defined names, no payload reads

@pytest.mark.parametrize('rank',[0,1])
def test_all_kv_extents(placement,rank):
    for layer in range(36):
        k,v=placement.kv_bases(layer,rank)
        assert v-k==4194304 and k%32==v%32==0
    assert placement.aperture(rank,'KV_provider_state')[1]==37504
    assert placement.aperture(rank,'activation_scratch')[1]==33554432

def test_every_RF_home_and_last_word(placement):
    for h in placement.rf.values():
        r=request(h)
        assert placement.validate_rf(r,True)==h
        key,lane=h.key(h.words-1)
        assert key[:3]==('RF',h.rank,h.sm) and h.first<=key[3]<h.end and 0<=lane<128
        with pytest.raises(TransportError): h.key(h.words)

@pytest.mark.parametrize('field,value',[('program_sha256','wrong'),('lease','wrong'),('version','missing'),('source_PC',1737)])
def test_bad_identity(placement,field,value):
    r=request(next(iter(placement.rf.values())));r[field]=value
    with pytest.raises(TransportError):placement.validate_rf(r,True)

@pytest.mark.parametrize('axis,value',[(1,2),(2,32),(3,512),(3,0)])
def test_bad_RF_location(placement,axis,value):
    r=request(next(iter(placement.rf.values())));r['source_key'][axis]=value
    with pytest.raises(TransportError):placement.validate_rf(r,True)

def test_rank_stripe_is_not_physical_PC_alias():
    a=SourcePlacement.stripe(0,(1<<33)+128)
    b=SourcePlacement.stripe(1,(1<<33)+128)
    assert a['rank_byte']==b['rank_byte']==(1<<33)+128
    assert a['rank']!=b['rank'] and a['stack']==b['stack']

@pytest.mark.parametrize('width',[4,32,34,46])
def test_fullwidth_bounds(width):
    assert uint((1<<width)-1,width,'full')==(1<<width)-1
    for n in (-1,1<<width,True):
        with pytest.raises(TransportError):uint(n,width,'full')

def test_no_software_grant_fallback(placement):
    with pytest.raises(TransportError):PhysicalRFSourceAuthority(None,placement,None)

def test_model_not_qualification(placement):
    m=placement.owner_model()
    assert m['raw_lease_bits']==m['rows']*123
    assert m['GEN']==4 and m['CTAG']==32 and m['NC']==6
    assert m['hardware_build_admitted'] is False


def test_all_home_word_dispatch(placement):
    for (version,rank,sm),h in placement.rf.items():
        local=h.words-1
        global_word=(local//256)*8192+sm*256+local%256
        result=placement.locate_word(version,rank,global_word)
        key,lane=h.key(local)
        assert result['source_key']==list(key) and result['lane']==lane
        assert result['SM_instance']==rank*32+sm


def test_no_wrapped_rank_or_unsigned_alias():
    for rank,byte in [(2,0),(0,1<<34),(-1,0),(0,-1)]:
        with pytest.raises(TransportError):SourcePlacement.stripe(rank,byte)

def test_callback_dictionary_cannot_create_authority(placement):
    class Fake:
        def claim(self,*a):return 0
        def retained(self,*a):return True
    with pytest.raises(TransportError):PhysicalRFSourceAuthority(None,placement,Fake())

def test_allocator_source_owned_costs(placement):
    from tools.gpu_sys.canonical_qwen_source_allocator_model import model
    m=model(placement)
    assert len(m['peak_live_home_contexts_per_SM'])==64
    assert m['existing_native_context']['additional_runtime_lease_state_credit']==0
    assert m['existing_native_context']['general_source_owner'] is False
    for a in m['alternatives']:
        assert a['protected_row_bits']==a['compiled_rows']*a['sealed_words_per_row']*72
        assert a['payload_bits_per_row']==sum(a['row_fields'].values())
        assert a['FF_body_area_mm2_floor']>0 and a['CLK_SS_cap_fF_floor']>0
        assert a['physical_admitted'] is False and a['full_area_mm2'] is None
    assert m['RTL_admitted'] is False

@pytest.mark.parametrize('revision',['r1','r2','r3','r4'])
def test_immutable_model_replay(placement,revision):
    import importlib.util,json
    from pathlib import Path
    import tools.gpu_sys.canonical_qwen_source_allocator_model as current
    root=Path(__file__).resolve().parents[1]
    directory=root/'results/uarch/canonical_qwen_source_mapping_20261003'/revision
    if revision=='r4':module=current
    else:
        spec=importlib.util.spec_from_file_location('allocator_'+revision,directory/'allocator_generator.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=root
    expected=json.loads((directory/'allocator_model.json').read_text())
    assert module.model(placement)==expected

def test_compiled_padding_not_active_only(placement):
    from tools.gpu_sys.canonical_qwen_source_allocator_model import model
    m=model(placement)
    for a in m['alternatives']:
        assert a['compiled_rows']==64*a['maximum_local_rows']
        assert a['padding_rows']==a['compiled_rows']-a['rows']
        assert a['input_replica_fanout']>0 and a['selector_levels']>0
        assert a['outstanding_consumer_capacity_per_context']==1
        assert 'enrollment' in a['outstanding_consumer_policy']
