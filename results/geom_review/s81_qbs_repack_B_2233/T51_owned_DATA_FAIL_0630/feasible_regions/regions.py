"""DISABLED feasible-region/capacity design analysis, no selection or new placement/CAD."""
from pathlib import Path
import json,gzip,collections,bisect,re,sys,math,gc
R=Path(__file__).parent;P=R/'inputs';sys.path.insert(0,str(R/'tools'));import geom_rules as G
from exact_cones import endpoints
cells=[json.loads(x)for x in gzip.open(P/'cells.jsonl.gz','rt')];native={c[0]:c for c in cells};rows=json.load(open(P/'rows.json'));ys=sorted({r['origin_dbu'][1]for r in rows});rby=collections.defaultdict(list)
for r in rows:rby[r['origin_dbu'][1]].append(r)
F=json.load(open(P/'FF_targets.json'));cg=json.load(gzip.open(P/'classification_graph.json.gz','rt'));owned_DATA={cg['names'][i]for i in cg['eligible']};del cg
movnames={n for n,t in F.items()if t['family']in('ft2_ring_band_FFs','ft2_stage0')};assert len(movnames)==3192
core=json.load(open(P/'native_census.json'))['core_dbu'];occ=collections.defaultdict(list)
def occupy(bb):
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:occ[y].append((bb[0],bb[2]))
for c in cells:
 if c[0]in movnames or c[0]in owned_DATA:continue
 occupy(F[c[0]]['bbox_dbu']if c[0]in F else c[2])
for band in json.load(open(P/'other_declared_band_reservations.json'))['rectangles']:occupy(band['bbox_dbu'])
free={};freearea=0
for y in ys:
 merged=[]
 for a,b in sorted(occ[y]):
  a=max(a,core[0]);b=min(b,core[2])
  if a>=b:continue
  if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
  else:merged.append((a,b))
 gaps=[];last=core[0]
 for a,b in merged:
  if a>last:gaps.append((last,a))
  last=max(last,b)
 if last<core[2]:gaps.append((last,core[2]))
 free[y]=gaps;freearea+=sum(b-a for a,b in gaps)*270
