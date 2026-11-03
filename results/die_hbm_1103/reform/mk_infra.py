#!/usr/bin/env python3
"""DIE-HBM-61/PLAN d44v scope (a) slot infrastructure: PG-CORECONN-2 core_pg_connect: true on every partition type that
places hard-core macros without it (check.py check_core_pg WARN 'physical PG open'; gen_phys lands a CORE macro grid on
the macro PG pins).  python3 mk_infra.py PLAN_DIR OUT_DIR TOOLS_DIE_PLAN_DIR  (OUT_DIR = hard-linked copy + new die_plan.json)"""
import json, os, shutil, sys, hashlib
from pathlib import Path
plan, out, tools = map(Path, sys.argv[1:4])
sys.path.insert(0, str(tools))
import gen_phys as GP  # noqa: E402
P = json.loads((plan / 'die_plan.json').read_text())
import schema as S  # noqa: E402
set_on = []
PV = S.Plan(P, plan / 'die_plan.json')
for tn, t in sorted(P['partition_types'].items()):
    if t.get('core_pg_connect'):
        continue
    try:
        mac = GP.type_macros(PV, tn)
        phy = {i for d in GP.phy_pg_domains(PV, tn) for i in d[4]}
    except Exception as ex:
        print('skip', tn, ex); continue
    mac = [m for m in mac if m[0] not in phy]
    if mac:
        lefs = sorted({m[2] for m in mac})
        t['core_pg_connect'] = True
        t['note'] = (t.get('note', '') + ' | DIE-HBM-61 d44v slot infra: core_pg_connect (PG-CORECONN-2, %d macros)' % len(mac)).strip(' |')
        set_on.append(dict(type=tn, macros=len(mac), lefs=lefs[:6]))
if out.exists():
    shutil.rmtree(out)
shutil.copytree(plan, out, copy_function=os.link, symlinks=True)
(out / 'die_plan.json').unlink()
(out / 'die_plan.json').write_text(json.dumps(P, indent=1) + '\n')
(out / 'infra_event.json').write_text(json.dumps(dict(schema='opentallas.hbm_plan_event.v1', event='d44v-infra',
                                                      core_pg_connect_set=set_on), indent=1))
print(json.dumps(set_on, indent=1)[:2000])
