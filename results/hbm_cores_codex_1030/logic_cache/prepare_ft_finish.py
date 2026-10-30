import json,hashlib,shutil
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-hbm-cores-1030/ftshape')
for label,base in [('collar','ot_hbm_static_cfg_collar_idx256r_ae70500553b2-_ftshape1030'),('query','ot_hbm_idx_query_static_8685b722456c-_ftshape1030')]:
 k=r/'kits'/base
 assert json.load(open(k/'lec/lec.json'))['verdict']=='EQUIVALENT'
 inventories={g:sorted(str(p.relative_to(k)) for p in (k/g).rglob('*') if p.is_file()) for g in ['rtl','macros','reset_contract']}
 files=[n for v in inventories.values() for n in v]+['config.mk','freeze.json','reset_contract.json','lec/lec.json','lec/gold.ys','lec/gold.aig','lec/gate.ys','lec/gate.aig']
 files += ['lec.py','run_kit_hbm.sh']
 for must in ['lec/lec.json','lec/gold.ys','lec/gold.aig','lec/gate.ys','lec/gate.aig']: assert (k/must).is_file(),must
 files += [str(p.relative_to(k)) for p in (k/'run/results/asap7').glob('*/base/1*.v')]
 manifest=dict(inventories=inventories,files={n:hashlib.sha256((k/n).read_bytes()).hexdigest() for n in files if (k/n).is_file()})
 (k/'lec/native_cache.json').write_text(json.dumps(manifest,indent=1)+'\n')
 shutil.copyfile(r/'check_native_cache.py',k/'check_native_cache.py')
 s=(k/'run_kit_hbm.sh').read_text()
 old='python3 -I /work/lec.py /work --netlist \\$N --out /work/lec'
 new='( python3 -I /work/check_native_cache.py /work || python3 -I /work/lec.py /work --netlist \\$N --out /work/lec )'
 assert s.count(old)==1,(label,s.count(old))
 s=s.replace(old,new)
 marker='elif [ \\$lr != 0 ]; then echo'
 assert s.count(marker)==1
 s=s.replace(marker,'elif [ \\$lr != 0 ]; then rc=3; echo').replace('LEC WARNING','LEC NOT QUALIFIED').replace('the flow continues','stopping before P&R')
 (r/('finish_'+label+'_cached.sh')).write_text(s)
 print('PREPARED_NATIVE_CACHE',label,len(manifest['files']))
