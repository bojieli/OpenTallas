"""Same-outline S81 ES PHY clock/reset geometric estimate; no plan mutation or physical timing claim."""
import json,math,heapq
from pathlib import Path
ROOT=Path(__file__).parent
P=json.load(open(ROOT/'input.json'));HALF=2.16

def hit_point(p,r):return r[0]-HALF < p[0] < r[2]+HALF and r[1]-HALF < p[1] < r[3]+HALF

def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0])+1e-6 and min(a[3],b[3])>max(a[1],b[1])+1e-6

def clear_segment(a,b,r):
 e=[r[0]-HALF,r[1]-HALF,r[2]+HALF,r[3]+HALF]
 if a[0]==b[0]:return not(e[0]<a[0]<e[2] and min(a[1],b[1])<e[3] and max(a[1],b[1])>e[1])
 if a[1]==b[1]:return not(e[1]<a[1]<e[3] and min(a[0],b[0])<e[2] and max(a[0],b[0])>e[0])
 return False

def path(a,b,r):
 left=math.floor((r[0]-HALF)/8.64)*8.64;right=math.ceil((r[2]+HALF)/8.64)*8.64
 low=math.floor((r[1]-HALF)/.27)*.27;high=math.ceil((r[3]+HALF)/.27)*.27
 paths=[[a,[b[0],a[1]],b],[a,[a[0],b[1]],b],
        [a,[a[0],low],[b[0],low],b],[a,[a[0],high],[b[0],high],b],
        [a,[left,a[1]],[left,b[1]],b],[a,[right,a[1]],[right,b[1]],b]]
 ok=[]
 for ps in paths:
  if all(clear_segment(x,y,r) for x,y in zip(ps,ps[1:])):
   length=sum(abs(x[0]-y[0])+abs(x[1]-y[1]) for x,y in zip(ps,ps[1:]));ok.append((length,ps))
 return min(ok,key=lambda v:v[0])

def estimate(part,t,x,guard):
 macro=[x,86.4,x+2608.48,1010.88];g=[macro[0]-guard,macro[1]-guard,macro[2]+guard,macro[3]+guard]
 lc=t['clock']['landing_contract'];tree=lc['collector_tree'];taps=[r for r in tree['relays'] if r['q'].startswith('rst_n_t')]
 bands=[b['rect_um'] for b in lc['bands'].values() if b.get('rect_um')]
 fixed=[r['xy'] for r in taps if not hit_point(r['xy'],g)];used=[];mapped=[]
 def legal(p):
  r=[p[0]-HALF,p[1]-HALF,p[0]+HALF,p[1]+HALF]
  return all(0<=p[k]-HALF and p[k]+HALF<=t['outline_um'][k] for k in [0,1]) and not overlap(r,g) and not any(overlap(r,b) for b in bands) and not any(abs(p[0]-q[0])<4.32-1e-6 and abs(p[1]-q[1])<4.32-1e-6 for q in used)
 left=math.floor((g[0]-HALF)/8.64)*8.64;right=math.ceil((g[2]+HALF)/8.64)*8.64
 rows=[64.8,70.2] if guard==10.8 else [8.64,17.28]
 high=math.ceil((g[3]+HALF)/8.64)*8.64
 for r in taps:
  old=r['xy'];candidates=[old] if not hit_point(old,g) else []
  for d in range(-5,6):
   candidates += [[old[0]+8.64*d,y] for y in rows]+[[left,old[1]+8.64*d],[right,old[1]+8.64*d],[old[0]+8.64*d,high]]
  good=[p for p in candidates if legal(p)]
  if not good:return dict(verdict='FAIL',reason='no legal tap island site',tap=r['q'],macro=macro,guard=g)
  new=min(good,key=lambda p:abs(p[0]-old[0])+abs(p[1]-old[1]));used.append(new)
  length,ps=path(tree['root'],new,g)
  mapped.append(dict(tap=r['q'],old_xy=old,new_xy=[round(v,3) for v in new],reset_path_um=round(length,3),min_hops405=math.ceil((length-1e-6)/405),min_hops395=math.ceil((length-1e-6)/395),path=ps))
 collisions=[k for k,b in lc['bands'].items() if b.get('rect_um') and overlap(b['rect_um'],g)]
 maxrow=max(mapped,key=lambda r:r['reset_path_um'])
 return dict(part=part['name'],macro_origin_um=[x,86.4],phy_guard_um=guard,guard_rect_um=g,
             preserved_external_interfaces=True,old_reset_depth=tree['depth'],tap_count=len(mapped),
             landing_bands_in_phy_domain=collisions,all_mapped_tap_boxes_clear=True,
             worst_reset_path=maxrow,depth405_lower_bound=max(r['min_hops405'] for r in mapped),
             depth395_geometric_budget=max(r['min_hops395'] for r in mapped),
             reset_depth_headroom395=tree['depth']-max(r['min_hops395'] for r in mapped),
             geometry_verdict='FAIL' if collisions or max(r['min_hops395'] for r in mapped)>tree['depth'] else 'CANDIDATE_GEOMETRICALLY_FEASIBLE',
             build_allowed=False,not_yet_qualified=['shared reset-tree synthesis/site legality','actual clock sink census/NLDM/related-pair timing','IR with explicit narrower guard','die clock+CA after block clock pin relocation'],tap_map=mapped)

out=[]
for guard in [63.64,10.8]:
 for x in [63.64,138.24]:
  for part in P['partitions']:out.append(estimate(part,P['partition_types'][part['type']],x,guard))
json.dump(dict(scope='Estimate only: unchanged outline, macro size, external buses/FT pins; explicit guard variants',variants=out),open(ROOT/'clock_reset_estimate.json','w'),indent=1)
for r in out:print(r['part'],r['macro_origin_um'],r['phy_guard_um'],r.get('geometry_verdict'),r.get('landing_bands_in_phy_domain'),r.get('depth405_lower_bound'),r.get('depth395_geometric_budget'),r.get('old_reset_depth'))
