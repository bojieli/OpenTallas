#!/usr/bin/env python3
"""TYPE-REDUCE-3 10-25: apply the orientation-only one-table merges that pass G0C with 0 new findings
(orient_apply.py probe): ot_hgi_sm_xload_cl2_bdring 86.4x302.4 (u_xq_Q_p0_bd table, both R0) and
ot_hbm_xp_aq_tree13_fmt 183.6x108 (u_xl_Q_aqhi table; aqlo MX + track offset y +0.096 um = 0 mod M4 0.048 and
the M6 half pitch 0.032 that MX of a 108 um core leaves).  Idempotent; run from the repo root on the TYPE-REDUCE-2
B2n plan (claude/type-reduce2-hbm-1025@623e81076)."""
import json, os, shutil
P = 'physical/die_plan/hbm_arch/B2n'
MERGES = [  # module, template inst, {inst: (orient, dtrack)}
    ('ot_hgi_sm_xload_cl2_bdring', 'u_xq_Q_p0_bd', {'u_xq_Q_p1_bd': ('R0', (0.0, 0.0))}),
    ('ot_hbm_xp_aq_tree13_fmt', 'u_xl_Q_aqhi', {'u_xl_Q_aqlo': ('MX', (0.0, 0.096))}),
]
plan = json.load(open(f'{P}/die_plan.json'))
T = plan['partition_types']
for mod, tinst, mem in MERGES:
    hcs = [hc for t in T.values() for hc in (t.get('hard_cores') or []) if hc['module'] == mod]
    src = next(hc for hc in hcs if hc['inst'] == tinst)
    wh = 'x'.join(f'{v:g}' for v in src['outline_um'])
    rel = f'cores_tmpl/{mod}__{wh}.json'
    if src['pins_file'] != rel:
        shutil.copy(f'{P}/{src["pins_file"]}', f'{P}/{rel}')
    for hc in hcs:
        if hc['inst'] != tinst and hc['inst'] not in mem:
            raise SystemExit(f'{mod}: unexpected member {hc["inst"]}')
        old = hc['pins_file']
        if old == rel:
            continue
        o, (dx, dy) = mem.get(hc['inst'], ('R0', (0.0, 0.0)))
        off = list(src.get('track_offset_um', [0.0, 0.0]))
        hc['track_offset_um'] = [round(off[0] + dx, 4), round(off[1] + dy, 4)]
        if o != 'R0':
            hc['orient'] = o
        hc['pins_file'] = rel
        hc['note'] = (f'TYPE-REDUCE-3/HBM 10-25: one pin table per (master, outline) ({rel}), orient {o}, '
                      f'track offset +{dx:g}/+{dy:g}; G0C 0 new findings; was {old} | ' + hc.get('note', ''))
json.dump(plan, open(f'{P}/die_plan.json', 'w'), indent=0)
open(f'{P}/die_plan.json', 'a').write('\n')