with gzip.open(R/'actual_fixed_free_rows.json.gz','wt')as f:f.write(json.dumps(dict(scope='actual4512rows minus fixed native population/TAP/52bands; only3192ring+stage0FF and9288ownedDATA freed; no PG routing OBS added',rows=[dict(y_dbu=y,origin_x_dbu=rby[y][0]['origin_dbu'][0],orient=rby[y][0]['orient'],spacing_dbu=rby[y][0]['spacing_dbu'],free_x_intervals_dbu=free[y])for y in ys]),separators=(',',':')))
INF=10**15;R405=405000;R150=150000
area_classes={};records={};coupled=[];summaries={};firstclass=[]
def cxy(c):return(round((c[2]+c[4])*500),round((c[3]+c[5])*500))
def getregions(ty):
 D=G.Design(P/ty/'geom.tsv');ld=G.land_ring_captures(D,json.load(open(P/ty/'land_slots.json')),json.load(open(P/ty/'face_guard.json')));assert not ld['errors'];idof={c[6]:i for i,c in D.cells.items()};M={i for i,c in D.cells.items()if c[0]=='S'and((c[6].replace('\\','').startswith('u_bound.u_cland_ft2_i/')and 17.28<=G.ctr(c)[0]<=128.22 and 935.82<=G.ctr(c)[1]<=961.74)or c[6].replace('\\','').startswith('u_bound.u_ft_ft2_o_0/'))};assert len(M)==3192,(ty,len(M))
 if ty=='t51':
  for name,t in F.items():
   if name not in movnames:
    i=idof[name];a=list(D.cells[i]);a[2:6]=[v/1000 for v in t['bbox_dbu']];D.cells[i]=tuple(a)
 pc=collections.defaultdict(list)
 for name,ids in ld['caps'].items():
  if name.startswith('ft2_i['):
   pin=next(p for p in D.pins if p['name']==name)
   for i in ids:pc[i].append((round(pin['x']*1000),round(pin['y']*1000),name))
 out=[];bad=[];radiusmax=0
 for k,i in enumerate(sorted(M)):
  c=D.cells[i];fw=round((c[4]-c[2])*1000);fh=round((c[5]-c[3])*1000);fwd,_=endpoints(D,i,True);back,_=endpoints(D,i,False);neigh=(fwd|back)-{i};fixed=neigh-M;u0,v0,u1,v1=-INF,-INF,INF,INF;why={};uv=[]
  for j in fixed:
   x,y=cxy(D.cells[j]);u=x+y;v=x-y;uv.append((u,v,j))
   for label,val,old in(('u0',u-R405,u0),('v0',v-R405,v0),('u1',u+R405,u1),('v1',v+R405,v1)):
    improve=val>old if label in('u0','v0')else val<old
    if improve:why[label]=dict(endpoint=D.cells[j][6],xy_dbu=[x,y],radius_dbu=R405)
   u0=max(u0,u-R405);v0=max(v0,v-R405);u1=min(u1,u+R405);v1=min(v1,v+R405)
  for x,y,name in pc[i]:
   u=x+y;v=x-y
   for label,val,old in(('u0',u-R150,u0),('v0',v-R150,v0),('u1',u+R150,u1),('v1',v+R150,v1)):
    improve=val>old if label in('u0','v0')else val<old
    if improve:why[label]=dict(pin=name,xy_dbu=[x,y],radius_dbu=R150)
   u0=max(u0,u-R150);v0=max(v0,v-R150);u1=min(u1,u+R150);v1=min(v1,v+R150)
  radius=max(max((x[0]for x in uv),default=0)-min((x[0]for x in uv),default=0),max((x[1]for x in uv),default=0)-min((x[1]for x in uv),default=0))/2;radiusmax=max(radiusmax,radius)
  family='ft2_stage0'if'.u_ft_ft2_o_0/'in c[6]else'ft2_ring'
  rec=dict(name=c[6],master=c[1],width_dbu=fw,height_dbu=fh,family=family,first_capture_pins=[p[2]for p in pc[i]],fixed_endpoint_count=len(fixed),fixed_endpoint_L1_minmax_radius_dbu=radius,UV_bounds_dbu=[u0,u1,v0,v1],active_bound_witnesses=why,coupled_mover_neighbors=[D.cells[j][6]for j in sorted(neigh&M)])
  if u0>u1 or v0>v1:bad.append(rec)
  if ty=='t51':
   nc=native[c[6]];phases=tuple(sorted({r['orient']for r in rby[nc[2][1]]}));key=(u0,u1,v0,v1,fw,fh,phases)
   if key not in area_classes:area_classes[key]=dict(id=len(area_classes),UV_bounds_dbu=[u0,u1,v0,v1],width_dbu=fw,height_dbu=fh,phases=phases,members=[])
   ac=area_classes[key];ac['members'].append(c[6]);rec['legal_area_class']=ac['id'];rec['native_supply_phases']=phases
   if pc[i]:firstclass.append(ac['id'])
  out.append(rec)
  for j in sorted(fwd&M):coupled.append(dict(type=ty,launch=c[6],capture=D.cells[j][6],radius_dbu=R405))
 summaries[ty]=dict(movable_FF=len(M),first_capture_FF=sum(bool(pc[i])for i in M),stage0_FF=sum(x['family']=='ft2_stage0'for x in out),pin_diamond_empty_fixed_cases=len(bad),fixed_endpoint_minmax_radius_max_um=radiusmax/1000,actual_clock_FF=sum(c[0]=='S'for c in D.cells.values()),full_native_ROW_TAP_inventory_available=ty=='t51',notes='all relations between3192movableFFs remain explicit coupled405constraints; no freezing them at old poses in fixed-endpoint bounds')
 records[ty]=out
 print('BOUNDS_READY',ty,summaries[ty],flush=True)
