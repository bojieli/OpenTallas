#!/usr/bin/env python3
"""Necessary transport depth from actual per-plane LEF endpoint incidence."""
import argparse,gzip,hashlib,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('graph',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
rows=json.loads(gzip.decompress(a.graph.read_bytes()))['rows'];groups={}
for r in rows:groups.setdefault(r['target'].split('.d[')[0],[]).append(r['su1024_output_xy'])
assert len(rows)==24576 and len(groups)==96
assert all(len(v)==256 for v in groups.values())
out=[]
for n,ps in sorted(groups.items()):
 diameter=max(max(x+y for x,y in ps)-min(x+y for x,y in ps),max(x-y for x,y in ps)-min(x-y for x,y in ps));radius=diameter/2
 out.append({'target':n,'source_pins':len(ps),'source_L1_diameter_um':diameter,'minimum_worst_source_to_target_L1_um':radius,'minimum_500um_hops':math.ceil(radius/500),'minimum_relay_stages':math.ceil(radius/500)-1,'RO1_feasible_even_without_obstacles':radius<=1000})
report={'scope':'Necessary geometric lower bound from actual transformed LEF SU1024 output pins and per-plane RTL bit mapping. Target home unconstrained. Each path with RO relay stages has at most RO+1 registered hops. Obstacles, relay tile size and pair-specific reach can only increase needed stages. No physical qualification.','graph_sha256':hashlib.sha256(a.graph.read_bytes()).hexdigest(),'planes':out}
a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'planes':len(out),'minimum_worst_pin_distance_um':min(o['minimum_worst_source_to_target_L1_um'] for o in out),'minimum_RO':max(o['minimum_relay_stages'] for o in out),'all_RO1_infeasible':all(not o['RO1_feasible_even_without_obstacles'] for o in out)}))
