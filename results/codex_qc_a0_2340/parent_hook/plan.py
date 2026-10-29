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
a=json.loads(Path('/work/parent_trunk_options.json').read_text())
subprocess.run(['python3','-I','/work/parent_trunk_dme.py','plan','/work/parent_clusters.json','/work/parent_cluster_ins.json','/work/parent_trunk_plan.json','--entry',','.join(map(str,a['entry_um'])),'--ungated-split','--topology','bipart','--icg-note','RTL ICG enable preserved; gated and ungated clusters split before CTS']+a.get('plan_args',[]),check=True)
subprocess.run(['python3','-I','/work/parent_trunk_dme.py','tcl','/work/parent_trunk_plan.json','/work/parent_trunk_plan.tcl'],check=True)
