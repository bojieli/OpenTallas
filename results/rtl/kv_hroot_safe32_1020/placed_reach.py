import odb,json,hashlib
from pathlib import Path
root=Path('/work/routes/gate/work/orfs/results/asap7/opentallas_qkd_kvs_hroot_safe32_asap7_ref_gate/base')
p=root/'4_1_cts.odb';d=odb.dbDatabase.create();odb.read_db(d,str(p));b=d.getChip().getBlock();u=b.getDbUnitsPerMicron();rows=[]
def point(t):
 if hasattr(t,'getInst'):
  z=t.getInst().getBBox();return ((z.xMin()+z.xMax())/2,(z.yMin()+z.yMax())/2)
 boxes=[z for pin in t.getBPins() for z in pin.getBoxes()]
 if not boxes:return None
 z=boxes[0];return ((z.xMin()+z.xMax())/2,(z.yMin()+z.yMax())/2)
for n in b.getNets():
 if n.getSigType() in ('POWER','GROUND','CLOCK') or n.getName()=='ck':continue
 drivers=[t for t in n.getITerms() if t.getIoType()=='OUTPUT']+[t for t in n.getBTerms() if t.getIoType()=='INPUT']
 sinks=[t for t in n.getITerms() if t.getIoType()=='INPUT']+[t for t in n.getBTerms() if t.getIoType()=='OUTPUT']
 if len(drivers)!=1:continue
 dr=drivers[0]
 if hasattr(dr,'getInst') and dr.getInst().getMaster().getName().startswith(('TIEHI','TIELO')):continue
 dp=point(dr)
 if dp is None:continue
 vals=[(abs(dp[0]-sp[0])+abs(dp[1]-sp[1]))/u for t in sinks if (sp:=point(t)) is not None]
 if vals:rows.append(dict(net=n.getName(),max_manhattan_um=round(max(vals),3),sinks=len(sinks)))
rows.sort(key=lambda x:-x['max_manhattan_um']);r=dict(odb=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),method='Instance bbox centres and first BPin bbox centre; stdcell pin-centre proxy, direct nonclock/nonconstant nets. No cross-buffer endpoint collapsing for reach.',dbu_per_um=u,max_manhattan_um=rows[0]['max_manhattan_um'],over405=[x for x in rows if x['max_manhattan_um']>405],top30=rows[:30]);Path('/out/placed_reach.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k not in ['top30','over405']});print('over405',len(r['over405']))
