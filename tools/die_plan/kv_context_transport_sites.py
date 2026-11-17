"""Site candidate banks for the ten externally located C4 port groups; local HOST/service/slot endpoints remain open."""
import json,math,argparse
from pathlib import Path

def hit(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
def run(geometry,placement,paths,out,macro_ff_sites):
 g=json.loads(geometry.read_text());p=json.loads(placement.read_text());pr=json.loads(paths.read_text());blocked=[]
 for c in g['cores']:
  x,y=c['origin_um'];w,h=c['outline_um'];blocked.append((x-10.8,y-10.8,x+w+10.8,y+h+10.8))
 blocked += [tuple(x['rect_um']) for x in g['reserved']]
 for f in g['ft']:
  for st in f.get('bit_sites_um',[]):
   xs=[x[0] for x in st];ys=[x[1] for x in st];blocked.append((min(xs)-2.16,min(ys)-2.16,max(xs)+2.16,max(ys)+2.16))
 blocked += [tuple(m['halo_rect_um']) for m in p['macros']]
 blocked.append(tuple(p['logic_region_um']));blocked += [tuple(r['rect_um']) for r in json.loads(macro_ff_sites.read_text())['rows']];base_n=len(blocked);result=[]
 for r in sorted(pr['rows'],key=lambda r:-r['bits']):
  if r['status']!='PATH_FOUND_GEOMETRY_ONLY':result.append(dict(bus=r['bus'],status='NO_PATH'));continue
  inp=r['bus'].startswith('i_');n=4 if inp else 2;data=r['bits']-1;poly=r['worst']['polyline_um'];length=r['worst']['length_um'];area=(max(1,data)*.2916+.37908)/.55
  bw=12.96 if data>32 else 6.48;bh=math.ceil(area/bw/.27)*.27
  # Candidate centres on the proved path plus nearby offsets. Track exact along-path distance and lateral stub price.
  cum=0;nodes=[]
  for a,b in zip(poly,poly[1:]):
   seg=abs(a[0]-b[0])+abs(a[1]-b[1]);nodes.append((cum,a));cum+=seg
  nodes.append((cum,poly[-1]));assert abs(cum-length)<1e-5
  layers=[]
  for s in range(1,n+1):
   ideal=length*s/(n+1);options=[]
   for along,(x,y) in nodes:
    if abs(along-ideal)>100:continue
    for dx in [-21.6,-10.8,0,10.8,21.6]:
     for dy in [-21.6,-10.8,0,10.8,21.6]:
      cx=round((x+dx)/2.16)*2.16;cy=round((y+dy)/.27)*.27;rect=(cx-bw/2,cy-bh/2,cx+bw/2,cy+bh/2)
      if rect[0]<2.16 or rect[1]<2.16 or rect[2]>g['outline_um'][0]-2.16 or rect[3]>g['outline_um'][1]-2.16:continue
      if any(hit(rect,b) for b in blocked):continue
      spur=abs(cx-x)+abs(cy-y);options.append(dict(along=along,xy=[cx,cy],rect=list(rect),spur=spur,cost=abs(along-ideal)+spur))
   # Keep every geometrically different candidate; the DP uses all options, no retry cap.
   opts={tuple(o['rect']):o for o in options};layers.append(list(opts.values()))
  states=[dict(node=None,along=0,spur=0,cost=0,path=[])]
  for options in layers:
   nxt=[]
   for o in options:
    parents=[st for st in states if o['along']>=st['along'] and o['along']-st['along']+o['spur']+st['spur']<=405 and all(not hit(o['rect'],z['rect']) for z in st['path'])]
    if not parents:continue
    st=min(parents,key=lambda st:st['cost']);nxt.append(dict(node=o,along=o['along'],spur=o['spur'],cost=st['cost']+o['cost'],path=st['path']+[o]))
   states=nxt
  feasible=[s for s in states if length-s['along']+s['spur']<=405]
  if not feasible:result.append(dict(bus=r['bus'],status='NO_COMPLETE_BANK_SITING',data_bits=data,stages=n,bank_wh_um=[bw,bh],candidate_counts=[len(o) for o in layers]));continue
  st=min(feasible,key=lambda st:st['cost']);banks=st['path'];blocked += [tuple(o['rect']) for o in banks]
  hops=[];prev=0;spur=0
  for b in banks:hops.append(b['along']-prev+spur+b['spur']);prev=b['along'];spur=b['spur']
  hops.append(length-prev+spur)
  result.append(dict(bus=r['bus'],status='SITE_CANDIDATE',data_bits=data,stages=n,banks=banks,conservative_polyline_spur_hops_um=hops,max_hop_um=max(hops)))
 res=dict(schema='opentallas.qwen-kv-context-transport-sites.v1',state='EXTERNAL_PORT_SUBSET_ONLY_NOT_BUILD_READY',placement_obstacles=base_n,rows=result,
 unplaced_interfaces=['HOST i_head_record unique98bits from actual hard-core origin','mixed-source d2d__svc139usedbits after current internal delay chains','d2d__emb_tx_slot after current5edge delay'],
 joint_track_capacity_qualified=False,clock_qualified=False,reset_qualified=False,physical_registered_RTL=False,
 note='Endpoint two-extremes paths are geometric representatives; all-bit stage FF assignment and valid/epoch alignment must be emitted and checked before build. Sources and producer endpoints are reverse-direction for output buses; pipeline banks share the same geometric path.')
 out.write_text(json.dumps(res,indent=1)+'\n');print([(r['bus'],r['status'],r.get('max_hop_um')) for r in result])
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--geometry',type=Path,required=True);a.add_argument('--placement',type=Path,required=True);a.add_argument('--paths',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--macro-ff-sites',type=Path,required=True);p=a.parse_args();run(p.geometry,p.placement,p.paths,p.out,p.macro_ff_sites)
