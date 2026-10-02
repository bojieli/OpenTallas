import copy
import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('D',ROOT/'tools/h3_distributed_norm_endpoint.py');D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)

def test_32SM_partition_full_rank_and_HC_planes():
    for n in [1,128,4096,5120,32768,4194304]:
        assert sum(D.stripe_words(n,s) for s in range(32))==n
    v={'name':'h','elements_per_rank':[20480]*96,'bits_per_element':32}
    assert [D.counts(v,0,s,'DeepSeek') for s in range(32)]==[1024]*20+[0]*12

def test_exact_gather_and_pair_permutation():
    a=list(range(128));b=list(range(128,256))
    for p in range(8):
        y=D.word_bits('GATHER8',a,b,p)
        assert y[:32]==[8*i+p for i in range(32)] and y[32:]==[0]*96
    for active in (32,16,8,4,2):
        assert D.word_bits('PAIR_EVEN',a,b,active=active)[:active//2]==list(range(0,active,2))
        assert D.word_bits('PAIR_ODD',a,b,active=active)[:active//2]==list(range(1,active,2))

def test_INT_rounding_bit_sequence_and_wrap():
    a=[0xffffffff]*128;b=[1]*128
    assert D.word_bits('IADD',a,b)==[0]*128
    assert D.word_bits('ISUB',[0]*128,b)==a
    for word in [0,0x3f807fff,0x3f808000,0x3f818000,0xbf808000,0x7f800000]:
        v=[word]*128
        hi=D.word_bits('SHR',v,v,phase=1);lsb=D.word_bits('AND',hi,[1]*128)
        bias=D.word_bits('IADD',v,[0x7fff]*128);r=D.word_bits('IADD',bias,lsb)
        got=D.word_bits('AND',r,[0xffff0000]*128)
        assert got==[((word+0x7fff+((word>>16)&1))&0xffffffff)&0xffff0000]*128

def test_root_insert_preserves_other_owners():
    a=list(range(128));b=[999]*128
    for sm in range(20):
        y=D.word_bits('ROOT_INSERT',a,b,active=sm+1)
        assert y[sm]==999 and all(y[i]==a[i] for i in range(128) if i!=sm)

def test_RF_provider_lease_and_same_identity_retire():
    x=D.SpillLease('op7.version2');x.issue_write('op7.version2')
    with pytest.raises(ValueError,match='causal'):x.visible('op7.version2',False)
    with pytest.raises(ValueError,match='early'):x.retire('op7.version2',True,True)
    x.visible('op7.version2',True)
    with pytest.raises(ValueError):x.retire('old',True,True)
    x.retire('op7.version2',True,True)

def test_root_duplicate_stale_and_premature_fence():
    r=D.RootLedger(2);r.offer(0,'v0')
    with pytest.raises(ValueError):r.offer(0,'v0')
    with pytest.raises(ValueError):r.ack(0,'old',True)
    with pytest.raises(ValueError):r.ack(0,'v0',False)
    r.ack(0,'v0',True)
    with pytest.raises(ValueError):r.seal(True)
    r.offer(1,'v1');r.ack(1,'v1',True)
    with pytest.raises(ValueError):r.seal(False)
    r.seal(True);r.restart();assert r.token==1

def test_no_extra_Qwen_reduction_level():
    q=D.norm(4096,False);d=D.norm(5120,True)
    assert len(q['root_tree'])==15 and len(d['root_tree'])==31
    assert q['root_padding_SM_ids']==[] and d['root_padding_SM_ids']==list(range(20,32))
    assert q['native_FP_cycle_candidate']['critical_path_FP_only']==760
    assert d['native_FP_cycle_candidate']['critical_path_FP_only']==1102

def test_allocator_rejects_RF_live_alias():
    homes={'homes':[{'version':'a','rank_group':[0],'SM':0,'birth_pc':0,'retire_pc':2,'home':{'class':'RF','slot_first':32,'vectors':1}},
                    {'version':'b','rank_group':[0],'SM':0,'birth_pc':1,'retire_pc':3,'home':{'class':'RF','slot_first':32,'vectors':1}}]}
    with pytest.raises(ValueError,match='overlap'):D.verify_homes(homes)

def test_unpriced_endpoint_cannot_build_and_no_clock_transfer():
    c=D.cost();assert not c['build_admitted'] and not c['SSFF']
    assert c['replicas_per_rank']==32
    assert c['route_corridor_price']['DeepSeek']['reserved_extra_channel_width_um_candidate']>0
    assert D.abi()['enabled_default'] is False

def test_typed_operand_and_tree_shape_rejections():
    with pytest.raises(ValueError):D.word_bits('GATHER8',[0]*127,[0]*128)
    with pytest.raises(ValueError):D.word_bits('PAIR_EVEN',[0]*128,[0]*128,active=3)


def test_pack_BF16_is_pure_source_bit_movement():
    a=[((0x3f00+i)&0xffff)<<16 for i in range(128)];b=[((0x4000+i)&0xffff)<<16 for i in range(128)]
    packed=D.word_bits('PACK_BF16',a,b)
    words=[x for p in packed for x in (p&0xffff,p>>16)]
    assert words==[x>>16 for x in a+b]
    assert D.norm(5120,True)['matrix_consumer_delivery']['native_xw_beats_all_targets']==10240
