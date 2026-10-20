import json,collections,hashlib
from pathlib import Path
p=Path('flat.json');m=json.loads(p.read_text())['modules']['ot_qfd_tt_ctlm_static_hr']
loads=collections.Counter();drivers=[];clock=set()
for n,p0 in m['ports'].items():
 if n.startswith('ck_'):clock.update(p0['bits'])
for c in m['cells'].values():
 for pn,b in c['connections'].items():
  if c['port_directions'][pn]=='input' and pn not in ['CLK','CK','VDD','VSS','VPWR','VGND']:
   loads.update(x for x in b if isinstance(x,int))
for _ in range(100):
 old=len(clock)
 for c in m['cells'].values():
  if not c['type'].startswith(('BUF','INV','CLK')):continue
  if any(x in clock for pn,bs in c['connections'].items() if c['port_directions'][pn]=='input' for x in bs):
   clock.update(x for pn,bs in c['connections'].items() if c['port_directions'][pn]=='output' for x in bs if isinstance(x,int))
 if len(clock)==old:break
for n,c in m['cells'].items():
 if c['type'].startswith(('TIE','LOGIC0','LOGIC1')):continue
 for pn,bs in c['connections'].items():
  if c['port_directions'][pn]!='output':continue
  for x in bs:
   if isinstance(x,int) and x not in clock:drivers.append(dict(inst=n,type=c['type'],pin=pn,bit=x,loads=loads[x]))
drivers.sort(key=lambda x:-x['loads']);bad=[x for x in drivers if x['loads']>32]
ports={n:[loads[x] for x in v['bits']] for n,v in m['ports'].items() if v['direction']=='input' and not n.startswith('ck_')}
macros=[dict(inst=n,type=c['type'])for n,c in m['cells'].items() if 'sram' in c['type'].lower()]
seq=[n for n,c in m['cells'].items() if c['type'].startswith(('DFF','SDFF','DF'))]
const_outputs={n:v['bits'] for n,v in m['ports'].items()if v['direction']=='output'and any(isinstance(x,str)for x in v['bits'])}
out=dict(schema='opentallas.segcal.native-driver-census.v1',flat_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),cells=len(m['cells']),flops=len(seq),macros=macros,maximum_nonclock_driver_loads=drivers[0]['loads'],violations=bad,top_drivers=drivers[:30],input_port_loads=ports,constant_output_bits=const_outputs,status='FAIL' if bad else 'PASS_FANOUT_ONLY',not_proven=['storage source-array classification','registered functional boundaries','placed reach <=405um'])
for d in bad:
 d['netnames']=[n for n,v in m['netnames'].items()if d['bit'] in v['bits']]
storage={}
out['fifo_netname_samples']=[n for n in m['netnames']if 'fq' in n][:24]
out['head_netname_samples']=[n for n in m['netnames']if 'hq' in n][:8]
fifo_bits={x for n,v in m['netnames'].items()if '.g_fqwe.g_e[' in n and '].v[' in n for x in v['bits']if isinstance(x,int)}
storage['fqwe_fifo_distinct_retained_bits']=len(fifo_bits)
# Native enable-cone census: kept FIFO write-enable registers feed only
# FIFO data muxes; walk combinational loads and stop at every sequential cell.
we_bits={x for n,v in m['netnames'].items()if '.g_fqwe.g_e['in n and n.endswith('.we')for x in v['bits']if isinstance(x,int)}
users=collections.defaultdict(set)
for cn,c in m['cells'].items():
 for pn,bs in c['connections'].items():
  if c['port_directions'][pn]=='input'and pn not in ['CLK','CK','VDD','VSS']:
   for b in bs:
    if isinstance(b,int):users[b].add(cn)
seen=set(we_bits);todo=list(we_bits);fifo_ff=set()
while todo:
 b=todo.pop()
 for cn in users[b]:
  c=m['cells'][cn]
  if c['type'].startswith(('DFF','SDFF','DF')):fifo_ff.add(cn);continue
  if 'sram'in c['type'].lower():continue
  for pn,bs in c['connections'].items():
   if c['port_directions'][pn]=='output':
    for x in bs:
     if isinstance(x,int)and x not in seen:seen.add(x);todo.append(x)
storage['fifo_write_enable_register_bits']=len(we_bits)
storage['fifo_first_sequential_endpoints_from_native_we']=len(fifo_ff)

for marker in ['.fqv[','.fq[','.hq','.grows[','.rows[']:
 bits={x for n,v in m['netnames'].items()if marker in n for x in v['bits']if isinstance(x,int)}
 storage[marker]=len(bits)
out['retained_storage_net_bits']=storage
Path('native_census.json').write_text(json.dumps(out,indent=2)+'\n');print('NATIVE_CENSUS',out['status'],'max',drivers[0]['loads'],'over32',len(bad),'FF',len(seq),'macros',len(macros))
