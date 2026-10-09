#!/usr/bin/env python3
"""Native command table gate; production dispatch dependencies stay explicit."""
import copy,json,sys
from pathlib import Path
from native_descriptors import compile_jobs
root=Path(sys.argv[1])
registry=json.loads((root/'tools/s81_ctrl/native_registry.json').read_text())
window=(1<<67)|(99091<<34)|(2<<17)|17
request={'context':{'win_ids':window,'rank':3},'jobs':[
 {'id':'L1.eng.lookup','engine':10},{'id':'L14.eng.lookup','engine':10}]}
result=compile_jobs(request,registry,root)
assert result['command_table_eligible'] and not result['dispatch_eligible'],result
assert result['unbound_endpoints']==['L1.eng.lookup','L14.eng.lookup']
for row,layer in zip(result['rows'],[0,1]):
 assert int(row['signals']['win_ids']['hex'],16)==window
 assert int(row['signals']['cfg_rank']['hex'],16)==3
 assert int(row['signals']['cfg_layer']['hex'],16)==layer
checks=3
for field,value in [('win_ids',1<<68),('rank',4),('win_ids',-1)]:
 bad=copy.deepcopy(request);bad['context'][field]=value
 out=compile_jobs(bad,registry,root)
 assert not out['command_table_eligible'] and not out['rows'];checks+=1
bad=copy.deepcopy(request);del bad['context']['win_ids']
out=compile_jobs(bad,registry,root)
assert not out['command_table_eligible'] and not out['rows'];checks+=1
bad=copy.deepcopy(request);bad['jobs'].append({'id':'unknown','engine':10})
out=compile_jobs(bad,registry,root)
assert not out['command_table_eligible'] and not out['rows'];checks+=1
print(f'ENGRAM_NATIVE_COMMAND_SCHEMA width68 layer0/1 rank3 checks{checks} PASS dispatch_eligible0 pending_common_sequence_publication_retirement_and_gate_mask')
