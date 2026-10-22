import odb,os,json,collections,hashlib
from pathlib import Path
p=Path(os.environ['AUDIT_ODB']);db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();scale=b.getDbUnitsPerMicron()
def xy(t):
 v=t.getAvgXY();assert v[0];return (v[1]/scale,v[2]/scale,t.getInst().getName()+'/'+t.getMTerm().getName())
nets={n.getId():n for n in b.getNets() if str(n.getSigType()) not in ('POWER','GROUND','CLOCK')};orig={};successors=collections.defaultdict(set);ops=[];sinks=[];sources=[];macroboxes=[];seqmasters=collections.Counter()
def seed(n,pt,inst,master):
 if n and n.getId() in nets:
  idx=len(sources);sources.append(dict(point=pt,inst=inst,master=master));orig[n.getId()]=orig.get(n.getId(),0)|(1<<idx)
for inst in b.getInsts():
 master=inst.getMaster().getName();seq=('DFF' in master.upper() or 'SRAM' in master.upper());ins=[];outs=[]
 if seq:seqmasters[master]+=1
 if 'SRAM' in master.upper():
  box=inst.getBBox();macroboxes.append(dict(name=inst.getName(),master=master,bbox=[box.xMin()/scale,box.yMin()/scale,box.xMax()/scale,box.yMax()/scale]))
 for t in inst.getITerms():
  n=t.getNet()
  if not n or n.getId() not in nets:continue
  direction=str(t.getIoType())
  if direction=='OUTPUT':
   if seq:seed(n,xy(t),inst.getName(),master)
   else:outs.append(n.getId())
  elif direction=='INPUT':
   if seq:sinks.append((n.getId(),xy(t),inst.getName(),master))
   else:ins.append(n.getId())
 if not seq and outs:
  idx=len(ops);ops.append((ins,outs))
  for i in ins:successors[i].add(idx)
for t in b.getBTerms():
 n=t.getNet()
 if not n or n.getId() not in nets:continue
 for pin in t.getBPins():
  for box in pin.getBoxes():
   pt=((box.xMin()+box.xMax())/2/scale,(box.yMin()+box.yMax())/2/scale,'PORT/'+t.getName())
   if str(t.getIoType())=='INPUT':seed(n,pt,'PORT/'+t.getName(),'PORT')
   elif str(t.getIoType())=='OUTPUT':sinks.append((n.getId(),pt,'PORT/'+t.getName(),'PORT'))
queue=collections.deque(orig);pending=set(orig);updates=0
while queue:
 n=queue.popleft();pending.discard(n)
 for op in successors[n]:
  ins,outs=ops[op];pts=0
  for i in ins:pts|=orig.get(i,0)
  if not pts:continue
  for out in outs:
   val=orig.get(out,0)|pts
   if val!=orig.get(out):
    orig[out]=val;updates+=1
    if out not in pending:queue.append(out);pending.add(out)
def indices(bits):
 while bits:
  v=bits&-bits;yield v.bit_length()-1;bits-=v
bounds={};failures=[];planned_failures=[];planned_max=0
planned_bays={'strap':[188.352,153.36,209.952,174.96],'control':[190.512,190.08,199.152,198.72]}
def which(name):
 clean=name.replace('\\','')
 if (clean.startswith('u_leaf.g_sm[') and ('.q1[' in clean or '.q2[' in clean)) or clean.startswith('u_leaf.r0a['):return 'strap'
 if clean.startswith('u_leaf.c3bd['):return 'control'
 return None
def selected(name):return which(name) is not None
def corners(name,point):
 k=which(name)
 if k is None:return [(point[0],point[1])]
 box=planned_bays[k];return [(box[x],box[y]) for x in (0,2) for y in (1,3)]
def plan_dist(a,ai,z,zi):
 return max(abs(x-xx)+abs(y-yy) for x,y in corners(ai,a) for xx,yy in corners(zi,z))
