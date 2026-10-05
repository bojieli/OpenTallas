import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w13_index_f32_ports as M

def test_source_defined_ports_and_dependencies():
    d=M.receipt()
    for p in d['programs'].values():
        assert p['peak_registers_conservative']<=32
        assert p['cycles'] is None and not p['actual_runtime_path_bound']
        for e in p['events']:
            assert e['RF_reads_per_lane']<=2 and e['RF_write_ports']<=1
            assert all(x<e['event_id'] for x in e['dependencies'])
            for o in e['operands']:
                if 'producer_events' in o:
                    assert set(o['producer_events'])<=set(e['dependencies'])
            assert e['launch_tick'] is None and e['finish_tick'] is None
    assert d['programs']['decode32']['unknown_opcode_latency_variants']['F2I']>0
    assert d['physical_admission']=='FAIL_CLOSED'

def test_scatter_bank_and_finite_addresses():
    d=M.staging()
    addresses=[]
    for e in d['events']:
        assert len(set(e['banks']))==32
        assert e['shared_write_bytes']==128
        addresses+=e['word_addresses']
    assert len(addresses)==len(set(addresses))==8192
    assert min(addresses)==4096 and max(addresses)==12287
    assert d['shared_peak_bytes']==57472<65536
    assert all(e['tick'] is None for e in d['ACK_calendar'])

def test_branches_carry_both_reaching_definitions():
    p=[{'op':'MOV','dst':'x','src':[1]}, {'op':'BEQ','src':['x',1],'yes':[{'op':'MOV','dst':'v','src':[2]}],'no':[{'op':'MOV','dst':'v','src':[3]}]}, {'op':'IADD','dst':'z','src':['v',1]}]
    r=M.graph(p,'test')['events']
    assert r[-1]['operands'][0]['producer_events']==[2,3]
    assert r[2]['control_path']==[1] and r[3]['control_path']==[1]
