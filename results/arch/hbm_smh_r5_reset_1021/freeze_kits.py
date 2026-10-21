import subprocess,sys,json
from pathlib import Path
r=Path(__file__).parent;src=r/'src';rows=[];rc=0
for f in ['n_m','n_f','s_m','s_f']:
 log=r/('gen_'+f+'.log')
 with log.open('w') as out:one=subprocess.call(['python3','tools/ref_tile/ref_tile.py','gen','physical/ref_tile/smh_rp5'+f+'/spec.json','--commit','8060df44e'],cwd=src,stdout=out,stderr=subprocess.STDOUT)
 rows.append(dict(form=f,rc=one,log=log.name));rc=max(rc,one);print('RESET_KIT_GEN_EXIT',f,one,flush=True)
(r/'gen_receipt.json').write_text(json.dumps(rows,indent=2)+'\n')
raise SystemExit(rc)
