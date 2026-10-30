import json,hashlib
from pathlib import Path
P=Path('/srv/opentallas-scratch2/claude/die-hbm-29/b29d/out/asbuilt.json');y=json.load(P.open());M=y['modules'];out=[]
for side in ('NE','NW'):
 m=M['hbm_current_native_top'];mp={};trace=[];prefix=''
 for child in ('hb_coll_'+side,'u_body','u_ring'):
  c=m['cells'][child];prefix+=('.' if prefix else '')+child
  q=c['connections']['qid'];vals=[b if isinstance(b,str) else mp.get(b,(prefix,b)) for b in q];trace.append(dict(path=prefix,port='qid',local_bits=q,resolved=vals))
  nxt=M[c['type']];npm={}
  for pn,port in nxt['ports'].items():
   bs=c['connections'].get(pn,[])
   for i,b in enumerate(port['bits']):
    if isinstance(b,str) or i>=len(bs):continue
    cb=bs[i];v=cb if isinstance(cb,str) else mp.get(cb,(prefix,cb))
    if b not in npm or isinstance(v,str):npm[b]=v
  m,mp=nxt,npm
 assert len(vals)==2 and all(v in ('0','1') for v in vals),(side,trace)
 out.append(dict(side=side,value=sum(int(v)<<i for i,v in enumerate(vals)),lsb_bits=vals,terminals=[dict(member=prefix,port='qid',bit=i,value=v) for i,v in enumerate(vals)],trace=trace))
R=Path('/srv/opentallas-scratch2/claude/codex-hbm-bind-2249/ring_qid_actual.json');R.write_text(json.dumps(dict(source=str(P),source_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),rows=out),indent=1));print(json.dumps(out,indent=1))
