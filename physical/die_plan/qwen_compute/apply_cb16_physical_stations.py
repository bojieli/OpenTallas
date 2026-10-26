#!/usr/bin/env python3
"""Add priced physical source/capture stations before a fresh R8 solve; never remove old stages."""
import argparse,copy,json,collections
from pathlib import Path
from cb16_physical_pads import at, schema

def apply(raw,reports):
 out=copy.deepcopy(raw);changes=[];deltas={};types=out['partition_types']
 for r in reports:
  tn=r['type']
  if tn not in types:continue
  t=types[tn];entries=t.setdefault('internal_stations',[]);by={e['conn'][4:]:e for e in entries if e.get('conn','').startswith('bus:')};buses={b['name']:b for b in t.get('buses',[])}
  for b in r['interface_routes']:
   if 'error' in b:raise ValueError(f"{tn}/{b['bus']}: unresolved physical route {b['error']}")
   name=b['bus'];old=len(by.get(name,{}).get('regs_um',[]));new=max(old,b['minimum_stations_lower_bound']);delta=new-old;deltas[tn,name]=delta
   if not new:continue
   e=by.get(name)
   if e is None:
    leaf=buses[name]['leaf'];e=dict(conn='bus:'+name,bits=buses[name]['width']+1,launch='face flop' if b['direction']=='in' else leaf,capture=leaf if b['direction']=='in' else 'face flop');entries.append(e)
   # Keep longstanding plan coordinate convention: face -> leaf. Signal order is reversed for outputs.
   pts=[]
   for i in range(new):
    x,y=at(b['path_um'],(i+1)/(new+1));x,y=round(x/2.16)*2.16,round(y/2.16)*2.16
    pts.append(list(schema.tap_clear(t,x,y,pts,clear=4.32,strict=True)))
   before=copy.deepcopy(e);e.update(from_um=b['face_um'],to_um=b['leaf_um'],regs_um=pts,note='CB16 actual inward-pin physical route: payload+epoch, priced in lane.fixed_cycles; fresh R8 required, no RTL insertion')
   for obsolete in ('bit_route','bit_sites_um'):e.pop(obsolete,None)
   changes.append(dict(type=tn,bus=name,direction=b['direction'],old_stations=old,new_stations=new,delta=delta,route_um=b['centroid_route_um'],minimum_stations=b['minimum_stations_lower_bound'],signal_order_targets_um=pts if b['direction']=='in' else list(reversed(pts)),placement='SNAPPED_CORE_CLEAR_TARGETS_NOT_DPL',before=before))
 parts={p['name']:p['type'] for p in out['partitions']};ports={p['id']:p for p in out['ports']};lanes=[]
 for lane in out['lanes']:
  # Ports are successive physical segments of one logical lane, not parallel copies.
  endpoints={(p[side]['part'],p[side]['bus']) for pid in lane['ports'] for p in [ports[pid]] for side in ('src','dst')}
  delta=sum(deltas.get((parts.get(part),bus),0) for part,bus in endpoints)
  if delta:
   old=lane.get('fixed_cycles',0);lane['fixed_cycles']=old+delta;lanes.append(dict(lane=lane['id'],old_fixed_cycles=old,new_fixed_cycles=old+delta,delta=delta))
 report=dict(scope='UNADOPTED physical station plan delta; fresh R8/DAG/token and actual P&R gates required',types=len(set(x['type'] for x in changes)),changed_bus_counts=sum(x['delta']>0 for x in changes),repositioned_bus_banks=len(changes),additional_stations_per_type=sum(x['delta'] for x in changes),changed_lanes=len(lanes),lane_delta_histogram=dict(collections.Counter(x['delta'] for x in lanes)),lanes=lanes,buses=changes,preserved_old_stage_counts=True,soft_clock_interface='87 soft drops is mapped max-profile candidate; native hard clocks additional; not adopted',outline_change=False)
 return out,report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--physical',type=Path,required=True);p.add_argument('--out-plan',type=Path,required=True);p.add_argument('--report',type=Path,required=True);q=p.parse_args();raw=json.loads(q.plan.read_text());reports=json.loads(q.physical.read_text());out,r=apply(raw,reports);q.out_plan.parent.mkdir(parents=True,exist_ok=True);q.out_plan.write_text(json.dumps(out,indent=1)+'\n');q.report.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('lanes','buses')}))
if __name__=='__main__':main()
