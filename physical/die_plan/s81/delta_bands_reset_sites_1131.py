#!/usr/bin/env python3
"""Refill S81's17 newly added ring bands around actual fixed reset/control sites.
Usage: PYTHONPATH=tools/die_plan python physical/die_plan/s81/delta_bands_reset_sites_1131.py ROOT OUT.
Each complete type retains all macro/FT/other-band obstacles and original padded reserve.
PHY domain nonintersection is asserted before this type-local geometry solver is used.
"""
import copy,hashlib,json,re,sys,time
from pathlib import Path
import clock_landing_plan as C,compact_plan as CP
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
pp=root/'physical/die_plan/s81/plan_h2_2249.json';sp=root/'physical/die_plan/s81/h2_2249/landed_sidecar_h2.json'
raw=json.loads(pp.read_text());side=json.loads(sp.read_text());targets=json.load(open(root/'physical/die_plan/s81/delta_bands_1101_report.json'))['bands']
by={}
for r in targets:
 tn,bus=r['type'],r['bus'];by.setdefault(tn,[]).append(bus);b=raw['partition_types'][tn]['clock']['landing_contract']['bands'][bus]
 raw['partition_types'][tn]['clock']['landing_contract']['bands'][bus]=dict(placement='FAIL',rect_um=None,instance=b['instance'])
# No target instance overlaps a PHY PG domain, so this geometry-only
# snapshot needs no external PHY LEF materialization. Never skip an intersecting domain.
for part in raw['partitions']:
 if part['type'] not in by:continue
 x,y=part['origin_um'];w,h=raw['partition_types'][part['type']]['outline_um']
 for domain in raw['die']['pg']['domains']:
  if domain.get('io'):
   a,b,c,d=domain['rect_um'];assert min(x+w,c)<=max(x,a)+1e-6 or min(y+h,d)<=max(y,b)+1e-6,(part['name'],domain['name'])
report=[];failures=[]
# Each singleton type is independent. Save each completed type immediately.
for tn,buses in by.items():
 start=time.time()
 try:
  planning={'partition_types':{tn:raw['partition_types'][tn]}}
  new,rep=C.fill_failed_bands(planning,side,[tn]);raw['partition_types'][tn]=new['partition_types'][tn]
 except Exception as e:
  failure=dict(type=tn,buses=buses,error=str(e),seconds=round(time.time()-start,2));failures.append(failure)
  (out/(tn+'.failure.json')).write_text(json.dumps(failure,indent=1)+'\n');print('FAIL',json.dumps(failure),flush=True);continue
 lc=raw['partition_types'][tn]['clock']['landing_contract'];stored=side['collector']['types'][tn]
 for bus in buses:
  b=lc['bands'][bus];rs=b.get('rects_um') or [b['rect_um']]
  actual=C.reset_site_rects(lc.get('collector_tree'))
  assert not any(C._rect_overlap(r,o) for r in rs for o in actual),(tn,bus)
  for src in lc.get('collector_local_sources',[]):
   if src['name']==bus:src['band']=copy.deepcopy(b)
  stored.setdefault('bands',{})[bus]=copy.deepcopy(b)
  for src in stored.get('local_sources',[]):
   if src['name']==bus:src['band']=copy.deepcopy(b)
 (out/(tn+'.json')).write_text(json.dumps(dict(type=raw['partition_types'][tn],sidecar=stored,report=rep),indent=1)+'\n')
 for r in rep:r['seconds']=round(time.time()-start,2)
 report+=rep;print(tn,json.dumps(rep),flush=True)
text=pp.read_text()
for tn in by:
 m=re.search(r'^  "'+re.escape(tn)+r'": ',text,re.M);assert m
 _,j=json.JSONDecoder().raw_decode(text,m.end());text=text[:m.end()]+CP._d(raw['partition_types'][tn],2)+text[j:]
assert json.loads(text)==raw
(out/'plan.json').write_text(text);(out/'sidecar.json').write_text(json.dumps(side,separators=(',',':'))+'\n')
(out/'report.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(pp.read_bytes()).hexdigest(),bands=report,failures=failures,types=list(by),rule='actual fixed reset/control sites excluded; existing padded reserve and pin reach unchanged'),indent=1)+'\n')
print('DONE',len(report),'bands',len(by),'types','failures',len(failures),flush=True)
if failures:sys.exit(1)
