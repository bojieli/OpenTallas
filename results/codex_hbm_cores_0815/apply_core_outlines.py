#!/usr/bin/env python3
"""Fold measured-content core outlines into a TRIAL plan; caller owns repack/restation/G0/G1.

Usage: apply_core_outlines.py PLANDIR
Pin order and face are preserved. Every pin is spread on its original layer's
0.024+0.048*k tracks with an 8.64um end reserve. No RTL or cycle change.
Shrinks preserve each instance centre; growth stays at its original origin and
is explicitly reported for the composing plan owner's neighbour check.
"""
import collections
import json
from pathlib import Path
import sys

TARGETS = {
    'ot_hbm_su_static_pgslice_lg__pretree': ([164.16, 241.92], 18169.39188, 0),
    'ot_hbm_idx_vm_query_static_n12': ([216., 138.24], 11404.53432, 0),
    'ot_hbm_sm_vm_wr_q_t_lanes4': ([142.56, 216.], 6203.51298, 3893.851),
    'ot_hgi_coll_inj_idx_join_rg': ([211.68, 207.36], 9690.0138, 0),
    'ot_hgi_sm_xload_xq_pegress': ([181.44, 276.48], 6032.92698, 0),
}


def snap(v):
    return round(.024 + .048 * round((v - .024) / .048), 6)


def transform(plan_dir):
    root = Path(plan_dir)
    plan = json.loads((root / 'die_plan.json').read_text())
    entries = json.loads((root / 'clock_entries.json').read_text())
    report = {'status': 'TRIAL: repack/restation/G0/G1 still required', 'cores': []}
    generated = {}
    for tn, ty in plan['partition_types'].items():
        for c in ty.get('hard_cores', []):
            mod = c['module']
            if mod not in TARGETS:
                continue
            wh, area, macro = TARGETS[mod]
            old = c['outline_um']
            key = (c['pins_file'], tuple(wh))
            if key not in generated:
                pins = json.loads((root / c['pins_file']).read_text())
                groups = collections.defaultdict(list)
                for pin in pins:
                    d = [abs(pin['x']), abs(pin['x']-old[0]), abs(pin['y']), abs(pin['y']-old[1])]
                    face = ['W', 'E', 'S', 'N'][d.index(min(d))]
                    groups[face, pin['layer']].append(pin)
                for (face, layer), ps in groups.items():
                    axis = 'y' if face in 'EW' else 'x'
                    length = wh[1] if axis == 'y' else wh[0]
                    ps.sort(key=lambda p: (p[axis], p['name']))
                    lo = round((8.64-.024)/.048)
                    hi = round((length-8.64-.024)/.048)
                    assert hi-lo+1 >= len(ps), (mod, face, layer, len(ps), hi-lo+1)
                    used = set()
                    for i, p in enumerate(ps):
                        track = round(lo + (hi-lo)*(i+.5)/len(ps))
                        assert track not in used, (mod, face, layer, track)
                        used.add(track)
                        p[axis] = round(.024 + .048*track, 6)
                        p['x' if axis == 'y' else 'y'] = .019 if face in 'WS' else round(wh[0 if face == 'E' else 1]-.019, 6)
                rel = 'cores/' + mod + '__' + 'x'.join(f'{x:g}' for x in wh) + '__content_trial.json'
                (root / rel).write_text(json.dumps(pins, indent=1)+'\n')
                generated[key] = rel
            grow = any(n > o + .001 for n, o in zip(wh, old))
            if not grow:
                c['origin_um'] = [round(x+(o-n)/2, 6) for x, o, n in zip(c['origin_um'], old, wh)]
            c['outline_um'] = wh[:]
            c['pins_file'] = generated[key]
            c['note'] = c.get('note', '') + '; CODEX measured-content outline TRIAL, no cycle change'
            entry = entries.get(tn, {}).get(c['inst'])
            if entry:
                # Macro-free cores use the centre. wr_q's lone SRAM stays in its
                # lower band; its centre entry at y108 clears the SRAM top58.4.
                x, y = snap(wh[0]/2), snap(wh[1]/2)
                entry['xy_um'] = [x, y]
                entry['island_um'] = [round(x-4.32,6),round(y-4.32,6),round(x+4.32,6),round(y+4.32,6)]
                entry['source'] = 'CODEX measured-content structural outline trial, centre channel'
            free = (wh[0]-8.64)*(wh[1]-8.64)-macro
            report['cores'].append(dict(type=tn,inst=c['inst'],module=mod,old_outline=old,outline=wh,
                std_area_um2=area,macro_area_um2=macro,free_fill=round(area/free,4),
                growth_needs_neighbour_check=grow,pins_file=c['pins_file'],entry=entry))
    (root / 'die_plan.json').write_text(json.dumps(plan, indent=1)+'\n')
    (root / 'clock_entries.json').write_text(json.dumps(entries, indent=1)+'\n')
    (root / 'content_outline_report.json').write_text(json.dumps(report, indent=1)+'\n')
    print('updated',len(report['cores']),'instances;',len(generated),'pin tables; TRIAL only')


if __name__ == '__main__':
    transform(sys.argv[1])
