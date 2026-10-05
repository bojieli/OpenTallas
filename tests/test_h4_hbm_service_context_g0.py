import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import h4_hbm_service_context_g0 as G

@pytest.fixture(scope='module')
def model():return G.build()

def test_geometry_helper_pin_rejects_drift(monkeypatch,tmp_path):
    changed=tmp_path/'geometry_helper.py'
    changed.write_text('unreviewed geometry constants\n')
    monkeypatch.setattr(G.E,'__file__',str(changed))
    with pytest.raises(ValueError,match='geometry helper source pin mismatch'):
        G.build()

@pytest.mark.parametrize('name',['Qwen','DeepSeek'])
def test_complete_context_area_and_source_gates(model,name):
    m=model['models'][name];s=m['storage']
    assert s['RF_macros_per_SM']==128 and s['shared_macro_count']==2
    assert s['RF_logical_bytes_per_SM']==262144 and s['RF_physical_bytes_per_SM']==524288
    assert s['L2_macros_per_die']==256 and s['L2_bytes_per_die']==8388608
    assert m['area']['new_logic_fits_inside_existing_expanded_reservations']
    assert all(r['fit']for r in m['SM_connector_slots']) and all(r['fit']for r in m['L2_controller_slots'])
    assert all(not r['macro_halo_conflicts']for r in m['L2_controller_slots'])
    assert m['routing']['constructive_cut_screen_pass'] and m['routing']['additional_wide_data_trunk_bits']==0
    assert m['admission']=='FAIL_PHYSICAL_SOURCE_BINDING'
    assert not m['atomic_connector_source_present'] and not m['L2_generic_word_endpoint_source_present']
    assert not m['hardware_admitted'] and not model['hardware_opcode_coverage']

@pytest.mark.parametrize('stack',range(4))
def test_actual_quad_mapping(model,stack):
    q=model['models']['Qwen'];ids=[t['SM']for t in q['source_SM_placement_adapter']if t['source_provider_identity']['stack']==stack]
    assert sorted(ids)==list(range(stack*8,stack*8+8))
    assert q['source_quad_clients'][stack]==list(range(stack*8,stack*8+8))+[32+stack]
    assert len({t['SM']for t in q['source_SM_placement_adapter']})==32

@pytest.mark.parametrize('address',[0,64,65536-64])
def test_shared_boundaries(address):assert G.shared_address(address)['beat']==address//64

@pytest.mark.parametrize('address',[-64,1,65536,2**32])
def test_shared_rejects_unaligned_or_wrap(address):
    with pytest.raises(ValueError):G.shared_address(address)