getregions('t51');getregions('t41')
# Exact candidate-origin counts and same-width nonoverlapping capacity; no full FF arrangement is selected.
def inventory(bounds,w,h,phases,region=None):
 u0,u1,v0,v1=bounds;starts=0;pack=0;xmin,ymin=INF,INF;xmax,ymax=-INF,-INF
 ylow=max(core[1],-((-(u0-v1-h))//2));yhigh=min(core[3]-h,(u1-v0-h)//2)
 if region:ylow=max(ylow,region[1]);yhigh=min(yhigh,region[3]-h)
 for y in ys[bisect.bisect_left(ys,ylow):bisect.bisect_right(ys,yhigh)]:
  cy=y+h//2
  for row in rby[y]:
   if row['orient']not in phases:continue
   if region and not(region[1]<=y and y+h<=region[3]):continue
   a=max(core[0],u0-cy-w//2,v0+cy-w//2);b=min(core[2]-w,u1-cy-w//2,v1+cy-w//2)
   if region:a=max(a,region[0]);b=min(b,region[2]-w)
   if a>b:continue
   rx=row['origin_dbu'][0];step=row['spacing_dbu']
   for lo,hi in free[y]:
    if hi-w<a:continue
    if lo>b:break
    aa=max(a,lo);bb=min(b,hi-w)
    if aa>bb:continue
    ka=-((rx-aa)//step);kb=(bb-rx)//step
    if ka>kb:continue
    first=rx+ka*step;last=rx+kb*step;starts+=kb-ka+1;pack+=(last-first)//w+1;xmin=min(xmin,first+w//2);xmax=max(xmax,last+w//2);ymin=min(ymin,cy);ymax=max(ymax,cy)
 return dict(legal_origin_start_sites=starts,legal_origin_configuration_area_um2=starts*54*270/1e6,maximum_same_width_nonoverlap_slots=pack,legal_center_bbox_dbu=None if not starts else[xmin,ymin,xmax,ymax])
for n,ac in enumerate(area_classes.values()):
 ac['inventory']=inventory(ac['UV_bounds_dbu'],ac['width_dbu'],ac['height_dbu'],ac['phases'])
 if n%300==0:print('AREA_CLASSES',n,'of',len(area_classes),flush=True)
# A common region for every public first-capture FF is a strong sufficient capacity witness for pin/fixed constraints,
# but does not solve their coupling to the other movable state/read/stage0 FFs.
fc=[r for r in records['t51']if r['first_capture_pins']];common=[max(x['UV_bounds_dbu'][0]for x in fc),min(x['UV_bounds_dbu'][1]for x in fc),max(x['UV_bounds_dbu'][2]for x in fc),min(x['UV_bounds_dbu'][3]for x in fc)];wmax=max(x['width_dbu']for x in fc);phase_demand=collections.Counter(p for x in fc for p in x['native_supply_phases']);common_report={}
# Rectangles follow existing band/core boundaries, not adopted new floorplan boxes.
corridors={'whole_common_region':None,'above_other_bands':[core[0],1211760,227880,core[3]],'right_of_left_bands':[77540,1076784,227880,1211760],'previous_compressed_bbox':[60480,1134540,128682,1168560]}
for name,reg in corridors.items():
 common_report[name]={phase:dict(demand=phase_demand[phase],max_master_width_dbu=wmax,inventory=inventory(common,wmax,270,(phase,),reg))for phase in phase_demand}
zero_classes=[a['id']for a in area_classes.values()if not a['inventory']['legal_origin_start_sites']]
summary=dict(scope='DISABLED exact perFF pin150/fixed-stage405 feasibility/free-native-row capacity; no chosennewlayout/model/cut/DB/CAD',actual_T51_rows=4512,actual_T51_TAP=137673,held_other_band_rectangles=52,freed_for_joint_design=dict(FF3192=len(movnames),owned_DATA9288=len(owned_DATA)),fixed_native_population=len(cells)-len(movnames)-len(owned_DATA),free_footprint_area_um2=freearea/1e6,type_summaries=summaries,unique_T51_region_classes=len(area_classes),zero_legal_area_classes=zero_classes,first_capture_common_UV_bounds_dbu=common,first_capture_common_region_capacity=common_report,capacity_interpretation='legal starts are configuration-space alternatives, not simultaneous placements; same-width pack counts are exact1D free-row capacities for a common region. Coupled mover405 constraints/read-control layout/demand remain unresolved.',holds=['no intrinsic infeasibility inferred by freezing coupled movers','T41 has exact graph/pin bounds only; no imported T51ROW/TAP authority','clock/source/PG/actualGRT/fill/partialface holds persist; optionalFCLK geometric bounds not silently adopted','existing9288DATAmodel newcut2.703 remains FAIL, unchanged'])
(R/'summary.json').write_text(json.dumps(summary,indent=2));(R/'per_FF_regions.json').write_text(json.dumps(records,indent=2));(R/'region_classes.json').write_text(json.dumps(list(area_classes.values()),indent=2));(R/'coupled_FF_405_edges.json').write_text(json.dumps(coupled,indent=2));print(json.dumps(summary,indent=2))
