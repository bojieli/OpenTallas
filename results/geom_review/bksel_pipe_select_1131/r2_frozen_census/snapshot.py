import odb,json,hashlib,os
from pathlib import Path
p=Path('/work');tag=os.environ['OT_CENSUS_TAG'];path=p/(tag+'.odb');expected={'old':'969fdb3e7d0f6b3aa58152d20eeb87706ee3d04d424af1e9588a6c0b34eb04df','new':'a3db31fecf1ec367b28e69ad84ef3a885f391f5b9afe2023b2412b1475d77840'}[tag]
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(path)==expected
D=odb.read_db(odb.dbDatabase.create(),str(path));B=D.getChip().getBlock();mover=r'u_c.rst_s\[1\]$_DFF_PN0_'
def rect(r):return [r.xMin(),r.yMin(),r.xMax(),r.yMax()]
def record(h,v):h.update(json.dumps(v,ensure_ascii=True,separators=(',',':')).encode()+b'\n')
def digest(values):
 h=hashlib.sha256()
 for v in values:record(h,v)
 return h.hexdigest()
def inst(i):
 return {'name':i.getName(),'xy':list(i.getLocation()),'orientation':str(i.getOrient()),'master':i.getMaster().getName(),'master_dimensions':[i.getMaster().getWidth(),i.getMaster().getHeight()],'placement_status':str(i.getPlacementStatus()),'dont_touch':i.isDoNotTouch()}
I=sorted(B.getInsts(),key=lambda x:x.getName());assert sum(i.getName()==mover for i in I)==1
frozen=hashlib.sha256();masters=hashlib.sha256();mv=None
for i in I:
 z=inst(i);record(masters,[z['name'],z['master'],z['master_dimensions']])
 if z['name']==mover:mv=z
 else:record(frozen,z)
nh=hashlib.sha256();ih=hashlib.sha256();bh=hashlib.sha256();full=hashlib.sha256();ch=hashlib.sha256();ic=bc=clockc=0
for n in sorted(B.getNets(),key=lambda x:x.getName()):
 its=sorted(n.getITerms(),key=lambda t:(t.getInst().getName(),t.getMTerm().getName()));bts=sorted(n.getBTerms(),key=lambda t:t.getName())
 hdr=[n.getName(),str(n.getSigType()),n.isSpecial(),n.isDoNotTouch()];record(nh,hdr);record(full,['N',hdr])
 clock=str(n.getSigType())=='CLOCK' or any(str(t.getMTerm().getSigType())=='CLOCK' for t in its) or any(str(t.getSigType())=='CLOCK' for t in bts)
 if clock:clockc+=1;record(ch,['N',hdr])
 for t in its:
  z=[n.getName(),t.getInst().getName(),t.getMTerm().getName(),str(t.getIoType()),str(t.getMTerm().getSigType())];record(ih,z);record(full,['I',z]);ic+=1
  if clock:record(ch,['I',z])
 for t in bts:
  z=[n.getName(),t.getName(),str(t.getIoType()),str(t.getSigType())];record(bh,z);record(full,['B',z]);bc+=1
  if clock:record(ch,['B',z])
ports=[];boxes=0
for t in sorted(B.getBTerms(),key=lambda x:x.getName()):
 pins=[]
 for bp in t.getBPins():
  shapes=[]
  for box in bp.getBoxes():
   lay=box.getTechLayer();shapes.append([lay.getName() if lay else None,rect(box)]);boxes+=1
  pins.append([str(bp.getPlacementStatus()),sorted(shapes,key=lambda z:json.dumps(z))])
 ports.append([t.getName(),t.getNet().getName() if t.getNet() else None,str(t.getIoType()),str(t.getSigType()),sorted(pins,key=lambda z:json.dumps(z))])
rows=[]
for r in sorted(B.getRows(),key=lambda x:x.getName()):rows.append([r.getName(),rect(r.getBBox()),str(r.getOrient()),r.getSite().getName(),r.getSite().getWidth(),r.getSite().getHeight()])
assert sha(path)==expected
out={'tag':tag,'odb_sha256':expected,'db_units':B.getDbUnitsPerMicron(),'mover':mv,'counts':{'instances':len(I),'nets':len(B.getNets()),'iterms':ic,'net_bterms':bc,'ports':len(ports),'port_boxes':boxes,'rows':len(rows),'typed_clock_nets':clockc},'digests':{'all_inst_master_dimensions':masters.hexdigest(),'all_other_inst_pose_status_donttouch':frozen.hexdigest(),'net_headers':nh.hexdigest(),'full_iterm_membership':ih.hexdigest(),'full_bterm_membership':bh.hexdigest(),'full_net_graph':full.hexdigest(),'typed_clock_graph':ch.hexdigest(),'all_ports_boxes_net_io_sigtype':digest(ports),'all_rows':digest(rows)},'outline_dbu':{'die':rect(B.getDieArea()),'core':rect(B.getCoreArea())},'scope':'read-only native OpenDB full census; all nets/PG/ITerms/BTerms included; clock graph subset plus global graph; moved FF clock-load coordinate follows its sole allowed XY change; no STA or P&R'}
Path('/out',tag+'.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
