#!/usr/bin/env python3
"""Compare current W128 subtree composition at all original adder/client boundaries."""
import argparse,json,re,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--source-commit',required=True);a=ap.parse_args();r=a.root.resolve();o=r/'miter';o.mkdir(exist_ok=True);top='ot_hbm_hc_qhub_static';y=str(Path.home()/'.local/opentallas-tools/bin/yosys')
def run(n,s):
 p=o/(n+'.ys');p.write_text(s);return subprocess.run([y,'-ql',str(o/(n+'.log')),'-s',str(p)]).returncode
prep=''
for label,path in [('gold',r/'qhub128.json'),('gate',r/'compact/qhub_compact128.json')]:
 prep+=f'read_json {path}\nblackbox ot_hdc_fp32_add_lat*\nsetattr -unset keep_hierarchy\nsetattr -mod -unset keep_hierarchy\nhierarchy -top {top}\nflatten\nwrite_json {o}/{label}_flat.json\ndesign -reset\n'
assert run('prep',prep)==0
j={n:json.loads((o/(n+'_flat.json')).read_text()) for n in ['gold','gate']}
m=j['gate']['modules'][top];ren={}
for n,c in m['cells'].items():
 mat=re.match(r'^(.*)ot_hbm_hc_subtree32_([0-3])\\?\.(.*)$',n)
 if mat and c['type'].startswith('ot_hdc_fp32_add_lat'):
  prefix,k,tail=mat[1],int(mat[2]),mat[3]
  tail=re.sub(r'g_lvl\[(\d+)\]\.g_n\[(\d+)\]',lambda z:f'g_lvl[{z[1]}].g_n[{int(z[2])+k*((128>>int(z[1]))//4)}]',tail)
  n=prefix+tail
 assert n not in ren,n
 ren[n]=c
m['cells']=ren
gm=j['gold']['modules'][top];points=[]
for n in sorted(set(gm['cells']) & set(m['cells'])):
 x,z=gm['cells'][n],m['cells'][n]
 if x['type'].startswith('$') and x['port_directions'].get('Q')=='output':
  assert x['type']==z['type'] and x.get('parameters')==z.get('parameters'),n
  assert len(x['connections']['Q'])==len(z['connections']['Q']),n
  pn='proof_state_'+str(len(points));points.append(n)
  gm['ports'][pn]=dict(direction='output',bits=x['connections']['Q']);m['ports'][pn]=dict(direction='output',bits=z['connections']['Q'])
for n in j:(o/(n+'.json')).write_text(json.dumps(j[n]))
mut=json.loads(json.dumps(j['gate']));cells=mut['modules'][top]['cells'];target=next(n for n,c in cells.items() if c['type'].startswith('ot_hdc_fp32_add_lat'));port=next(p for p,d in cells[target]['port_directions'].items() if d=='input' and len(cells[target]['connections'][p])==32);cells[target]['connections'][port]=['0']*32;(o/'mutant.json').write_text(json.dumps(mut))
result=dict(schema='opentallas.hbm.hc128.qhub_miter.v1',source_commit=a.source_commit,split_cycles=0,state_points=len(points),scope='original qhub outputs plus every unchanged FP adder/client boundary input',checks={})
for mode in ['gate','mutant']:
 script=''
 for src,name in [('gold','gold'),(mode,'gate')]:
  script+=f'read_json {o}/{src}.json\nexpose -evert t:ot_hdc_fp32_add_lat* t:ot_hbm_hc_q_static\nrename -hide\nrename {top} {name}\nwrite_rtlil {o}/{name}.il\ndesign -reset\n'
 script+=f'read_rtlil {o}/gold.il\nread_rtlil {o}/gate.il\nasync2sync\nequiv_make gold gate eq\nsetattr -unset keep_hierarchy\nsetattr -mod -unset keep_hierarchy\nhierarchy -top eq\nopt -full\nequiv_simple -seq 2\nequiv_induct -seq 24\ntee -o {o}/{mode}_status.txt equiv_status\nequiv_status -assert\n'
 rc=run(mode,script);status=(o/(mode+'_status.txt')).read_text();ma=re.search(r'Of those cells (\d+) are proven and (\d+) are unproven',status);assert ma,(mode,rc)
 proven,unproven=map(int,ma.groups());verdict='PASS' if mode=='gate' and rc==0 and unproven==0 else 'CAUGHT' if mode=='mutant' and rc!=0 and unproven>0 else 'FAIL';result['checks'][mode]=dict(verdict=verdict,proven=proven,unproven=unproven,rc=rc);assert verdict!='FAIL',result
result['verdict']='PASS';(o/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
