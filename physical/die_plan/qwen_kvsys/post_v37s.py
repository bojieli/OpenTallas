#!/usr/bin/env python3
"""KV plan v3.7s (KV-P7-V38 10-23, GEOM-REVIEW8 FIX (2) hgi W band, KV-P7 22:30 window-move decision): on a v3.7r plan
(post_v37r.py output, before the pin step):
  * hg | hgi edge windows: the ectl tN bus (1559 b) is compressed into the hg ectl / hgi bottom-band span (type frame
    y lo .. lo+170) and the 1056-b W->E feedthrough (hg ft3 / hgi ft23) moves down beside it (lo+171 .. lo+290;
    lo = that instance's tN window start), so in
    hgi both enter the free bottom band instead of the 43.2-um W band; in hg tN leaves the ectl E face straight and ft3
    crosses in the ectl | head gap.  Same type-frame span in every stacked hg/hgi type (all 6 + 6 instances per side).
  * hgi head rows start at 302.4 with 51.84 gaps (the hg row grid): y 0..302 is a full-width channel for tN fan-out and
    the ft23 W->E turn-down; W band 43.2 then carries only the column traffic.
  ** The window move is OFF by default (OT_V37S_WINDOWS=1 enables it): G0 [faces] caps pins at 6/um per 10-um
     window, so tN (1559 b) needs >= 260 um and the ft (1056 b) >= 176 um; both do not fit below the hst windows
     (y ~311).  Default v3.7s = the original windows + the hgi row shift: tN (W y 10-310) enters the free bottom band
     directly and only the 1056-b ft turns down the W band from y <= 531 to the band top at 302.4.
Lanes, stations and widths are unchanged (window positions only), so lane cycles do not change.
usage: post_v37s.py die_plan_v37r.json > die_plan.json"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../tools/die_plan'))
import g2_channels_v37q as G  # noqa: E402
import post_v37q as Q  # noqa: E402


def tmap(P, inst, df, d):
    x0, y0, x1, y1 = P.rect(inst)
    if df in 'EW':
        return P.to_type(inst, (x0 if df == 'W' else x1, d))[1], y0
    return P.to_type(inst, (d, y0 if df == 'S' else y1))[0], x0


def to_die(P, inst, df, t):
    a, base = tmap(P, inst, df, 0.0)
    b, _ = tmap(P, inst, df, 1.0)
    s = b - a
    return (t - a) / s


def main():
    raw = json.load(open(sys.argv[1]))
    P = G.S.Plan(raw)
    typ = {n: p['type'] for n, p in P.parts.items()}
    moved = 0
    tnlo = {}
    for pr in (raw['ports'] if os.environ.get('OT_V37S_WINDOWS') == '1' else []):
        parts = [pr['src']['part'], pr['dst']['part']]
        if not (any(typ.get(p, '').startswith('kv3_hg_') or typ.get(p) == 'kv3_hg' for p in parts) and
                any(typ.get(p, '').startswith('kv3_hgi') for p in parts)):
            continue
        tn = 'ectl_Q_N_tN' in pr['src']['bus']
        ft = pr['src']['bus'].startswith('ft') and pr['width'] == 1056
        if not (tn or ft):
            continue
        side = 'src' if typ[pr['src']['part']].startswith('kv3_hgi') else 'dst'
        inst = pr[side]['part']
        df = pr['face'] if side == 'src' else G.C.OPP[pr['face']]
        lo = min(tmap(P, inst, df, w)[0] for w in pr['window_um'])
        pr.setdefault('_lo', lo)
        if tn:
            tnlo[inst] = lo
        moved += 1
    for pr in raw['ports']:
        if '_lo' not in pr:
            continue
        side = 'src' if typ[pr['src']['part']].startswith('kv3_hgi') else 'dst'
        inst = pr[side]['part']
        df = pr['face'] if side == 'src' else G.C.OPP[pr['face']]
        if 'ectl_Q_N_tN' in pr['src']['bus']:
            lo = pr['_lo']
            a, b = lo, lo + 170.0
        else:
            a, b = tnlo[inst] + 171.0, tnlo[inst] + 290.0
        d = sorted([round(to_die(P, inst, df, a), 3), round(to_die(P, inst, df, b), 3)])
        pr['window_um'] = d
        pr['note'] = (pr.get('note', '') + ' | v3.7s window moved (hgi bottom band)').strip(' |')
        del pr['_lo']
    n = 0
    for tname, t in raw['partition_types'].items():
        if re.match(r'kv3_hgi(_|$)', tname) and t.get('hard_cores'):
            hs = {h['inst']: h for h in t['hard_cores']}
            heads = sorted({re.match(r'(head\d)_e\d', i).group(1) for i in hs if re.match(r'head\d_e\d', i)})
            rowy = [302.4]
            for r in range(1, 4):
                rowy.append(Q.L(rowy[-1] + Q.EDGE[2 * (r - 1)] + 51.84))
            for hd in heads:
                for e in range(8):
                    h = hs[f'{hd}_e{e}']
                    h['origin_um'][1] = rowy[e // 2]
                    n += 1
    raw['note'] += (f' | v3.7s (KV-P7-V38 10-23, GEOM-REVIEW8 FIX (2)): {moved} hg|hgi tN / 1056-b ft port windows '
                    f'moved into the hgi bottom band; {n} hgi head cores on the hg row grid (rows from 302.4)')
    sys.stderr.write(f'post_v37s: {moved} windows moved, {n} hgi cores\n')
    json.dump(raw, sys.stdout, indent=1)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
