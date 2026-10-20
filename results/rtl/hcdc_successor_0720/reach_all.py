import odb,json,collections,hashlib
from pathlib import Path
p=Path('/case/routes/gate/work/orfs/results/asap7/opentallas_qkd_hr_cdc_pc_sram_asap7_ref_gate/base/3_5_place_dp-failed.odb')
db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def ip(it):
 v=it.getAvgXY()
 if len(v)==3:ok,x,y=v
 else:x,y=v;ok=True
 if not ok:raise RuntimeError('No pin geometry '+it.getInst().getName()+'/'+it.getMTerm().getName())
 return x/u,y/u

def bp(bt):
 boxes=[z for pin in bt.getBPins() for z in pin.getBoxes()]
 if not boxes:raise RuntimeError('No BTerm geometry '+bt.getName())
 return sum((z.xMin()+z.xMax())/2 for z in boxes)/len(boxes)/u,sum((z.yMin()+z.yMax())/2 for z in boxes)/len(boxes)/u

def role(it):
 i=it.getInst();nm=i.getName();m=i.getMaster()
 if m.isBlock():return 'macro'
 if nm.startswith(('ot_inhold_','ot_ihdrv_','ot_outhold_')):return 'boundary_hold'
 if nm.startswith('ot_prs_'):return 'pin_split'
 if i.getGroup():return 'central'
 return 'other'

counts=collections.Counter();maximum=collections.defaultdict(float);worst=[];rows=[];clock=[];missing=[]
for net in b.getNets():
 if net.getSigType() in ['POWER','GROUND']:continue
 src=[];dst=[]
 for it in net.getITerms():
  io=str(it.getIoType());name=it.getInst().getName()+'/'+it.getMTerm().getName()
  try:xy=ip(it)
  except RuntimeError as e:missing.append(str(e));continue
  term=(name,*xy,role(it))
  if io in ['OUTPUT','INOUT']:src.append(term)
  if io in ['INPUT','INOUT']:dst.append(term)
 for bt in net.getBTerms():
  try:xy=bp(bt)
  except RuntimeError as e:missing.append(str(e));continue
  term=('PORT/'+bt.getName(),*xy,'port')
  if str(bt.getIoType()) in ['INPUT','INOUT']:src.append(term)
  if str(bt.getIoType()) in ['OUTPUT','INOUT']:dst.append(term)
 if not src or not dst:
  counts['nets_without_driver_or_sink']+=1;continue
 for s in src:
  for d in dst:
   if s[0]==d[0]:continue
   length=abs(s[1]-d[1])+abs(s[2]-d[2]);rec=(net.getName(),s[0],d[0],length,s[3],d[3],s[1:3],d[1:3])
   if net.getSigType()=='CLOCK' or any(k in net.getName() for k in ['ck_core','ck_phy_fam']):
    clock.append(rec);continue
   key=s[3]+'->'+d[3];counts['pairs']+=1;counts[key]+=1;maximum[key]=max(maximum[key],length)
   if length>405:counts['over405']+=1;worst.append(rec)
   rows.append(rec)
worst.sort(key=lambda x:-x[3]);out=Path('/audit')
summary=dict(scope='FULL connected direct driver-to-sink L1 at exact frozen failed PC1j ODB; no cell-centre macro approximation; no new-region universal claim',odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),counts=counts,max_L1_by_role=maximum,clock_pairs=len(clock),clock_max_L1=max((x[3] for x in clock),default=0),missing_geometry=missing,worst=worst[:30])
(out/'reach_all.json').write_text(json.dumps(summary,indent=2)+'\n');(out/'connected_pairs.json').write_text(json.dumps(rows)+'\n');(out/'clock_pairs.json').write_text(json.dumps(clock)+'\n');print(json.dumps(summary))
