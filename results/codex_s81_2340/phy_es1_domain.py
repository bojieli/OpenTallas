# WITHDRAWN ANALYSIS: assumed stale phy_macro_um metadata was authoritative.
# DO NOT APPLY. Actual type.contents u_phy proves existing PG domain is correct.
#!/usr/bin/env python3
"""Repair ES1 PHY domain from its existing macro+guard contract; no power/grid/bump assumption changes."""
import json,sys,copy
from pathlib import Path
sys.path.insert(0,'tools/die_plan');import schema as S,die_trial as D
raw=json.load(open(sys.argv[1]));p=S.Plan(raw);d=next(d for d in raw['die']['pg']['domains'] if d['name']=='phy_lk_ES1')
old=d['rect_um'][:];r=p.rect('lk_ES1');m=d['phy_macro_um'];guard=63.64
new=[max(r[0],m[0]-guard),max(r[1],m[1]-guard),min(r[2],m[2]+guard),min(r[3],m[3]+guard)]
assert all(new[i]<=m[i] for i in (0,1)) and all(new[i]>=m[i] for i in (2,3))
for st in d['core_strip_um']:
 assert min(st[2],new[2])<=max(st[0],new[0])+1e-6 or min(st[3],new[3])<=max(st[1],new[1])+1e-6
before=copy.deepcopy(d);d['rect_um']=new;d['note']+='; CODEX ES1 domain repair: regenerate macro+63.64um guard in actual partition frame; prior y placement covered digital strip and missed the true PHY macro. Grid width/pitch/nets, macro, bumps and power unchanged; IR rerun required before signal routing.'
json.dump(raw,open(sys.argv[2],'w'),indent=1)
rec=dict(part='lk_ES1',partition_rect=r,macro=m,guard_um=guard,before=before,after=d,clock_source=sys.argv[3])
t=json.load(open(sys.argv[3]));bp=S.Plan(json.load(open(sys.argv[1])));bs=D.SiteMap(bp);ns=D.SiteMap(S.Plan(raw))
rec['newly_illegal_clock_sites']=[dict(cell=c,xy=xy) for c,xy in t['sites'].items() if bs.legal(xy) and not ns.legal(xy)]
json.dump(rec,open(sys.argv[4],'w'),indent=2);print(json.dumps(dict(old=old,new=new,newly_illegal_clock_sites=len(rec['newly_illegal_clock_sites']))))
