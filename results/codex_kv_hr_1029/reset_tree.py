#!/usr/bin/env python3
"""OpenDB preparation: spatial four-way noninverting reset trees, no FF/cycles.
Run under OpenROAD -python. Default emits a plan; --apply writes an owned clone.
Only native delivered-reset ports are visited; clock and data terminals retain
bindings. Odd-polarity residual leaves retain their original path.
"""
import argparse,copy,json,math,re
from pathlib import Path
import odb
p=argparse.ArgumentParser();p.add_argument('odb');p.add_argument('out');p.add_argument('--apply',action='store_true');p.add_argument('--leaf-loads',type=int,default=32);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
db=odb.dbDatabase.create();odb.read_db(db,a.odb);b=db.getChip().getBlock();u=db.getTech().getDbUnitsPerMicron();master=db.findMaster('BUFx24_ASAP7_75t_R');assert master;w,h=master.getWidth(),master.getHeight();old=list(b.getInsts());roots=[]
def trace(bt):
 todo=[(bt.getNet(),0)];seen=set();bufs=set();leaves={}
 while todo:
  net,phase=todo.pop()
  if (net.getId(),phase) in seen:continue
  seen.add((net.getId(),phase))
  for it in net.getITerms():
   if not it.isInputSignal():continue
   inst=it.getInst();mn=inst.getMaster().getName()
   if mn.startswith(('BUF','INV')):
    bufs.add(inst.getName())
    for q in inst.getITerms():
     if q.isOutputSignal() and q.getNet():todo.append((q.getNet(),phase^int(mn.startswith('INV'))))
   else:
    key=(inst.getName(),it.getMTerm().getName());assert key not in leaves or leaves[key][0]==phase,'mixed reset phases';bb=it.getBBox();leaves[key]=(phase,[(bb.xMin()+bb.xMax())/2,(bb.yMin()+bb.yMax())/2])
 return bufs,leaves
for bt in b.getBTerms():
 if not re.search(r'(rst_n|por_n)(\[0\])?$',bt.getName()):continue
 bufs,leaves=trace(bt);q=bt.getBBox();roots.append({'port':bt.getName(),'net':bt.getNet().getName(),'xy_dbu':[(q.xMin()+q.xMax())/2,(q.yMin()+q.yMax())/2],'old_buffers':sorted(bufs),'leaves':leaves})
rows=[]
for row in b.getRows():
 rr=row.getBBox();site=row.getSite()
 if site.getHeight()!=h:continue
 step=row.getSpacing() or site.getWidth();n=row.getSiteCount();blocked=[]
 for inst in old:
  q=inst.getBBox()
  if q.yMin()>=rr.yMin()+h or q.yMax()<=rr.yMin():continue
  lo=max(0,math.floor((q.xMin()-rr.xMin())/step));hi=min(n,math.ceil((q.xMax()-rr.xMin())/step))
  if hi>lo:blocked.append((lo,hi))
 end=0;free=[]
 for lo,hi in sorted(blocked):
  if lo>end:free.append((end,lo))
  end=max(end,hi)
 if end<n:free.append((end,n))
 rows.append({'x':rr.xMin(),'y':rr.yMin(),'step':step,'n':n,'orient':str(row.getOrient()),'free':free})
def site(tx,ty):
 best=None
 for k,row in enumerate(rows):
  need=math.ceil(w/row['step'])
  for q,(lo,hi) in enumerate(row['free']):
   if hi-lo<need:continue
   ix=max(lo,min(hi-need,round((tx-w/2-row['x'])/row['step'])));x=row['x']+ix*row['step'];y=row['y'];rank=(abs(x+w/2-tx)+abs(y+h/2-ty),y,x)
   if best is None or rank<best[0]:best=(rank,k,q,ix,need)
 if best is None:raise ValueError('no full legal reset buffer site')
 _,k,q,ix,need=best;row=rows[k];lo,hi=row['free'].pop(q)
 if ix>lo:row['free'].append((lo,ix))
 if ix+need<hi:row['free'].append((ix+need,hi))
 row['free'].sort();return {'x':row['x']+ix*row['step'],'y':row['y'],'orient':row['orient'],'displacement_um':best[0][0]/u}
