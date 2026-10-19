"""Exact-source bounded native geometry preflight; never runs CTS or routing."""
import odb, json, math, collections, hashlib, sys
from pathlib import Path
sys.path.insert(0, '/run')
import check_macro_track_alignment as cm

db=odb.dbDatabase.create(); odb.read_db(db,'init.odb')
b=db.getChip().getBlock(); u=b.getDbUnitsPerMicron()
def rect(r):return [r.xMin()/u,r.yMin()/u,r.xMax()/u,r.yMax()/u]
def box(i):return rect(i.getBBox())
def area(i):return i.getMaster().getWidth()*i.getMaster().getHeight()/u/u
def seq(i):return any(t.getMTerm().getName() in ('CLK','CK') for t in i.getITerms()) and not i.getMaster().isBlock()
def transparent(i):return i.getMaster().getName().startswith(('BUF','INV','HB'))
def trace(n,forward,seen=None):
 seen=set() if seen is None else seen
 if n is None or n.getId() in seen:return []
 seen=seen|{n.getId()}; out=[]
 for t in n.getITerms():
  if t.getIoType()!=('INPUT' if forward else 'OUTPUT'):continue
  i=t.getInst()
  if seq(i) or i.getMaster().isBlock() or not transparent(i):out.append(t);continue
  for q in i.getITerms():
   if q.getIoType()==('OUTPUT' if forward else 'INPUT'):out+=trace(q.getNet(),forward,seen)
 return out

macros=sorted((i for i in b.getInsts() if i.getMaster().isBlock()),key=lambda i:i.getName())
assert len(macros)==5
placements=[(43.2,43.2),(259.2,43.2),(43.2,345.6),(259.2,345.6)]
zs=[i for i in macros if i.getMaster().getName()=='ot_nhb_zh']
for i,(x,y) in zip(zs,placements):i.setOrient('R0');i.setLocation(round(x*u),round(y*u));i.setPlacementStatus('FIRM')
rr=[i for i in macros if i.getMaster().getName()=='ot_qkh_recip_leaf'];assert len(rr)==1
rr[0].setOrient('R0');rr[0].setLocation(round(475.2*u),round(259.2*u));rr[0].setPlacementStatus('FIRM')
contact={}
for fn in ['zh.lef','recip.lef']:
 m=cm.parse_lef(Path(fn).read_text())[0]
 contact[m['name']]={'sha256':hashlib.sha256(Path(fn).read_bytes()).hexdigest(),'size_um':[m['W']/1000,m['H']/1000],'declared_symmetry':m['symmetry'],'orientations':{o:cm.check_placement(m,o,43200,43200) for o in cm.MIRROR_SET}}

ports=[]; faces=collections.defaultdict(list)
for p in b.getBTerms():
 n=p.getName();root=n.split('[')[0]
 if root.startswith(('ap0','ap1','am0','am1','fr_')):face='W'
 elif root.startswith(('ap2','ap3','am2','am3')):face='E'
 else:face='N'
 faces[face].append(p)
for face,ps in faces.items():
 ps.sort(key=lambda p:p.getName())
 L=540 if face in 'WE' else 734.4
 for k,p in enumerate(ps):
  q=(k+1)*L/(len(ps)+1)
  if p.getName()=='ck':q=367.2
  elif p.getName()=='rst_n':q=368.16
  elif face=='N' and abs(q-367.68)<2.16:q-=4.32
  # Exact preferred-direction track; legal 24x84nm pin area 2016nm2.
  q=(round((q-.012)/.048)*.048+.012)
  if face=='W':xy=[0,q];r=[0,q-.012,.084,q+.012];layer='M4'
  elif face=='E':xy=[734.4,q];r=[734.316,q-.012,734.4,q+.012];layer='M4'
  else:xy=[q,540];r=[q-.012,539.916,q+.012,540];layer='M5'
  pin=odb.dbBPin_create(p);pin.setPlacementStatus('FIRM');odb.dbBox_create(pin,db.getTech().findLayer(layer),*[round(v*u) for v in r])
  endpoints=trace(p.getNet(),p.getIoType()=='INPUT') if p.getName() not in ('ck','rst_n') else []
  xy=[(r[0]+r[2])/2,(r[1]+r[3])/2]
  ports.append({'port':p.getName(),'face':face,'xy':xy,'pin_rect_um':r,'pin_layer':layer,'endpoints':[{'inst':t.getInst().getName(),'master':t.getInst().getMaster().getName(),'pin':t.getMTerm().getName(),'area_um2':area(t.getInst()),'is_ff':seq(t.getInst())} for t in endpoints]})

