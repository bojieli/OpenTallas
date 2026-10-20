"""Check recorded arithmetic and same-anchor collisions; source hashes may be checked on original host."""
import gzip,json,collections,hashlib,sys
from pathlib import Path
root=Path(__file__).resolve().parent
j=json.load(gzip.open(root/'actual_inventory.json.gz','rt'));s=json.load(open(root/'summary.json'))
assert hashlib.sha256((root/'actual_inventory.json.gz').read_bytes()).hexdigest()==s['inventory_gzip_sha256']
inst=j['instances'];assert len(inst)==13766 and len({x['instance'] for x in inst})==13766
assert not j['hard_macro_dimension_errors'];assert dict(collections.Counter(x['master'] for x in inst))==j['master_counts']
native=[x for x in inst if x['master']=='qfd_native59_dv_service'];assert len(native)==1
n=native[0];x,y,xx,yy=n['bbox_um'];assert abs((xx-x)*(yy-y)-403107.84)<1e-6
p=[x,y,x+950.4,y+734.4];over=[]
for i in inst:
 if i['instance']==n['instance']:continue
 a,b,c,d=i['bbox_um']
 if min(p[2],c)>max(p[0],a) and min(p[3],d)>max(p[1],b):over.append(i['instance'])
assert sorted(over)==sorted(x['instance'] for x in j['proposal_same_anchor_overlaps']) and len(over)==142
assert abs(j['price']['delta_um2_per_replica']-(950.4*734.4-777.6*518.4))<1e-6
assert abs(j['price']['ratio_to_actual']-950.4*734.4/(777.6*518.4))<1e-12
assert j['native59_assumed_in_chain'] and j['source_port_bind_native59']['param_sets']=={'{}':1}
if '--verify-source' in sys.argv:
 for p,z in j['inputs'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==z['sha256'],p
print(json.dumps({'status':'ARITHMETIC_AND_INVENTORY_PASS_MODEL_ONLY_HOLD','hard_instances':len(inst),'native59_replicas':1,'same_anchor_overlaps':len(over),'ratio_to_actual':j['price']['ratio_to_actual'],'additional_mm2':j['price']['additional_die_area_mm2']}))
