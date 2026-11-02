"""DISABLED exact-native T51 all-obstacle/site allocation; no DB writes or CAD."""
from pathlib import Path
import json,gzip,sys,collections,bisect,math,re
R=Path(__file__).parent;P=R/'inputs';sys.path.insert(0,str(R/'tools'));import geom_rules as G
from exact_cones import endpoints
D=G.Design(P/'geom.tsv');orig=dict(D.cells);cs=[json.loads(x)for x in gzip.open(P/'cells.jsonl.gz','rt')];native={c[0]:c for c in cs};idof={c[6]:i for i,c in D.cells.items()};joint=json.load(open(P/'joint_translation.json'))[-1];moves={x['name']:x for x in joint['moved']};rows=json.load(open(P/'rows.json'));ys=sorted({r['origin_dbu'][1]for r in rows});rs=collections.defaultdict(list);occ=collections.defaultdict(list)
for r in rows:rs[r['origin_dbu'][1]].append(r)
def occupy(bb):
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:occ[y].append((bb[0],bb[2]))
for c in cs:
 if c[0]not in moves:occupy(c[2])
for y in occ:occ[y].sort()
land=G.land_ring_captures(D,json.load(open(P/'land_slots.json')),json.load(open(P/'face_guard.json')));assert not land['errors'];pinby={p['name']:p for p in D.pins};pin_constraints=collections.defaultdict(list)
for name,ids in land['caps'].items():
 if name.startswith('ft2_i['):
  for i in ids:pin_constraints[i].append((pinby[name]['x'],pinby[name]['y'],name))
# Actual graph neighbours include reset/control paths as well as data. Both directions constrain movement.
neighbours={};positions={i:G.ctr(c)for i,c in D.cells.items()if c[0]=='S'}
for name,m in moves.items():positions[idof[name]]=m['new']
prior=json.load(open(P/'prior_targets.json'))
for name,t in prior.items():
 i=idof[name];positions[i]=t['xy_um'];dc=list(D.cells[i]);dc[2:6]=[v/1000 for v in t['bbox_dbu']];D.cells[i]=tuple(dc);occupy(t['bbox_dbu'])
for y in occ:occ[y].sort()
for name in moves:
 i=idof[name];a,_=endpoints(D,i,True);b,_=endpoints(D,i,False);neighbours[i]=(a|b)-{i}
print('PREP',len(moves),'moves',sum(len(x)for x in neighbours.values()),'neighbour entries',flush=True)
allocated=dict(prior);failed=[];byfamily=collections.Counter(t['family']for t in prior.values());R2R=402.5
# Reuse accepted coupled translation as desired geometry, then enforce actual occupancy and every incident endpoint.
def allocate(name):
 m=moves[name];i=idof[name];c=native[name];bb0=c[2];w=bb0[2]-bb0[0];h=bb0[3]-bb0[1];wanted=[v*1000 for v in m['new']];family=m['family'];oldroworient={r['orient']for r in rs[bb0[1]]}
 if family=='ft2_ring_band_FFs':area=[60480,1134540,145800,1168560];wanted[0]=max(area[0]+w/2,min(area[2]-w/2,wanted[0]));max_jog=90000
 else:area=[round(wanted[0]-2500),round(wanted[1]-2500),round(wanted[0]+2500),round(wanted[1]+2500)];max_jog=2500
 # Intersect exact L1 diamonds using u=x+y,v=x-y; include all-slot public capture bounds with5um margin.
 umin,vmin=-1e20,-1e20;umax,vmax=1e20,1e20
 for ni in neighbours[i]:
  x,y=[z*1000 for z in positions[ni]];r=R2R*1000;umin=max(umin,x+y-r);umax=min(umax,x+y+r);vmin=max(vmin,x-y-r);vmax=min(vmax,x-y+r)
 for x,y,pname in pin_constraints.get(i,[]):
  x*=1000;y*=1000;r=145000;umin=max(umin,x+y-r);umax=min(umax,x+y+r);vmin=max(vmin,x-y-r);vmax=min(vmax,x-y+r)
 best=None
 for y in ys[bisect.bisect_left(ys,area[1]):bisect.bisect_right(ys,area[3]-h)]:
  cy=y+h/2
  for row in rs[y]:
   if row['orient']not in oldroworient:continue
   lo=max(area[0],row['bbox_dbu'][0],umin-cy-w/2,vmin+cy-w/2);hi=min(area[2]-w,row['bbox_dbu'][2]-w,umax-cy-w/2,vmax+cy-w/2)
   if lo>hi:continue
   free=[];last=lo
   for a,b in occ[y]:
    if b<=lo:continue
    if a>=hi+w:break
    if a>last:free.append((last,min(a,hi+w)))
    last=max(last,b)
   if last<hi+w:free.append((last,hi+w))
   for a,b in free:
    step=row['spacing_dbu'];rx=row['origin_dbu'][0];ia=math.ceil((a-rx)/step);ib=math.floor((b-w-rx)/step)
    if ib<ia:continue
    k=min(ib,max(ia,round((wanted[0]-w/2-rx)/step)));x=rx+k*step;jog=abs(x+w/2-wanted[0])+abs(cy-wanted[1]);key=(jog,y,x)
    if jog<=max_jog and(best is None or key<best[0]):best=(key,[x,y,x+w,y+h],row)
 if best is None:
  failed.append(dict(name=name,family=family,desired=m['new'],area_dbu=area,UV_bounds_dbu=[umin,umax,vmin,vmax],neighbours=[dict(name=D.cells[k][6],xy=positions[k])for k in sorted(neighbours[i])],public_capture_constraints=pin_constraints.get(i,[])));return
 key,bb,row=best;occupy(bb)
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:occ[y].sort()
 pos=[(bb[0]+bb[2])/2000,(bb[1]+bb[3])/2000];positions[i]=pos;dc=list(D.cells[i]);dc[2:6]=[v/1000 for v in bb];D.cells[i]=tuple(dc);byfamily[family]+=1;allocated[name]=dict(master=c[1],bbox_dbu=bb,xy_um=pos,orient=c[4],row=row['name'],family=family,original_xy_um=G.ctr(orig[i]),desired_xy_um=m['new'],jog_from_clamped_desired_um=key[0]/1000,old_status=c[5],proposed_status='FIRM',DPL_pair_margin_um=2.5)