@pytest.mark.parametrize('address',[0,128,32768-128,32768,262144-128])
def test_l2_all_macro_boundaries(address):
    x=G.L2_words(7,address)
    assert len(x)==4 and [a['word_ordinal']for a in x]==list(range(4))
    assert [a['macro']*1024+a['row']for a in x]==list(range(address//32,address//32+4))
    assert all(a['bank']==7 for a in x)

@pytest.mark.parametrize('address',[-128,1,262144])
def test_l2_rejects_illegal_extent(address):
    with pytest.raises(ValueError):G.L2_words(0,address)

@pytest.fixture
def connector():return G.AtomicConnector(model='Qwen',rank=1,SM=7,generation=12,slice_seats=G.SliceSeats(0))
T=(12,1736,1,1,7)

def test_out_of_order_raw_exception_bits_preserved(connector):
    # Movement copies bit patterns without treating them as FP32 numbers.
    raw=bytes.fromhex('00000080000000000000807f000080ff0100c07f0000803f')
    payload=(raw*6)[:128]
    tag=connector.accept(T,'L2_128',base=1000000,extent=262144,byte_address=1000000,lease='real-home-lease',producer_ref='source/version/producer',producer_bank=2,producer_stack=0, physical_base=0, RF_drained=True, shared_drained=True)
    for word in [3,1,0]:connector.backend_word(T,word,lease='real-home-lease',producer_ref='source/version/producer',global_tag=tag,data=payload[word*32:(word+1)*32])
    with pytest.raises(ValueError):connector.visible(T,'real-home-lease')
    assert not connector.unrelated_RF_shared_ready()
    connector.backend_word(T,2,lease='real-home-lease',producer_ref='source/version/producer',global_tag=tag,data=payload[64:96])
    assert connector.visible(T,'real-home-lease')==payload
    connector.consumer(T)
    with pytest.raises(ValueError):connector.retire(T,reverse_grant=False)
    assert len(connector.pool.active)==1
    connector.retire(T,reverse_grant=True)
    assert not connector.pool.active
    assert [event[0]for event in connector.trace]==G.MODEL_PHASES

@pytest.mark.parametrize('kind',['shared64','L2_128'])
def test_write_requires_all_actual_commits(connector,kind):
    size=64 if kind=='shared64' else 128
    tag=connector.accept(T,kind,base=0,extent=65536 if size==64 else 262144,byte_address=0,lease='lease',producer_ref='mutable/source-home',producer_bank=2 if kind=='L2_128' else None,producer_stack=0 if kind=='L2_128' else None,write=True,payload=bytes(range(size)), physical_base=0, RF_drained=True, shared_drained=True)
    with pytest.raises(ValueError):connector.backend_word(T,0,lease='lease',producer_ref='mutable/source-home',global_tag=tag,committed=False)
    words=1 if size==64 else 4
    for i in range(words):connector.backend_word(T,i,lease='lease',producer_ref='mutable/source-home',global_tag=tag,committed=True)
    assert connector.visible(T,'lease')==bytes(range(size))
    connector.consumer(T);connector.retire(T,reverse_grant=True)

@pytest.mark.parametrize('bad', ['lease','producer','ticket','tag','ordinal'])
def test_wrong_receipt_retains_owner(connector,bad):
    tag=connector.accept(T,'L2_128',base=0,extent=262144,byte_address=0,lease='owned',producer_ref='real-source',producer_bank=0,producer_stack=0, physical_base=0, RF_drained=True, shared_drained=True)
    args=dict(ticket=T,ordinal=0,lease='owned',producer_ref='real-source',global_tag=tag,data=bytes(32))
    if bad=='lease':args['lease']='foreign'
    if bad=='producer':args['producer_ref']='foreign'
    if bad=='ticket':args['ticket']=(13,1736,1,1,7)
    if bad=='tag':args['global_tag']=tag+1
    if bad=='ordinal':args['ordinal']=4
    with pytest.raises(ValueError):connector.backend_word(**args)
    assert connector.owner==T and not connector.complete_set and len(connector.pool.active)==1

def test_seats_total_and_atomic_admission(connector):
    for i in range(512):connector.pool.reserve('KV-real-owner'+str(i),'KV')
    with pytest.raises(ValueError):connector.accept(T,'L2_128',base=0,extent=262144,byte_address=0,lease='real',producer_ref='real',producer_bank=0,producer_stack=0, physical_base=0, RF_drained=True, shared_drained=True)
    assert connector.owner is None and connector.seq==0
    assert len(connector.pool.active)==512

def test_c0_shares_512_not_extra_seats():
    pool=G.SliceSeats(0)
    for sm in range(8):pool.reserve((1,0,1,0,sm),'C0')
    for i in range(504):pool.reserve('KV'+str(i),'KV')
    assert len(pool.active)==512
    with pytest.raises(ValueError):pool.reserve('overflow','KV')
    with pytest.raises(ValueError):pool.reserve((2,0,1,0,0),'C0')

def test_weight_no_ready_path_unchanged(connector):
    assert 'No ready port' in connector.weight_response_ready_contract()
    connector.accept(T,'shared64',base=0,extent=65536,byte_address=0,lease='lease',producer_ref='source', physical_base=0, RF_drained=True, shared_drained=True)
    assert 'always accepts' in connector.weight_response_ready_contract()

@pytest.mark.parametrize('kind',['FP8_PACK','DIV','READ_UNBOUNDED'])
def test_unsupported_operator_rejects_without_allocation(connector,kind):
    with pytest.raises(ValueError):connector.accept(T,kind,base=0,extent=65536,byte_address=0,lease='lease',producer_ref='source', physical_base=0, RF_drained=True, shared_drained=True)
    assert connector.owner is None and not connector.pool.active

def test_positive_finite_latency_and_capacity_price(model):
    x=G.service_cost('L2_128',write=False,request_hops=5,response_hops=5,stall_bound=1,commands_ahead=511)
    assert x['leaf_transactions']==4 and x['leaf_no_stall_ticks']==12
    assert x['bounded_ticks']>x['no_stall_ticks']>0
    with pytest.raises(ValueError):G.service_cost('L2_128',request_hops=0,response_hops=0,stall_bound=-1)
    assert model['tag_contract']['KV_seats_at_full_C0_occupancy']==504
    assert model['tag_contract']['weight_seats_reduced']==0
    assert model['tag_contract']['KV_outstanding_capacity_reduction_fraction']==8/512


@pytest.mark.parametrize('bank,stack',[(None,0),(0,None),(0,1),(8,0),(-1,0)])
def test_actual_producer_coordinates_required(connector,bank,stack):
    with pytest.raises(ValueError):connector.accept(T,'L2_128',base=0,extent=262144,byte_address=0,lease='owned',producer_ref='real-source',producer_bank=bank,producer_stack=stack, physical_base=0, RF_drained=True, shared_drained=True)
    assert connector.owner is None and not connector.pool.active

def test_duplicate_word_fault_is_atomic(connector):
    tag=connector.accept(T,'L2_128',base=0,extent=262144,byte_address=0,lease='owned',producer_ref='real-source',producer_bank=0,producer_stack=0, physical_base=0, RF_drained=True, shared_drained=True)
    connector.backend_word(T,0,lease='owned',producer_ref='real-source',global_tag=tag,data=bytes(32))
    with pytest.raises(ValueError):connector.backend_word(T,0,lease='owned',producer_ref='real-source',global_tag=tag,data=bytes(32))
    assert connector.complete_set=={0} and connector.owner==T


@pytest.mark.parametrize('RF_idle,shared_idle',[(False,True),(True,False),(False,False)])
def test_previous_source_transactions_must_drain(connector,RF_idle,shared_idle):
    with pytest.raises(ValueError):connector.accept(T,'shared64',base=0,extent=64,byte_address=0,lease='owned',producer_ref='actual',physical_base=0,RF_drained=RF_idle,shared_drained=shared_idle)
    assert connector.owner is None and connector.seq==0

def test_concrete_physical_base_used(connector):
    connector.accept(T,'shared64',base=1000000,extent=64,byte_address=1000000,lease='owned',producer_ref='actual',physical_base=128,RF_drained=True,shared_drained=True)
    assert connector.word_refs['beat']==2

def test_physical_alias_cannot_hide_behind_logical_extent(connector):
    with pytest.raises(ValueError):connector.accept(T,'shared64',base=1000000,extent=64,byte_address=1000000,lease='owned',producer_ref='actual',physical_base=65536,RF_drained=True,shared_drained=True)
    assert connector.owner is None

def test_cache_writer_range_holds_through_reverse():
    pool=G.SliceSeats(0)
    a=G.AtomicConnector(model='Qwen',rank=0,SM=0,generation=1,slice_seats=pool)
    b=G.AtomicConnector(model='Qwen',rank=0,SM=1,generation=1,slice_seats=pool)
    ta=(1,0,1,0,0);tb=(1,0,1,0,1)
    args=dict(base=0,extent=262144,byte_address=0,lease='actual',producer_ref='actual',producer_bank=0,producer_stack=0,physical_base=0,RF_drained=True,shared_drained=True)
    tag=a.accept(ta,'L2_128',write=True,payload=bytes(128),**args)
    with pytest.raises(ValueError):b.accept(tb,'L2_128',**args)
    assert b.owner is None and len(pool.active)==1
    for i in range(4):a.backend_word(ta,i,lease='actual',producer_ref='actual',global_tag=tag,committed=True)
    a.visible(ta,'actual');a.consumer(ta)
    with pytest.raises(ValueError):b.accept(tb,'L2_128',**args)
    a.retire(ta,reverse_grant=True)
    b.accept(tb,'L2_128',**args)
    assert len(pool.active)==1
