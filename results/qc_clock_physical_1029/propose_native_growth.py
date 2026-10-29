#!/usr/bin/env python3
"""Type-uniform parent M7 proxy growth; protected PHY geometry is excluded.
Does not modify signed child views or adopt a plan. Fresh load/G1 checks required.
"""
import argparse,collections,copy,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--census',required=True);p.add_argument('--plan',required=True);p.add_argument('--endpoints',required=True);p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
c=json.load(open(a.census));plan=json.load(open(a.plan));ep=json.load(open(a.endpoints));ep=ep.get('endpoints',ep);types=plan['partition_types'];parts={r['name']:r for r in plan['partitions']};updates=collections.defaultdict(dict);protected=[];unsupported=[]
for r in c['rows']:
 if r['classification']=='PHY_WRAPPER_CLOCK_REVIEW_PRESERVE':protected.append(r);continue
 ty,pin=r['type'],r['pin']
 if types[ty].get('hard'):unsupported.append(r);continue
 needed=r['diagnostic_minimum_symmetric_pin_height_um']
 if needed is None:unsupported.append(r);continue
 # 32nm guard covers the existing small centroid/track projection discrepancy;
 # integer32nm height steps match current768/800nm clock proxy geometry.
 target=round(math.ceil((needed+.032-1e-9)/.032)*.032,6)
 old=types[ty].get('clock',{}).get('tap_pin_heights_um',{}).get(pin,.768)
 updates[ty][pin]=max(updates[ty].get(pin,old),old,target)
proposal=copy.deepcopy(plan)
for ty,pins in updates.items():proposal['partition_types'][ty]['clock'].setdefault('tap_pin_heights_um',{}).update(pins)
# Assert no contents, placement, signed child interface, clock target, latency,
# reset/START contract, pin centre or clock-domain field changes.
stripped=copy.deepcopy(proposal);baseline=copy.deepcopy(plan)
for ty in updates:
 for obj in [stripped,baseline]:obj['partition_types'][ty]['clock'].pop('tap_pin_heights_um',None)
assert stripped==baseline
impacted=[];extra_length=0
for port,r in ep.items():
 ty=parts[r['inst']]['type']
 if r['pin'] not in updates.get(ty,{}):continue
 old=r['rect_um'][3]-r['rect_um'][1];new=updates[ty][r['pin']];extra_length+=max(0,new-old)
 impacted.append(dict(port=port,instance=r['inst'],type=ty,pin=r['pin'],old_height_um=round(old,6),proposed_height_um=new))
summary=dict(status='PROPOSED_NOT_ADOPTED',spacing_um=.32,updated_types=len(updates),updated_type_pin_pairs=sum(map(len,updates.values())),impacted_instance_pins=len(impacted),minimum_new_height_um=min(v for q in updates.values() for v in q.values()),maximum_new_height_um=max(v for q in updates.values() for v in q.values()),added_M7_length_um=round(extra_length,6),added_M7_area_um2=round(.032*extra_length,6),added_cycles=0,centres_moved=0,signed_child_interfaces_edited=[],protected_PHY_pins=len(protected),unsupported=len(unsupported),capacitance_load='NOT RUN; fresh extraction/model required',G1='NOT RUN; fresh native signal/PG/clock geometry required')
json.dump(dict(summary=summary,type_updates=dict(updates),protected_PHY=protected,unsupported=unsupported,impacted_pins=impacted),open(out/'growth_candidate.json','w'),indent=1)
json.dump(proposal,open(out/'plan_growth_candidate.json','w'),indent=2)
print(summary,flush=True)
