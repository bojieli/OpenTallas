#!/usr/bin/env python3
import json,statistics,subprocess
from pathlib import Path
out={}
for C in ('TT','FF'):
    vals={}
    for line in Path('/work/parent_cluster_'+C+'.txt').read_text().splitlines():
        name,t=line.split();vals.setdefault(name,[]).append(float(t))
    for n,v in vals.items():out.setdefault(n,{})[C]=dict(mean=statistics.mean(v),min=min(v),max=max(v),n=len(v))
Path('/work/parent_cluster_ins.json').write_text(json.dumps(out,indent=1)+'\n')
geom_path=Path('/work/parent_clusters.json')
geom=json.loads(geom_path.read_text()); sites={}
for line in Path('/work/parent_cluster_sites.txt').read_text().splitlines():
    name,x,y=line.split()
    if name in sites:raise ValueError('duplicate built cluster root '+name)
    sites[name]=[float(x),float(y)]
if set(sites)!={c['name'] for c in geom['clusters']}:raise ValueError('missing/extra built cluster root')
for c in geom['clusters']:c['root']=sites[c['name']]
geom_path.write_text(json.dumps(geom,indent=1)+'\n')
a=json.loads(Path('/work/parent_trunk_options.json').read_text())
subprocess.run(['python3','-I','/work/parent_trunk_dme.py','plan','/work/parent_clusters.json','/work/parent_cluster_ins.json','/work/parent_trunk_plan.json','--entry',','.join(map(str,a['entry_um'])),'--ungated-split','--topology','bipart','--icg-note','RTL ICG enable preserved; gated and ungated clusters split before CTS']+a.get('plan_args',[]),check=True)
subprocess.run(['python3','-I','/work/parent_trunk_dme.py','tcl','/work/parent_trunk_plan.json','/work/parent_trunk_plan.tcl'],check=True)
# Publish the pre-build reference for the typed macro IO contract. This file is
# a plan output only; the old 250/202.5 kit frame is not silently overwritten.
plan=json.loads(Path('/work/parent_trunk_plan.json').read_text());summ=plan['summary']
ref={c.lower():(summ['plan_'+c.lower()]['min']+summ['plan_'+c.lower()]['max'])/2 for c in ('TT','FF')}
ref.update(kind='plan_declared',basis='Pre-build DME total internal clock latency midpoint; exact native local CTS cluster insertion and actual SIGNED hard-child latency inputs',source='results/codex_qc_a0_2340/nl_parent_clock_plan.json')
Path('/work/parent_planned_io_reference.json').write_text(json.dumps(dict(kind='hard_core_latency',io_reference_ps=ref,status='PLANNED_NOT_ADOPTED'),indent=1)+'\n')
