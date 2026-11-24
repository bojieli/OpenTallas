#!/usr/bin/env python3
"""Current source CN/IK/pool positives with exact CLOSED reduce/quant wrappers."""
import hashlib,json,sys,shutil
from pathlib import Path
import gate as G
out=Path(sys.argv[1]).resolve();images=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
lvl=int(sys.argv[3]) if len(sys.argv)>3 else 1  # 1: closed reduce/quant wrappers; 2: every engine and pool lane is its wrapper master
src=list(dict.fromkeys(G.H.FP['rtl']+G.S.RTL+G.S.HIER+G.SRC_COMMON+['rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_kv.sv','rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_qn.sv','rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_kvcn.sv',G.TB]))
pins={p:hashlib.sha256((G.ROOT/p).read_bytes()).hexdigest() for p in src}
params=dict(VLAT=4,HARD_RQ=lvl,**({'KV_XD':sys.argv[4]} if len(sys.argv)>4 else {}),**({'KV_KST':sys.argv[5]} if len(sys.argv)>5 else {}))
params.update(a.split('=',1) for a in sys.argv[6:])  # later K=V win (VLAT=5: the OT_S81SL_VP_SRAMREG store loop); recorded in the receipt
exe=G.build(out,f'hard_rq{lvl}','tb_s81sl_kv_leaf_sukv',src,params)
results={}
for name in ('L2','L14','L20'):
 d=out/name;d.mkdir(exist_ok=True)
 for p in (images/name).glob('*.mem'):shutil.copy2(p,d/p.name)
 args=(['+CP'] if name!='L20' else [])+(['+KV'] if name=='L14' else [])
 rc,s=G.run(exe,d,args,'run.log');results[name]=dict(ok=rc==0 and 'SUKV PASS' in s,lines=[l for l in s.splitlines() if l.startswith('SUKV')])
assert pins=={p:hashlib.sha256((G.ROOT/p).read_bytes()).hexdigest() for p in pins},'source changed'
r=dict(hard_rq=lvl,params=params,status='PASS' if all(v['ok'] for v in results.values()) else 'FAIL',source_sha256=pins,results=results,scope='current source hard reduce/quant wrapper positives; inherited causal suite separate')
(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['results'],indent=2));sys.exit(0 if r['status']=='PASS' else 1)