# Small translated stage families first, then most-constrained ring FFs. No latency feedback or target relaxation.
ordered=sorted(moves,key=lambda name:({'ft6_stage2':0,'ft2_stage0':1,'ft2_ring_band_FFs':2}[moves[name]['family']],-len(neighbours[idof[name]]),name))
for name in ordered:
 if name not in prior:allocate(name)
bad=[];metrics=G.r2r_metrics(D,bad);ck=G.clock_metrics(D);pm=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT),frozenset(ck['tap_sinks'])|frozenset(land['clock_exports']),land['caps']);ce=G.clock_entry_metrics(D,ck)
# Preserve a complete ft6 five-stage target census; the accepted explicit-site API maps landed stage i to j=i+1.
ft6={}
for i,c in D.cells.items():
 n=c[6].replace('\\','')
 if c[0]=='S'and n.startswith('u_bound.u_ft_ft6_o_'):
  st=int(n.split('u_ft_ft6_o_')[1].split('/')[0]);ft6[c[6]]=dict(stage=st,master=c[1],bbox_um=list(c[2:6]),xy_um=G.ctr(c),changed=c[6]in allocated)
report=dict(scope='DISABLED bounded continuation for60unallocatedring FFs;3647priorlegaltargets fixed; add30actual270nm rows above previous arbitraryband; no nativeDB/plan/source mutation or CAD',requested_moves=len(moves),allocated=len(allocated),byfamily=dict(byfamily),failed=len(failed),failures=failed,all_native_obstacles=len(cs)-len(moves),actual_TAP=137673,actual_rows=len(rows),all_existing_other_cells_fixed=True,masters_orientations_counts_preserved=True,R2R_constraint_um=R2R,r2r=metrics,remaining_over405=bad,pin_metrics=pm,clock_nearest_INFO=ce,ft6_all_five_stage_FFs=len(ft6),max_jog_um=max((a['jog_from_clamped_desired_um']for a in allocated.values()),default=0),native_census=json.load(open(P/'native_census.json')),holds=['all95696originalPGnull terms remain on47848std buffers; no repair or retroactive timing claim','E/W partial-face pin geometry unchanged FAIL; sparsefill/actualcongestion remain','full native PG geometry unchanged; row parity/native master orientation preserved, but future PG landing/pinaccess must be checked before physical release','no public pins/clock names/source833/stages/cycles/RTL/FFcounts changed','FFtargets remain model-only; future bounded DPL/pose/master guard and all endpoint census required'])
(R/'model.json').write_text(json.dumps(report,indent=2));(R/'targets.json').write_text(json.dumps(allocated,indent=2));(R/'ft6_all_stages.json').write_text(json.dumps(ft6,indent=2));print({k:v for k,v in report.items()if k not in('failures','remaining_over405','pin_metrics','clock_nearest_INFO','native_census','holds')});print(pm);print('CLOCK_INFO',ce)
