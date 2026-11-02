from pathlib import Path
import odb,json,hashlib,copy,os
from core_cts_open_rebind import snapshot,digest,require
R=Path('/out');src=R/'input.odb';dst=R/'WEST2_geometry_ONLY.odb';H='b317b6613ccf8d6d72cadd2937bf1fd84d4c42f5f255405d6c3586e5969c4e86';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();plan=json.load(open(R/'plan.json'))['options'][0];mode=os.environ['MODE']
def box(i):
 b=i.getBBox();return [b.xMin(),b.yMin(),b.xMax(),b.yMax()]
def hit(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
def mask(s,deleted):
 s=copy.deepcopy(s)
 for n in deleted:s['instances'].pop(n,None)
 for n in plan['changes']:
  for k in ['bbox','origin']:s['instances'][n][k]='EXPLICIT_TWO_DATA_POSES'
 return s
require(sha(src)==H,'immutable input hash');db=odb.dbDatabase.create();odb.read_db(db,str(src if mode=='copy' else dst));b=db.getChip().getBlock();u=db.getTech().getDbUnitsPerMicron()
if mode=='audit':
 rec=json.load(open(R/'receipt.json'));require(sha(dst)==rec['output_sha256'],'saved identity');require(digest(mask(snapshot(b),rec['deleted_spacers']))==rec['guard_after'],'independent saved full snapshot');print('SAVED_COPY_GUARD_PASS');(R/'saved_audit.json').write_text(json.dumps({'verdict':'PASS','output_sha256':sha(dst),'scope':'independent fresh native DB; all preserved state digest'},indent=2));raise SystemExit
require(not dst.exists() and not (R/'receipt.json').exists(),'fresh only');before=snapshot(b);names=set(plan['changes']);targets={};deleted=[];rows=[]
for row in b.getRows():
 bb=row.getBBox();rows.append([bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax(),str(row.getOrient()),row.getOrigin(),row.getSpacing()])
for n,q in plan['changes'].items():
 i=b.findInst(n);require(i is not None,'target exists');old=q['old'];require(i.getMaster().getName()==q['master']==old['master'],'same master');require(str(i.getOrient())=='R0' and old['orient']=='N' and q['orient']=='N','same N orientation');require([round(z/u,6) for z in i.getLocation()]==[old['x'],old['y']],'actual old lowerleft');xy=[round(z*u) for z in q['origin_um']];bb=[round(z*u) for z in q['bbox_um']];require(any(r[4]=='R0' and r[1]==xy[1] and r[0]<=xy[0] and bb[2]<=r[2] and (xy[0]-r[5][0])%r[6]==0 for r in rows),'native actual ROW/site/orient');targets[n]=dict(instance=i,xy=xy,bbox=bb)
for i in b.getInsts():
 if i.getName() in names:continue
 if not any(hit(box(i),q['bbox']) for q in targets.values()):continue
 require(str(i.getMaster().getType())=='CORE_SPACER','only exact PG spacer overlap, no TAP/functional');require(all(str(mt.getSigType()) in ['POWER','GROUND'] for mt in i.getMaster().getMTerms()),'PG-only spacer');deleted.append(i.getName())
# Macro halo and actual retained upper PG obstruction census, excluding normal followpin rails.
for i in b.getInsts():
 if str(i.getMaster().getType())!='BLOCK':continue
 a=box(i);halo=round(4.32*u);a=[a[0]-halo,a[1]-halo,a[2]+halo,a[3]+halo];require(not any(hit(a,q['bbox']) for q in targets.values()),'actual macro halo4.32')
for net in b.getNets():
 if str(net.getSigType()) not in ['POWER','GROUND']:continue
 for sw in net.getSWires():
  for sh in sw.getWires():
   layer=sh.getTechLayer() if not sh.isVia() else None
   if layer and layer.getName() in ['M4','M5']:
    a=[sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax()];require(not any(hit(a,q['bbox']) for q in targets.values()),'actual upper PG clearance')
def def_guard(path):
 h=hashlib.sha256();inside=False;skip=False
 with path.open() as f:
  for line in f:
   if line.startswith('COMPONENTS '):inside=True;continue
   if inside and line.startswith('END COMPONENTS'):inside=False;skip=False;continue
   if inside and line.lstrip().startswith('- '):skip=line.split()[1] in (names|set(deleted))
   if not (inside and skip):h.update(line.encode())
 return h.hexdigest()
odb.write_def(b,str(R/'before.def'));wire_guard_before=def_guard(R/'before.def')
for n in deleted:odb.dbInst.destroy(b.findInst(n))
for n,q in targets.items():
 i=q['instance'];status=i.getPlacementStatus();i.setPlacementStatus('PLACED');i.setLocation(*q['xy']);i.setPlacementStatus(status);require(box(i)==q['bbox'],'actual new bbox exact')
odb.write_def(b,str(R/'after.def'));wire_guard_after=def_guard(R/'after.def');require(wire_guard_before==wire_guard_after,'full native DEF preserved except enumerated component records/count');after=snapshot(b);a=digest(mask(before,deleted));z=digest(mask(after,deleted));require(a==z,'all non-target instance/master/status/DNT/net/CLK/DATA/PG/port state preserved');require(set(before['instances'])-set(after['instances'])==set(deleted),'exact deletion set');require(set(after['instances'])-set(before['instances'])==set(),'no new cells');odb.write_db(db,str(dst));rec=dict(schema='opentallas.caprt_west2_geometry_copy.v1',verdict='GEOMETRY_ONLY_NO_RC_ROUTE_STA',input_sha256=H,output_sha256=sha(dst),full_DEF_masked_before=wire_guard_before,full_DEF_masked_after=wire_guard_after,changes=plan['changes'],deleted_spacers=sorted(deleted),guard_before=a,guard_after=z,instance_count_before=len(before['instances']),instance_count_after=len(after['instances']),retained_routes='OLD WIRES UNCHANGED; STALE FOR MOVED DATA ENDPOINTS; NO TIMING OR ROUTING CREDIT',scope='two DATA poses only, exact same N orient/masters; minimal overlapping PG-only CORE_SPACER deletion; all other state unchanged')
(R/'receipt.json').write_text(json.dumps(rec,indent=2));print('WEST2_GEOMETRY_COPY_PASS',json.dumps(rec))
