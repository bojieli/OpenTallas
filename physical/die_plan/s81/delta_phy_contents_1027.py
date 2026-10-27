#!/usr/bin/env python3
"""S81 PHY content outline follows the already adopted physical IO/PHY power lot.
This fixes stale pre-PHY-3.36mm2 content metadata; never expands a power domain.
Every changed type must be unique to that physical instance, or fail closed.
"""
import argparse,copy,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--tools',required=True);p.add_argument('src');p.add_argument('dst');p.add_argument('report');a=p.parse_args();sys.path.insert(0,a.tools)
import schema as S
raw=S.load(a.src);P=S.Plan(raw,a.src);rows=[]
for dom in raw['die'].get('pg',{}).get('domains',[]):
 if not dom['name'].startswith('phy_lk_'):continue
 name=dom['name'].removeprefix('phy_');part=P.parts[name];tn=part['type'];t=P.types[tn]
 insts=[k for k,v in P.parts.items() if v['type']==tn]
 if insts!=[name]:raise ValueError(f'{tn}: PHY content correction needs one physical instance, got{insts}')
 cs=[c for c in t.get('contents',[]) if c.get('module')=='ot_pdie_serdes']
 if len(cs)!=1:raise ValueError(f'{tn}: expected exactly one actual PHY content')
 c=cs[0];box=dom['phy_macro_um'];u=P.to_type(name,box[:2]);v=P.to_type(name,box[2:]);x0,y0,x1,y1=[round(q,4) for q in (min(u[0],v[0]),min(u[1],v[1]),max(u[0],v[0]),max(u[1],v[1]))]
 w,h=t['outline_um']
 if not(0<=x0<x1<=w+1e-4 and 0<=y0<y1<=h+1e-4):raise ValueError(f'{name}: physical PHY lot outside partition')
 if abs((x1-x0)*(y1-y0)/1e6-dom['phy_area_target_mm2'])>0.01:raise ValueError(f'{name}: declared PHY target area mismatch')
 old=copy.deepcopy(c);c['origin_um']=[x0,y0];c['outline_um']=[round(x1-x0,4),round(y1-y0,4)];c['note']='Actual 3.36mm2 PHY assumption lot from adopted die.pg.domains.phy_macro_um; same VDDPHY domain/bump rectangle, no core-strip reassignment. Supersedes stale pre-PHY-lot contents origin/outline.'
 rows.append(dict(part=name,type=tn,orient=part.get('orient','R0'),old=old,new=copy.deepcopy(c),domain_type_um=[x0,y0,x1,y1],domain_die_um=box))
Path(a.dst).write_text(json.dumps(raw,indent=1)+'\n');Path(a.report).write_text(json.dumps(dict(kind='PLAN_DELTA_CANDIDATE',source=a.src,changed_types=len(rows),rows=rows,unchanged=['partition outlines/orientation','PG domains/grids/bumps','signal interfaces/latencies','clock topology']),indent=1)+'\n');print(json.dumps(dict(changed_types=len(rows),verdict='CANDIDATE_NOT_ADOPTED')))