regs=[i for i in b.getInsts() if seq(i)]
boundary={e['inst'] for p in ports for e in p['endpoints'] if e['is_ff']}
face_area=sum(area(b.findInst(n)) for n in boundary)
nonboundary_area=sum(area(i) for i in b.getInsts() if not i.getMaster().isBlock() and i.getName() not in boundary)
out={'schema':'opentallas.ahub.safe_physical_preflight.v1','source_commit':'483ac4ba8','tools_commit':'59835e962','source_native_sha256':hashlib.sha256(Path('native.v').read_bytes()).hexdigest(),'qualified':False,'native_contact':contact,'macros':[{'inst':i.getName(),'master':i.getMaster().getName(),'box_um':box(i),'orientation':i.getOrient()} for i in macros],'std_area_um2':sum(area(i) for i in b.getInsts() if not i.getMaster().isBlock()),'ff_count':len(regs),'boundary_ff_count':len(boundary),'boundary_ff_area_um2':face_area,'other_std_area_um2':nonboundary_area,'face_counts':{k:len(v) for k,v in faces.items()},'face_density_per_um':{k:len(v)/(540 if k in 'WE' else 734.4) for k,v in faces.items()},'ports':ports,'actual_rows':{'count':len(list(b.getRows())),'area_um2':sum(r.getSite().getWidth()*r.getSite().getHeight()*r.getSiteCount()/u/u for r in b.getRows())}}
out['blockers']=['Source-bound region/row allocation must fit actual boundary and core cell areas before placement; no global placement, CTS, route, PG or native timing qualification.']
shared=collections.defaultdict(list)
for p in ports:
 for e in p['endpoints']:
  if e['is_ff']:shared[e['inst']].append(p)
out['cross_face_sources']=[]
for name,ps in shared.items():
 if len(set(p['face'] for p in ps))<2:continue
 def rect_distance(p,q):
  a=p['pin_rect_um'];z=q['pin_rect_um']
  return max(0,a[0]-z[2],z[0]-a[2])+max(0,a[1]-z[3],z[1]-a[3])
 pairs=[(rect_distance(p,q),p['port'],q['port']) for p in ps for q in ps]
 d,a,z=max(pairs)
 out['cross_face_sources'].append({'inst':name,'ports':[p['port'] for p in ps],'diameter_um':d,'minimum_possible_max_leg_um':d/2,'witness_pair':[a,z]})
out['cross_face_sources'].sort(key=lambda r:-r['diameter_um'])
out['face_flop_port_count']=sum(any(e['is_ff'] for e in p['endpoints']) for p in ports)
out['face_flop_endpoint_occurrences']=sum(e['is_ff'] for p in ports for e in p['endpoints'])
out['blockers']=[
 'Boundary correspondence fails dedicated-face identity:623 signal ports with FF endpoints use only540 distinct FF;35 AM sources each drive allfour stacks. Additional22 same-edge command copies account for645 FF endpoint occurrences.',
 'Current explicit full-face pin assignment has paired AM pin-rectangle minimum distance914.784um. Triangle inequality requires at least457.392um on one leg, greater than405um even allowing arbitrary access points within both contacts. Different pin assignment may reduce this bound; it does not restore dedicated face FF identities.',
 'No source-bound row/fence/clock ownership plan can be admitted before dedicated face-source identity is repaired; GP/DPL/CTS/route intentionally not launched.'
]
json.dump(out,open('floorplan.json','w'),indent=2)
odb.write_db(db,'floorplan.odb')
print(json.dumps({k:v for k,v in out.items() if k not in ('ports','native_contact')},indent=2))
