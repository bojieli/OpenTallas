"""Name concrete failing XFIN cones using the exact census graph and Liberty roles."""
import collections, importlib.util, json, re, sys
from pathlib import Path
src,native,out=map(Path,sys.argv[1:])
spec=importlib.util.spec_from_file_location('nc',src/'tools/ref_tile/native_census.py'); nc=importlib.util.module_from_spec(spec);spec.loader.exec_module(nc)
r=json.loads((native/'native_census.json').read_text());roles,_=nc.liberty_roles([x['path'] for x in r['liberty']]);raw=(native/'results/asap7/opentallas_ot_s81dv_xfin_asap7_ref_gate/base/1_2_yosys.v').read_text();mods=nc.TL.parse_verilog(raw);mods={k:v for k,v in mods.items() if k=='ot_s81dv_xfin' or k not in roles};g,_=nc.TL.flatten(mods,'ot_s81dv_xfin')
load=collections.defaultdict(set);driver={}; outs={};ins={}
for i,(master,name,pins) in enumerate(g.cells):
 role=roles[master];outs[i]=[];ins[i]=[]
 for pn,nets in pins.items():
  for n in nets:
   if role['pins'].get(pn,{}).get('direction')=='output':driver[n]=i;outs[i].append(n)
   else:load[n].add(i);ins[i].append(n)
def label(i):return re.sub(r'\[\d+\]','[*]',g.cells[i][1]).rsplit('.',1)[0]
def walk(start,forward):
 todo=[(start,0)];seen=set();hits=collections.Counter()
 while todo:
  i,d=todo.pop()
  if i in seen:continue
  seen.add(i)
  if roles[g.cells[i][0]].get('sequential') or d>=10:
   hits[label(i)]+=1;continue
  for n in (outs[i] if forward else ins[i]):
   todo.extend((j,d+1) for j in (load[n] if forward else ([driver[n]] if n in driver else [])))
 return hits.most_common(12)
byname={name:i for i,(_,name,_) in enumerate(g.cells)};result=[]
for v in sorted(r['violations'],key=lambda x:-x['loads'])[:20]:
 name=v['driver'].rsplit('/',1)[0];i=byname.get(name)
 if i is not None:result.append(dict(driver=v['driver'],loads=v['loads'],fanin=walk(i,False),fanout=walk(i,True)))
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=1))
