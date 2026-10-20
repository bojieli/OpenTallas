#!/usr/bin/env python3
"""Read-only, source-bound PC async-assert/two-edge-release proof packet.

This is not a canonical gate helper, threshold change, or generic reset alias.
It audits the actual two selected mapped PC sources and every physical bank
consumer, against the real Liberty sequential and combinational functions.
"""
from collections import Counter
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys

ASR='DFFASRHQNx1_ASAP7_75t_R'
HQN='DFFHQNx1_ASAP7_75t_R'
MODEL_HASHES={
 'canonical_ASR_normalized.v':'ee63e9a38cab2a9fa507f6fdc0480b04f047088a2f76464a5fca6182a9ba26d5',
 'canonical_DFF_normalized.v':'cbba1c176afe1a03e677d21ee4e095c7b3d326689d8ec5ec46640d3e43a26254'}
sp=importlib.util.spec_from_file_location('tl','textbook_lint.py')
m=importlib.util.module_from_spec(sp);sys.modules['tl']=m;sp.loader.exec_module(m)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def block(text,header):
    match=re.search(header+r'\s*\{',text)
    assert match,header
    depth=1;end=match.end()
    while depth:
        if text[end]=='{':depth+=1
        elif text[end]=='}':depth-=1
        end+=1
    return text[match.end():end-1]

cells={};lib_hashes={}
for path in sorted(Path('libs').glob('*.lib')):
    lib_hashes[str(path)]=sha(path);text=path.read_text()
    for match in re.finditer(r'\bcell\s*\(\s*(\w+)\s*\)',text):
        cells[match[1]]=block(text[match.start():],r'cell\s*\(\s*'+re.escape(match[1])+r'\s*\)')

def fn(typ,pin):
    body=block(cells[typ],r'pin\s*\(\s*'+re.escape(pin)+r'\s*\)')
    match=re.search(r'\bfunction\s*:\s*"([^"]+)"',body)
    assert match,(typ,pin)
    return match[1]

ff=block(cells[ASR],r'ff\s*\(\s*IQN\s*,\s*IQNN\s*\)')
expected=dict(clear='!SETN',preset='!RESETN',clocked_on='CLK',next_state='!D')
for key,value in expected.items():
    assert re.search(r'\b'+key+r'\s*:\s*"'+re.escape(value)+r'"\s*;',ff),(key,ff)
assert re.search(r'clear_preset_var1\s*:\s*L\s*;',ff)
assert re.search(r'clear_preset_var2\s*:\s*L\s*;',ff)
assert fn(ASR,'QN')=='IQN'
for path,value in MODEL_HASHES.items():assert sha(path)==value,(path,sha(path))
corner_identity={}
for path in sorted(Path('lib_corners').glob('*.lib')):
    cell=block(path.read_text(),r'cell\s*\(\s*'+ASR+r'\s*\)')
    sequential=block(cell,r'ff\s*\(\s*IQN\s*,\s*IQNN\s*\)')
    for key,value in expected.items():
        assert re.search(r'\b'+key+r'\s*:\s*"'+re.escape(value)+r'"\s*;',sequential),(path,key)
    assert re.search(r'clear_preset_var1\s*:\s*L\s*;',sequential)
    assert re.search(r'clear_preset_var2\s*:\s*L\s*;',sequential)
    qn=block(cell,r'pin\s*\(\s*QN\s*\)')
    assert re.search(r'function\s*:\s*"IQN"',qn)
    corner_identity[str(path)]=dict(sha256=sha(path),sequential_identity=expected,QN_function='IQN')
assert len(corner_identity)==3,'must audit real SS/TT/FF sequential Liberty identities'

