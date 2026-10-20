#!/usr/bin/env python3
"""Causal mapped-graph negatives for the actual retained-source reset proof.

These do not change production RTL, gate verdicts or thresholds. Each fixture
changes one physical primitive/pin relation in the actual re-synthesis graph.
"""
import copy
import importlib.util
import json
from pathlib import Path
import sys

sp=importlib.util.spec_from_file_location('tl','textbook_lint.py')
m=importlib.util.module_from_spec(sp);sys.modules['tl']=m;sp.loader.exec_module(m)
g,_=m.flatten(m.parse_verilog(Path('resynth.v').read_text()),'qkd_hr_core_order_n32')
a=m.build(g,None)
profile=json.loads(Path('native32.json').read_text())['reset_profile']
root=g.ports['host_rst_n'][1]
first=[ci for ci,pin,unused in a['loads'][root]]
assert len(first)==12
q=next(x for pin,bits in g.cells[first[0]][2].items() if a['pin_dir'][first[0]][pin]=='out' for x in bits)
stack=[q];last=[];seen=set()
while stack:
    net=stack.pop()
    if net in seen:continue
    seen.add(net)
    for ci,pin,unused in a['loads'].get(net,[]):
        if a['kind'][ci]=='buf':
            stack.extend(x for pn,bits in g.cells[ci][2].items() if a['pin_dir'][ci][pn]=='out' for x in bits)
        else:last.append(ci)
assert last

def proof(graph,payload):
    return m.balanced_reset_proof(graph,m.build(graph,None),'host_rst_n',root,payload)

baseline=proof(g,profile)
assert baseline['pass']
rows=[]
for name in ['root_d','extra_first','final_clock','final_qn_polarity','extra_reset_consumer','final_stage_bypass','missing_final']:
    h=copy.deepcopy(g)
    if name=='root_d':h.cells[first[0]][2]['D']=[0]
    elif name=='extra_first':
        typ,inst,pins=h.cells[first[0]]
        pins=copy.deepcopy(pins)
        pn=next(p for p in pins if a['pin_dir'][first[0]][p]=='out')
        pins[pn]=[h.net('negative_extra_first')]
        h.cells.append((typ,'negative_extra_first',pins))
    elif name=='final_clock':h.cells[last[0]][2]['CLK']=[0]
    elif name=='final_qn_polarity':
        old=h.cells[last[0]][2]['D'][0]
        inv=h.net('negative_final_inv')
        h.cells.append(('INVxp67_ASAP7_75t_R','negative_final_inv',dict(A=[old],Y=[inv])))
        h.cells[last[0]][2]['D']=[inv]
    elif name=='extra_reset_consumer':
        net=h.net('negative_comb_reset')
        h.cells.append(('OR2x2_ASAP7_75t_R','negative_comb_reset',dict(A=[root],B=[0],Y=[net])))
    elif name=='final_stage_bypass':h.cells[last[0]][2]['D']=[root]
    elif name=='missing_final':h.cells[last[0]][2]['D']=[0]
    result=proof(h,profile)
    assert result['pass'] is False,(name,result)
    rows.append(dict(fixture=name,expected='refuse',actual=result))
result=dict(baseline=baseline,causal_negatives=rows,all_refused=True,
            note='Graph proof does not carry Verilog init attributes; the reviewed interface must bind exact selected-source and model hashes separately.')
Path('reset_negatives.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
