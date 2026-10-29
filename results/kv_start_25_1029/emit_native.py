#!/usr/bin/env python3
import json,sys
from pathlib import Path
r=Path(sys.argv[1]);sys.path.insert(0,str(r/'source'))
import start_stage_emit as E
import schema as S
import die_trial as D
b=json.load(open(r/'native_bind.json'));meta=json.load(open(r/'inputs/proof/tap_arrivals_TT.json'))
p=S.Plan(S.load(r/'inputs/event/plan_sites_astk.json'))
ct=Path('/srv/opentallas-scratch2/claude/die-kv-21-1028/kit_c/clock')
doc,sv,v,t=E.emit(b,meta,(ct/'ctree.v').read_text(),(ct/'ctree.tcl').read_text(),D.SiteMap(p),(p.W,p.H),path_encoding='base36',reset_wave=True)
o=r/'emitted';o.mkdir();(o/'start_stages.json').write_text(json.dumps(doc,indent=1));(o/'start_stages.sv').write_text(sv);(o/'ctree.v').write_text(v);(o/'ctree.tcl').write_text(t)
print(json.dumps(doc['counts']),flush=True)