def terminals(g,a,start):
    stack=[(start,0)];seen=set();ends=[];exports=[]
    while stack:
        net,inv=stack.pop()
        if (net,inv) in seen:continue
        seen.add((net,inv))
        exports += [(p,inv) for p in a['out_ports'].get(net,[])]
        for ci,pin,unused in a['loads'].get(net,[]):
            if a['kind'][ci]=='buf':
                typ=g.cells[ci][0];neg=bool(re.match(r'^(INV|CKINV)',typ))
                stack += [(x,inv^neg) for pn,bits in g.cells[ci][2].items() if a['pin_dir'][ci][pn]=='out' for x in bits]
            else:ends.append((ci,pin,net,inv))
    return ends,exports

def resolve(g,a,net):
    inv=0;seen=set()
    while net in a['driver']:
        ci,pin=a['driver'][net]
        if ci<0 or a['kind'][ci]!='buf':break
        assert net not in seen;seen.add(net)
        typ,unused,pins=g.cells[ci]
        ins=[x for pn,bits in pins.items() if a['pin_dir'][ci][pn]=='in' for x in bits]
        assert len(ins)==1
        inv^=bool(re.match(r'^(INV|CKINV)',typ));net=ins[0]
    return net,int(inv)

def constant(g,a,net):
    net,inv=resolve(g,a,net)
    if net<=1:return net^inv
    driver=a['driver'].get(net)
    if driver is None or driver[0]<0:return None
    ci,pin=driver;typ,unused,pins=g.cells[ci]
    if a['kind'][ci]!='tie':return None
    value=fn(typ,pin).strip()
    assert value in ('0','1'),(typ,pin,value)
    assert not any(a['pin_dir'][ci][p]=='in' for p in pins)
    return int(value)^inv

def clamp_zero(typ,pin,value):
    expression=fn(typ,'Y')
    assert re.fullmatch(r'[A-Za-z0-9_!&|*+^()\s]+',expression),expression
    names=sorted(set(re.findall(r'\b[A-Za-z_]\w*\b',expression)))
    assert pin in names
    expression=expression.replace('!',' not ').replace('&',' and ').replace('*',' and ').replace('|',' or ').replace('+',' or ')
    for bits in itertools.product((0,1),repeat=len(names)-1):
        values=dict(zip([n for n in names if n!=pin],bits));values[pin]=value
        if bool(eval(expression,{'__builtins__':{}},values)):return False
    return True

