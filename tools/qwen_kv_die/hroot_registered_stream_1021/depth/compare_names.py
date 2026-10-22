from pathlib import Path
import json,hashlib,collections
import textbook_lint as T
j=json.loads(Path('mapped_names.json').read_text())['modules']['qkd_host_native_engine']
g,_=T.flatten(T.parse_verilog(Path('original.v').read_text()),None)
h,_=T.flatten(T.parse_verilog(Path('named.v').read_text()),None)
assert len(g.cells)==len(h.cells),(len(g.cells),len(h.cells))
fwd={};back={};cells={}
for (gt,gn,gp),(ht,hn,hp)in zip(g.cells,h.cells):
 assert gt==ht,(gn,hn,gt,ht)
 assert gp.keys()==hp.keys(),(gn,hn)
 cells[gn]=hn
 for pin,ns in gp.items():
  ms=hp[pin];assert len(ns)==len(ms),(gn,pin)
  for a,b in zip(ns,ms):
   assert a not in fwd or fwd[a]==b,('net divergence',gn,pin,a,b,fwd.get(a))
   assert b not in back or back[b]==a,('reverse net divergence',hn,pin,a,b,back.get(b))
   fwd[a]=b;back[b]=a
r=json.loads(Path('profile.json').read_text());out=dict(status='PASS_IDENTICAL_ORDERED_CELLS_PINS_AND_BIJECTIVE_NET_CONNECTIVITY',cells=len(cells),nets=len(fwd),source_endpoint_map={})
for key in ['start','endpoint']:
 old=r['reg_to_reg_top'][0][key].split('/')[0];name=cells[old];out['source_endpoint_map'][key]=dict(original=old,named=name,source_attributes=j['cells'][name.lstrip('\\')]['attributes'])
Path('name_correspondence.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
