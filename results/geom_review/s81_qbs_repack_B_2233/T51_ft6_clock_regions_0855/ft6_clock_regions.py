"""Finite feasible-region diagnosis of existing ft6 stage2; no layout, target allocation, DB or CAD."""
from pathlib import Path
import json,gzip,collections,bisect,math,sys
R=Path(__file__).parent;P=R/'inputs';sys.path.insert(0,str(R/'tools'));import geom_rules as G
from exact_cones import endpoints
C=[json.loads(s)for s in gzip.open(P/'cells.jsonl.gz','rt')];native={c[0]:c for c in C};F=json.load(open(P/'joint_FF_targets.json'));T=json.load(open(R/'DATA_targets.json'));A=dict(F);A.update(T);M={n for n,t in F.items()if t['family']=='ft6_stage2'};assert len(M)==515;rows=json.load(open(P/'rows.json'));rs=collections.defaultdict(list);occ=collections.defaultdict(list)
for r in rows:rs[r['origin_dbu'][1]].append(r)
ys=sorted(rs);core=json.load(open(P/'native_census.json'))['core_dbu'];taplist=json.load(open(P/'current_plan.json'))['partition_types']['slice_station__t51']['clock']['taps'];taps=[(t['name'],*[round(v*1000)for v in t['xy']])for t in taplist if t.get('kind')!='core']
def occupy(bb):
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:occ[y].append((bb[0],bb[2]))
for c in C:
 if c[0]in M:continue
 occupy(A[c[0]]['bbox_dbu']if c[0]in A else c[2])
for band in json.load(open(P/'other_declared_band_reservations.json'))['rectangles']:occupy(band['bbox_dbu'])
free={}
for y in ys:
 merged=[]
 for a,b in sorted(occ[y]):
  if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
  else:merged.append((a,b))
 gaps=[];last=core[0]
 for a,b in merged:
  if a>last:gaps.append((last,a))
  last=max(last,b)
 if last<core[2]:gaps.append((last,core[2]))
 free[y]=gaps
D=G.Design(P/'geom.tsv');idof={c[6]:i for i,c in D.cells.items()}
for n,t in A.items():
 i=idof[n];c=list(D.cells[i]);c[2:6]=[v/1000 for v in t['bbox_dbu']];D.cells[i]=tuple(c)
out=[];INFT=10**15
for n in sorted(M):
 i=idof[n];c=native[n];w=c[2][2]-c[2][0];h=c[2][3]-c[2][1];phases={r['orient']for r in rs[c[2][1]]};fd,_=endpoints(D,i,True);bk,_=endpoints(D,i,False);ns=(fd|bk)-{i};assert not any(D.cells[j][6]in M for j in ns),'stage2 neighbours should be fixed first-register frontiers';u0,v0=-INFT,-INFT;u1,v1=INFT,INFT;end=[]
 for j in ns:
  x,y=[round(z*1000)for z in G.ctr(D.cells[j])];u=x+y;v=x-y;u0=max(u0,u-405000);u1=min(u1,u+405000);v0=max(v0,v-405000);v1=min(v1,v+405000);end.append(dict(name=D.cells[j][6],xy_dbu=[x,y]))
 old=F[n]['xy_um'];cx,cy=[v*1000 for v in old];count=0;best=None;count405=0
 # All permissible native sites, not merely a chosen search window.
 yl=max(core[1],math.ceil((u0-v1-h)/2));yh=min(core[3]-h,math.floor((u1-v0-h)/2))
 for y in ys[bisect.bisect_left(ys,yl):bisect.bisect_right(ys,yh)]:
  yy=y+h/2
  for row in rs[y]:
   if row['orient']not in phases:continue
   lo=max(core[0],row['bbox_dbu'][0],u0-yy-w/2,v0+yy-w/2);hi=min(core[2]-w,row['bbox_dbu'][2]-w,u1-yy-w/2,v1+yy-w/2)
   if lo>hi:continue
   available=[]
   for aa,bb in free[y]:
    a=max(aa,lo);b=min(bb-w,hi)
    if a>b:continue
    rx=row['origin_dbu'][0];step=row['spacing_dbu'];count405+=max(0,math.floor((b-rx)/step)-math.ceil((a-rx)/step)+1)
    for name,tx,ty in taps:
     rad=150000-abs(yy-ty)
     if rad<0:continue
     ca=max(a,tx-rad-w/2);cb=min(b,tx+rad-w/2)
     if ca<=cb:available.append((ca,cb))
   union=[]
   for a,b in sorted(available):
    if union and a<=union[-1][1]:union[-1]=(union[-1][0],max(b,union[-1][1]))
    else:union.append((a,b))
   for a,b in union:
    rx=row['origin_dbu'][0];step=row['spacing_dbu'];ia=math.ceil((a-rx)/step);ib=math.floor((b-rx)/step)
    if ib<ia:continue
    count+=ib-ia+1;k=min(ib,max(ia,round((cx-w/2-rx)/step)));x=rx+k*step;dist=abs(x+w/2-cx)+abs(yy-cy);key=(dist,y,x)
    if best is None or key<best[0]:best=(key,[x+w/2,yy],row['name'])
 current_nearest=min((abs(cx-tx)+abs(cy-ty),name)for name,tx,ty in taps);record=dict(name=n,master=c[1],orient=c[4],current_model_xy_um=old,current_nearest_tap=current_nearest[1],current_nearest_radius_um=current_nearest[0]/1000,UV_fixed405_bounds_dbu=[u0,u1,v0,v1],fixed_endpoint_witnesses=end,native405legal_start_sites=count405,native405_and_tap150_legal_start_sites=count,independent_nearest_site_witness=None)
 if best:
  key,xy,row=best;tapdist,tapname=min((abs(xy[0]-tx)+abs(xy[1]-ty),name)for name,tx,ty in taps);maxedge=max(abs(xy[0]-v['xy_dbu'][0])+abs(xy[1]-v['xy_dbu'][1])for v in end);record['independent_nearest_site_witness']=dict(xy_um=[v/1000 for v in xy],jog_um=key[0]/1000,row=row,tap=tapname,radius_um=tapdist/1000,max_fixed_endpoint_um=maxedge/1000)
 out.append(record)
 if len(out)%100==0:print('REGIONS',len(out),'ZERO',sum(x['native405_and_tap150_legal_start_sites']==0 for x in out),flush=True)
report=dict(scope='No-target-selecting independent feasible-region diagnosis; no simultaneous515FF placement/load/cut/CAD result. All current-model othercells/FF/DATA/TAP/52bands fixed.',stage2_FFs=len(M),actual_taps=len(taps),required_reach_um=405,required_clock_radius_um=150,zero_fixed405_native_area=sum(x['native405legal_start_sites']==0for x in out),zero_fixed405_and_tap150_native_area=sum(x['native405_and_tap150_legal_start_sites']==0for x in out),current_over150=sum(x['current_nearest_radius_um']>150for x in out),max_independent_nearest_jog_um=max((x['independent_nearest_site_witness']['jog_um']for x in out if x['independent_nearest_site_witness']),default=None),minimum_site_count=min(x['native405_and_tap150_legal_start_sites']for x in out),simultaneous_occupancy_and_load_not_evaluated=True,unchanged_node_cycle_port_counts=True,records=out)
(R/'ft6_clock_regions.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items()if k!='records'},flush=True)
