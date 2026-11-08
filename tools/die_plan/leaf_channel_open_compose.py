#!/usr/bin/env python3
"""Compose the wave plan with S81-TYPES-7-LEAFB channel-open moves: for each row, hard_cores origin/orient =
the kit's facing-form position (macro_moves.json 'to'/'orient', else plan) + this form's delta; grid taps moved per tap_moves.
usage: compose.py PLAN OUT.json ROW=KITDIR=RESULT.json ..."""
import json, sys
P, OUT = sys.argv[1:3]
plan = json.load(open(P))
rep = {}
for spec in sys.argv[3:]:
    row, kit, res = spec.split('=')
    T = 'ot_s81sl_leaf__' + row; t = plan['partition_types'][T]
    try: mm = json.load(open(kit + '/macro_moves.json'))
    except FileNotFoundError: mm = {}
    facing = {v['inst']: (v['to'], v['orient']) for v in mm.values()}
    r = json.load(open(res)); mine = {v['inst']: v['delta_um'] for v in r['moves'].values()}
    ch = []
    for h in t['hard_cores']:
        inst = h['inst']; short = inst.split('.', 1)[-1]
        o, ori = facing.get(inst, (h['origin_um'], h['orient']))
        d = mine.get(short, [0, 0])
        new = [round(o[0] + d[0], 4), round(o[1] + d[1], 4)]
        if new != list(h['origin_um']) or ori != h['orient']:
            ch.append((short, h['origin_um'], new, h['orient'], ori)); h['origin_um'] = new; h['orient'] = ori
    tm = r.get('tap_moves', {}); nt = 0
    c = t['clock']
    for tp in c.get('taps', []) + c.get('added_taps', []):
        if tp.get('name') in tm and tp.get('kind') != 'core':
            tp['xy'] = tm[tp['name']]['to']; nt += 1
    assert nt == len(tm), (row, nt, tm)
    t.setdefault('note', ''); t['note'] = (t['note'] + ' | ' if t['note'] else '') + 'S81-TYPES-7-LEAFB 11-08 channel-open form (claude/s81-types-7-leafb-1108): facing-form + channel-open macro positions; grid taps moved: %s' % sorted(tm)
    rep[T] = dict(cores_changed=len(ch), taps_moved=sorted(tm))
json.dump(plan, open(OUT, 'w'), indent=1)
print(json.dumps(rep))
