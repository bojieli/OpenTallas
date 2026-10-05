import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from hbm_provider_microvm_r21 import *

def provider(tags=8,write_residence=4):
    return SectorProvider({('Qwen',0):[{'base':0,'bytes':1048576}],('DeepSeek',95):[{'base':0,'bytes':1048576}]},tags=tags,write_residence=write_residence)

def ident(n,sector=0,target='Qwen',rank=0):return Identity(target,rank,2**63+7,17,n,sector)

def test_reserve_before_headpop_and_finite_backpressure():
    p=provider();ts=[p.submit(ident(i,i),True,bytes([i])*32) for i in range(5)]
    for _ in range(4):assert p.issue()
    assert p.resident==4 and not p.issue() and p.queue[0] is ts[4]
    for t in ts:p.wait(t);p.finish(t)
    assert not p.live and not p.queue and p.resident==0
    ev=[e['event'] for e in p.events if e['identity']['serial']==0]
    assert ev.index('write_residence_reserved')<ev.index('software_owned_issue')<ev.index('software_backing_visible')<ev.index('consumer_accept')<ev.index('validated_reverse_grant')

def test_raw_wait_full_address_and_held_return_immutable():
    p=provider();p.seed('Qwen',0,0,bytes(32));w=p.submit(ident(0),True,bytes([9])*32);r=p.submit(ident(1))
    assert p.issue() and not p.issue();p.step();assert p.wait(r)==bytes([9])*32
    w2=p.submit(ident(2),True,bytes([3])*32);p.wait(w2)
    assert r.returned==bytes([9])*32
    p.finish(w);p.finish(r);p.finish(w2)
    p.seed('DeepSeek',95,0,bytes([4])*32)
    assert p.wait(p.submit(ident(3,target='DeepSeek',rank=95)))==bytes([4])*32

def test_read_before_future_write_and_tag_quarantine():
    p=provider(tags=2);p.seed('Qwen',0,0,bytes([2])*32)
    r=p.submit(ident(1));w=p.submit(ident(2),True,bytes([5])*32)
    assert p.issue() and not p.issue();assert p.wait(r)==bytes([2])*32;p.finish(r);p.wait(w);p.finish(w)
    old=w;new=p.submit(ident(3),True,bytes(32));p.wait(new);p.consume(new)
    with pytest.raises(OwnershipFault):p.reverse(new,old.identity,new.tag,old.generation)
    assert new.state=='quarantine' and p.live[new.tag] is new
    with pytest.raises(OwnershipFault):p.reset()

def test_credit_retained_until_grant_and_cancel_no_rollback():
    p=provider(tags=1);t=p.submit(ident(1),True,bytes([6])*32);p.issue();p.cancel(t);p.wait(t)
    assert t.cancelled and p.backing['Qwen',0,0]==[6]*32
    with pytest.raises(Backpressure):p.submit(ident(2))
    p.consume(t);p.reverse(t,t.identity,t.tag,t.generation)
    with pytest.raises(Backpressure):p.submit(ident(2))
    p.step();assert t.state=='released';p.reset()

def setup_vm(target='Qwen',rank=0,tile=128):
    p=provider();s=Storage(p,target,rank,4096,1044480,tile=tile);return p,s,MicroVM(s)

def ins(op,dst,src=(),shape=(),**attrs):return dict(op=op,dst=dst,src=list(src),shape=list(shape),attrs=attrs)

def load_fixture(p,name,base,value,dtype,target='Qwen',rank=0):
    a=np.asarray(value,DTYPE[dtype]);raw=a.tobytes();p.seed(target,rank,base,raw+bytes((-len(raw))%32));return name,Tensor(target,rank,base,a.shape,dtype)

def materialize(s,t):
    chunks=[s.read(t,np.arange(k,min(k+s.tile,t.count),dtype=np.int64)) for k in range(0,t.count,s.tile)]
    return (np.concatenate(chunks) if chunks else np.empty(0,DTYPE[t.dtype])).reshape(t.shape)

