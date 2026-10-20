"""Complete nonclock endpoint-stage diagnostics plus nominal boundary overlay."""
import json,gzip,collections,sys,hashlib
from pathlib import Path
p=Path(sys.argv[1]);d=json.load(gzip.open(p,'rt'));m=json.load(open(sys.argv[2]));ff=m['FF_nominal_targets'];ports=m['ports'];w,h=m['outline_um'];counts=collections.Counter();maxima={};worst={}
def target(z):
 if z.get('instance') in ff:return ff[z['instance']]
 if z['kind']=='output_port' or z['kind']=='input_port':
  n=z['pin'];a=ports[n]['along_um'];f=ports[n]['face'];return [0,a] if f=='W' else [w,a] if f=='E' else [a,0] if f=='S' else [a,h]
 return z['xy_um']
def check(a,b,category):
 for mode in ('actual_preCTS','nominal_boundary_overlay'):
  x,y=(a['xy_um'],b['xy_um']) if mode=='actual_preCTS' else (target(a),target(b));dist=sum(abs(u-v)for u,v in zip(x,y));key=mode+':'+category;counts[key+':pairs']+=1
  if dist>405+1e-8:counts[key+':over405']+=1
  if dist>maxima.get(key,-1):maxima[key]=dist;worst[key]={'root':a,'endpoint':b,'evaluated_root_xy':x,'evaluated_endpoint_xy':y,'L1_um':dist}
for e in d['data_stage_edges']:check(e['root'],e['endpoint'],'data_to_seq_or_memory')
for s in d['sequential_instances']:
 for e in s['input_pins']:
  if e['kind'] in ('data_next_state','memory_data_control'):continue
  for a in e['roots']:check(a,e,'async_or_other_seq_control')
byport={x['pin']:x for x in d['port_bits']}
for e in d['output_port_sources']:
 for a in e['roots']:check(a,byport[e['port']],'roots_to_output_port')
r={'schema':'peer.complete_nonclock_stage_overlay.v1','identity_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'pin_model_sha256':hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(),'scope':'Actual frozen3_place plus nominal boundary-only pin/FF overlay, interior FFs and macro coordinates unchanged. Standardcell centers approximate actual pin XY; macro actualpin. data_stage_edges augmented with all captured nondata seq controls and output-port roots; constants retained in separate source identity. No legalization, reach or physical approval.','counts':dict(counts),'max_L1_um':maxima,'worst':worst}
p.with_name('complete_stage_overlay.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k!='worst'})
