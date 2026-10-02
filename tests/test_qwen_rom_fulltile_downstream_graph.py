import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_fulltile_downstream_graph import Graph,boolean,variables,address_boundary,kv_capture_boundary

def test_liberty_boolean_operators_exhaustive():
    a,b,c=variables(3);u=(1<<8)-1
    assert boolean('(!A * B) + (C)',dict(A=a,B=b,C=c),u)==((u^a)&b)|c

def test_unrecognized_function_refused():
    with pytest.raises(ValueError):boolean('A and B',dict(A=1,B=0),1)

def fixture(function='A * B'):
    lib='cell (AND) { pin (Y) { function : "'+function+'"; } }'
    net={'cells':{'merge':{'type':'AND','port_directions':{'A':'input','B':'input','Y':'output'},'connections':{'A':[1],'B':[2],'Y':[3]}}}}
    return Graph(net,lib)

def test_actual_gate_function_and_wrong_polarity_detected():
    a,b=variables(2);u=15
    assert fixture().eval(3,{1:a,2:b},u,{})==a&b
    assert fixture('!A * B').eval(3,{1:a,2:b},u,{})!=a&b

def test_missing_boundary_refused():
    with pytest.raises(KeyError):fixture().eval(3,{1:3},15,{})

def test_sequential_boundary_cannot_be_zero_filled():
    net={'cells':{'ff':{'type':'DFF','port_directions':{'D':'input','Q':'output'},'connections':{'D':[1],'Q':[2]}}}}
    with pytest.raises(ValueError,match='unbound sequential'):Graph(net,'').eval(2,{},15,{})

def decoder_fixture(wrong_bank=False):
    src={'src':'/p/ot_qwen_w12_matvec.sv:491.5-547.8'}
    cells={};lib='cell (DFFHQNx1_ASAP7_75t_R) { ff (I,N) { next_state : "!D"; } } cell (INV) { pin (Y) { function : "!A"; } }'
    for i in range(12):
        cells[f'addr{i}']={'type':'DFFHQNx1_ASAP7_75t_R','attributes':src,'connections':{'CLK':[2],'D':[1000+i],'QN':[100+i]},'port_directions':{'CLK':'input','D':'input','QN':'output'}}
    cells['read']={'type':'DFFASRHQNx1_ASAP7_75t_R','connections':{'QN':[200],'CLK':[2]},'port_directions':{'QN':'output','CLK':'input'}}
    cells['read_inv']={'type':'INV','connections':{'A':[200],'Y':[201]},'port_directions':{'A':'input','Y':'output'}}
    for bank in range(5):
        value=2 if wrong_bank and bank==3 else bank
        on={j for k,j in enumerate((3,7,10)) if (value>>k)&1}
        expr='!R * '+' * '.join(('!' if i in on else '')+f'A{i}' for i in range(12))
        kind=f'DEC{bank}';lib+=f'cell ({kind}) {{ pin (Y) {{ function : "{expr}"; }} }}'
        inputs={f'A{i}':[100+i] for i in range(12)};inputs.update(R=[200],Y=[300+bank])
        cells[kind]={'type':kind,'connections':inputs,'port_directions':{p:'output' if p=='Y' else 'input' for p in inputs}}
        for pair in range(2):cells[f'u_tile.g_col[{pair}].g_bank[{bank}].u_rom']={'type':'ot_rom_4096x266_m8','connections':{'ce_in':[300+bank]},'port_directions':{'ce_in':'input'}}
    n={'cells':cells,'netnames':{'u_tile.u_logic.u_me.wrom_re':{'bits':[201]}}}
    return Graph(n,lib),n

def test_decoder_recovers_significance_not_ff_name_order():
    g,n=decoder_fixture();r=address_boundary(g,n)
    assert r['source_low_bank_bit_FFs']=={'12':'addr3','13':'addr7','14':'addr10'}
    assert len(r['source_high_zero_check_FFs'])==9
    assert r['per_bit_transition_identity_for_zero_check_group']=='OPEN'

def test_wrong_bank_decode_refused():
    g,n=decoder_fixture(True)
    with pytest.raises(ValueError):address_boundary(g,n)

def kv_fixture(duplicate=False,wrong_hold=False):
    cells={};src='/p/ot_qwen_rom_tile_context_candidate_r2.sv:'
    lib='cell (DFFHQNx1_ASAP7_75t_R) { ff (I,N) { next_state : "!D"; } }'
    fn='(!EN * RAW) + (EN * !OLD)' if not wrong_hold else '(!EN * RAW) + (EN * OLD)'
    lib+=f'cell (MUX) {{ pin (Y) {{ function : "{fn}"; }} }}'
    cells['qual']={'type':'DFFHQNx1_ASAP7_75t_R','attributes':{'src':src+'312.13-312.106'},'connections':{'QN':[1],'CLK':[2]},'port_directions':{'QN':'output','CLK':'input'}}
    for m in range(2):
        cells[f'kv{m}']={'type':'ot_sram_1r1w_128x256_m1_r2c2','connections':{'rd_out':list(range(10000+256*m,10000+256*(m+1))),'clk':[2]},'port_directions':{'rd_out':'output','clk':'input'}}
    for i in range(512):
        raw=10000+(0 if duplicate and i==511 else i)
        cells[f'ff{i}']={'type':'DFFHQNx1_ASAP7_75t_R','attributes':{'src':src+'313.13-313.62'},'connections':{'QN':[20000+i],'D':[30000+i],'CLK':[2]},'port_directions':{'QN':'output','D':'input','CLK':'input'}}
        cells[f'mux{i}']={'type':'MUX','connections':{'RAW':[raw],'OLD':[20000+i],'EN':[1],'Y':[30000+i]},'port_directions':{'RAW':'input','OLD':'input','EN':'input','Y':'output'}}
    n={'cells':cells};return Graph(n,lib),n

def test_all_raw_kv_code_bits_survive_held_stage():
    g,n=kv_fixture();r=kv_capture_boundary(g,n)
    assert r['actual_raw_capture_FFs']==512 and r['E4M3_decoder_consumer_equivalence']=='OPEN'

@pytest.mark.parametrize('duplicate,wrong_hold',[(True,False),(False,True)])
def test_missing_or_wrong_kv_bit_mux_refused(duplicate,wrong_hold):
    g,n=kv_fixture(duplicate,wrong_hold)
    with pytest.raises(ValueError):kv_capture_boundary(g,n)
