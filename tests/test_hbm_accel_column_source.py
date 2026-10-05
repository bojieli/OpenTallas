from types import SimpleNamespace
import struct
import pytest
from tools.hbm_accel_column_source import ColumnSource, REGIONS
from tools.hbm_accel_column_probes import emit_top, emit_driver, ColumnProbePins, SectorReadbackPins

SHA = '1'*64

class Pins:
    def __init__(self):
        self.observers=[]; self.reads=[]; self.ctr=2
        self.snap=dict(time_ps=100, cycle=10, sms=[dict(pc=20,can_issue=1)] +
                       [dict(pc=0,can_issue=0) for _ in range(3)])
    def snapshot(self): return self.snap.copy()
    def read_bytes(self,die,address,size,*,mem_words):
        self.reads.append((die,address,size))
        if address==100: return struct.pack('<I',self.ctr)
        if address==512*2+4: return struct.pack('<I',100000)
        if address==512*2+8: return struct.pack('<I',200000)
        return bytes(size)
    def read_shared(self,die,sm,address,size):
        if address==0x7C80: return struct.pack('<II',1,3)
        return bytes(size)
    def read_bd_activation(self,die,sm,index): return (1<<2000)+index
    def read_ur(self,die,sm,index): return 7
    def read_instruction(self,die,sm,index): return 123

def setup():
    pins=Pins()
    owner=SimpleNamespace(state='WAIT',entry=10,job=9,generation=3,position=7,token=42)
    entering=dict(kind='swapin',token=99,input_token=4,pos=2,job=9,generation=3,source_sha256=SHA)
    engine=SimpleNamespace(pins=pins,ndie=2,nsm=2,source_sha256=SHA,
                           entries=dict(layer=10),sm_engine=owner,receipts=[entering])
    p=SimpleNamespace(CSTR=4736,a=dict(COL=4096,DESC=0,CTR=100),
                      desc_fields=dict(rexp0=1,shexp0=2),ex_stride=20000,
                      ex_w2off=46080,sh_w2off=46080,m=SimpleNamespace(dim=160,L=40,k_exp=2,n_exp=4))
    # Exact packed per-expert stride must contain both phases; use real-sized envelope.
    p.ex_stride=69120
    join=ColumnSource(engine,p,source_sha256=SHA,mem_words=100000,enable=True)
    compiled=dict(entries=engine.entries,images={(0,0):[0]*20+[123]},
                  boundaries=[dict(die=0,sm=0,linked_pc=20,phase='prefix_begin',kind='layer',slot=2)])
    return join,pins,engine,compiled


def test_actual_router_activation_and_shared_weight_join():
    join,pins,engine,compiled=setup()
    callback=join.attach(compiled); callback(None,pins.snapshot())
    record=join.movements[0]
    assert (record['column'],record['layer'],record['job'],record['generation'])==(4,2,9,3)
    assert record['expert_ids']==(1,3)
    assert len(record['activation_bd266x8'])==5
    lines=record['weight_lines']
    assert len(lines)==160
    assert [r['row'] for r in lines[:10]]==list(range(8))+[0,1]
    assert lines[0]['address']==200000 and lines[8]['address']==200000+8*288
    assert lines[0]['sectors']==tuple(200000+32*q for q in range(9))
    assert all(r['expert'] is None and len(r['payload'])==288 for r in lines)
    callback(None,pins.snapshot()); assert len(join.movements)==1
    assert len(pins.observers)==1 and pins.snapshot()['cycle']==10


def test_down_selected_expert_original_stride_and_phase():
    join,pins,engine,compiled=setup()
    compiled['boundaries'][0].update(phase='down_begin',slot=1)
    join.attach(compiled)(None,pins.snapshot())
    lines=join.movements[0]['weight_lines']
    assert len(lines)==80
    assert lines[0]['address']==100000+3*69120+46080
    assert all(r['expert']==3 for r in lines)
    assert len(join.movements[0]['activation_bd266x8'])==2


def test_owner_source_and_router_refusals():
    join,pins,engine,compiled=setup()
    pins.ctr=1
    with pytest.raises(RuntimeError,match='owner mismatch'): join.attach(compiled)(None,pins.snapshot())
    assert not join.movements
    pins.ctr=2; pins.read_shared=lambda *args: struct.pack('<II',3,1)
    with pytest.raises(RuntimeError,match='ordering'): pins.observers[0](None,pins.snapshot())
    assert not join.movements
    join2, pins2, _, compiled2=setup()
    pins2.read_instruction=lambda *args: 99
    with pytest.raises(ValueError,match='instruction differs'): join2.attach(compiled2)
    with pytest.raises(ValueError,match='same loaded'): ColumnSource(engine,join.p,source_sha256='2'*64,mem_words=1,enable=True)


