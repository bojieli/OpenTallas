import odb,json,collections
from pathlib import Path
root=Path('/work/native_orfs/results/asap7/qkd_kvs_hroot_safe32/base')
db=odb.dbDatabase.create();odb.read_db(db,str(root/'1_synth.odb'));b=db.getChip().getBlock();rows=[]
for n in b.getNets():
 if n.getSigType() in ('POWER','GROUND','CLOCK') or n.getName()=='ck':continue
 sinks=[t for t in n.getITerms() if t.getIoType()=='INPUT']
 sinks += [t for t in n.getBTerms() if t.getIoType()=='OUTPUT']
 ds=[t.getInst().getName()+'/'+t.getMTerm().getName() for t in n.getITerms() if t.getIoType()=='OUTPUT']
 ds += ['port:'+t.getName() for t in n.getBTerms() if t.getIoType()=='INPUT']
 rows.append(dict(net=n.getName(),loads=len(sinks),drivers=ds))
# Preserve original mapped ODB; split constant tie high/low only, before any layout.
raw=list(rows)
repairs=[]
for n in list(b.getNets()):
 ds=[t for t in n.getITerms() if t.getIoType()=='OUTPUT']
 ss=[t for t in n.getITerms() if t.getIoType()=='INPUT']
 if len(ds)!=1 or len(ss)<=32:continue
 drv=ds[0];inst=drv.getInst();master=inst.getMaster()
 if not master.getName().startswith(('TIEHI','TIELO')):continue
 for start in range(32,len(ss),32):
  cp=odb.dbInst.create(b,master,'safe32_tie_'+str(len(repairs)))
  net=odb.dbNet.create(b,'safe32_tie_net_'+str(len(repairs)))
  cp.findITerm(drv.getMTerm().getName()).connect(net)
  for sink in ss[start:start+32]:sink.disconnect();sink.connect(net)
  repairs.append(dict(source=n.getName(),copy=cp.getName(),loads=len(ss[start:start+32])))
if repairs:
 odb.write_db(db,str(root/'1_synth_tie32.odb'))
 rows=[]
 for n in b.getNets():
  if n.getSigType() in ('POWER','GROUND','CLOCK') or n.getName()=='ck':continue
  ss=[t for t in n.getITerms() if t.getIoType()=='INPUT'];ss += [t for t in n.getBTerms() if t.getIoType()=='OUTPUT']
  ds=[t.getInst().getName()+'/'+t.getMTerm().getName() for t in n.getITerms() if t.getIoType()=='OUTPUT'];ds += ['port:'+t.getName() for t in n.getBTerms() if t.getIoType()=='INPUT']
  rows.append(dict(net=n.getName(),loads=len(ss),drivers=ds))
Path('/work/results/rtl/kv_hroot_safe32_1020/tie_repair.json').write_text(json.dumps(dict(repairs=repairs,raw_over32=[x for x in raw if x['loads']>32]),indent=2)+'\n')
rows.sort(key=lambda x:-x['loads'])
r=dict(vehicle='ORFS ASAP7 default RVT-FF mapped synth only, no placement',cells=len(b.getInsts()),max_loads=rows[0]['loads'],over32=[r for r in rows if r['loads']>32],top50=rows[:50],clock_exclusion='CLOCK signal type plus top ck only',pass_census=all(r['loads']<=32 for r in rows))
Path('/work/results/rtl/kv_hroot_safe32_1020/native_census_tie32.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='top50'},indent=2))
