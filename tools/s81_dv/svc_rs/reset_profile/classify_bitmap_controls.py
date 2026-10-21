#!/usr/bin/env python3
"""Read-only mapped reset-DFF control ancestry; named-cone witness, not a waiver."""
import sys,re,json,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]));import textbook_lint as T
g,top=T.flatten(T.parse_verilog(Path(sys.argv[1]).read_text()),'dsdv_svc_att')
for ty,n,ps in g.cells:
 if re.match(r'^(INV|BUF)',ty)and 'Y'in ps:
  inp=[b for p,b in ps.items()if p!='Y']
  if len(inp)==1 and len(inp[0])==1 and len(ps['Y'])==1:g.union(inp[0][0],ps['Y'][0])
names=collections.defaultdict(list)
for i,n in enumerate(g.net_name):
 if n.startswith('u_core.')and not any(k in n for k in ['.rst_n','.clk']):names[g.find(i)].append(n)
dr={}
for i,(ty,n,ps)in enumerate(g.cells):
 if re.match(r'^(INV|BUF)',ty):continue
 for p in ['Y','Q','QN']:
  for x in ps.get(p,[]):dr[g.find(x)]=i
root=g.find(g.net_id['rst_n']);counts=collections.Counter();examples=collections.defaultdict(list);states=0
for i,(ty,n,ps)in enumerate(g.cells):
 if not ty.startswith('DFFASR')or not any(g.find(x)==root for x in ps.get('RESETN',[])):continue
 qs=[g.find(x)for p in ['Q','QN']for x in ps.get(p,[])]
 if any(names.get(x)for x in qs):continue
 states+=1;todo=[(g.find(x),0)for x in ps.get('D',[])];visited=set();found=set();feedback=False
 while todo:
  x,d=todo.pop()
  if x in visited:continue
  visited.add(x)
  if x in qs:feedback=True;continue
  for a in names.get(x,[]):found.add(re.sub(r'\[\d+\]','',a))
  ci=dr.get(x)
  if ci is None or d>=6:continue
  ct,cn,cp=g.cells[ci]
  if ct.startswith(('DFF','SDFF','LATCH','ot_sram')):continue
  for p,bs in cp.items():
   if p not in ['Y','Q','QN','CLK','CK','RESETN','SETN']:
    todo.extend((g.find(b),d+1)for b in bs)
 # Concrete named source roots are listed, never used to waive an unknown field.
 selected=sorted(a for a in found if any(k in a for k in ['lw_v','lw_a','start','rows_mine','qrv','f_type','pay_mine','sm_','pres','lv0','lv1','lv2']))
 key=('feedback'if feedback else'no-feedback')+' | '+','.join(selected[:8]);counts[key]+=1
 if len(examples[key])<2:examples[key].append({'cell':n,'master':ty,'named_ancestry':sorted(found)[:40]})
r={'scope':'Read-only prior NORST map unknown reset-DFF ancestry at most6 comb levels; a source witness, NOT symbolic equivalence, nativePASS or authority to remove state.','unattributed_states':states,'groups':counts.most_common(),'examples':dict(examples)}
Path(sys.argv[2]).write_text(json.dumps(r,indent=2)+'\n')
for k,v in counts.most_common(20):print(v,k[:250])
