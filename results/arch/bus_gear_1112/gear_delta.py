#!/usr/bin/env python3
"""BUS-GEAR-1 (2026-11-12): plan delta for the approved 2:1 gearboxes (COORD ruling 01:49 + OWNER adoption of (B)).

  s81: every lane whose ports use an x_i*/x_o*/xo_i*/xo_o* bus: width 1104 -> 556 (4 lanes x {f, 138-b beat}), on every
       port (ft hops included) and on the endpoint type buses; lane note tagged; DEC12 word latency +1 (beats 2,
       word_bits 1104 is NOT used: the beat lane carries 4 x (1 + 138) bits, see ot_s81_xlane_gear.sv).
  hbm: lanes L8, L8m (3070 -> 1630) and L9, L9m (1842 -> 978): per PC the 288-b write payload becomes one 144-b beat.

Usage: gear_delta.py DIE PLAN_IN.json[.gz] PLAN_OUT.json DELTA_OUT.json
The delta JSON lists every changed (port | type bus) with old/new width, so the die owner can apply it in the event
compose instead of taking PLAN_OUT whole.  Latency (+1 word edge per geared lane) is recorded in the lane note and in
the delta (the plan schema has no gear key); regenerate the table with gen.py latency --inplace after adding it to the event's latency pads.
"""
import gzip, json, sys

def load(p):
    return json.load(gzip.open(p) if p.endswith('.gz') else open(p))

def sub(sites, old, new):
    return [sites[round(k * (old - 1) / (new - 1))] for k in range(new)]


def main():
    die, pin, pout, dout = sys.argv[1:5]
    d = load(pin)
    P = {p['id']: p for p in d['ports']}
    ptype = {p['name']: p['type'] for p in d['partitions']}
    if die == 's81':
        X = ('x_i', 'x_o', 'xo_i', 'xo_o')
        rule = {}
        for l in d['lanes']:
            if any(P[i][e]['bus'].startswith(X) for i in l['ports'] for e in ('src', 'dst')):
                rule[l['id']] = (1104, 556)
    elif die == 'hbm':
        rule = {'L8': (3070, 1630), 'L8m': (3070, 1630), 'L9': (1842, 978), 'L9m': (1842, 978)}
    else:
        raise SystemExit('die must be s81 or hbm')
    delta = dict(die=die, base=pin, note='BUS-GEAR-1 2:1 gear; +1 word edge per geared lane (RX lands the word one '
                 'edge after beat 0); ft slot windows kept (pin pitch doubles; the die owner may narrow them)',
                 lanes=[], ports=[], type_buses=[], ft_slots=[])
    tb = {}
    fsl = {}
    for l in d['lanes']:
        if l['id'] not in rule:
            continue
        old, new = rule[l['id']]
        for i in l['ports']:
            p = P[i]
            assert p['width'] == old, (l['id'], i, p['width'])
            p['width'] = new
            delta['ports'].append(dict(port=i, old=old, new=new))
            for e in ('src', 'dst'):
                t = ptype.get(p[e]['part'])
                T = d['partition_types'].get(t) if t else None
                if T is None:
                    continue
                for b in T['buses']:
                    if b['name'] == p[e]['bus'] and b['width'] == old:
                        tb[(t, b['name'])] = (old, new)
                        b['width'] = new
                for f in T.get('ft_slots', []):      # ft slot buses <name>_i / <name>_o
                    if p[e]['bus'] in (f['name'] + '_i', f['name'] + '_o') and f['width'] == old:
                        fsl[(t, f['name'])] = (old, new)
                        f['width'] = new
                        # explicit FF sites are 'payload then epoch'.  The new pins spread over the SAME face windows
                        # (pitch x old/new), so new bit k takes the site of old bit round(k (old-1)/(new-1)): the
                        # site keeps tracking its pin; the epoch site is kept.
                        if 'bit_sites_um' in f:
                            f['bit_sites_um'] = [sub(st[:old], old, new) + st[old:] if len(st) == old + 1 else st
                                                 for st in f['bit_sites_um']]
                        fb = f.get('face_bit_sites_um')
                        if isinstance(fb, list) and len(fb) in (old, old + 1):
                            f['face_bit_sites_um'] = sub(fb[:old], old, new) + fb[old:]
        l['note'] = (l.get('note', '') + ' | BUS-GEAR-1 2:1').strip(' |')
        delta['lanes'].append(dict(lane=l['id'], old=old, new=new, ports=len(l['ports']), word_extra_cycles=1))
    delta['type_buses'] = [dict(type=t, bus=b, old=o, new=n) for (t, b), (o, n) in sorted(tb.items())]
    delta['ft_slots'] = [dict(type=t, slot=n, old=o, new=w) for (t, n), (o, w) in sorted(fsl.items())]
    delta['summary'] = dict(lanes=len(delta['lanes']), ports=len(delta['ports']), type_buses=len(tb), ft_slots=len(fsl),
                            bits_saved_on_ports=sum(x['old'] - x['new'] for x in delta['ports']))
    json.dump(d, open(pout, 'w'), indent=1)
    json.dump(delta, open(dout, 'w'), indent=1)
    print(json.dumps(delta['summary']))

if __name__ == '__main__':
    main()
