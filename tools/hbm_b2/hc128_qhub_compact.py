#!/usr/bin/env python3
"""Give all four exact32-leaf cuts one compact reusable physical master."""
import argparse,collections,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('split',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);j=json.loads(a.split.read_text());mods=j['modules'];qt=mods['ot_hbm_hc_qhub_static']['cells']['u_cen']['type'];q=mods[qt];master='ot_hbm_hc_subtree32_core';maps={}
nextbit=1+max(b for c in q['cells'].values() for bs in c['connections'].values() for b in bs if isinstance(b,int))
labels={'clk':'clk','s_i':'data','vl':'valid_in','rn':'rst_n','nd':'sum','ne':'node_fault','nv':'valid_out'}
for k in range(4):
 old=f'ot_hbm_hc_subtree32_{k}';m=mods[old];cell=q['cells'][old];read={b for c in m['cells'].values() for pn,bs in c['connections'].items() if c['port_directions'][pn]=='input' for b in bs if isinstance(b,int)}
 groups=collections.defaultdict(list)
 for pn,p in m['ports'].items():
  mat=re.match(r'^(.*)\[(\d+)\]$',pn);base=mat[1] if mat else pn;ix=int(mat[2]) if mat else -1;assert base in labels,pn
  for z,b in enumerate(p['bits']):
   if p['direction']=='input' and b not in read:continue
   groups[labels[base]].append((ix if len(p['bits'])==1 else z,pn,z,b,p['direction']))
 ports={};conns={};mapping={}
 for label,items in sorted(groups.items()):
  items.sort(key=lambda x:x[0]);directions={v[4] for v in items};assert len(directions)==1
  ports[label]=dict(direction=next(iter(directions)),bits=[v[3] for v in items]);conns[label]=[cell['connections'][v[1]][v[2]] for v in items];mapping[label]=[(v[1],v[2]) for v in items]
 if 'valid_out' not in ports:
  root=m['cells'][f'g_lvl[5].g_n[{k}].u_a'];vb=root['connections']['valid_out'];assert len(vb)==1
  ports['valid_out']=dict(direction='output',bits=vb);conns['valid_out']=[nextbit];nextbit+=1;mapping['valid_out']='unused at original parent; retained common ABI'
 counts={n:(p['direction'],len(p['bits'])) for n,p in ports.items()}
 assert counts=={'clk':('input',1),'data':('input',1024),'node_fault':('output',31),'rst_n':('input',1),'sum':('output',32),'valid_in':('input',1),'valid_out':('output',1)},counts
 if k==0:
  cm=json.loads(json.dumps(m));cm['ports']=ports;cm['attributes'].pop('hdlname',None);mods[master]=cm
 cell['type']=master;cell['connections']=conns;cell['port_directions']={n:p['direction'] for n,p in ports.items()};maps[old]=mapping
for k in range(4):del mods[f'ot_hbm_hc_subtree32_{k}']
(a.out/'qhub_compact128.json').write_text(json.dumps(j));(a.out/'port_map.json').write_text(json.dumps(dict(master=master,ports=counts,instances=maps),indent=2)+'\n');(a.out/'export.ys').write_text(f'read_json {a.out.resolve()}/qhub_compact128.json\nselect {master}\nwrite_verilog -selected {a.out.resolve()}/{master}.sv\n');print(master,counts)
