#!/usr/bin/env python3
"""Lower the HEAD planned H-tree to shared R8 fixed clock wires, for physical trials.

The input nodes and equal-cut repeaters remain unchanged; buffers at a shared island
are packed into consecutive rows, without deleting or merging a logic stage.
"""
import argparse,json,sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'die_plan'))
import die_clock_mesh as D
import head_mesh_r3 as H

def lower(plan,nodes):
 P=H.Plan(plan); by={n['tag']:n for n in nodes}; logical={}; edges=[]
 for n in nodes:
  logical[n['tag']]=dict(xy=n['xy'],mult=int(n.get('drive_mult',2)),kind='tree_node' if n['kids'] else 'mesh_driver')
 for n in nodes:
  if not n.get('parent'): continue
  prev=n['parent']; a=by[prev]['xy']; b=n['xy']
  layer='M8' if abs(a[0]-b[0])>=abs(a[1]-b[1]) else 'M9'
  for k in range(1,n['nseg']):
   tag=n['tag']+'_rep'+str(k)
   logical[tag]=dict(xy=[a[0]+(b[0]-a[0])*k/n['nseg'],a[1]+(b[1]-a[1])*k/n['nseg']],mult=2,kind='tree_rep')
   edges.append((prev,tag,layer)); prev=tag
  edges.append((prev,n['tag'],layer))
 groups={tag:i for i,tag in enumerate(logical)}; buckets=defaultdict(list)
 for tag,v in logical.items(): buckets[tuple(round(q,4) for q in v['xy'])].append(tag)
 cells={}; packing=[]
 for xy,tags in buckets.items():
  p=P.part_at(xy)
  if p is None: raise ValueError('no host '+str(xy))
  count=sum(logical[t]['mult'] for t in tags)
  if count*D.ROW_Y>8.64-0.54: raise ValueError('island cell overflow '+str((xy,tags,count)))
  cx=min(max(xy[0],p['x0']+4.32),p['x0']+p['w']-4.32); cy=min(max(xy[1],p['y0']+4.32),p['y0']+p['h']-4.32)
  if abs(cx-xy[0])+abs(cy-xy[1])>4.321: raise ValueError('site requires structural move '+str(xy))
  x=D.snap(cx-D.BUF_W/2,D.SITE_X); y=D.snap(cy-count*D.ROW_Y/2,D.ROW_Y)
  if x<p['x0'] or x+D.BUF_W>p['x0']+p['w'] or y<p['y0'] or y+count*D.ROW_Y>p['y0']+p['h']:
   raise ValueError('packed cells leave partition '+str((xy,tags)))
  off=0
  for tag in tags:
   g=groups[tag]
   for i in range(logical[tag]['mult']):
    cells['h%d_u%d'%(g,i)]=dict(origin_um=[x,round(y+(off+i)*D.ROW_Y,4)],part=p['name'],master=D.BUF,orient='R0',group=g,kind=logical[tag]['kind'])
   off+=logical[tag]['mult']
  if len(tags)>1: packing.append(dict(xy=xy,groups=tags,rows=count))
 nets=[dict(drv='g'+str(groups[a]),load='g'+str(groups[b]),layer=l,ndr='16w',edge=a+'>'+b) for a,b,l in edges]
 return dict(summary=dict(schema='ot_head_physical_tree/1',nodes=len(nodes),groups=len(logical),units=len(cells),packed_islands=packing),cell_sites=cells,nets=nets)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('plan',type=Path); ap.add_argument('mesh',type=Path); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--fixed',action='store_true'); o=ap.parse_args(); o.out.mkdir(parents=True,exist_ok=True)
 s=lower(o.plan,json.loads((o.mesh/'tree_nodes.json').read_text())); (o.out/'explicit_tree.json').write_text(json.dumps(s,indent=1)+'\n'); print(json.dumps(s['summary'],indent=1))
 if o.fixed:
  P=D.S.Plan(D.S.load(o.plan))
  try: cells,nets,ports,M=D.build_explicit(s,P,ndr='16w',root_um=P.raw['clock']['spine']['root_um'] if hasattr(P,'raw') else None)
  except D.C128.PlanError as e:
   (o.out/'plan_errors.json').write_text(json.dumps(dict(error=str(e),rows=e.rows),indent=1)+'\n'); raise
  ren=D.write_verilog(cells,nets,ports,o.out/'ctree.v')
  for n in nets: n['name']=ren.get(n['name'],n['name'])
  for w in M.get('fixed_wires',[]): w['name']=ren.get(w['name'],w['name'])
  (o.out/'mesh.json').write_text(json.dumps(M)+'\n'); (o.out/'place.json').write_text(json.dumps(cells)+'\n'); (o.out/'nets.json').write_text(json.dumps(dict(ports=ports,nets=nets))+'\n'); print(json.dumps(M['meta'],indent=1))
if __name__=='__main__': main()
