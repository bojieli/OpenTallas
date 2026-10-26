#!/usr/bin/env python3
"""Apply exact indexed physical moves only to a matching source and old coordinates."""
import argparse,hashlib,json
from pathlib import Path
import schema as S,bit_roads as BR,master_plan as MP
p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan');p.add_argument('proposal');p.add_argument('--out',required=True);p.add_argument('--receipt',required=True);a=p.parse_args();source=Path(a.plan).read_bytes();proposal=json.load(open(a.proposal));assert hashlib.sha256(source).hexdigest()==proposal['source_sha256'],'proposal source SHA mismatch';raw=json.loads(source);changed=set();seen=set()
for move in proposal['moves']:
 tn,slot,stage,bit=move['type'],move['slot'],move['group'],move['bit'];key=(tn,slot,stage,bit);assert key not in seen,'duplicate move';seen.add(key);t=raw['partition_types'][tn];s=next(x for x in t['ft_slots'] if x['name']==slot);assert s['bit_sites_um'][stage][bit]==move['old'],'stale indexed coordinate';assert len(move['new'])==2;s['bit_sites_um'][stage][bit]=move['new'];changed.add((tn,slot))
P=S.Plan(raw,a.plan);paths=MP.census(P);checks=[]
for path in paths:
 for leg in path['legs']:
  if (P.parts[leg['part']]['type'],leg.get('slot')) in changed:
   _,stats=BR.indexed_chains(P,leg['part'],leg['slot'],leg['pin'],leg['pout']);checks.append(dict(part=leg['part'],slot=leg['slot'],**stats))
assert {(P.parts[c['part']]['type'],c['slot']) for c in checks}==changed,'missing exact endpoint census'
out=Path(a.out);assert not out.exists(),'do not overwrite a candidate';out.write_text(json.dumps(raw,indent=1)+'\n');receipt=dict(scope='ONE HBM B1 candidate; indexed moves only; no full routing/PG/capacity qualification',source_sha256=proposal['source_sha256'],output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),moved_cells=len(seen),added_cells=0,added_cycles=0,checks=checks,proposal=str(Path(a.proposal).resolve()))
Path(a.receipt).write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps(receipt))