def test_bounded_microop_execution_both_targets_and_rounding():
    for target,rank in [('Qwen',0),('DeepSeek',95)]:
        p,s,v=setup_vm(target,rank,tile=31);x=np.arange(257,dtype=np.float32)/7;y=np.float32(.125)
        providers=dict([load_fixture(p,'x',0,x,'F32',target,rank),load_fixture(p,'y',2048,y,'F32',target,rank)])
        program={'source_pc':1730,'code':[ins('LOAD','x',shape=(257,),name='x',dtype='F32'),ins('LOAD','y',name='y',dtype='F32'),ins('FMUL','m',['x','y'],(257,)),ins('FADD','z',['m','x'],(257,))],'outputs':{'out':'z'}}
        out=v.run(program,providers)['out'];actual=materialize(s,out)
        assert np.array_equal(actual.view(np.uint32),(x*y+x).astype(np.float32).view(np.uint32))
        assert s.peak_lanes<=31 and all(e['identity']['pc']==1730 for e in p.events)
        assert not p.live and not p.calendar

def test_i64_codec_carry_modulo_no32bit_truncation():
    p,s,v=setup_vm();x=np.array([2**40+7,-2**40,2**62],np.int64);y=np.array([9,13,17],np.int64)
    providers=dict([load_fixture(p,'x',0,x,'I64'),load_fixture(p,'y',64,y,'I64')])
    program={'code':[ins('LOAD','x',shape=(3,),name='x',dtype='I64'),ins('LOAD','y',shape=(3,),name='y',dtype='I64'),ins('IADD64','z',['x','y'],(3,)),ins('IMOD','r',['z','y'],(3,))],'outputs':{'out':'r','wide':'z'}}
    out=v.run(program,providers)
    assert np.array_equal(materialize(s,out['wide']),x+y)
    assert np.array_equal(materialize(s,out['out']),(x+y)%y)
    assert out['wide'].dtype=='I64'

def test_source_explicit_bf16_integer_sequence():
    p,s,v=setup_vm();x=np.array([1.,1.00390625,1.0078125,0.,-0.],np.float32)
    providers=dict([load_fixture(p,'x',0,x,'F32')])
    code=[ins('LOAD','x',shape=(5,),name='x',dtype='F32'),ins('BITCAST_U','u',['x'],(5,)),ins('CONST','shift',value=16,dtype='U32'),ins('SHR','hi',['u','shift'],(5,)),ins('CONST','one',value=1,dtype='U32'),ins('AND','odd',['hi','one'],(5,)),ins('CONST','bias',value=0x7fff,dtype='U32'),ins('IADD','b',['u','bias'],(5,)),ins('IADD','c',['b','odd'],(5,)),ins('CONST','mask',value=0xffff0000,dtype='U32'),ins('AND','d',['c','mask'],(5,)),ins('BITCAST_F','out',['d'],(5,))]
    out=materialize(s,v.run({'code':code,'outputs':{'y':'out'}},providers)['y'])
    u=x.view(np.uint32);expected=(u+0x7fff+((u>>16)&1))&0xffff0000
    assert np.array_equal(out.view(np.uint32),expected)

def test_exact_DIV_underflow_fault_and_rational_rounding():
    cases=[(0x00800000,0x40000000,0x00400000),(1,0x40000000,0),(3,0x40000000,2),(0x3f800000,0x40400000,0x3eaaaaab),(0x80000000,0x3f800000,0)]
    for a,b,q in cases:assert divide_bits(a,b)==(q,False)
    assert divide_bits(0x7f7fffff,0x00800000)==(0,True)
    assert divide_bits(0x7fc00000,0x3f800000)==(0,True)
    assert divide_bits(0x3f800000,0)==(0,True)

def test_movement_gather_scatter_preserve_order():
    p,s,v=setup_vm(tile=3);x=np.arange(12,dtype=np.float32).reshape(3,4);ids=np.array([2,0],np.int64)
    providers=dict([load_fixture(p,'x',0,x,'F32'),load_fixture(p,'ids',64,ids,'I64')])
    code=[ins('LOAD','x',shape=(3,4),name='x',dtype='F32'),ins('LOAD','ids',shape=(2,),name='ids',dtype='I64'),ins('TAKE','g',['x','ids'],(2,4),axis=0),ins('TRANSPOSE','t',['g'],(4,2),axes=[1,0]),ins('SLICE','sl',['t'],(2,2),axis=0,start=1,stop=3,step=1),ins('CONCAT','out',['sl','sl'],(4,2),axis=0)]
    actual=materialize(s,v.run({'code':code,'outputs':{'out':'out'}},providers)['out'])
    expected=np.concatenate([x[ids].T[1:3],x[ids].T[1:3]],axis=0)
    assert np.array_equal(actual,expected) and s.peak_lanes<=3

