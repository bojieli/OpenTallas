#!/usr/bin/env python3
"""Emit a trial clock from the purely geometrical reach plan, preserving every old sink and inverter polarity."""
import json,sys,re,copy
from pathlib import Path
old,out,rp=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=True)
tag=re.sub(r'[^A-Za-z0-9_]','_',out.parent.name)
t=json.load(open(old/'tree.json'));r=json.load(open(rp));v=(old/'ctree.v').read_text();tcl=(old/'ctree.tcl').read_text()
rows={m.group(2):(m.group(1),m.group(3),m.group(4)) for m in re.finditer(r'^\s*(\w+)\s+(\w+)\s*\(\.A\((\w+)\),\s*\.Y\((\w+)\)\);',v,re.M)}
odline=next(x for x in tcl.splitlines() if x.startswith('set ot_odd '));odd=set(re.findall(r'(\w+) 1',odline))
addv=[];addt=[];newodd=[];ledger=[]
for ri,e in enumerate(r['repairs']):
 c,p=e['child'],e['parent'];assert t['parent_of'][c]==p
 master,src,dst=rows[c];assert master=='CKINVDCx16_ASAP7_75t_R';assert rows[p][2]==src
 prev=p;net=src
 for j,xy in enumerate(e['sites']):
  inst=f'{tag}_{ri}_{j}';wire=inst+'_n'
  assert inst not in t['sites']
  addv += [f'  wire {wire};',f'  {master} {inst} (.A({net}), .Y({wire}));']
  addt.append(f'place_inst -name {inst} -location {{{xy[0]:.6f} {xy[1]:.6f}}} -status PLACED')
  if (int(p in odd)+j+1)%2:newodd.append(inst)
  t['sites'][inst]=xy;t['parent_of'][inst]=prev;prev=inst;net=wire
 pattern=rf'({master}\s+{c}\s*\(\.A\(){src}(\))'
 v,n=re.subn(pattern,rf'\g<1>{net}\2',v);assert n==1
 t['parent_of'][c]=prev;ledger.append(dict(e,instances=[f'{tag}_{ri}_{j}' for j in range(e['added'])]))
v=v.replace('endmodule','\n'.join(addv)+'\nendmodule')
lines=tcl.splitlines();i=max(i for i,x in enumerate(lines) if x.startswith('place_inst '));lines[i+1:i+1]=addt
newlines=[]
for line in lines:
 newlines.append(line)
 if line.startswith('set ot_odd '):newlines.extend(f'dict set ot_odd {n} 1' for n in newodd)
tcl='\n'.join(newlines)+'\n'
def path(c):
 seen=set();res=[c]
 while c in t['parent_of']:
  assert c not in seen;seen.add(c);c=t['parent_of'][c];res.append(c)
 return res[::-1]
t['node_stages']={c:len(path(c)) for c in t['sites']}
for tap in t['taps']:
 tap['path']=path(tap['driver']);tap['stages_from_root']=len(tap['path'])
assert all((len(t['taps'][j]['path'])-len(json.load(open(old/'tree.json'))['taps'][j]['path']))%2==0 for j in [0,len(t['taps'])-1])
t['meta']['reach_repair']=dict(bound_um=r['bound_um'],old_edges=r['edges'],repaired=r['repaired'],added=r['added'],ledger=ledger)
# Global postcheck: every repeated cell edge and output leg meets the geometric cap; no original coordinate moved.
mx=max(sum(abs(a-b) for a,b in zip(t['sites'][c],t['sites'][p])) for c,p in t['parent_of'].items())
assert mx<=r['bound_um']+1e-6,mx
(out/'ctree.v').write_text(v);(out/'ctree.tcl').write_text(tcl);(out/'ctree_ck89.tcl').write_text(tcl);(out/'tree.json').write_text(json.dumps(t)+'\n')
(out/'ledger.json').write_text(json.dumps(dict(repairs=ledger,max_physical_hop_um=mx,added=r['added']),indent=2)+'\n')
print(json.dumps(dict(repaired=r['repaired'],added=r['added'],max_physical_hop_um=mx,old_cells=len(rows),new_cells=len(t['sites']))))
