#!/usr/bin/env python3
"""DIE-HBM-61/PLAN d44v scope (d) uniform templates (DIE-HBM-61 ruling 11-03: design count stays 84): every hard-core
instance whose pins_file in PLAN is a per-instance '__sp_<type>_<inst>' variant (DIE-HBM-60 v1 core_faces repins) goes back
to the shared table it had in BASE.  python3 mk_tmpl.py BASE_DIR PLAN_DIR OUT_DIR"""
import json, os, shutil, sys
from pathlib import Path
base, plan, out = map(Path, sys.argv[1:4])
B = json.loads((base / 'die_plan.json').read_text()); P = json.loads((plan / 'die_plan.json').read_text())
rev = []
for tn, t in P['partition_types'].items():
    hb = {h['inst']: h for h in B['partition_types'][tn].get('hard_cores') or []}
    for h in t.get('hard_cores') or []:
        o = hb.get(h['inst'])
        if o and '__sp_' in (h.get('pins_file') or '') and '__sp_' not in (o.get('pins_file') or '') and o['module'] == h['module']:
            rev.append(dict(type=tn, inst=h['inst'], module=h['module'], from_=h['pins_file'], to=o['pins_file']))
            h['pins_file'] = o['pins_file']
            h['note'] = (h.get('note', '') + ' | DIE-HBM-61 d44v templates: per-instance repin reverted to the shared table').strip(' |')
if out.exists():
    shutil.rmtree(out)
shutil.copytree(plan, out, copy_function=os.link, symlinks=True)
(out / 'die_plan.json').unlink()
(out / 'die_plan.json').write_text(json.dumps(P, indent=1) + '\n')
(out / 'template_event.json').write_text(json.dumps(dict(schema='opentallas.hbm_plan_event.v1', event='d44v-templates', reverted=rev), indent=1))
print(len(rev), 'reverted')
