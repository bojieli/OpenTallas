"""Finite existing-comb GPL guide model; insert no logic and move no FF/clock."""
import json,gzip,csv,math,bisect,collections,sys,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parent/'kv_ctl_compact233x302_PREP_1102';C=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-compact250-0430/collector');hot=json.loads(gzip.decompress((O/'hotspot_contributors.json.gz').read_bytes()));cells={c[6]:c for c in json.loads(gzip.decompress((P/'source_cell_model_PREP.json.gz').read_bytes()))};ff=json.loads(gzip.decompress((P/'FF_sites_PREP.json.gz').read_bytes()));sites=json.load(open(P/'candidate_macro_sites_PREP.json'));buf=json.load(open(O/'measured_buffer_space_summary.json'))
zones=[dict(name=f'H{i}',direction='H',bbox_um=[4.32,269.73+9.45*i,228.96,279.18+9.45*i]) for i in range(3)]+[dict(name='V0',direction='V',bbox_um=[82.566,50.22,97.2,250.02]),dict(name='V1',direction='V',bbox_um=[97.2,50.22,108.,250.02]),dict(name='V2',direction='V',bbox_um=[123.12,50.22,151.2,250.02])];byzone={z['name']:z for z in zones};members={};weights=collections.defaultdict(float);cover={}
for win in hot['windows']:
 d=win['direction'];eligible=set()
 for q in win['contributors']:
  for n in q['movable_comb_cells']:
   c=cells[n];x,y=(c[2]+c[4])/2,(c[3]+c[5])/2
   if (d=='H' and 255<=y<=267) or(d=='V' and 98<=x<=110 and 60<=y<=250):eligible.add(n)
 for q in win['contributors']:
  ns=sorted(eligible&set(q['movable_comb_cells']))
  for n in ns:weights[n]+=q['crossing_share']/len(ns)
 cover[d]=dict(selected_cells=len(eligible),old_hot_window_share_covered=sum(q['crossing_share'] for q in win['contributors'] if eligible&set(q['movable_comb_cells'])),old_hot_window_residual=sum(q['crossing_share'] for q in win['contributors'] if not eligible&set(q['movable_comb_cells'])))
 zz=[z for z in zones if z['direction']==d];cum=0.;total=sum(weights[n] for n in eligible)
 if d=='V':
  packing_quantum=max(weights[n] for n in eligible);middle=max(0,min(total,.6*win['derated_window_tracks']-cover[d]['old_hot_window_residual']-packing_quantum));targets=[(total-middle)/2,middle,(total-middle)/2]
 else:targets=[total/3]*3
 boundaries=[targets[0],targets[0]+targets[1],total]
 # Preserve source-cone ordering while equalising the observed hotspot crossing-share workload.
 for n in sorted(eligible,key=lambda n:((cells[n][3]+cells[n][5])/2,(cells[n][2]+cells[n][4])/2,n) if d=='H' else((cells[n][2]+cells[n][4])/2,(cells[n][3]+cells[n][5])/2,n)):
  assert n not in members
  k=bisect.bisect_right(boundaries,cum+weights[n]/2);k=min(2,k);members[n]=zz[k]['name'];cum+=weights[n]
raw=list(csv.DictReader(open(C/'instances.csv')));occ=collections.defaultdict(list);RH,SW=270,54
for q in raw:
 if q['kind']=='tap':
  x,y,w,h=[round(float(q[k])*1000) for k in ['x','y','w','h']];x-=8640;y+=8640
  if 4320<=y<298080 and x+w>4320 and x<228960:occ[y].append((x,x+w,'PRIOR_TAP_OBSTACLE'))
for q in ff:
 x,y=q['ll_dbu'];w,h=q['size_dbu'];occ[y].append((x,x+w,q['name']))
for y in occ:occ[y].sort()
rows=json.load(open(C/'rows.json'))['rows'];first=min(rows,key=lambda q:q['bbox'][1]);first_y=first['bbox'][1];first_orient=first['orient'];block=collections.defaultdict(list);ys=list(range(4320,298080,RH))
for y in ys:
 for m in sites:
  x0,y0,x1,y1=m['x']*1000-4320,m['y']*1000-4320,(m['x']+m['width'])*1000+4320,(m['y']+m['height'])*1000+4320
  if y<y1 and y+RH>y0:block[y].append((x0,x1,'MACRO_HALO'))
 if y<155720 and y+RH>146680:block[y].append((112120,121160,'CLOCK_BAY'))
def free_intervals(lo,hi,blocked):
 left=lo
 for a,b,_ in sorted(blocked):
  if b<=left:continue
  if a>=hi:break
  if a>left:yield left,min(a,hi)
  left=max(left,b)
 if left<hi:yield left,hi

