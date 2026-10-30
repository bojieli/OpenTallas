"""Equal-depth binary PREP. Concrete shared rectilinear net trees; no NLDM call."""
from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-kvleaf-clock-0336')
# Reuse frozen proposal geometry/visibility code only; do not execute old planner.
exec((p/'graph.py').read_text().split('allplans=[];geo=[]')[0])
D=P/'clock_balanced';D.mkdir(exist_ok=True)
def net_tree(driver,targets):
 paths=[route(driver,t) for t in targets];segments=[(a,b) for path in paths for a,b in zip(path,path[1:]) if a!=b]
 pts=set(a for seg in segments for a in seg)
 for a,b in segments:
  for c,d in segments:
   if a[0]==b[0] and c[1]==d[1] and min(a[1],b[1])<=c[1]<=max(a[1],b[1]) and min(c[0],d[0])<=a[0]<=max(c[0],d[0]):pts.add((a[0],c[1]))
 pts.add(driver);pts.update(targets);pts=[driver]+sorted(pts-{driver});ix={t:i for i,t in enumerate(pts)};edges=set()
 for a,b in segments:
  q=sorted((t for t in pts if (a[0]==b[0]==t[0] and min(a[1],b[1])<=t[1]<=max(a[1],b[1])) or (a[1]==b[1]==t[1] and min(a[0],b[0])<=t[0]<=max(a[0],b[0]))),key=lambda t:man(a,t))
  for c,d in zip(q,q[1:]):
   i,j=sorted((ix[c],ix[d]));edges.add((i,j,man(c,d)))
 # Explicit wire-union route intent. Remove an optional closed loop by dropping
 # its longest segment; this emits one actual rectilinear tree, not a cap fudge.
 parent=list(range(len(pts)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 out=[]
 for a,b,w in sorted(edges,key=lambda e:e[2]):
  aa,bb=find(a),find(b)
  if aa!=bb:out.append((a,b,w));parent[aa]=bb
 assert all(find(ix[t])==find(0) for t in targets)
 return pts,out,ix
# Child pin coordinates are explicitly PROPOSED contract choices. Choose the
# face that a native future hardened view must actually implement, using the
# shortest body-halo-avoiding path to one of the retained die clock inputs.
for terminal,child in zip(x['hard_clock_terminals'][:23],x['children']):
 a,b=child['proposed_origin_um'];w,h=child['body_um'];options=[]
 for face,pin,driver in [('W',(a+.012,b+h/2),(a-halo-.6,b+h/2)),('E',(a+w-.012,b+h/2),(a+w+halo+.6,b+h/2)),('S',(a+w/2,b+.012),(a+w/2,b-halo-.6)),('N',(a+w/2,b+h-.012),(a+w/2,b+h+halo+.6))]:
  if not free(driver):continue
  for root in roots:
   path=route(tuple(root['xy_um']),driver);length=sum(man(c,d) for c,d in zip(path,path[1:]));options.append((length,face,pin,driver,root['pin']))
 length,face,pin,driver,rootpin=min(options)
 terminal.update(xy_um=list(pin),parent_driver_xy=list(driver),proposed_core_root=rootpin,proposed_entry_face=face,parent_route_um=length,basis='REVISED PROPOSED native child scalar clock entry on nearest body-halo-accessible face; no existing view pin movement authorized')
plans_by_type=[];inventory=[]
for variant in x['variants']:
 plans=[];rootstats=[]
 for root,budget in zip(roots,variant['distributed_tree']):
  terminals=[t for t in x['hard_clock_terminals'] if t['proposed_core_root']==root['pin']]
  required=math.ceil(budget['proposed_soft_ff']/48)+len(terminals);count=2**math.ceil(math.log2(required));ffcount=count-len(terminals);points=choose_leaf_sites(root,ffcount)
  remaining=budget['proposed_soft_ff'];nodes={};kids={};counter=itertools.count();cap={c:variant['soft_ff_total_clock_pin_cap_fF'][c]/variant['measured_parent_census']['flops'] for c in ('TT','FF')}
  for k,pt in enumerate(points):
   n=remaining//(len(points)-k);remaining-=n;assert 0<n<=48
   nodes[f'f{next(counter)}']={'xy':pt,'kind':'leaf','cell':'BUFx8_ASAP7_75t_R','sinks':[(pt[0]+(i%8-3.5)*.27,pt[1]+(i//8-2.5)*.54) for i in range(n)],'cpin':cap}
  for t in terminals:
   tx,ty=t['xy_um'];nodes[f'h{next(counter)}']={'xy':tuple(t.get('parent_driver_xy',home((tx-halo-.6,ty)))),'kind':'macro','cell':'BUFx8_ASAP7_75t_R','sinks':[t['xy_um']],'cpin':t['cap_fF'],'terminal':t['inst']}
  def branch(group,name=None):
   if len(group)==1:return group[0]
   spans=[max(nodes[n]['xy'][i] for n in group)-min(nodes[n]['xy'][i] for n in group) for i in (0,1)];axis=max(range(2),key=lambda i:spans[i]);group.sort(key=lambda n:nodes[n]['xy'][axis]);left=branch(group[:len(group)//2]);right=branch(group[len(group)//2:]);xy=home(tuple((nodes[left]['xy'][i]+nodes[right]['xy'][i])/2 for i in (0,1)))
   name=name or f'b{next(counter)}';nodes[name]={'xy':tuple(root['xy_um']) if name=='root' else xy,'kind':'buf','cell':'BUFx24_ASAP7_75t_R'};kids[name]=[left,right];return name
  branch(list(nodes),name='root');nets={};netstats=[]
  for driver,children in kids.items():
   pts,E,ix=net_tree(nodes[driver]['xy'],[nodes[c]['xy'] for c in children]);nets[driver]={'pts':pts,'edges':E,'pin':{c:ix[nodes[c]['xy']] for c in children},'detour':1.0};wire=sum(w for a,b,w in E);cin={c:len(children)*x['native_libcaps']['corners'][c]['cells']['BUFx24_ASAP7_75t_R']['capacitance'] for c in ('TT','FF')}
   # Actual child-master Cin, including BUF8 leaves.
   cin={c:sum(x['native_libcaps']['corners'][c]['cells'][nodes[n]['cell']]['capacitance'] for n in children) for c in ('TT','FF')}
   netstats.append({'driver':driver,'master':nodes[driver]['cell'],'wire_um':wire,'TT_total_load_fF':wire*.15423255+cin['TT'],'FF_total_load_fF':wire*.15423255+cin['FF'],'branch_children':len(children),'max_axis_segment_um':max((w for a,b,w in E),default=0)})
  depths={'root':1};todo=['root']
  while todo:
   n=todo.pop(0)
   for c in kids.get(n,[]):depths[c]=depths[n]+1;todo.append(c)
  d={depths[n] for n in nodes if n not in kids};assert len(d)==1
  rootstats.append({'pin':root['pin'],'FF':budget['proposed_soft_ff'],'terminal_driver_count':count,'stage_count':d.pop(),'buffers':len(nodes),'max_net_load_fF':max(n['TT_total_load_fF'] for n in netstats),'max_net_wire_um':max(n['wire_um'] for n in netstats),'worst_nets':sorted(netstats,key=lambda n:n['TT_total_load_fF'],reverse=True)[:4]});plans.append(SimpleNamespace(nodes=nodes,kids=kids,nets=nets))
 plans_by_type.append((variant['type'],plans));inventory.append({'type':variant['type'],'roots':rootstats})
(D/'proposed_child_entry_contracts.json').write_text(json.dumps(x['hard_clock_terminals'],indent=2)+'\n')
(D/'geometry_inventory.json').write_text(json.dumps(inventory,indent=2)+'\n');(D/'graphs.pkl').write_bytes(pickle.dumps(plans_by_type))
for v in inventory:print(v['type'],'maxload',max(r['max_net_load_fF'] for r in v['roots']),'maxwire',max(r['max_net_wire_um'] for r in v['roots']),'depths',[r['stage_count'] for r in v['roots']])
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(11,10))
for b in boxes:ax.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],facecolor='#e1e8ef',edgecolor='#607587',lw=.4))
for plan in plans_by_type[1][1]:
 for net in plan.nets.values():
  for a,b,_ in net['edges']:ax.plot([net['pts'][a][0],net['pts'][b][0]],[net['pts'][a][1],net['pts'][b][1]],color='#206f68',lw=.18)
 ax.scatter(*plan.nodes['root']['xy'],s=14,c='red')
ax.set(xlim=(0,W),ylim=(0,H),aspect='equal',title='KVleaf23 t3 proposed equal-depth binary clock model\nExplicit shared rectilinear net trees; no sizing/physical qualification',xlabel='um',ylabel='um');fig.tight_layout();fig.savefig(D/'geometry.png',dpi=160)
