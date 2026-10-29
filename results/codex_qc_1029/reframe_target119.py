#!/usr/bin/env python3
"""Build the scalar-complete QC route target around the frozen26 clock tree.

This is a static target, not a physical provider, timing or route qualification.
The clock topology/placement is copied without recalibration or regeneration.
"""
import argparse
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ap=argparse.ArgumentParser(description=__doc__)
for n in ('plan','base','islands','tools','out'):
    ap.add_argument('--'+n,type=Path,required=True)
a=ap.parse_args()
sys.path.insert(0,str(a.tools))
# Pin the candidate contract before legacy helper imports reorder sys.path.
# Production uses one coherent tools package; this experiment intentionally
# combines the reviewed baseline with the pending provider-contract patch.
import landing_contract
import schema as S
import gen_phys as GP
import die_trial as DT
import landing_route as LR
p=S.Plan(S.load(a.plan),a.plan)
network=LR.network(p)
a.out.mkdir(parents=True,exist_ok=False)
shutil.copytree(a.islands/'abstracts',a.out/'abstracts')
shutil.copytree(a.base/'clock',a.out/'clock')
shutil.copytree(a.base/'grt',a.out/'grt')
bits={}
for tn in p.types:
    widths=defaultdict(int)
    for bus,bit,*_ in GP.type_pins(p,tn):
        widths[bus]=max(widths[bus],bit+1)
    bits[tn]=dict(widths)
text,nft=DT.route_netlist(p,bits,landing_infra=True)
(a.out/'grt/route.v').write_text(text)
lefs=sorted(path.name for path in (a.out/'abstracts').glob('*.lef'))
ftf=sorted({t.get('ft_track_frac',.25) for t in p.types.values()})
ca=p.layer_budget.get('cut_avail',{'M8':.6,'M9':.6})
adjust=[(ln,round(1-ftf[0],3)) for ln in ('M4','M5','M6','M7')]+[(ln,round(1-ca.get(ln,.6),3)) for ln in ('M8','M9')]
text=DT.grt_tcl(p,a.out/'grt',.72,lefs,[],adjust)
(a.out/'grt/grt.tcl').write_text(text)
# Same physical26 clock and same die PG reservations: preserve their exact
# previous capacity model until actual FIXED infrastructure replaces it.
shutil.copyfile(a.base/'grt/obs.tcl',a.out/'grt/obs.tcl')
(a.out/'grt/landing_provisional_nets.txt').write_text(''.join(n+'\n' for n in network['provisional']))
kit=json.loads((a.base/'kit.json').read_text())
kit.update(source_clock_plan_sha256=kit['plan_sha256'],
    plan=str(a.plan),plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),
    types=len(p.types),parts=len(p.parts),ports=len(p.ports),
    static_target_only=True,source_clock=str(a.base/'clock'),
    qualification='NO START hardware, physical route or timing qualification; actual source prewire graft required',
    landing_infra=dict(edges=network['edges'],nets=len(network['wires']),provisional=len(network['provisional'])))
(a.out/'kit.json').write_text(json.dumps(kit,indent=1)+'\n')
print('QC119_STATIC_TARGET',len(p.types),len(p.parts),network['edges'],len(network['provisional']),nft)
