import json,collections,hashlib
from pathlib import Path
j=json.loads(Path('shadow_full.json').read_text());m=j['modules']['ot_hgi_coll_tkm_tp192_root_core_x'];q=m['netnames']['ot_tk_shadow_q']['bits'];cs=m['cells'];ff=[(n,c) for n,c in cs.items() if c['connections'].get('Q')==q];assert len(ff)==1
name,f=ff[0];root=f['connections']['D'];drivers={}
for n,c in cs.items():
 for p,d in c.get('port_directions',{}).items():
  if d=='output':
   for b in c['connections'][p]:
    if isinstance(b,int):drivers[b]=n
state=('$adff','$dff','$sdff','$dlatch','$mem');keep=set();inputs=set();todo=list(root)
while todo:
 b=todo.pop()
 if not isinstance(b,int):continue
 n=drivers.get(b)
 if n is None or cs[n]['type'].startswith(state):inputs.add(b);continue
 if n in keep:continue
 keep.add(n)
 for p,d in cs[n].get('port_directions',{}).items():
  if d=='input':todo.extend(cs[n]['connections'][p])
cells={n:cs[n] for n in keep};bits=sorted(inputs);out={'attributes':{'top':1},'ports':{'state':{'direction':'input','bits':bits},'shadow_d':{'direction':'output','bits':root}},'cells':cells,'netnames':{}}
Path('shadow_cone.json').write_text(json.dumps({'creator':'actual source shadow D combinational cut','modules':{'tkm_shadow_d':out}}))
Path('shadow_cone_binding.json').write_text(json.dumps({'source_sha256':hashlib.sha256(Path('shadow_source.sv').read_bytes()).hexdigest(),'state_bits':len(bits),'cells':len(keep),'native_shadow_ff':name,'ff_type':f['type'],'D':root,'Q':q},indent=2))
