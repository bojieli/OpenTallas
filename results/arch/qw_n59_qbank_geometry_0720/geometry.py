import odb,json,sys,hashlib,collections,math
from pathlib import Path
p=Path(sys.argv[1]);out=Path(sys.argv[2]);db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def rect(z):return [z.xMin()/u,z.yMin()/u,z.xMax()/u,z.yMax()/u]
mac=[]
for i in b.getInsts():
 if not i.getMaster().isBlock():continue
 bb=rect(i.getBBox());faces=collections.defaultdict(list)
 for pin in i.getITerms():
  if str(pin.getSigType()) in ['POWER','GROUND']:continue
  z=rect(pin.getBBox());x=(z[0]+z[2])/2;y=(z[1]+z[3])/2;side=min(['W','E','S','N'],key=lambda s:{'W':abs(x-bb[0]),'E':abs(x-bb[2]),'S':abs(y-bb[1]),'N':abs(y-bb[3])}[s]);faces[side].append({'pin':pin.getMTerm().getName(),'rect':z,'net':pin.getNet().getName() if pin.getNet() else None})
 densities={k:{'pins':len(v),'face_um':bb[3]-bb[1] if k in ['W','E'] else bb[2]-bb[0],'pins_per_um':len(v)/(bb[3]-bb[1] if k in ['W','E'] else bb[2]-bb[0])} for k,v in faces.items()}
 mac.append({'inst':i.getName(),'master':i.getMaster().getName(),'orient':str(i.getOrient()),'bbox_um':bb,'literal43_2':all(abs(a/43.2-round(a/43.2))<1e-5 for a in bb[:2]),'faces':dict(faces),'density':densities})
channels=[]
for ia,a in enumerate(mac):
 for c in mac[ia+1:]:
  x1,y1,x2,y2=a['bbox_um'];X1,Y1,X2,Y2=c['bbox_um']
  if min(x2,X2)>max(x1,X1):channels.append({'a':a['inst'],'b':c['inst'],'axis':'Y','gap_um':max(Y1-y2,y1-Y2)})
  if min(y2,Y2)>max(y1,Y1):channels.append({'a':a['inst'],'b':c['inst'],'axis':'X','gap_um':max(X1-x2,x1-X2)})
ports=[]
for pin in b.getBTerms():
 if str(pin.getSigType()) in ['POWER','GROUND']:continue
 ports.append({'name':pin.getName(),'direction':str(pin.getIoType()),'bbox_um':rect(pin.getBBox())})
result={'odb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_odb':str(p),'scope':'Immutable completed3_5placement geometry; NOT finalroute/CTS qualification','dbu':u,'die_um':rect(b.getDieArea()),'macros':mac,'channels':channels,'channel_lt20':[x for x in channels if x['gap_um']<20],'nonliteral43_2':[x['inst'] for x in mac if not x['literal43_2']],'ports':ports}
out.write_text(json.dumps(result,indent=2));print(json.dumps({'macro_count':len(mac),'nonliteral43_2':result['nonliteral43_2'],'channel_lt20':result['channel_lt20'],'face_density':[{x['inst']:x['density']} for x in mac]}))
