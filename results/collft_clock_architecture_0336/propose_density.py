import json,sys,types
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan');import taps
B=Path(__file__).parent;allrows=json.loads((B/'clock_sinks.json').read_text());rows=[a for a in allrows if a['root']=='clk'];pts=[(*a['xy'],1.)for a in rows]
# Results-local application of canonical density algorithm to exact current RCLK sinks only.
# Forwarded FCLK owners are excluded, never reassigned or counted twice.
taps.sink_sites=lambda P,tn,control=False:pts
out={}
for target in (1500,1200):
 P=types.SimpleNamespace(types={'collft':dict(outline_um=[786.24,993.6],clock=dict(tap_mode='density',tap_um=[388.8,501.12],tap_max_sinks=1500,tap_target_sinks=target,tap_radius_um=200,tap_min_sinks=75,tap_refine_iters=6))})
 ts=taps.density_taps(P,'collft',control=False)
 load,far,asg=taps.assign(ts,pts,1500,200,max_distance_um=200)
 groups={}
 for a,j in zip(rows,asg):groups.setdefault(a['name'].split('/')[0],set()).add(ts[j][0])
 split={k:sorted(v)for k,v in groups.items()if len(v)>1}
 out[str(target)]=dict(taps=ts,total_sinks=sum(load),max_sinks=max(load),max_distance=max(far),split_functional_prefixes=split,source_scope='model proposal only; unsnapped, no fixed-body/PG/via/tree/electrical/timing qualification',assignments=[dict(instance=a['name'],tap=ts[j][0])for a,j in zip(rows,asg)])
 print(target,len(ts),'load',load,'maxdistance',max(far),'splitgroups',len(split))
(B/'density_candidates.json').write_text(json.dumps(out,indent=1))
