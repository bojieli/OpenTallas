#!/usr/bin/env python3
"""Read DECLARED parent-plan native START pin metal, never claim ODB evidence."""
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--die-plan',required=True);p.add_argument('--inventory',required=True);p.add_argument('--tools',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.path.insert(0,a.tools);import schema,landing_route
P=schema.Plan(schema.load(a.die_plan),Path(a.die_plan));inv=json.load(open(a.inventory));out={}
for q in inv['outputs']:
 part=q['dst_part'];typ=P.parts[part]['type'];found=[r for r in landing_route.scalar_pins(P,typ) if r['name']=='cland_tstart_in'];assert len(found)==1,(part,found);p=found[0];x,y=p['xy_um'];aa=P.to_die(part,(x-.04,y-.216));bb=P.to_die(part,(x+.04,y+.216));out[q['net']]=dict(part=part,type=typ,pin=p['name'],layer=p['layer'],rect_um=[min(aa[0],bb[0]),min(aa[1],bb[1]),max(aa[0],bb[0]),max(aa[1],bb[1])],geometry_kind='DECLARED_PLAN_NATIVE_PIN',source=a.die_plan,actual_ODB_bound=False)
Path(a.out).write_text(json.dumps(out,separators=(',',':'))+'\n');print('DECLARED native START pins',len(out),'actualODBbound=FALSE')
