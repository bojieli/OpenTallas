#!/usr/bin/env python3
"""Fleet-only geometry/model probe. Does not emit RTL, kit, or a bindable view.
Uses actual CB16 macro inventory, 43.2-grid origins and >=20um channels.
Compares narrow bank-split hard landing halves; records any infeasible placement.
"""
import argparse,json,math,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
GRID=43.2; GAP=20.0

def clash(a,b):
 return not(a[0]+a[2]+GAP<=b[0]+1e-7 or b[0]+b[2]+GAP<=a[0]+1e-7 or a[1]+a[3]+GAP<=b[1]+1e-7 or b[1]+b[3]+GAP<=a[1]+1e-7)
def dist(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
 c=json.loads((ROOT/'results/arch/qwen_cluster_1017/cluster_contract_dv.json').read_text())
 sites=json.loads((ROOT/'results/arch/qwen_cluster_1017/relay_sites_dv.json').read_text())['sites']
 oldx=sorted(set(t['at'][0] for t in c['tiles']));oldw=c['outline_um']['w'];H=c['outline_um']['h']
 rows=[]
 # Step=691.2 is the minimum grid pitch leaving two64.8-wide children plus20um channels.
 for step,height in [(st,h) for h in [129.6,103.68] for st in [691.2,777.6,864.,950.4,1036.8,1123.2]]:
  cols=[129.6+i*step for i in range(4)];W=math.ceil((cols[-1]+457.92+129.6)/GRID-1e-8)*GRID
  xs=[cols[i]+(math.ceil((457.92+GAP)/GRID)*GRID)+64.8+10.8 for i in range(3)]
  xb=[0]+xs+[W];yb=[0]+c['region_seams']['y']+[H]
  # Piecewise affine x-map preserves each A0 width; expands corridors only.
  knots=[(0.,0.),(oldw,W)]
  for ox,nx in zip(oldx,cols):knots.extend([(ox,nx),(ox+457.92,nx+457.92)])
  knots.sort()
  def mx(x):
   for (oa,na),(ob,nb) in zip(knots,knots[1:]):
    if oa-1e-5<=x<=ob+1e-5:return na+(x-oa)*(nb-na)/(ob-oa)
   raise ValueError(x)
  def mp(p):return [mx(p[0]),p[1]]
  def bounds(q):return [xb[int(q[1])],yb[int(q[3])],xb[int(q[1])+1],yb[int(q[3])+1]]
  obs=[(cols[int(t['inst'][4])],t['at'][1],457.92,1166.4) for t in c['tiles']]
  jobs=[]
  for s in sites:
   if s.get('landing'):
    # Two257/258b siblings per half, physically independent hard child clocks.
    for part in range(2):jobs.append(dict(inst=s['inst']+f'_p{part}',region=s['region'],w=64.8,h=height,target=mp(s['at']),kind='landing_'+s['half'],logical=s['inst'],bits=math.ceil(c['landings']['list'][0]['bits']/2)))
   elif s['bits']>1:
    master=s.get('master') or 'qfd_c_stn514' # re-alignment pad is one514b stage, not a long delay line
    w,h=(56.16,86.4) if 'xstn' in master else (51.84,51.84)
    jobs.append(dict(inst=s['inst'],region=s['region'],w=w,h=h,target=mp(s['at']),kind='station' if s.get('master') else 'hardened_pad',logical=s['inst'],bits=s['bits']))
  placed=[];failed=[]
  # Place big children first; then station tiles. Never put cells over an A0.
  for j in sorted(jobs,key=lambda j:(-j['w']*j['h'],j['region'],j['inst'])):
   lo,bot,hi,top=bounds(j['region']);cand=[]
   for ix in range(math.ceil(lo/GRID),math.floor((hi-j['w'])/GRID)+1):
    for iy in range(math.ceil(bot/GRID),math.floor((top-j['h'])/GRID)+1):
     rect=(ix*GRID,iy*GRID,j['w'],j['h'])
     if rect[0]<GAP or rect[1]<GAP or rect[0]+rect[2]>W-GAP or rect[1]+rect[3]>H-GAP:continue
     if any(clash(rect,o)for o in obs):continue
     cand.append((dist([rect[0]+rect[2]/2,rect[1]+rect[3]/2],j['target']),rect))
   cand.sort()
   for d,rect in cand:
    if any(clash(rect,(p['at'][0],p['at'][1],p['w'],p['h'])) for p in placed):continue
    j=dict(j,at=[round(rect[0],3),round(rect[1],3)],target_displacement_um=round(d,3));placed.append(j);break
   else:failed.append(j)
  by=collections.defaultdict(list)
  for p in placed:by[p['logical']].append(p)
  def centers(n):return [[p['at'][0]+p['w']/2,p['at'][1]+p['h']/2]for p in by.get(n,[])]
  hops=[]
  for land in c['landings']['list']:
   name=land['name'];src=centers('u_fab.u_'+land['crossing'].split(' ')[0]);missing_source=not src
   dst=centers('u_fab.u_'+name)
   wr=centers(land['ring']['inst']);rd=centers(land['read']['inst'])
   def md(aa,bb):return round(max((dist(x,y)for x in aa for y in bb),default=0),3)
   capture=md(src,wr);emit=md(rd,dst);cross=md(wr,rd)
   hops.append(dict(name=name,source_to_ring_um=capture,ring_to_read_um=cross,read_to_sink_um=emit,
     unresolved_endpoints=bool(missing_source or not dst or not wr or not rd),added_capture_relay_edges=max(0,math.ceil(capture/315)-1) if src and wr else None,added_output_relay_edges=max(0,math.ceil(emit/315)-1) if rd and dst else None,
     crossing_more_than_2x405_um=cross>810))
  reset=[s for s in sites if s['bits']==1]
  row=dict(outline_um=dict(w=round(W,3),h=H),area_mm2=round(W*H/1e6,6),area_ratio=round(W/oldw,6),aspect=round(H/W,5),tile_origins_x_um=cols,
    inner_corridor_um=round(step-457.92,3),clock_region_seams_x_um=xs,landing_child=dict(w=64.8,h=height,bank_faces='W/E each516b, a/q N/S258b',peak_pins_per_um=round(258/63.72,4)),
    hard_candidates=len(jobs),placed=len(placed),unplaced=len(failed),placement=placed,failed=failed,hop_repricing=hops,
    reset_hardening_blocker=dict(count=len(reset),existing_depth_edges=19,target_hop_um=315,required='pack regional reset relay children, two face stages; no soft root sinks at parent gate'),
    macro_channels_um=GAP,lattice_um=GRID,release_ready=False)
  rows.append(row)
 out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(dict(schema='opentallas.cb16.safe_parent_plan.v1',source='ac8e4c483',diagnostic_only=True,candidates=rows),indent=1)+'\n')
 for r in rows:print('PARENT_PLAN',r['outline_um'],r['area_mm2'],'mm2',r['placed'],'placed',r['unplaced'],'UNPLACED','capture relays',sum(h['added_capture_relay_edges'] or 0 for h in r['hop_repricing']),'output relays',sum(h['added_output_relay_edges'] or 0 for h in r['hop_repricing']))
if __name__=='__main__':main()
