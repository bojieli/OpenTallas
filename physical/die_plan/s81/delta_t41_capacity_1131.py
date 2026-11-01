#!/usr/bin/env python3
"""Prepare one reviewed T41 local-capacity prototype; does not adopt a plan.
Usage: delta_t41_capacity_1131.py PLAN OUT REPORT --variant A|B [--sidecar IN OUT]
"""
import argparse,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
sys.path.insert(0,str(ROOT/'physical/die_plan/s81'))
import clock_landing_plan as C
import compact_plan as CP
TN='slice_station__t41';BUS='ft2_i'
RECTS={'A':[79.7,1098.66,183.38,1152.66],'B':[79.7,1098.66,228.828,1179.]}
def prepare(raw,variant):
 new=copy.deepcopy(raw);t=new['partition_types'][TN];lc=t['clock']['landing_contract'];b=lc['bands'][BUS];old=copy.deepcopy(b)
 assert old['rect_um']==[79.7,1098.66,105.62,1209.6]
 r=RECTS[variant];w,h=t['outline_um'];assert 17.28<=r[0]<r[2]<=w-17.28 and 17.28<=r[1]<r[3]<=h-17.28
 used=[q for n,z in lc['bands'].items() if n!=BUS for q in z.get('rects_um') or [z['rect_um']]]
 resets=C.reset_site_rects(lc.get('collector_tree'))
 import landing_place as LP
 resets += [q for _,q,_ in LP._reader_start_groups(t)+LP._writer_start_groups(t)+LP._status_reset_groups(t)]
 resets += list(lc.get('group_rects_um',{}).values())
 C.BAND_RESERVE='padded';obstacles=C._band_obstacles(t,used,resets=resets)
 obstacles+=t['clock'].get('die_islands_um',[])+[q['rect_um'] for q in t['clock'].get('reserved_sites_um',[]) if q.get('kind')=='die_clock_tree']
 assert not any(C._rect_overlap(r,q) for q in obstacles),'actual core/FT/band/reset/clock obstacle'
 pin=C._bus_xy(t,BUS);hop=C._hop(r,*pin);assert hop<=402.84
 area=(r[2]-r[0])*(r[3]-r[1]);assert area>=b['area_reserve_um2']
 b['rect_um']=list(r);b['max_pin_to_band_hop_um']=round(hop,3)
 for source in lc.get('collector_local_sources',[]):
  if source['name']==BUS:source['band']=copy.deepcopy(b)
 parts=[q for q in raw['partitions'] if q['type']==TN]
 for part in parts:
  x,y=part['origin_um']
  for d in raw['die']['pg']['domains']:
   if d.get('io'):
    a,b0,c,d0=d['rect_um'];assert min(x+w,c)<=max(x,a) or min(y+h,d0)<=max(y,b0),'PHY-domain overlap requires actual PHY obstacle model'
 # The complete logical type remains equal after geometry and its stored copy are removed.
 a=copy.deepcopy(raw);z=copy.deepcopy(new)
 for obj in (a,z):
  q=obj['partition_types'][TN]['clock']['landing_contract'];q['bands'][BUS]={k:v for k,v in q['bands'][BUS].items() if k not in ('rect_um','max_pin_to_band_hop_um')}
  for source in q.get('collector_local_sources',[]):
   if source['name']==BUS:source['band']={k:v for k,v in source['band'].items() if k not in ('rect_um','max_pin_to_band_hop_um')}
 assert a==z
 report=dict(type=TN,bus=BUS,variant=variant,parts=parts,old_rect_um=old['rect_um'],rect_um=r,area_um2=round(area,3),reserve_um2=old['area_reserve_um2'],reserve_ratio=round(area/old['area_reserve_um2'],3),pin_um=pin,max_pin_hop_um=round(hop,3),core_ft_band_reset_clock_obstacle_hits=0,logical_changes=0,clock_reset_sites_changed=0,rtl_cycles_added=0,placement_mode='existing ring_place=ff, normal pinslot and automatic spread unchanged',minimum_N_face_to_band_um=round(h-r[3],3),status='GEOMETRY PROTOTYPE: actual mapped placement/GRT/timing unmeasured')
 return new,report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('out');p.add_argument('report');p.add_argument('--variant',required=True,choices=RECTS);p.add_argument('--sidecar',nargs=2);a=p.parse_args()
 raw=json.load(open(a.plan));new,report=prepare(raw,a.variant);Path(a.out).write_text(CP.dumps(new));Path(a.report).write_text(json.dumps(report,indent=1)+'\n')
 if a.sidecar:
  side=json.load(open(a.sidecar[0]));info=side['collector']['types'][TN];band=new['partition_types'][TN]['clock']['landing_contract']['bands'][BUS];info['bands'][BUS]=copy.deepcopy(band)
  for source in info.get('local_sources',[]):
   if source['name']==BUS:source['band']=copy.deepcopy(band)
  Path(a.sidecar[1]).write_text(json.dumps(side,separators=(',',':'))+'\n')
 print(json.dumps(report))
