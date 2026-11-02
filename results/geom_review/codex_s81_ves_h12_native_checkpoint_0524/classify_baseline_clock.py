from pathlib import Path
import importlib.util,json,collections
p=Path('/home/ubuntu/coord/tmp/codex-ves-final-look-0452');s=importlib.util.spec_from_file_location('G','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g);d=g.Design(p/'geom.tsv')
# Backward exact native register-clock ancestry, same criterion as clock_metrics.
back=set()
for cid,c in d.cells.items():
 if c[0] not in 'SM':continue
 for n,ck in d.cell_in.get(cid,[]):
  if not ck:continue
  seen=set()
  while n not in seen:
   seen.add(n);dr=d.nets[n][1]
   if not dr or dr[0]!='i' or d.kind(dr[1]) not in ['B','K']:break
   cid2=dr[1];back.add(cid2);ins=d.cell_in.get(cid2,[])
   if not ins:break
   n=next((a for a,b in ins if b),ins[0][0])
# Forward native clock graph, all buffer/inverter input loads including no-register branches.
roots={x['k'] for x in d.pins if x['name']=='clk'};q=[n for n,(_,dr,_) in enumerate(d.nets) if dr and dr[0]=='p' and dr[1] in roots];forward=set();nets=set();ff=set();unknown=[]
while q:
 n=q.pop()
 if n in nets:continue
 nets.add(n)
 for e in d.nets[n][2]:
  if e[0]!='i':continue
  k=d.kind(e[1])
  if k=='S' and e[2]:ff.add(e[1])
  elif k in ['B','K']:
   forward.add(e[1]);q.extend(d.drives.get(e[1],[]))
  else:unknown.append(e)
extra=forward-back;r=[]
for cid in sorted(extra):
 c=d.cells[cid];outs=d.drives.get(cid,[]);r.append(dict(name=c[6],master=c[1],outputs=[dict(net=d.nets[n][0],sinks=d.nets[n][2]) for n in outs]))
x=dict(native_rooted_FF=len(ff),functional_clock_ancestry=len(back),all_clock_input_load_cells=len(forward),extra_no_register_descendants=len(extra),extra=r,unexpected_children=unknown)
(p/'actual_clock_load_classification.json').write_text(json.dumps(x,indent=2));print(json.dumps(x,indent=1))