pred_by_inst=collections.defaultdict(int);unreached=[];pairs=0
for net,sink,inst,master in sinks:
 support=orig.get(net,0);pred_by_inst[inst]|=support
 if not support:unreached.append(sink[2]);continue
 for idx in indices(support):
  pairs+=1;s=sources[idx];a=s['point'];pd=plan_dist(a,s['inst'],sink,inst);planned_max=max(planned_max,pd)
  if pd>405:planned_failures.append(dict(source=a,sink=sink,um=round(pd,6),source_moved=selected(s['inst']),sink_moved=selected(inst)))
  dist=abs(a[0]-sink[0])+abs(a[1]-sink[1]);u=sink[0]+sink[1];v=sink[0]-sink[1]
  if idx not in bounds:bounds[idx]=dict(minu=u,maxu=u,minv=v,maxv=v,sink_count=0,worst_um=0)
  z=bounds[idx];z['minu']=min(z['minu'],u);z['maxu']=max(z['maxu'],u);z['minv']=min(z['minv'],v);z['maxv']=max(z['maxv'],v);z['sink_count']+=1;z['worst_um']=max(z['worst_um'],dist)
  if dist>405:failures.append(dict(source_idx=idx,source=a,sink=sink,um=round(dist,6),sink_master=master))
rows=[]
for idx,z in bounds.items():
 if z['worst_um']<=405 and not selected(sources[idx]['inst']):continue
 s=sources[idx];u=[z['maxu']-405,z['minu']+405];v=[z['maxv']-405,z['minv']+405];pred=list(indices(pred_by_inst[s['inst']]));pu=[sources[i]['point'][0]+sources[i]['point'][1] for i in pred];pv=[sources[i]['point'][0]-sources[i]['point'][1] for i in pred]
 bothu=[max(u[0],max(pu)-405),min(u[1],min(pu)+405)] if pu else u;bothv=[max(v[0],max(pv)-405),min(v[1],min(pv)+405)] if pv else v
 rows.append(dict(idx=idx,**s,**z,allowed_by_all_sinks_uv=[u,v],predecessor_source_count=len(pred),allowed_with_fixed_predecessors_uv=[bothu,bothv],fixed_predecessors=[sources[i]['point'] for i in pred],feasible_sinks=u[0]<=u[1] and v[0]<=v[1],feasible_with_fixed_predecessors=bothu[0]<=bothu[1] and bothv[0]<=bothv[1]))
rows.sort(key=lambda x:x['worst_um'],reverse=True);failures.sort(key=lambda x:x['um'],reverse=True)
bay_area=collections.defaultdict(float);bay_counts=collections.Counter()
for inst in b.getInsts():
 k=which(inst.getName())
 if k is not None:
  master=inst.getMaster();bay_counts[k]+=1;bay_area[k]+=master.getWidth()*master.getHeight()/scale**2
bay_model={k:dict(box=box,instances=bay_counts[k],cell_area_um2=bay_area[k],rectangle_capacity_um2=(box[2]-box[0])*(box[3]-box[1]),nominal_fill=bay_area[k]/((box[2]-box[0])*(box[3]-box[1]))) for k,box in planned_bays.items()}
box=b.getDieArea();out=dict(schema='opentallas.exact_source_region.v1',scope='all non-PG non-CLOCK combinational input/output arcs; every source bitset retained; DFF/SRAM cuts; pin-center405um bounds, buffer transparent; conservative functional support but exact pure BUF/INV witnesses separately proven',odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),die=[box.xMin()/scale,box.yMin()/scale,box.xMax()/scale,box.yMax()/scale],macroboxes=macroboxes,source_count=len(sources),checked_origin_capture_pairs=pairs,unreached_capture_count=len(unreached),violating_pair_count=len(failures),planned_bays=planned_bays,planned_moved_instances=len(set(x['inst'] for x in sources if selected(x['inst']))),planned_pair_bound_max=planned_max,bay_model=bay_model,planned_violating_pairs=planned_failures,violating_sources=rows,violating_pairs=failures,updates=updates,sequential_masters=dict(seqmasters))
Path(os.environ['AUDIT_OUT']).write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k not in ['macroboxes','violating_sources','violating_pairs','sequential_masters','planned_violating_pairs']});print('sources',len(rows),'feasible_fixed_pred',sum(r['feasible_with_fixed_predecessors'] for r in rows))