def bank(g,a,reset,clock,expected_consumers=None):
    root=g.ports[reset][1];ck=g.ports[clock][1]
    ends,exports=terminals(g,a,root)
    assert not exports,'root reset is exported'
    assert len(ends)==9,'root must reach exactly one first and eight final ASR pins'
    ids=[]
    for ci,pin,net,inv in ends:
        typ,name,pins=g.cells[ci]
        assert typ==ASR and set(pins)=={'CLK','D','QN','RESETN','SETN'},('wrong ASR identity',name)
        assert pin=='RESETN' and inv==0,('wrong asynchronous assertion polarity/value',name,pin,inv)
        assert resolve(g,a,pins['CLK'][0])==(ck,0),('wrong bank clock',name)
        assert constant(g,a,pins['SETN'][0])==1,('SETN must be constant one',name)
        ids.append(ci)
    assert len(set(ids))==9,'duplicate ASR terminal'
    first=[ci for ci in ids if constant(g,a,g.cells[ci][2]['D'][0])==1]
    assert len(first)==1,'first D is not exactly one constant-one stage'
    first=first[0];last=set(ids)-{first};first_q=g.cells[first][2]['QN'][0]
    first_ends,first_exports=terminals(g,a,first_q)
    assert not first_exports and len(first_ends)==8,'first Q has a side consumer/export or missing final stage'
    assert {(ci,pin,inv) for ci,pin,net,inv in first_ends}=={(ci,'D',1) for ci in last},'first QN must invert exactly once to all final D pins'
    consumers=[];last_rows=[]
    for ci in sorted(last):
        typ,name,pins=g.cells[ci];q=pins['QN'][0]
        ends,exports=terminals(g,a,q)
        assert not exports,('final reset exported',name,exports)
        assert len(ends)<=32,('final reset fanout exceeds 32',name,len(ends))
        identities=[]
        for target,pin,net,inv in ends:
            tt,tn,tp=g.cells[target]
            if tt==ASR:
                assert pin=='RESETN' and inv==1,('not a logical ASR reset consumer',tn,pin,inv)
                role='ASR active-low reset'
            elif tt==HQN:
                assert pin=='D' and inv==1,('not a sampled logical release consumer',tn,pin,inv)
                role='registered logical release sample'
            else:
                assert tt in ('AND3x1_ASAP7_75t_R','NOR2x1_ASAP7_75t_R'),('unreviewed combinational reset consumer',tt,tn)
                assert clamp_zero(tt,pin,1^inv),('reset consumer does not clamp output zero',tn)
                role='Liberty-proven reset clamp to zero for all other inputs'
            identity=dict(stage=name,type=tt,cell=tn,pin=pin,polarity=inv,role=role)
            if tt in (ASR,HQN):
                consumer_destination,consumer_polarity=resolve(g,a,tp['CLK'][0])
                identity['consumer_clock_ports']=[p for p,(direction,x) in g.ports.items() if direction=='input' and x==consumer_destination]
                identity['consumer_clock_polarity']=consumer_polarity
                identity['first_use_calendar']='First destination rising edge strictly after final logical release; if same bank clock, raw release edges1/2 establish final release, edge3 is first legal use.'
                identity['parent_calendar_obligation']='Different destination clocks require actual phase/boot calendar; graph proof does not assume coincident edges.'
            if tt==HQN:
                destination,clock_polarity=resolve(g,a,tp['CLK'][0])
                identity['observer_clock_ports']=[p for p,(direction,x) in g.ports.items() if direction=='input' and x==destination]
                identity['observer_clock_polarity']=clock_polarity
                identity['existing_observer_capture_edges_after_final_release']=1
                identity['schedule_scope']='Existing source RTL edge, not removed or masked. If destination clock differs, parent must price the actual capture phase.'
            identities.append(identity);consumers.append(identity)
        last_rows.append(dict(cell=name,type=typ,clock=clock,D=g.net_name[pins['D'][0]],QN=g.net_name[q],terminal_loads=len(ends),consumers=identities))
    consumers.sort(key=lambda r:(r['stage'],r['cell'],r['pin'],r['polarity']))
    if expected_consumers is not None:assert consumers==expected_consumers,'missing/extra/changed declared final reset consumer'
    return dict(pass_graph=True,reset_port=reset,clock_port=clock,root_terminal_loads=9,
                first=dict(cell=g.cells[first][1],type=ASR,D='Liberty-proven constant one',QN=g.net_name[first_q],terminal_loads=8),
                final=last_rows,declared_consumers=consumers,stages=2,
                assertion='root low asynchronously presets all physical QNs; logical release is their inverse',
                release='first D=1; every final D is the logical first-stage release, on the same literal destination clock')

packet=dict(schema='opentallas.pc.normal_sr8.private_async_conditioner.proof.v1',models=MODEL_HASHES,
            liberty_files=lib_hashes,ASR_liberty_cell_sha256=hashlib.sha256(cells[ASR].encode()).hexdigest(),
            loaded_corner_sequential_identities=corner_identity,
            ASR_sequential_identity=expected,ASR_output_function=fn(ASR,'QN'),cases={})