nodes=[];root_reports=[]
for r in roots:
 leaves=[{'inst':key[0],'pin':key[1],'xy_dbu':v[1]} for key,v in sorted(r['leaves'].items()) if v[0]==0];stem=re.sub(r'\W','_',r['port'])
 def group(items,parent,depth):
  if not items:return
  xy=[sum(x['xy_dbu'][k] for x in items)/len(items) for k in range(2)]
  if depth==0:xy=r['xy_dbu']
  idx=len(nodes);node={'name':f'hr_reset_{stem}_{idx}','net':f'hr_reset_n_{stem}_{idx}','parent_net':parent,'root':r['port'],'depth':depth+1,'leaf_loads':[],'target_dbu':xy,'placement':site(*xy)};nodes.append(node)
  if len(items)<=a.leaf_loads:node['leaf_loads']=[{k:x[k] for k in ['inst','pin']} for x in items];return
  spans=[max(x['xy_dbu'][k] for x in items)-min(x['xy_dbu'][k] for x in items) for k in range(2)];axis=int(spans[1]>spans[0]);items=sorted(items,key=lambda x:(x['xy_dbu'][axis],x['xy_dbu'][1-axis],x['inst'],x['pin']))
  for k in range(4):group(items[len(items)*k//4:len(items)*(k+1)//4],node['net'],depth+1)
 group(leaves,r['net'],0);root_reports.append({'port':r['port'],'terminals':len(r['leaves']),'rewired':len(leaves),'odd_residual':len(r['leaves'])-len(leaves),'old_buffers':len(r['old_buffers'])})
by_net={n['net']:n for n in nodes};by_root={r['net']:r['xy_dbu'] for r in roots};maxhop=0
for n in nodes:
 q=n['placement'];xy=[q['x']+w/2,q['y']+h/2];pnode=by_net.get(n['parent_net']);pxy=by_root[n['parent_net']] if pnode is None else [pnode['placement']['x']+w/2,pnode['placement']['y']+h/2];maxhop=max(maxhop,sum(abs(xy[k]-pxy[k]) for k in range(2))/u)
 for l in n['leaf_loads']:
  it=b.findInst(l['inst']).findITerm(l['pin']);bb=it.getBBox();lx=[(bb.xMin()+bb.xMax())/2,(bb.yMin()+bb.yMax())/2];maxhop=max(maxhop,sum(abs(xy[k]-lx[k]) for k in range(2))/u)
assert maxhop<=405,('reset leg reach',maxhop)
report={'status':'PREP_ONLY','master':master.getName(),'cell_size_um':[w/u,h/u],'dbu':u,'roots':root_reports,'buffers':len(nodes),'max_depth':max(n['depth'] for n in nodes),'max_leaf_loads':max(len(n['leaf_loads']) for n in nodes),'max_hop_um':maxhop,'area_um2':len(nodes)*w*h/u**2,'cycles_added':0,'nodes':nodes}
(out/'plan.json').write_text(json.dumps(report,indent=1)+'\n');print({k:v for k,v in report.items() if k!='nodes'})
if a.apply:
 for n in nodes:
  assert b.findInst(n['name']) is None
  ins=odb.dbInst_create(b,master,n['name']);q=n['placement'];ins.setOrient(q['orient']);ins.setLocation(q['x'],q['y']);ins.setPlacementStatus('FIRM');net=odb.dbNet_create(b,n['net']);assert ins.findITerm('A') and ins.findITerm('Y');ins.findITerm('A').connect(b.findNet(n['parent_net']));ins.findITerm('Y').connect(net)
  for it in ins.getITerms():
   sg=str(it.getMTerm().getSigType())
   if sg in ('POWER','GROUND'):
    pn=b.findNet('VDD' if sg=='POWER' else 'VSS');assert pn is not None;it.connect(pn)
  for l in n['leaf_loads']:
   it=b.findInst(l['inst']).findITerm(l['pin']);li=it.getInst();kept=li.isDoNotTouch();li.setDoNotTouch(False);it.disconnect();it.connect(net);li.setDoNotTouch(kept)
  ins.setDoNotTouch(True)
 for r in roots:
  _,now=trace(b.findBTerm(r['port']));assert {k:v[0] for k,v in now.items()}=={k:v[0] for k,v in r['leaves'].items()},('reset topology changed',r['port'])
 # Remove only now-unused buffers from the original reset cone. Odd residuals stay.
 old_names={x for r in roots for x in r['old_buffers']};removed=[]
 while True:
  delta=[]
  for name in old_names:
   ins=b.findInst(name)
   if ins is None:continue
   outs=[it.getNet() for it in ins.getITerms() if it.isOutputSignal() and it.getNet()];live=any(any(it.isInputSignal() for it in net.getITerms()) or any(str(bt.getIoType())=='OUTPUT' for bt in net.getBTerms()) for net in outs)
   if not live:delta.append(ins)
  if not delta:break
  for ins in delta:removed.append(ins.getName());odb.dbInst_destroy(ins)
 for r in roots:
  _,now=trace(b.findBTerm(r['port']));assert {k:v[0] for k,v in now.items()}=={k:v[0] for k,v in r['leaves'].items()}
 odb.write_db(db,str(out/'applied.odb'));report['status']='NATIVE_TOPOLOGY_PASS_NO_STA';report['removed_legacy_buffers']=len(removed);(out/'applied_receipt.json').write_text(json.dumps({k:v for k,v in report.items() if k!='nodes'},indent=1)+'\n');print('NATIVE_RESET_BINDING_PASS',len(nodes),len(removed))
