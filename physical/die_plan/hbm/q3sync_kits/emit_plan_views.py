#!/usr/bin/env python3
"""Publish only the five qualified q3 source views from an explicit plan batch."""
import argparse, hashlib, json, re
from pathlib import Path
from build_kit import TOPS, REPO
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--out',required=True);a=p.parse_args()
plan=Path(a.plan).resolve();root=plan.parent;j=json.loads(plan.read_text())
canonical=json.loads((REPO/'physical/die_plan/hbm/cores/harden/canonical_ports_split.json').read_text())['types']
aliases={v:k for k,v in TOPS.items()};aliases.update({'ot_hfd_coll_q2_hard_v8g__reduce':'reduce','ot_hfd_coll_q2_hard_v8g__ring_ag':'ring_ag'})
views={};seen=set()
for typ,t in j['partition_types'].items():
 for c in t.get('hard_cores',[]):
  core=aliases.get(c['module'])
  if core is None:continue
  pins=(root/c['pins_file']).resolve();raw=pins.read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['module']+'@'+sha[:12]
  names=[p['name']for p in json.loads(raw)]
  # This publisher serves the explicit one-clock batch only.
  assert names.count('clk')==1 and not any(re.match(r'(?:clk_|.*_clk|link\d+_ck)(?:\[|$)',n)for n in names if n!='clk'),(core,'oldclockpins')
  if key not in views:
   v=dict(view=key,module=c['module'],outline_um=c['outline_um'],pins_file=c['pins_file'],pins_sha256=sha,recipe_keys=[],instances=[],placed=0)
   if c['module']!=TOPS[core]:
    matches=[k for k,x in canonical.items() if x.get('top')==TOPS[core] and any(re.sub(r'__[\d.]+x[\d.]+$','',tid)==c['module']for tid in x['type_ids'])]
    assert len(matches)==1,(core,'canonical metadata');v['canonical_type']=matches[0]
   views[key]=v
  v=views[key];v['instances'].append(typ+'/'+c['inst']);v['placed']+=sum(p['type']==typ for p in j['partitions']);seen.add(core)
assert seen==set(TOPS) and len(views)==5,(seen,len(views))
out=Path(a.out);out.write_text(json.dumps(dict(plan=str(plan),view_list=list(views.values())),indent=1)+'\n')
print(json.dumps(dict(status='PASS_SOURCE_VIEWS',views=len(views),hard_core_slots=sum(len(v['instances'])for v in views.values()),path=str(out))))
