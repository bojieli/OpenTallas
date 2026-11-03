from pathlib import Path
from bisect import bisect_left
from collections import Counter
import json,sys
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv');d=json.load(open(P/'comparison.json'));names={c[6].replace(chr(92),''):(cid,c) for cid,c in D.cells.items()};ordered=sorted(names);seen=set();receipts=[];spec=['# STATIC PREP only. Not a dispatched hook. Source original face hook first.','# Reuses standard macro_reg_guide.tcl then standard release before DPL.','set ::ot_mrg_spec {']
for z in d['guide_groups']:
 prefixes=[s.replace(chr(92),'') for s in z['names']];expanded=set()
 for p in prefixes:
  k=bisect_left(ordered,p)
  while k<len(ordered) and ordered[k].startswith(p):expanded.add(ordered[k]);k+=1
 want=set(prefixes);assert expanded==want,(len(expanded),len(want));assert not seen&want;seen|=want
 statuses=dict(Counter(D.extra['status'].get(names[n][0],'?') for n in want));receipts.append(dict(chunk=z['chunk'],role=z['role'],expected_members=len(want),prefix_expanded=len(expanded),actual_statuses=statuses))
 spec.append('  hroot_c%d_%s {'%(z['chunk'],z['role']))
 for n in sorted(want):
  assert '{' not in n and '}' not in n;spec.append('    {'+n+'}')
 spec.append('  } '+' '.join(str(round(v,6)) for v in z['box']))
spec.append('}')
(P/'guide_spec_PREP.tcl').write_text('\n'.join(spec)+'\n');(P/'guide_membership_receipt.json').write_text(json.dumps(dict(scope='STATIC exact literal-prefix expansion against actual213407-cell dump; no CAD',groups=receipts,total=len(seen),crossgroup_overlap=0),indent=1)+'\n');print(receipts)
