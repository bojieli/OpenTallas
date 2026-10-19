#!/usr/bin/env python3
import collections,copy,hashlib,json,pathlib,subprocess
p=pathlib.Path('native_final');j=json.loads((p/'candidate.json').read_text());m=j['modules']['qfd_dv_stream_controls']
for n,c in m['cells'].items():c['attributes']['qwen_id']=n
(p/'tagged.json').write_text(json.dumps(j))
subprocess.run(['yosys','-Q','-T','-p','read_json native_final/tagged.json; write_verilog native_final/qfd_dv_stream_controls_retained.v; design -reset; read_liberty -lib mapped/combined.lib; read_verilog native_final/qfd_dv_stream_controls_retained.v; hierarchy -top qfd_dv_stream_controls; write_json native_final/reimport.json; stat -liberty mapped/combined.lib'],check=True,stdout=(p/'reimport.log').open('w'),stderr=subprocess.STDOUT)
r=json.loads((p/'reimport.json').read_text())['modules']['qfd_dv_stream_controls']
def normal(d,tag):
 identities={n:(c['attributes']['qwen_id'] if tag else n) for n,c in d['cells'].items()};drivers={}
 for pn,v in d['ports'].items():
  if v['direction']=='input':
   for b,x in enumerate(v['bits']):drivers[x]=('PORT',pn,b)
 for n,c in d['cells'].items():
  for pn,bs in c['connections'].items():
   if c['port_directions'][pn]=='output':
    for b,x in enumerate(bs):
     assert x not in drivers,(x,n,pn);drivers[x]=('CELL',identities[n],pn,b)
 def net(x):return drivers[x] if isinstance(x,int) else ('CONST',x)
 cells={identities[n]:{'type':c['type'],'parameters':c['parameters'],'ports':{pn:[net(x) for x in bs] for pn,bs in c['connections'].items()}} for n,c in d['cells'].items()}
 ports={pn:{'direction':v['direction'],'bits':[net(x) for x in v['bits']]} for pn,v in d['ports'].items()}
 return cells,ports
assert normal(m,False)==normal(r,True),'emitted native source changes primitive equation/connectivity'
loads=collections.defaultdict(list);drivers={}
for n,c in r['cells'].items():
 assert not c['type'].startswith('$_'),c['type']
 for pn,bs in c['connections'].items():
  for b in bs:
   if not isinstance(b,int):continue
   if c['port_directions'][pn]=='input':loads[b].append((n,pn))
   else:drivers[b]=(n,pn)
clock=set(r['ports']['ck']['bits']);rows=[]
for b in set(loads)-clock:
 if b in drivers and r['cells'][drivers[b][0]]['type'].startswith(('INV','BUF')):continue
 todo=[b];seen=set();ends=set()
 while todo:
  x=todo.pop()
  if x in seen:continue
  seen.add(x)
  for n,pn in loads.get(x,[]):
   c=r['cells'][n]
   if c['type'].startswith(('INV','BUF')):todo.extend(bb for op,bs in c['connections'].items() if c['port_directions'][op]=='output' for bb in bs)
   else:ends.add((n,pn))
 rows.append({'net':b,'direct':len(loads[b]),'ultimate':len(ends)})
assert max(x['ultimate'] for x in rows)<=32
assert max(len(ls) for b,ls in loads.items() if b not in clock)<=32
copied=[(n,c) for n,c in m['cells'].items() if n.startswith('sc_copy_') and c['type'].startswith('DFF')]
assert len(copied)==1 and copied[0][1]['type']=='DFFASRHQNx1_ASAP7_75t_R'
info={'cells':len(r['cells']),'native_ff':sum(c['type'].startswith('DFF') for c in r['cells'].values()),'new_native_ff':copied,'native_master_pin_connectivity_exact_after_emission':True,'max_direct_nonclock':max(len(ls) for b,ls in loads.items() if b not in clock),'max_transparent_ultimate':max(x['ultimate'] for x in rows),'source_sha256':hashlib.sha256((p/'qfd_dv_stream_controls_retained.v').read_bytes()).hexdigest(),'clock_loads':sum(len(loads[x]) for x in clock),'qualified':False,'initialization':'Only new consumer state is one exact asynchronous-reset open-copy FF; reset/source input equivalence implies identical value after assertion and forever by native equation induction. External predecessor copies must independently prove their reset/first qualified use.'}
(p/'native_census.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info,indent=2))
