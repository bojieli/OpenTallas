"""Guarded N-only NB sidecar translation. Input exact current M sidecar; writes new output."""
import json,sys,hashlib
from pathlib import Path
src,out=map(Path,sys.argv[1:3]); assert src.resolve()!=out.resolve()
d=json.loads(src.read_bytes());tn='cbn_q00__cldbcda913';r=d['collector']['types'][tn]
targets=[r['bands']['nb_i00']]+[s['band'] for s in r['local_sources'] if s['name']=='nb_i00']
assert len(targets)==2
for b in targets:
 assert b['instance']=='u_cland_nb_i00'
 assert abs(b['rect_um'][0]-1129.392)<1e-6 and abs(b['rect_um'][2]-1218.24)<1e-6,b
 b['rect_um'][0]=1086.192;b['rect_um'][2]=1175.04
out.write_text(json.dumps(d,indent=1)+'\n')
print(json.dumps(dict(input=str(src),input_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),output=str(out),output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),fields_changed=4,preserved='source xy/node/tap, native tree, all cycle/count values, all other types')))
