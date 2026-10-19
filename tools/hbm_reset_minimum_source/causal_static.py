import json,copy
from pathlib import Path
p=Path('.')
t=json.loads((p/'compressed_topology.json').read_text());s=json.loads((p/'sinks.json').read_text());rows=json.loads((p/'downstream_row_composition.json').read_text());base=json.loads((p/'row_ownership.json').read_text())
def check(top,sinks,row):
 assert all(x['path_um']+3<=405 for x in top),'REACH'
 assert all(max(x['trunk_transparent_loads'],x['clock_direct_loads'],x['leaf_maxload'])<=32 for x in top),'FANOUT'
 for a,b in zip(sinks,s):assert (a['instance'],a['port'],a['bit'],a['domain'],a['source'])==(b['instance'],b['port'],b['bit'],b['domain'],b['source']),'OWNERSHIP'
 for a in row:assert a['head_original_offset']==base['heads'][a['head']],'ROW_OFFSET'
 return True
assert check(t,s,rows)
cases=[]
for name,expected in [('reach406','REACH'),('fanout33','FANOUT'),('ownership_swap','OWNERSHIP'),('omitted_row_offset','ROW_OFFSET')]:
 a,b,c=copy.deepcopy((t,s,rows))
 if name=='reach406':a[0]['path_um']=403
 elif name=='fanout33':a[0]['trunk_transparent_loads']=33
 elif name=='ownership_swap':b[0]['instance'],b[1]['instance']=b[1]['instance'],b[0]['instance']
 else:next(x for x in c if x['head_original_offset']!=0)['head_original_offset']=0
 try:check(a,b,c)
 except AssertionError as e:assert str(e)==expected;cases.append({'mutant':name,'refused':str(e)});(p/(name+'_witness.log')).write_text('EXPECTED_CAUSAL_REFUSAL '+str(e)+'\n')
 else:raise AssertionError('mutant escaped '+name)
(p/'causal_static_receipt.json').write_text(json.dumps(cases,indent=2)+'\n');print(cases)
