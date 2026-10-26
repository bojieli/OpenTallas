#!/usr/bin/env python3
"""Current source CN/IK/pool positives with exact CLOSED reduce/quant wrappers."""
import hashlib,json,sys,shutil
from pathlib import Path
import gate as G
out=Path(sys.argv[1]).resolve();images=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
src=list(dict.fromkeys(G.H.FP['rtl']+G.S.RTL+G.S.HIER+G.SRC_COMMON+['rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_kv.sv',G.TB]))
pins={p:hashlib.sha256((G.ROOT/p).read_bytes()).hexdigest() for p in src}
exe=G.build(out,'hard_rq','tb_s81sl_kv_leaf_sukv',src,dict(VLAT=4,HARD_RQ=1))
results={}
for name in ('L2','L14','L20'):
 d=out/name;d.mkdir(exist_ok=True)
 for p in (images/name).glob('*.mem'):shutil.copy2(p,d/p.name)
 args=(['+CP'] if name!='L20' else [])+(['+KV'] if name=='L14' else [])
 rc,s=G.run(exe,d,args,'run.log');results[name]=dict(ok=rc==0 and 'SUKV PASS' in s,lines=[l for l in s.splitlines() if l.startswith('SUKV')])
assert pins=={p:hashlib.sha256((G.ROOT/p).read_bytes()).hexdigest() for p in pins},'source changed'
r=dict(status='PASS' if all(v['ok'] for v in results.values()) else 'FAIL',source_sha256=pins,results=results,scope='current source hard reduce/quant wrapper positives; inherited causal suite separate')
(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['results'],indent=2));sys.exit(0 if r['status']=='PASS' else 1)