def test_undefined_provider_and_unimplemented_opcode_fail():
    p,s,v=setup_vm()
    with pytest.raises(KeyError):v.run({'code':[ins('LOAD','x',shape=(1,),name='missing',dtype='F32')],'outputs':{'x':'x'}},{})
    with pytest.raises(NotImplementedError):v.run({'code':[ins('SOURCE_MACRO_CALLBACK','x')],'outputs':{'x':'x'}},{})
    t=s.allocate((1,),'F32')
    with pytest.raises(OwnershipFault):s.read(t,[0])

def test_fp8_storage_codec_rne_saturation_and_noNaN():
    p,s,v=setup_vm();x=np.array([0.,-0.,1/1024,3/1024,448.,500.,-500.,1.,-1.],np.float32)
    providers=dict([load_fixture(p,'x',0,x,'F32')])
    code=[ins('LOAD','x',shape=x.shape,name='x',dtype='F32'),ins('FP8_PACK','packed',['x'],x.shape),ins('FP8_UNPACK','out',['packed'],x.shape)]
    out=v.run({'code':code,'outputs':{'packed':'packed','out':'out'}},providers)
    assert np.array_equal(materialize(s,out['packed']),[0,0,0,2,126,126,254,56,184])
    assert np.array_equal(materialize(s,out['out']),np.array([0,0,0,2/512,448,448,-448,1,-1],np.float32))
    with pytest.raises(OwnershipFault):v.execute('FP8_UNPACK',[np.array([127],np.uint8)],{})

def test_Qwen_integer_aliases_preserve_int64_and_bit_boundaries():
    p,s,v=setup_vm();x=np.array([-126.,127.],np.float32);providers=dict([load_fixture(p,'x',0,x,'F32')])
    code=[ins('LOAD','x',shape=(2,),name='x',dtype='F32'),ins('FTOI','i',['x'],(2,)),ins('CONST','shift',value=23,dtype='I64'),ins('SHL64','e',['i','shift'],(2,)),ins('MOV','out',['e'],(2,))]
    out=v.run({'code':code,'outputs':{'out':'out'}},providers)['out']
    assert out.dtype=='I64' and np.array_equal(materialize(s,out),np.array([-126,127],np.int64)<<23)

def test_split64_low_high_publication_blocks_torn_read_and_charges_traffic():
    p,s,v=setup_vm();t=Tensor('Qwen',0,65536,(128,),'I64',131072)
    words=np.array([2**40+i if i%2 else -2**42+i for i in range(128)],np.int64)
    original=s.transaction;first=True
    def interleave(sector,write=False,payload=b''):
        nonlocal first
        result=original(sector,write,payload)
        if write and first:
            first=False
            with pytest.raises(Backpressure):s.read(t,[0])
        return result
    s.transaction=interleave;s.write(t,0,words);s.transaction=original
    publish=s.codec_events[-1]
    assert publish['event']=='split64_both_streams_visible_granted_publication'
    write_events=[e for e in p.events if e['event']=='software_backing_visible']
    assert len(write_events)==32 and all(e['tick']<publish['tick'] for e in write_events)
    assert len([e for e in p.events if e['event']=='validated_reverse_grant'])==32
    before=len(p.events);actual=s.read(t,np.arange(128))
    assert np.array_equal(actual,words)
    assert len([e for e in p.events[before:] if e['event']=='software_read_capture'])==32
    assert s.codec_events[-1]['event']=='split64_actual_consumer_lease_release'
    assert all(c['codec_ticks']==32 for c in s.codec_events if 'codec_ticks' in c)

def test_split64_missing_highword_never_publishes_or_releases_lease():
    p,s,v=setup_vm();t=Tensor('Qwen',0,65536,(1,),'I64',1048576)
    with pytest.raises(ValueError):s.write(t,0,np.array([2**40],np.int64))
    assert ('Qwen',0,t.base,t.highword_base) in s.codec_locks
    assert not any(e['event']=='split64_both_streams_visible_granted_publication' for e in s.codec_events)
    with pytest.raises(Backpressure):s.read(t,[0])

