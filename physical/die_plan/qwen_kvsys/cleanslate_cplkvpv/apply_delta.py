#!/usr/bin/env python3
"""apply_delta.py PLAN_IN DELTA.json PLAN_OUT : positions/orients-only plan event.
A pair moving into a slot of the same module takes that slot's base orient, track_offset and the per-pin tap xy of the
slot's base occupant (identical module => identical footprint, island, internal ft/station relation). A core that only
changes orient in place (joins) gets its tap xy mirrored inside its outline. Refuses anything else."""
import json, sys
pin, dp, pout = sys.argv[1:4]
PL = json.load(open(pin)); D = json.load(open(dp))
def mir(o0, o1):
    # flip flags (fx, fy) between two orients of a rect
    f = {'R0': (0, 0), 'MY': (1, 0), 'MX': (0, 1), 'R180': (1, 1)}
    a, b = f[o0], f[o1]; return a[0] ^ b[0], a[1] ^ b[1]
for tn, d in D.items():
    T = PL['partition_types'][tn]
    H = {h['inst']: h for h in T['hard_cores']}
    slot = {(round(h['origin_um'][0], 3), round(h['origin_um'][1], 3), h['module']): h['inst'] for h in H.values()}
    base = {k: json.loads(json.dumps(h)) for k, h in H.items()}
    taps = (T.get('clock') or {}).get('taps') or []
    btap = {}
    for t in taps:
        if t.get('kind') == 'core' and '.' in t['name']:
            i, p = t['name'].split('.', 1); btap[(i, p)] = list(t['xy'])
    occ = set(); trans = set()
    newxy = {}
    for k, (x, y, o) in d.items():
        h = H[k]; b = base[k]
        key = (round(x, 3), round(y, 3), h['module'])
        if key not in slot and o == b['orient']:  # pure translation (legality checked by legal.py; taps move with the core)
            dx, dy = x - b['origin_um'][0], y - b['origin_um'][1]
            h['origin_um'] = [x, y]
            for (i, p), xy in btap.items():
                if i == k: newxy[(k, p)] = [round(xy[0] + dx, 4), round(xy[1] + dy, 4)]
            trans.add(k)
            h['note'] = (h.get('note') + ' | ' if h.get('note') else '') + 'CPL-KV-PV 11-11 clean-slate: translate %+.2f %+.2f' % (dx, dy)
            continue
        if key not in slot: raise SystemExit('%s %s: target is not a base slot of module %s' % (tn, k, h['module']))
        src = slot[key]
        if src in occ: raise SystemExit('%s: slot of %s taken twice' % (tn, src))
        occ.add(src)
        sb = base[src]
        if src != k:
            if o != sb['orient']: raise SystemExit('%s %s: moved core must keep slot orient %s (got %s)' % (tn, k, sb['orient'], o))
            h['origin_um'] = list(sb['origin_um']); h['orient'] = sb['orient']; h['track_offset_um'] = list(sb.get('track_offset_um') or [0, 0])
            for (i, p), xy in btap.items():
                if i == src: newxy[(k, p)] = list(xy)
        else:
            fx, fy = mir(b['orient'], o)
            x0, y0 = b['origin_um']; w, hh = b['outline_um']
            h['orient'] = o
            for (i, p), xy in btap.items():
                if i == k: newxy[(k, p)] = [round(2 * x0 + w - xy[0], 4) if fx else xy[0], round(2 * y0 + hh - xy[1], 4) if fy else xy[1]]
        h.setdefault('note', '')
        h['note'] = (h['note'] + ' | ' if h['note'] else '') + 'CPL-KV-PV 11-11 clean-slate: slot %s orient %s' % (src, o)
    # moved cores must form closed permutations
    moved = {k for k in d if k not in trans and slot[(round(d[k][0], 3), round(d[k][1], 3), H[k]['module'])] != k}
    vacated = {slot[(round(base[k]['origin_um'][0], 3), round(base[k]['origin_um'][1], 3), base[k]['module'])] for k in moved}
    tgt = {slot[(round(d[k][0], 3), round(d[k][1], 3), H[k]['module'])] for k in moved}
    if vacated != tgt: raise SystemExit('%s: moves are not a permutation (%s vs %s)' % (tn, sorted(vacated), sorted(tgt)))
    for t in taps:
        if t.get('kind') == 'core' and '.' in t['name']:
            i, p = t['name'].split('.', 1)
            if (i, p) in newxy: t['xy'] = newxy[(i, p)]
    print(tn, 'moved', len(moved), 'translated', len(trans), 'reoriented', sum(1 for k in d if k not in moved and k not in trans and d[k][2] != base[k]['orient']), 'taps', len(newxy))
json.dump(PL, open(pout, 'w'), indent=1)
open(pout, 'a').write('\n')