def test_complete_column_readback_no_fake_ctr():
    join,pins,engine,_=setup(); engine.sm_engine.state='IDLE'
    receipt=dict(kind='swapout',token=99,input_token=4,source_sha256=SHA,job=9,generation=3)
    engine.receipts.append(receipt)
    result=join.capture_column(4,receipt)
    assert all(set(fields)==set(REGIONS) for fields in result['values'])
    assert [len(result['values'][0][n]) for n in REGIONS]==[2560,16,4,128,4,1920]
    assert 'does not persist CTR' in result['CTR_scope']
    with pytest.raises(ValueError,match='identity'): join.capture_column(5,receipt)


def test_probe_range_and_direct_rtl_generation(tmp_path):
    top=tmp_path/'top.sv'; driver=tmp_path/'driver.cpp'
    emit_top(top,100,enable=True); emit_driver(driver,enable=True)
    text=top.read_text()
    assert 'source_data[31:0]=dut.u_cluster.g_on.g_die[1].g_sm[1].u_sm.g_on.smem[source_index]' in text
    assert '.g_bd.u_bdtc.xmem[source_index]' in text
    assert 'source_data[63:0]=' in text and 'imem[source_index]' in text
    cpp=driver.read_text(); assert "op=='H'" in cpp and 'index>=16384' in cpp
    assert 'wide(m.source_data,67)' in cpp
    probe=ColumnProbePins.__new__(ColumnProbePins)
    calls=[]; probe._rpc=lambda command: calls.append(command) or ['00']
    assert probe.read_shared(1,1,32765,3)==bytes(3)
    assert calls==['H 3 0 1fff']
    with pytest.raises(ValueError): probe.read_shared(0,0,32767,2)
    with pytest.raises(ValueError): probe.read_bd_activation(0,0,64)
    with pytest.raises(ValueError): probe.read_instruction(0,0,16384)


def test_same_command_multiple_columns_and_sector_interleave():
    join,pins,engine,compiled=setup(); observe=join.attach(compiled)
    observe(None,pins.snapshot())
    engine.receipts[-1]['input_token']=5
    observe(None,pins.snapshot())
    assert [r['column'] for r in join.movements]==[4,5]
    probe=SectorReadbackPins.__new__(SectorReadbackPins); calls=[]
    def rpc(command):
        calls.append(command)
        value=bytes([len(calls)])*32
        return [value[::-1].hex()]
    probe._rpc=rpc
    result=probe.read_bytes(1,120,20,mem_words=100)
    assert result==bytes([1])*8+bytes([2])*12
    assert calls==['M 2 3','M 3 0']
    assert probe.read_bytes(0,1,0,mem_words=100)==b''


def test_layer_zero_embed_retains_actual_entering_swapin():
    join,pins,engine,compiled=setup()
    engine.receipts[-1]['pos']=0; pins.ctr=0
    engine.receipts.append(dict(kind='embed',input_token=42,token=99,pos=7,
                               job=9,generation=3,source_sha256=SHA))
    join.attach(compiled)(None,pins.snapshot())
    assert (join.movements[0]['layer'],join.movements[0]['column'])==(0,4)
    assert engine.receipts[-1]['kind']=='embed'
    assert pins.snapshot()['cycle']==10


@pytest.mark.parametrize('change', ['job','generation','source','position','embed_input','interrupted','wrong_layer','missing_input','missing_swapin'])
def test_entering_swapin_refuses_stale_or_interrupted_receipts(change):
    join,pins,engine,compiled=setup()
    engine.receipts[-1]['pos']=0; pins.ctr=0
    embed=dict(kind='embed',input_token=42,token=99,pos=7,job=9,
               generation=3,source_sha256=SHA)
    engine.receipts.append(embed)
    if change=='job': engine.receipts[0]['job']=8
    if change=='generation': engine.receipts[0]['generation']=2
    if change=='source': embed['source_sha256']='2'*64
    if change=='position': embed['pos']=6
    if change=='embed_input': embed['input_token']=43
    if change=='interrupted': embed['kind']='swapout'
    if change=='wrong_layer': engine.receipts[0]['pos']=2
    if change=='missing_input': del engine.receipts[0]['input_token']
    if change=='missing_swapin': del engine.receipts[0]
    observe=join.attach(compiled)
    with pytest.raises(RuntimeError): observe(None,pins.snapshot())
    assert not join.movements and not pins.reads
