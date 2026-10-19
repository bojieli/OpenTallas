from pathlib import Path
import sys,json,re,collections,importlib.util
p=Path('src/tools/textbook_lint.py');sp=importlib.util.spec_from_file_location('tl',p);t=importlib.util.module_from_spec(sp);sp.loader.exec_module(t)
net=next(Path('sizing/work/orfs/results').glob('asap7/*/base/1_2_yosys.v'));g,top=t.flatten(t.parse_verilog(net.read_text()),'dsdv_mu_hwin');A=t.build(g,None)
def group(n):return re.sub(r'\[\d+\]','[]',n).split('$_')[0]
def walk(net,up):
 todo=[net];seen=set();out=collections.Counter()
 while todo:
  x=todo.pop()
  if x in seen:continue
  seen.add(x)
  ends=[A['driver'][x]] if up and x in A['driver'] else ([] if up else [(ci,pn) for ci,pn,_ in A['loads'].get(x,[])])
  for ci,pn in ends:
   if ci<0:out['port:'+pn]+=1
   elif A['kind'][ci] in ['ff','macro','icg']:out[A['kind'][ci]+':'+group(g.cells[ci][1])+'/'+pn]+=1
   else:todo.extend(t._in_nets(g,A,ci) if up else t._out_nets(g,A,ci))
 return out.most_common(12)
res=[]
for x in A['driver']:
 total,_,_=t.bufinv_fanout(g,A,x,set())
 if total<=32:continue
 dr=A['driver'].get(x)
 if dr is None or dr[0]<0 or A['kind'][dr[0]]!='comb':continue
 res.append({'net':t.net_label(g,A,x),'loads':total,'up':walk(x,True),'down':walk(x,False)})
res.sort(key=lambda r:-r['loads'])
Path('control_trace.json').write_text(json.dumps(res,indent=1));print(json.dumps(res[:8],indent=1))