def allocate(name,w,h,z,tx,ty):
 x0,y0,x1,y1=[round(v*1000) for v in z['bbox_um']];best=None
 for y in ys[max(0,bisect.bisect_left(ys,y0)):bisect.bisect_right(ys,y1-h)]:
  for a,b in free_intervals(x0,x1,occ[y]+block[y]):
   lo=4320+math.ceil((a-4320)/SW)*SW;hi=4320+math.floor((b-w-4320)/SW)*SW
   if lo>hi:continue
   x=max(lo,min(hi,4320+round((tx-w/2-4320)/SW)*SW));score=abs(x+w/2-tx)+4*abs(y+h/2-ty)
   if best is None or score<best[0]:best=(score,x,y)
 if best is None:raise RuntimeError(('GUIDE_ROW_SPACE_FAIL',name,z['name'],w,h))
 _,x,y=best;bisect.insort(occ[y],(x,x+w,name));return [x,y]
placed=[]
for z in zones:
 names=sorted([n for n,zn in members.items() if zn==z['name']],key=lambda n:((cells[n][2]+cells[n][4])/2,n) if z['direction']=='H' else((cells[n][3]+cells[n][5])/2,n));N=len(names)
 for k,n in enumerate(names):
  c=cells[n];w,h=round((c[4]-c[2])*1000),round((c[5]-c[3])*1000);assert h==RH
  x0,y0,x1,y1=[v*1000 for v in z['bbox_um']]
  if z['direction']=='H':tx=max(x0+w/2,min(x1-w/2,(c[2]+c[4])*500));ty=y0+h/2+(y1-y0-h)*(k+.5)/N
  else:tx=x0+w/2+(x1-x0-w)*(k+.5)/N;ty=max(y0+h/2,min(y1-h/2,(c[3]+c[5])*500))
  x,y=allocate(n,w,h,z,tx,ty);orient=first_orient if ((y-first_y)//RH)%2==0 else ('MX' if first_orient=='R0' else 'R0');placed.append(dict(name=n,master=c[1],zone=z['name'],old_bbox_um=c[2:6],ll_dbu=[x,y],size_dbu=[w,h],orient=orient,crossing_share_weight=weights[n]))
total_area=sum(p['size_dbu'][0]*p['size_dbu'][1]/1e6 for p in placed);buffer_space=buf['space_at_genuine_GPL_density_point6_um2'];zone_stats=[]
for z in zones:
 a,b,c,d=z['bbox_um'];sel=[p for p in placed if p['zone']==z['name']];area=sum(p['size_dbu'][0]*p['size_dbu'][1]/1e6 for p in sel);fixed=sum(max(0,min(c,(q['ll_dbu'][0]+q['size_dbu'][0])/1000)-max(a,q['ll_dbu'][0]/1000))*max(0,min(d,(q['ll_dbu'][1]+q['size_dbu'][1])/1000)-max(b,q['ll_dbu'][1]/1000)) for q in ff);box=(c-a)*(d-b);reserve=buffer_space*area/total_area;zone_stats.append(dict(**z,cells=len(sel),functional_cell_area_um2=area,fixed_FF_area_um2=fixed,measured_normal_buffer_space_reserve_um2=reserve,space_budget_fraction=(area/.6+fixed+reserve)/box,old_hot_window_crossing_share=sum(p['crossing_share_weight'] for p in sel)))
r=dict(status='FINITE_SAME_SOURCE_GPL_COMB_ROAD_PREP_NOT_NATIVE_PLACE',cells=len(placed),functional_cell_area_um2=total_area,measured_buffer_cell_area_um2=buf['selected_cell_area_um2'],measured_buffer_space_reserve_um2=buffer_space,buffer_insertions=0,FF_moves=0,FF_master_changes=0,clock_moves=0,RTL_changes=0,cycles_added=0,source_hotspot_coverage=cover,zones=zone_stats,maximum_modeled_cell_move_L1_um=max(abs((p['old_bbox_um'][0]+p['old_bbox_um'][2])/2-(p['ll_dbu'][0]+p['size_dbu'][0]/2)/1000)+abs((p['old_bbox_um'][1]+p['old_bbox_um'][3])/2-(p['ll_dbu'][1]+p['size_dbu'][1]/2)/1000) for p in placed),limits=['Model comb sites use expected source-phase rows and translated prior TAP obstacles, not a new native floorplan','Runtime mechanism is normal INCLUSIVE GPL regions, released before DPL/repair; no selected cell is FIRM or DONT_TOUCH','Known normal buffer footprint is space reserve only; no BUF inserted or route capacity claimed','Actual new ROW/TAP/PG, ordinary buffer counts, timing and resulting local geometry remain required'])
assert max(z['space_budget_fraction'] for z in zone_stats)<.6
(O/'comb_road_model.json.gz').write_bytes(gzip.compress(json.dumps(dict(report=r,cells=placed),separators=(',',':')).encode(),mtime=0));(O/'comb_road_summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
