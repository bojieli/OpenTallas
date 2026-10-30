import json,math
from pathlib import Path
from collections import defaultdict,Counter
base=Path(__file__).parent;cells={};nets=[]
for line in (base/'geom.tsv').open():
 a=line.rstrip().split('\t')
 if a[0]=='C':cells['i'+a[1]]=dict(name=a[8],kind=a[2],master=a[3],x=float(a[4]),y=float(a[5]),w=float(a[6])-float(a[4]),h=float(a[7])-float(a[5]))
 elif a[0]=='N':nets.append(a[2:])
holds={k for k,c in cells.items() if c['name'].startswith('hold')};adj=defaultdict(set)
for net in nets:
 hh=[x for x in net if x in holds]
 for x in hh:adj[x].update(hh)
seen=set();groups=[]
for k in holds:
 if k in seen:continue
 seen.add(k);todo=[k];c=[]
 while todo:
  x=todo.pop();c.append(x)
  for j in adj[x]-seen:seen.add(j);todo.append(j)
 groups.append(c)
hot={k for k in holds if 71<=cells[k]['x']+cells[k]['w']/2<=81 and 65<=cells[k]['y']+cells[k]['h']/2<=88}
groups=[g for g in groups if hot.intersection(g)];moves={x for g in groups for x in g};occ=defaultdict(list)
# Reserve existing non-moved cells by rows; all other geometry stays fixed.
for k,c in cells.items():
 if k in moves:continue
 for row in range(math.floor(c['y']/.27),math.ceil((c['y']+c['h'])/.27)):
  occ[row].append((c['x'],c['x']+c['w']))
for row in occ:occ[row].sort()
newpos={}
for g in sorted(groups,key=lambda g:(sum(cells[x]['y'] for x in g)/len(g),sum(cells[x]['x'] for x in g)/len(g))):
 g=sorted(g,key=lambda k:(cells[k]['y'],cells[k]['x']));w=sum(cells[k]['w'] for k in g)+.108*(len(g)-1)
 best=None
 for row in range(math.ceil(8/.27),math.floor(30/.27)):
  y=round(row*.27,3)
  for col in range(math.ceil(8/.054),math.floor((65-w)/.054)):
   x=round(col*.054,3)
   if any(l<x+w+.054 and r>x-.054 for l,r in occ[row]):continue
   score=y*1000+x
   if best is None or score<best[0]:best=(score,x,y,row)
   break
 if best is None:raise RuntimeError('No free target footprint')
 _,x,y,row=best
 for k in g:newpos[k]=(x,y);x+=cells[k]['w']+.108
 x0=newpos[g[0]][0];occ[row].append((x0,x0+w));occ[row].sort()
old_hpwl=new_hpwl=0;max_delta=0;n_changed=0
for net in nets:
 if not moves.intersection(net):continue
 pts=[(cells[k]['x']+cells[k]['w']/2,cells[k]['y']+cells[k]['h']/2) for k in net if k in cells]
 npts=[(newpos[k][0]+cells[k]['w']/2,newpos[k][1]+cells[k]['h']/2) if k in newpos else (cells[k]['x']+cells[k]['w']/2,cells[k]['y']+cells[k]['h']/2) for k in net if k in cells]
 if len(pts)<2:continue
 hp=lambda a:max(x for x,y in a)-min(x for x,y in a)+max(y for x,y in a)-min(y for x,y in a)
 old,new=hp(pts),hp(npts);old_hpwl+=old;new_hpwl+=new;max_delta=max(max_delta,new-old);n_changed+=1
out={'schema':'opentallas.kv.phypad_spread_estimate.v1','status':'ESTIMATE_NOT_BUILT','moved_hold_buffers':len(newpos),'whole_hold_chains':len(groups),'cycles_added':0,'flops_moved':0,'clock_cells_moved':0,'other_cells_moved':0,'pins_moved':0,'target_bay_um':[8,8,65,30],'new_occupied_area_um2':sum(cells[k]['w']*cells[k]['h'] for k in moves),'changed_signal_nets':n_changed,'changed_net_hpwl_um_old':round(old_hpwl,3),'changed_net_hpwl_um_new':round(new_hpwl,3),'largest_net_hpwl_increase_um':round(max_delta,3),'timing':'UNMEASURED; each chain retains buffers/order/connectivity. Longer first/last data wires require GRT+TT/FF before route. Existing TT115.71/FF9.84 not transferable.','cells':[{'name':cells[k]['name'],'master':cells[k]['master'],'old':[cells[k]['x'],cells[k]['y']],'new':list(newpos[k])} for k in sorted(newpos,key=lambda k:cells[k]['name'])]}
(base/'spread_estimate.json').write_text(json.dumps(out,indent=1)+'\n');print({k:v for k,v in out.items() if k!='cells'})
