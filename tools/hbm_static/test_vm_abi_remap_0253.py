#!/usr/bin/env python3
"""Compiler-only semantic migration proof; does not qualify a native VM tile."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hbm_vm_static_calendar import layout,compile_schedule,ROOT
from vm_abi_remap_0253 import migrate,packed

abi=json.loads((ROOT/'results/arch/hbm_vm_static_1014/quadrant_abi.json').read_text())
# Expected post-compaction shape, tested before adopting the physical worker's ABI.
new=copy.deepcopy(abi)
for q in ['SW','SE']:new['quadrants'][q]['params']['WG']=2
for q in ['NW','NE']:new['quadrants'][q]['params']['RG']=5
nw=new['quadrants']['NW'];nw['params'].update(NC=3,CW=2)
for p in nw['ports']:
 if p['name'] in {'client_seq','response_seq'}:p['bits']=8
 elif p['name']=='response_enable':p['bits']=4
 elif p['name']=='bank_client':p['bits']=16
 elif p['name']=='hub_ring_client':p['bits']=4
old={'base':7,'loops':3,'cycles':[dict(client_seq=packed([1,2,3,0,2],2),response_enable=0b10111,
 response_seq=packed([2,1,3,0,1],2),bank_enable=255,bank_client=packed([0,1,2,4,4,2,1,0],3),
 hub_ring_enable=3,hub_ring_client=packed([4,2],3),rslot_v=255,rslot=packed([0,1,2,4,5,6,5,1],3))]}
out=migrate(old,'NW');v=out['cycles'][0]
assert (out['base'],out['loops'],len(out['cycles']))==(7,3,1)
assert v['client_seq']==packed([1,2,3,2],2)
assert v['response_enable']==0b1111
assert v['bank_client']==packed([0,1,2,3,3,2,1,0],2)
assert v['hub_ring_client']==packed([3,2],2)
assert v['rslot']==packed([0,1,2,3,4,5,4,1],3)
spec=layout(new,'NW',True);compiled=compile_schedule(spec,out)
assert spec['bits']==187 and compiled['output_edges']==3
word=int(compiled['configuration_writes'][0]['data'],16)
assert (word>>33)&((1<<24)-1)==v['bank_client']
assert (word>>81)&((1<<24)-1)==v['rslot']
assert (word>>224)&1023==7 and word>>240==0xc7a1
for q in ['SW','SE']:
 s=dict(cycles=[dict(wslot_v=255,wslot=packed([0,1,2,3,4,5,0,1],3))])
 n=migrate(s,q);assert n['cycles'][0]['wslot']==packed([0,2,3,4,5,6,0,2],3)
 compile_schedule(layout(new,q,True),n)
for field,value in [('bank_client',3),('rslot',3),('client_seq',1<<6)]:
 bad=copy.deepcopy(old);bad['cycles'][0][field]=value
 try:migrate(bad,'NW')
 except ValueError:pass
 else:raise AssertionError('retired resource silently retained: '+field)
print('VM_ABI_MIGRATION PASS NW replay/client/read identity; SW/SE write identity;3deleted-resource negatives; unchangedW187 offsets/3loop edges')
