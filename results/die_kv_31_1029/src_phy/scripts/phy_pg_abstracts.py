#!/usr/bin/env python3
"""DIE-KV-31-SRC: give the KV source abstracts the plan's truthful VDDPHY interface.

Root cause of VDDPHY 0 ITerms: die.pg.domains phy_sys_c_ucie (VDDPHY/VSS, rect 5140.8,26058.24..5935.68,26853.12)
is drawn by pdngen, but no source master has a VDDPHY MTerm. The only macro over the domain is sys_c
(kv3_sys_c_part), whose abstract (die_trial.abstract_lef via rebuild_abstracts.py) exports one full-body CORE VDD
M7 pin straight through the PHY window, so `add_global_connection -pin_pattern ^VDDPHY$` matches nothing
(pg_regions.resolve_loads rejects exactly this: "CORE VDD pin metal enters ... PHY region").
Fix (source step, no ODB edit): apply the repo's existing planned PHY PG split pg_regions.prototype_lef (the same
call gen.py mockview --planned-phy-pg uses) to every abstract: CORE VDD M7 cut at the domain (+0.096 um gap),
VDDPHY M7 = the strap pieces inside the domain, VSS M7 unchanged. Types without a mapped die_io PHY window are
returned unchanged by prototype_lef. Signal pins and OBS are asserted byte-identical.
MODELED PHY interface (HBM PHY ruling (a) default): no licensed-IP / analog GDS claim.
"""
import argparse,json,re,sys,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--tools',required=True);p.add_argument('--abstracts',required=True);p.add_argument('--out',required=True);a=p.parse_args()
sys.path.insert(0,a.tools);import schema as S,die_trial as D,pg_regions as G
raw=S.load(a.plan);P=S.Plan(raw,Path(a.plan));io=raw['die']['io'];mods=D.standin_module_names(P)
out=Path(a.out);out.mkdir(parents=True,exist_ok=True);rec=[]
obs=re.compile(r'^  OBS\n.*?^  END\n',re.M|re.S)
def strip_pg(s):
 for net in ['VDD','VSS','VDDPHY']:s=re.sub(r'(?ms)^\s*PIN '+net+r'\s*$.*?^\s*END '+net+r'\s*$\n?','',s)
 return s
for tn in sorted(P.types):
 mod=mods[tn];src=Path(a.abstracts)/(mod+'.lef');old=src.read_text();new=G.prototype_lef(P,tn,old,io)
 if new!=old:
  body=new.split('\n',1)[1]  # drop the PLANNED comment line for the comparison
  assert obs.search(body).group()==obs.search(old).group(),tn+': OBS changed'
  assert strip_pg(body)==strip_pg(old),tn+': signal text changed'
  pins=G.lef_pg_pins(new);po=G.lef_pg_pins(old)
  rec.append(dict(type=tn,module=mod,changed=True,pg_rects_before={k:len(v['rects']) for k,v in po.items()},pg_rects_after={k:len(v['rects']) for k,v in pins.items()},layers_after={k:sorted({l for l,_ in v['rects']}) for k,v in pins.items()}))
 (out/(mod+'.lef')).write_text(new)
changed=[r for r in rec if r['changed']]
m=dict(schema='opentallas.kv_phy_pg_abstracts.v1',plan=a.plan,plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),domains=raw['die']['pg']['domains'],types=len(P.types),changed=changed,scope='PLANNED/MODELED PHY PG interface only (pg_regions.prototype_lef); no signed view, no licensed-IP claim')
(out/'phy_pg_manifest.json').write_text(json.dumps(m,indent=1)+'\n');print(json.dumps(dict(types=len(P.types),changed=changed)))
if len(changed)!=1 or changed[0]['module']!='kv3_sys_c_part' or 'VDDPHY' not in changed[0]['pg_rects_after']:raise SystemExit('UNEXPECTED: exactly kv3_sys_c_part must gain VDDPHY')