def test_actual_r20_codec_homes_execute_source_integer_steps():
    import gzip,json
    root=Path(__file__).resolve().parents[1]
    fixture=json.loads((root/'results/uarch/hbm_provider_microvm_r21_20261002/actual_r20_codec_fixture_metadata.json').read_text())
    a=fixture['rank_allocation'];selected={h['symbol']:h for h in fixture['PC14_homes']}
    p=SectorProvider({('Qwen',0):a['extents']});base=a['native_workspace_end']-4096
    assert all(h['end_exclusive']<=base for h in selected.values() if h['class_']=='HBM_native_workspace')
    s=Storage(p,'Qwen',0,base,4096);v=MicroVM(s)
    n=np.tile(np.array([-126.,-1.,0.,127.],np.float32),32);pb=np.full(128,0x3f800000,np.uint32)
    providers=dict([load_fixture(p,'n',selected['n']['base'],n,'F32'),load_fixture(p,'pb',selected['pb']['base'],pb,'U32')])
    bindings={name:tensor_from_native_binding(selected[name],(128,)) for name in ('ni','exponent','resultbits')}
    code=[ins('LOAD','n',shape=(128,),name='n',dtype='F32'),ins('LOAD','pb',shape=(128,),name='pb',dtype='U32'),ins('FTOI','ni',['n'],(128,)),ins('CONST','shift',value=23,dtype='I64'),ins('SHL64','exponent',['ni','shift'],(128,)),ins('IADD64','resultbits',['pb','exponent'],(128,))]
    out=v.run({'source_pc':14,'code':code,'destination_bindings':bindings,'outputs':{'out':'resultbits'}},providers)['out']
    actual=s.read(out,np.arange(128))
    assert np.array_equal(actual,pb.astype(np.int64)+(n.astype(np.int64)<<23))
    assert out.base==selected['resultbits']['base'] and out.highword_base==selected['resultbits']['highword_base']
    assert all(e['staging_payload_bytes']<=1536 for e in v.journal)
    assert all(e['lanes']<=64 for e in v.journal if e['op'] in ('SHL64','IADD64'))
    assert not p.live and not p.calendar


def test_split64_read_lease_blocks_overwrite_until_actual_consumer():
    p,s,v=setup_vm();t=Tensor('Qwen',0,65536,(2,),'I64',131072)
    data=np.array([2**40,-2**42],np.int64);s.write(t,0,data)
    lease=s.acquire_split64(t,[0,1]);assert np.array_equal(s.read(t,[0,1],lease),data)
    with pytest.raises(Backpressure):s.write(t,0,data+1)
    s.release_split64(lease);s.write(t,0,data+1)
    with pytest.raises(OwnershipFault):s.read(t,[0,1],lease)
    with pytest.raises(OwnershipFault):s.release_split64(lease)

def test_empty_owned_extent_cannot_alias_or_free_live_storage():
    p,s,v=setup_vm();live=s.allocate((8,),'U32');before=dict(s.allocations)
    empty=s.allocate((0,4),'I64');s.free(empty)
    assert empty.count==0 and s.allocations==before and s.cursor==live.base+32
    assert len(s.read(empty,[]))==0 and not p.events
    with pytest.raises(ValueError):s.allocate((-1,),'U32')

def test_foreign_rank_write_cannot_mutate_local_namespace():
    p,s,v=setup_vm();t=Tensor('DeepSeek',95,4096,(8,),'U32')
    with pytest.raises(ValueError):s.write(t,0,np.arange(8,dtype=np.uint32))
    assert not p.events and not p.backing

def test_committable_source_pc14_software_journal_has_complete_owner_chains():
    from qwen_split64_diagnostic_r22 import diagnostic
    d=diagnostic();chains={}
    for e in d['events']:
        key=(e['identity']['serial'],e['tag'],e['generation'])
        chains.setdefault(key,[]).append(e)
    assert d['values_match'] and d['all_ownership_drained'] and not d['hardware'] and not d['PHY']
    for chain in chains.values():
        names=[e['event'] for e in chain]
        assert names[0]=='request_accept' and names[-1]=='validated_reverse_grant'
        assert names.index('software_owned_issue')<names.index('consumer_accept')<names.index('validated_reverse_grant')
    assert len([e for e in d['codec_events'] if e['event']=='split64_both_streams_visible_granted_publication'])==5
