import json,subprocess,sys,re,os
from pathlib import Path
v=sys.argv[1];p=Path('physical/ref_tile')/f's81sl_lepmu{v}_dr/job.json';d=json.loads(p.read_text());root=Path.cwd()/f'campaign_{v}';root.mkdir(exist_ok=True)
results=[]
for b in d['stages']['bench']:
 cmd=b['cmd'].replace('{RUN}',str(root)).replace('MU_RX_SRAM=1','MU_CTRL32=1 MU_RX_SRAM=1')
 r=subprocess.run(['bash','-lc',cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (root/(b['name']+'.log')).write_text(r.stdout)
 pattern=b.get('pass_regex') if b['expect']=='pass' else b.get('fail_regex')
 ok=(r.returncode==0 if b['expect']=='pass' else r.returncode!=0) and (not pattern or bool(re.search(pattern,r.stdout,re.M)))
 results.append({'name':b['name'],'expect':b['expect'],'rc':r.returncode,'matched':ok});print(results[-1],flush=True)
 (root/'summary.json').write_text(json.dumps(results,indent=2))
print('CAMPAIGN_PASS' if all(x['matched'] for x in results) else 'CAMPAIGN_FAIL',flush=True)
sys.exit(0 if all(x['matched'] for x in results) else 1)
