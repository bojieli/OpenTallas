#!/usr/bin/env python3
"""Analysis-only PG windows: original IO bump sites, explicit PHY footprints, separate supplies.
No shared-generator default changes and no source-plan adoption.
"""
import json,sys,copy
from pathlib import Path
R=Path(sys.argv[1]);T=R/'tools/die_plan';sys.path.insert(0,str(T))
import schema as S,die_trial as D,infra_pg as I,infra_pg_domains as IPD
P=S.Plan(json.load(open(R/'event/pd/die_plan.json')),R/'event/pd/die_plan.json');meta=json.load(open(R/'phy_model/pg_domains_candidate.json'));dom={x['io'][0]:x for x in meta['domains']}
original_io=D.io_windows(P,R/'event/pd');model_io=copy.deepcopy(original_io)
for q in model_io:
 if q['name'] in dom:q['rect_um']=dom[q['name']]['rect_um']
model_raw=copy.deepcopy(P.raw);model_raw['die']['io']=model_io;Q=S.Plan(model_raw,R/'event/pd/die_plan.json');load=I.load_model
# The existing domain vehicle uses load_model for footprints/density and D.io_windows(P) for the unchanged bump field.
I.load_model=lambda unused,plandir,*a,**k:load(Q,plandir,*a,**k)
pg=dict(grid=P.die['pg']['grid'],phy_w_per_macro=4.37,core_w_mm2=.15,bump_pitch_um=150)
for part,box in [('sys_SW',[0,26006.4,2160,27043.2]),('sys_SE',[8916.48,26006.4,11076.48,27043.2])]:
 out=R/'phy_pg_r3'/part;win=dict(window=part,window_um=box);m=IPD.make(P,R/'event/pd',pg,win,out,8.64)
 m['assumptions']=dict(core_glue_w_mm2=.15,phy_w=4.37,footprint='half existing x12 area rounded above, explicit model, not vendorGDS',contacts='M7 boundary contact surrogate with original micro-bump sites; true leaf/kit alias remains pending');(out/'domains.json').write_text(json.dumps(m,indent=1)+'\n')
 print(part,'blocks',m['load_blocks'],'watts',m['power_w'],'bumps',len(m['bumps']),flush=True)
print('PG_WINDOWS_READY')
