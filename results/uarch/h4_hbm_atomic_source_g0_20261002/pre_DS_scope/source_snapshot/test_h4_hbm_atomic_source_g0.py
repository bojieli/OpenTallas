import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import h4_hbm_atomic_source_g0 as G

T=(1,14,1,0,0)
BASE=dict(producer='C0',bank=0,address=0,size=128,write=False,lease='source',producer_ref='actual-home')
GU=dict(epoch=7,mapped_epoch=7,row=100,partition_base=96,local_row=4,id=2,column=3)

def pins(**changes):
    p={s:False for s in G.DrainGate.SIGNALS}
    p.update(host_rd_ready=True,host_wr_ready=True,scratch_ready=True);p.update(changes);return p

@pytest.fixture
def fence():return G.BankFence('Qwen',0,0)

@pytest.mark.parametrize('name',['Qwen','DeepSeek'])
def test_composed_slot_and_source_model(name):
    m=G.build();v=m['models'][name]
    assert m['source_ports_verified'] and m['owner_slot_total_bits']<=256 and m['bank_owners_per_slice']==8
    assert v['area_and_constructive_cut_screen_pass'] and len(v['SM_local_mux_slots'])==32
    assert all(s['fit'] and not s['macro_halo_conflicts']for s in v['L2_controller_slots'])
    assert all(s['cut']['demand_tracks']==5336 and s['cut']['margin_tracks']==1864 for s in v['L2_controller_slots'])
    assert not m['implementation_allowed'] and m['admission']=='FAIL_PHYSICAL_SOURCE_BINDING'
    assert not m['latency_contract']['automatic_delta'] and m['latency_contract']['whole_token_ns']is None

@pytest.mark.parametrize('signal',['host_rd_ready','host_wr_ready','scratch_ready','host_rsp_valid','host_ack_valid','simd_done','scratch_done'])
def test_actual_busy_source_signal_prevents_owner(signal):
    d=G.DrainGate();d.request(T)
    assert not d.sample(pins(**{signal:signal.endswith('valid')or signal.endswith('done')}))
    assert d.phase=='drain' and d.controls()['retain_preexisting_completion_sinks']
    assert d.sample(pins()) and d.phase=='owned'

@pytest.mark.parametrize('signal',G.DrainGate.REQUESTS)
def test_unquiesced_source_requests_refuse(signal):
    d=G.DrainGate();d.request(T)
    with pytest.raises(ValueError,match='quiesced'):d.sample(pins(**{signal:True}))

def test_boolean_drained_substitute_refuses():
    d=G.DrainGate();d.request(T)
    with pytest.raises(ValueError,match='observations'):d.sample(dict(RF_drained=True,shared_drained=True))

def test_same_bank_nonoverlap_and_all_producers_serialized(fence):
    fence.reserve(T,**BASE)
    for kind in ['C0','KV','GU']:
        b=dict(BASE,producer=kind,address=128,write=kind=='GU',size=4 if kind=='GU' else 128)
        with pytest.raises(ValueError,match='bank owner busy'):fence.reserve((1,15,2,0,1),**b)
    assert len(fence.live)==1

def test_eight_banks_finite_and_independent(fence):
    for bank in range(8):fence.reserve((1,14,bank+1,0,bank),**dict(BASE,bank=bank))
    assert len(fence.live)==8
    with pytest.raises(ValueError):fence.reserve((1,14,9,0,0),**dict(BASE,bank=8))

