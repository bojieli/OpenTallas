#!/usr/bin/env python3
"""Make one explicit corrupt synthesizable source for a mechanism witness."""
import argparse,json,re,shutil,subprocess,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('profile');ap.add_argument('kind',choices=['copy_d','reset_short','buffer_input','gate_input']);a=ap.parse_args()
p=Path(a.profile);o=Path(a.profile+'_mut_'+a.kind);(o/'generated').mkdir(parents=True,exist_ok=True)
if not (p/'miter/miter.sv').exists():
 subprocess.run([sys.executable,str(Path(__file__).with_name('build_miter.py')),'--graph',str(p/'original.json'),'--manifest',str(p/'manifest.json'),'--receipt',str(p/'generated/receipt.json'),'--source','rtl/qwen_split/qfd_sys_face.sv','--out',str(p/'miter')],check=True)
for n in ['reference.sv','miter.sv','buffer_model.sv']:
 (o/'miter').mkdir(exist_ok=True);shutil.copy2(p/'miter'/n,o/'miter'/n)
r=json.loads((p/'generated/receipt.json').read_text());g=json.loads((p/'generated/graph.json').read_text());cells=next(iter(g['modules'].values()))['cells'];names=sorted(cells)
if a.kind=='copy_d':
 n=r['copies'][0]['cell'];idx=names.index(n);port='D';new='~'+('n'+str(cells[n]['connections']['D'][0]) if isinstance(cells[n]['connections']['D'][0],int) else "1'b"+cells[n]['connections']['D'][0]);inst='f'+str(idx)
elif a.kind=='reset_short':
 n=next(x['cell'] for x in r['forest'] if x['depth']==3);idx=names.index(n);port='R';new='n'+str(next(x['q'] for x in r['forest'] if x['depth']==1));inst='f'+str(idx)
elif a.kind=='gate_input':
 n=next(x['cell'] for x in r['useful_copies'] if cells[x['cell']]['type'] in ['$_AND_','$_OR_','$_XOR_']);idx=names.index(n);port='A';b=cells[n]['connections']['A'][0];new='~'+('n'+str(b) if isinstance(b,int) else "1'b"+b);inst='g'+str(idx)
else:
 n=r['buffers'][0]['cell'];idx=names.index(n);port='A';new='~n'+str(cells[n]['connections']['A'][0]);inst='b'+str(idx)
s=(p/'generated/parent.sv').read_text();lines=s.splitlines();hits=0
for i,line in enumerate(lines):
 if re.search(r'\b'+inst+r'\(',line):
  lines[i],count=re.subn(r'\.'+port+r'\([^)]*\)',lambda _:'.'+port+'('+new+')',line);assert count==1;hits+=1
assert hits==1
(o/'generated/parent.sv').write_text('\n'.join(lines)+'\n')
(o/'mutation.json').write_text(json.dumps({'kind':a.kind,'cell':n,'instance':inst,'port':port,'new':new},indent=2)+'\n')
print(o)
