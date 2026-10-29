"""Actual new-synthesis clock sinks and same-name old-placement homes (planning estimate)."""
import odb,json,os,hashlib,collections
from pathlib import Path
newpath=Path('/new/run/results/asap7/hbc_ot_hbm_sm_vm_wr_q_t_lanes4/base/1_synth.odb');oldpath=Path('/old/run/results/asap7/hbc_ot_hbm_sm_vm_wr_q_t_lanes4/base/4_cts.odb')
def load(p):
 d=odb.dbDatabase.create();odb.read_db(d,str(p));return d,d.getChip().getBlock()
oldD,old=load(oldpath);newD,new=load(newpath);du=old.getDbUnitsPerMicron();oldinst={i.getName():i for i in old.getInsts()};rows=[];missing=[]
for i in new.getInsts():
 m=i.getMaster();name=m.getName()
 if not (name.startswith(('DFF','SDFF')) or name.startswith('ot_sram_')):continue
 for t in i.getITerms():
  mt=t.getMTerm()
  if mt.getIoType()!='INPUT' or not (mt.getSigType()=='CLOCK' or mt.getName() in ('CLK','CK','clk')):continue
  rec={'instance':i.getName(),'master':name,'clock_pin':mt.getName(),'clock_net':t.getNet().getName() if t.getNet() else None,'kind':'SRAM' if name.startswith('ot_sram_') else 'FF'}
  oi=oldinst.get(i.getName())
  if oi is None:rec.update(home_status='MISSING_RENAMED',old_home_um=None);missing.append(rec['instance'])
  else:
   b=oi.getBBox();rec.update(home_status='SAME_NAME_OLD_PLACEMENT_ESTIMATE',old_master=oi.getMaster().getName(),old_home_um=[b.xMin()/du,b.yMin()/du,b.xMax()/du,b.yMax()/du],old_orientation=oi.getOrient(),old_placed=oi.isPlaced())
  rows.append(rec)
out=Path('/out');(out/'actual_sinks.json').write_text(json.dumps({'scope':'Newactual1_synth endpoints; old4CTS same-name homes are planning estimates only, freshplacement mandatory beforeCTS','new_db_sha256':hashlib.sha256(newpath.read_bytes()).hexdigest(),'old_db_sha256':hashlib.sha256(oldpath.read_bytes()).hexdigest(),'sinks':rows},indent=1)+'\n')
s={'sinks':len(rows),'kinds':dict(collections.Counter(q['kind']for q in rows)),'clock_nets':dict(collections.Counter(q['clock_net']for q in rows)),'same_name_old_home':len(rows)-len(missing),'missing_renamed':len(missing),'missing_instances':missing,'current_root_um':[69.12,108.0],'macro_rect_um':[23.868,116.7,118.692,157.764],'scope':'oldhomes planning only; newactualplacement/clocktree/PGreview beforeCTS'}
(out/'summary.json').write_text(json.dumps(s,indent=1)+'\n');print(json.dumps({k:v for k,v in s.items()if k!='missing_instances'}))
