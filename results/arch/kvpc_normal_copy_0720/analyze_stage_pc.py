import json,gzip,hashlib,collections,sys
from pathlib import Path
p=Path(sys.argv[1]);o=Path(sys.argv[2]);o.mkdir(exist_ok=True)
d=json.load(gzip.open(p,'rt'));assert d['status']=='PASS' and not d['role_errors']
seq={x['instance']:x for x in d['sequential_instances']};ports={x['pin']:x for x in d['port_bits']}
cnt=collections.Counter();bad=collections.Counter();mx={};worst=[];viol=[]
def cls(x):
 if x['kind'].startswith('synchronous_sram') or x['kind'].startswith('memory_'):return 'macro'
 return seq.get(x.get('instance'),{}).get('boundary_classification',x['kind'])
def add(a,b,scope):
 dist=sum(abs(x-y) for x,y in zip(a['xy_um'],b['xy_um']));k=scope+':'+cls(a)+' -> '+cls(b);cnt[k]+=1;mx[k]=max(mx.get(k,0),dist)
 if dist>405+1e-8:
  r={'root':a,'endpoint':b,'scope':scope,'L1_um':dist};bad[k]+=1;viol.append(r)
for e in d['data_stage_edges']:add(e['root'],e['endpoint'],'data_to_seq_or_macro')
# Explicitly include interface outputs; the inherited data_stage_edges collection only ends at sequential inputs.
for e in d['output_port_sources']:
 for a in e['roots']:add(a,ports[e['port']],'to_output_port')
# Keep reset/preset/other sequential-control endpoint reach separately visible, not silently omitted as data-only.
for s in d['sequential_instances']:
 for e in s['input_pins']:
  if e['kind'] not in ['data_next_state','memory_data_control']:
   for a in e['roots']:add(a,e,'async_or_other_control')
viol.sort(key=lambda x:-x['L1_um'])
s={'scope':'PRE-CTS normalPC6 all data-stage endpoints including interface outputs and separate async/other sequential controls, through actual Liberty functions. Stdcell centers approximate pin XY; macro exactpinXY. Clock/constant-only sources excluded. NO finalstage/admission/physicalclosure claim.','input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'odb_sha256':d['odb_sha256'],'pairs':sum(cnt.values()),'over405':len(viol),'max_L1_um':viol[0]['L1_um'] if viol else 0,'all_pairs_by_class':dict(cnt),'over405_by_class':dict(bad),'max_L1_by_class':mx,'worst20':viol[:20]}
(o/'reach_summary.json').write_text(json.dumps(s,indent=2)+'\n')
with gzip.open(o/'reach_violations.json.gz','wt') as f:json.dump(viol,f,separators=(',',':'))
print(json.dumps({k:s[k] for k in ['pairs','over405','max_L1_um','over405_by_class']},indent=2))
