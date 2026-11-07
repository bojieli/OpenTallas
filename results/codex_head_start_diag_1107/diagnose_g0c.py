import sys,json,subprocess,tarfile,io,hashlib
from pathlib import Path
T=Path(sys.argv[1]);O=Path(sys.argv[2]);O.mkdir(parents=True,exist_ok=True)
def git(*a):return subprocess.check_output(['git','-C',str(T),*a])
plan_rel='results/die_head_52_1031/pin/source_plan_l48x.json';raw=json.loads(git('show','93c061c396c:'+plan_rel))
refs=set()
def visit(x):
 if isinstance(x,str) and x.startswith('results/'):refs.add(x)
 elif isinstance(x,dict):
  for v in x.values():visit(v)
 elif isinstance(x,list):
  for v in x:visit(v)
visit(raw)
paths=['results/die_head_47_1031/l47']
for r in sorted(refs):
 if subprocess.run(['git','-C',str(T),'cat-file','-e','93c061c396c:'+r],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:paths.append(r)
p=subprocess.Popen(['git','-C',str(T),'archive','93c061c396c',*paths],stdout=subprocess.PIPE)
with tarfile.open(fileobj=p.stdout,mode='r|') as a:a.extractall(O,filter='data')
assert p.wait()==0
D=O/'physical/die_plan/s81_head';D.mkdir(parents=True,exist_ok=True)
import shutil
for f in (O/'results/die_head_47_1031/l47').rglob('*'):
 if f.is_file() and f.name not in ['die_plan.json','SHA256SUMS']:
  rel=str(f.relative_to(O/'results/die_head_47_1031/l47'));dst=D/(rel[:-3] if rel.endswith('.gz') else rel);dst.parent.mkdir(parents=True,exist_ok=True)
  if f.name.endswith('.gz'):
   import gzip;dst.write_bytes(gzip.decompress(f.read_bytes()))
  else:shutil.copyfile(f,dst)
def localize(x):
 if isinstance(x,str) and x.startswith('results/') and (O/x).is_file():return str(O/x)
 if isinstance(x,dict):return {k:localize(v) for k,v in x.items()}
 if isinstance(x,list):return [localize(v) for v in x]
 return x
raw=localize(raw);F=D/'source_plan_l48x.json';F.write_text(json.dumps(raw))
sys.path.insert(0,str(T/'tools/die_plan'));import schema as S,reset_tree as RT
P=S.Plan(raw,path=F);out={}
for tn in ['hd_ctl','hd_spn_wshim_rx','hd_serdes']:
 try:
  tree=RT.for_type(P,tn);rel=RT.start_relays(tree) if tree.get('start') else tree['relays'];by={r['name']:r for r in rel};rows=P.types[tn].get('reset_start_raw_exports',[]);sample=[];bad=0
  for r in rows:
   a=by.get(r['instance']);same=bool(a and a.get('q')==r['net'] and len(a.get('xy',[]))==2 and max(abs(v-w) for v,w in zip(a['xy'],r['xy_um']))<=1e-6)
   bad+=not same
   if len(sample)<3:sample.append({'declared':r,'actual_same_instance':a,'matching_q':[v for v in rel if v.get('q')==r['net']]})
  out[tn]={'exports':len(rows),'mismatches':bad,'tree_start':tree.get('start'),'samples':sample}
 except Exception as e:out[tn]={'error':str(e)}
(O/'diagnosis.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=1)[:14000])
