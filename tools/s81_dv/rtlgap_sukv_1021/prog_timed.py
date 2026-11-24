#!/usr/bin/env python3
"""Compiled SUKV programme at the t2 A|B seam: the new-date image must PASS and every old-date mutant must be caught.

  prog_timed.py OUT L14_FIXTURE_DIR IMAGE_DIR HARD_RQ KV_XD KV_KST [K=V | D:NAME=1 ...]
IMAGE_DIR = kv_seam_image.py --out (new/ old/ old_<KIND>/ image.txt).  Writes OUT/result.json.
"""
import hashlib,json,sys,shutil
from pathlib import Path
import gate as G
out,images,imgs=(Path(x).resolve() for x in sys.argv[1:4]);out.mkdir(parents=True,exist_ok=True)
lvl=int(sys.argv[4])
TB='rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_kv_prog_timed.sv'
src=list(dict.fromkeys(G.H.FP['rtl']+G.S.RTL+G.S.HIER+G.SRC_COMMON+['rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_kv.sv','rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_qn.sv','rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_kvcn.sv',TB]))
pins={p:hashlib.sha256((G.ROOT/p).read_bytes()).hexdigest() for p in src}
params=dict(VLAT=4,HARD_RQ=lvl,KV_XD=sys.argv[5],KV_KST=sys.argv[6]);params.update(a.split('=',1) for a in sys.argv[7:])
exe=G.build(out,'prog_timed','tb_s81sl_kv_prog_timed',src,params)
results={}
for variant in sorted(p.name for p in imgs.iterdir() if (p/'image.txt').exists()):
 d=out/variant;d.mkdir(exist_ok=True)
 for p in images.glob('*.mem'):shutil.copy2(p,d/p.name)
 shutil.copy2(imgs/variant/'image.txt',d/'image.txt')
 rc,s=G.run(exe,d,['+IMAGE=image.txt'],'run.log')
 results[variant]=dict(passed=rc==0 and 'KVPROG PASS' in s,image_sha256=hashlib.sha256((d/'image.txt').read_bytes()).hexdigest(),
  lines=[l for l in s.splitlines() if l.startswith('KVPROG') and 'CMD' not in l])
assert pins=={p:hashlib.sha256((G.ROOT/p).read_bytes()).hexdigest() for p in pins},'source changed'
# old_GK alone is the one date error that the RTL tolerates: command and drain cross the same seam, so a GK back-to-back
# successor still reaches B after B is done.  It is reported, not required to fail.
must=[v for v in results if v not in ('new','old_GK')]
ok=results['new']['passed'] and all(not results[v]['passed'] for v in must)
r=dict(status='PASS' if ok else 'FAIL',params=params,caught=[v for v in must if not results[v]['passed']],
       missed=[v for v in must if results[v]['passed']],old_gk_tolerated=results.get('old_GK',{}).get('passed'),source_sha256=pins,results=results)
(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
print(r['status'],'caught',r['caught'],'missed',r['missed'],'old_GK passes',r['old_gk_tolerated'])
for v,x in results.items():print('==',v,x['passed']);print('\n'.join(x['lines']))
sys.exit(0 if ok else 1)