@pytest.mark.parametrize('address',[0,32768-128,32768,262144-128])
def test_actual_macro_word_mapping_and_exact_bytes(fence,address):
    fence.reserve(T,**dict(BASE,address=address))
    raw=b''.join(x.to_bytes(4,'little')for x in [0x7fc01234,0x7f800000,0xff800000,0x80000000,0,0x7fffffff,0xffffffff,0x12345678])
    for i in range(4):
        r=fence.word_request(0,T)
        assert r['macro']==(address//32+i)//1024 and r['row']==(address//32+i)%1024 and r['ordinal']==i
        fence.capture(0,T,lease='source',producer_ref='actual-home',clock_edge=i+1,r_ce_captured=True,rdata=raw)
    assert fence.visible(0,T,'source')==raw*4
    fence.consume(0,T);fence.reverse(0,T,grant=True);assert not fence.live

@pytest.mark.parametrize('address',[-128,1,262144,262144-64])
def test_bank_out_of_bounds_refuses(fence,address):
    with pytest.raises(ValueError):fence.reserve(T,**dict(BASE,address=address))
    assert not fence.live

def test_partial_line_and_one_word_pending_refuse(fence):
    fence.reserve(T,**BASE);fence.word_request(0,T)
    with pytest.raises(ValueError,match='in flight'):fence.word_request(0,T)
    with pytest.raises(ValueError,match='all words'):fence.visible(0,T,'source')
    with pytest.raises(ValueError,match='reverse'):fence.reverse(0,T,grant=True)

@pytest.mark.parametrize('change',[dict(lease='stale'),dict(producer_ref='foreign'),dict(clock_edge=0),dict(r_ce_captured=False)])
def test_wrong_backend_receipt_refuses(fence,change):
    fence.reserve(T,**BASE);fence.word_request(0,T)
    args=dict(lease='source',producer_ref='actual-home',clock_edge=1,r_ce_captured=True,rdata=bytes(32));args.update(change)
    with pytest.raises(ValueError):fence.capture(0,T,**args)
    assert fence.live[0]['pending']is not None

def test_GU_source_mask_and_commit_identity(fence):
    f=dict(BASE,producer='GU',address=16,size=4,write=True,GU=GU);fence.reserve(T,**f)
    r=fence.word_request(0,T,data=bytes.fromhex('3412c07f'))
    assert r['w_mask']==0xffffffff<<128 and r['wdata']==bytes.fromhex('3412c07f')*8
    with pytest.raises(ValueError,match='write edge'):fence.capture(0,T,lease='source',producer_ref='actual-home',clock_edge=1)
    fence.capture(0,T,lease='source',producer_ref='actual-home',clock_edge=1,w_ce_accepted=True)
    assert fence.visible(0,T,'source')==dict(commit_v=True,commit_id=2,commit_row=100,commit_epoch=7,column=3)
    assert 0 in fence.live
    fence.consume(0,T);fence.reverse(0,T,grant=True)

@pytest.mark.parametrize('change',[dict(epoch=8),dict(row=99),dict(local_row=5)])
def test_GU_metadata_does_not_infer_physical_address(fence,change):
    with pytest.raises(ValueError,match='mismatch'):fence.reserve(T,**dict(BASE,producer='GU',address=16,size=4,write=True,GU={**GU,**change}))

def test_scalar_read_correct_lane(fence):
    fence.reserve(T,**dict(BASE,producer='KV',address=28,size=4))
    fence.word_request(0,T);fence.capture(0,T,lease='source',producer_ref='actual-home',clock_edge=1,r_ce_captured=True,rdata=bytes(range(32)))
    assert fence.visible(0,T,'source')==bytes(range(28,32))

def test_joined_gateway_preserves_weight_path_and_atomic_release(fence):
    g=G.JoinedGateway(fence,0);packet=dict(rsp_v=True,rsp_tag=1023,rsp_data=bytes(range(128)))
    assert g.bulk_response(packet)is packet
    g.submit(T,**BASE)
    with pytest.raises(ValueError,match='not drained'):g.word_request()
    assert g.bulk_response(packet)is packet and g.sample(pins())
    for i in range(4):
        g.word_request();g.capture(lease='source',producer_ref='actual-home',clock_edge=i+1,r_ce_captured=True,rdata=bytes([i])*32)
    assert g.visible('source')==b''.join(bytes([i])*32 for i in range(4));g.consume()
    with pytest.raises(ValueError):g.retire(all_completion_sinks_drained=True,reverse_grant=False)
    assert g.drain.phase=='owned' and len(fence.live)==1
    g.retire(all_completion_sinks_drained=True,reverse_grant=True)
    assert g.drain.phase=='idle' and not fence.live and g.bulk_response(packet)is packet

def test_blocked_bank_never_acquires_SM_gateway(fence):
    fence.reserve((1,14,1,0,1),**BASE);g=G.JoinedGateway(fence,0)
    with pytest.raises(ValueError,match='busy'):g.submit(T,**BASE)
    assert g.drain.phase=='idle' and g.ticket is None

def test_stale_generation_after_reverse_rejects(fence):
    fence.reserve(T,**dict(BASE,producer='GU',address=16,size=4,write=True,GU=GU))
    fence.word_request(0,T,data=bytes(4));fence.capture(0,T,lease='source',producer_ref='actual-home',clock_edge=1,w_ce_accepted=True)
    fence.visible(0,T,'source');fence.consume(0,T);fence.reverse(0,T,grant=True)
    with pytest.raises(ValueError,match='stale'):fence.reserve(T,**dict(BASE,producer='GU',address=16,size=4,write=True,GU=GU))