for case in ['qkd_kvs_pc','qkd_kvs_pc_h']:
    folder=Path(case); selected=json.loads((folder/'selected_source_manifest.json').read_text())
    source=folder/'selected_source.sv'
    assert sha(source)==selected['primary_source_sha256']
    for row in selected['source_closure']:
        assert sha(folder/'src'/row['path'])==row['sha256'],('selected source closure drift',row)
    text=source.read_text();assert not re.search(r'\binitial\b|\binit\s*=',text),'primary selected top initializes physical state'
    mapped=(folder/'resynth.v').read_text()
    assert not re.search(r'\binitial\b|\binit\s*=',mapped),'actual mapped source initializes physical state'
    g,top=m.flatten(m.parse_verilog(mapped),case);a=m.build(g,None)
    clocks,unused=m.clock_nets(g,a);maximum=0;drivers=0
    for net,(ci,pin) in a['driver'].items():
        if net in clocks or net<=3 or (ci>=0 and a['kind'][ci] in ('buf','tie')):continue
        count,unused,unused2=m.bufinv_fanout(g,a,net,clocks);maximum=max(maximum,count);drivers+=1
    assert maximum<=32,('actual native fanout violation',case,maximum)
    banks={reset:bank(g,a,reset,clock) for reset,clock in [('rst_n','ck'),('hrst_n','hck')]}
    negatives=[]
    for reset,clock in [('rst_n','ck'),('hrst_n','hck')]:
        baseline=banks[reset];byname={name:ci for ci,(_,name,_) in enumerate(g.cells)}
        first=byname[baseline['first']['cell']];last=byname[baseline['final'][0]['cell']]
        for mutation in ['root_polarity','root_assert_value','first_D','clock','QN_polarity','stage_bypass','extra_consumer','missing_stage']:
            h=copy.deepcopy(g)
            if mutation=='root_polarity':
                old=h.cells[first][2]['RESETN'][0];new=h.net('negative_root_inv')
                h.cells.append(('INVxp67_ASAP7_75t_R','negative_root_inv',dict(A=[old],Y=[new])))
                h.cells[first][2]['RESETN']=[new]
            elif mutation=='root_assert_value':
                pins=h.cells[first][2];pins['RESETN'],pins['SETN']=pins['SETN'],pins['RESETN']
            elif mutation=='first_D':h.cells[first][2]['D']=[0]
            elif mutation=='clock':h.cells[last][2]['CLK']=[h.ports['hck' if clock=='ck' else 'ck'][1]]
            elif mutation=='QN_polarity':h.cells[last][2]['D']=list(h.cells[first][2]['QN'])
            elif mutation=='stage_bypass':h.cells[last][2]['D']=list(h.cells[first][2]['D'])
            elif mutation=='extra_consumer':
                net=h.net('negative_extra_consumer')
                h.cells.append(('OR2x2_ASAP7_75t_R','negative_extra_consumer',dict(A=list(h.cells[last][2]['QN']),B=[0],Y=[net])))
            elif mutation=='missing_stage':h.cells.pop(last)
            try:bank(h,m.build(h,None),reset,clock,baseline['declared_consumers'])
            except (AssertionError,KeyError) as error:negatives.append(dict(reset=reset,mutation=mutation,refused=True,reason=str(error)))
            else:raise AssertionError(('negative unexpectedly accepted',case,reset,mutation))
    packet['cases'][case]=dict(selected_source=str(source),selected_source_sha256=sha(source),top=top,params={},defines=[],source_has_no_init=True,
                              source_closure=selected, mapped_sha256=sha(folder/'resynth.v'),
                              native_all_driver_maximum=maximum,native_checked_drivers=drivers,banks=banks,causal_graph_negatives=negatives)
packet['parent_fanout_scope']=dict(each_distinct_reset_port_per_top=9,
    sum_of_two_distinct_reset_port_loads_per_top=18,
    when_both_distinct_reset_ports_are_tied_to_one_external_raw_root=18,
    when_all_four_selected_top_reset_ports_are_tied_to_one_external_raw_root=36,
    requirement='Actual parent binding must count its actual root loads and provide registered regional distribution if aggregate exceeds32. Standalone proof does not establish die-level fanout.')

Path('pc_async_source_graph_proof.json').write_text(json.dumps(packet,indent=2)+'\n')
print(json.dumps({case:dict(source=row['selected_source_sha256'],native_max=row['native_all_driver_maximum'],banks={k:dict(first=v['first']['cell'],final=len(v['final']),max_final=max(x['terminal_loads'] for x in v['final'])) for k,v in row['banks'].items()},negative_refusals=len(row['causal_graph_negatives'])) for case,row in packet['cases'].items()}))
