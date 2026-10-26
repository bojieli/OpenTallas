#!/usr/bin/env python3
"""Report source/capture relay needs against actual destination pad reservoirs; never insert stages."""
import argparse,json,csv
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--physical',type=Path,required=True);p.add_argument('--latency',type=Path,required=True);p.add_argument('--out',type=Path,required=True);q=p.parse_args();q.out.mkdir(parents=True,exist_ok=False)
 raw=json.loads(q.plan.read_text());parts={x['name']:x['type'] for x in raw['partitions']};reports={x['type']:x for x in json.loads((q.physical/'summary.json').read_text())};routes={t:{b['bus']:b for b in r['interface_routes']} for t,r in reports.items()};types=[]
 for t,r in reports.items():
  for b in r['interface_routes']:
   if 'error' in b:continue
   types.append(dict(type=t,bus=b['bus'],direction=b['direction'],minimum=b['minimum_stations_lower_bound'],old_planned=b['declared_stations'],new_minus_old=b['minimum_stations_lower_bound']-b['declared_stations'],actual_destination_depth=b['actual_input_pad_depth'],route_um=round(b['centroid_route_um'],3),station_targets_um=b.get('minimum_station_targets_um',[]))))
 lanes=[]
 for b in json.loads(q.latency.read_text())['buses']:
  st,dt=parts.get(b['src']),parts.get(b['dst']);sr=routes.get(st,{}).get(b['bus_out']);dr=routes.get(dt,{}).get(b['bus_in'])
  if not sr and not dr:continue
  sm=sr.get('minimum_stations_lower_bound') if sr else None;dm=dr.get('minimum_stations_lower_bound') if dr else None;reservoir=dr.get('actual_input_pad_depth') if dr else None
  complete=sm is not None and dm is not None and reservoir is not None
  lanes.append(dict(lane=b['lane'],src=b['src'],dst=b['dst'],src_type=st,dst_type=dt,bus_out=b['bus_out'],bus_in=b['bus_in'],source_minimum=sm,capture_minimum=dm,actual_destination_reservoir=reservoir,old_bound_stages=b['bound_stages'],old_plan_cycles=b['plan_cycles'],source_retime_from_destination=min(sm,reservoir) if sm is not None and reservoir is not None else None,additional_total_stages_lower_bound=max(0,sm+dm-reservoir) if complete else None,status='PHYSICAL_LOWER_BOUND_ONLY_FRESH_SCHEDULE_REQUIRED' if complete else 'INCOMPLETE_NON_CB_ENDPOINT'))
 result=dict(scope='centroid lower bounds only; existing destination delay may be retimed coherently payload+epoch; no RTL or plan mutation',types=types,lanes=lanes)
 (q.out/'ledger.json').write_text(json.dumps(result,indent=1)+'\n')
 for name,rows in [('types',types),('lanes',lanes)]:
  with (q.out/(name+'.csv')).open('w') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print(json.dumps(dict(types=len(reports),buses=len(types),lanes=len(lanes),complete=sum(x['status'].startswith('PHYSICAL') for x in lanes),positive_extra_lanes=sum((x['additional_total_stages_lower_bound'] or 0)>0 for x in lanes))))
if __name__=='__main__':main()
