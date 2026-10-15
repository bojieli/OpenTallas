#!/usr/bin/env python3
"""Export actual cut nets/endpoints for geometry; does not qualify routing."""
import os,json,re
from collections import Counter
from pathlib import Path
import odb
d=odb.dbDatabase.create();odb.read_db(d,os.environ['DVM_ODB']);b=d.getChip().getBlock();u=b.getDbUnitsPerMicron();y=float(os.environ.get('DVM_CUT_Y_UM','31.32'))*u
rows=[];classes=Counter();bank_counts=Counter();source_classes=Counter()
def sources(inst):
 queue=[inst];seen=set();ff=set();ports=set()
 while queue:
  i=queue.pop();name=i.getName()
  if name in seen:continue
  seen.add(name)
  if re.search('DFF|SDFF|LATCH',i.getMaster().getName()):ff.add(name);continue
  for it in i.getITerms():
   if it.getMTerm().getIoType()!='INPUT' or it.getMTerm().getSigType()!='SIGNAL':continue
   net=it.getNet()
   if not net:continue
   queue.extend(p.getInst() for p in net.getITerms() if p.getMTerm().getIoType()=='OUTPUT')
   ports.update(bt.getName() for bt in net.getBTerms() if bt.getIoType()=='INPUT')
 return sorted(ff),sorted(ports)
def source_class(n):
 n=n.replace('\\','')
 m=re.search(r'(?:^|[./])(wd|wm|wv|wep|woff|cv|cep|wo|dd|en)\[?',n)
 return m[1] if m else 'bank_register' if '.u_bank/' in n else 'other_register'
def bank(n):
 m=re.search(r'g_t\[([01])\].*g_bank\[([0-3])\]',n.replace('\\',''))
 return int(m[1])*4+int(m[2]) if m else None
for n in b.getNets():
 if n.getSigType() in ('POWER','GROUND'):continue
 pp=[]
 for it in n.getITerms():
  xy=it.getAvgXY()
  if not xy[0]:continue
  inst=it.getInst();name=inst.getName();mt=it.getMTerm();master=inst.getMaster().getName()
  pp.append(dict(inst=name,pin=mt.getName(),io=mt.getIoType(),master=master,bank=bank(name),xy_um=[xy[1]/u,xy[2]/u],side='N' if xy[2]>y else 'S' if xy[2]<y else 'cut'))
 for bt in n.getBTerms():
  for bp in bt.getBPins():
   for q in bp.getBoxes():
    x0,y0=(q.xMin()+q.xMax())/2,(q.yMin()+q.yMax())/2
    pp.append(dict(port=bt.getName(),io=bt.getIoType(),xy_um=[x0/u,y0/u],side='N' if y0>y else 'S' if y0<y else 'cut'))
 if not pp or not min(q['xy_um'][1]*u for q in pp)<y<max(q['xy_um'][1]*u for q in pp):continue
 drivers=[p for p in pp if p.get('inst') and p['io']=='OUTPUT'];owners={p['bank'] for p in pp if p.get('bank') is not None}
 if n.getSigType()=='CLOCK':tag='clock'
 elif any(re.search('DFF|SDFF',p['master']) for p in drivers):tag='registered'
 else:tag='combinational'
 if len(owners)==1 and all(p.get('bank') in owners for p in pp):scope='within_one_bank'
 elif len(owners)>1:scope='multiple_banks'
 elif owners:scope='bank_to_common'
 else:scope='common_only'
 classes[(scope,tag)]+=1
 for owner in owners:bank_counts[owner]+=1
 ff=set();ports=set()
 if tag!='clock':
  for it in n.getITerms():
   if it.getMTerm().getIoType()=='OUTPUT':
    f,p=sources(it.getInst());ff.update(f);ports.update(p)
  for k in {source_class(f) for f in ff}:source_classes[(scope,k)]+=1
 rows.append(dict(net=n.getName(),scope=scope,driver_class=tag,banks=sorted(owners),endpoints=pp,first_sequential_sources=sorted(ff),source_input_ports=sorted(ports)))
r=dict(schema='opentallas.qwen.dvm.cut_nets.v1',odb=os.environ['DVM_ODB'],cut_y_um=y/u,definition='Net counts once if actual endpoints lie on both sides of global horizontal plane. No cut-window cropping; bank fences constrain cells, not wires.',signal_layers=['M2','M3','M4','M5'],vertical_tracks_raw={'M3':1800,'M5':1350},available_tracks_from_placement_audit={'M3':1764,'M5':1290},available_tracks_cut_y_scope_um=31.32,routing_adjustment=.25,net_count=len(rows),class_counts={a+'/'+c:v for (a,c),v in classes.items()},bank_incidence=dict(bank_counts),source_class_incidence={a+'/'+c:v for (a,c),v in source_classes.items()},nets=rows,routing_qualified=False)
Path(os.environ['DVM_AUDIT_OUT']).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:r[k] for k in ['cut_y_um','net_count','class_counts','bank_incidence','source_class_incidence','routing_qualified']}))
