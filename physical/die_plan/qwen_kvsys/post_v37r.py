#!/usr/bin/env python3
"""KV plan v3.7r (KV-P7-V38 10-23, GEOM-REVIEW8 21:47 v3.7q FAIL fix list): v3.7q core re-place (post_v37q.py) plus
type-internal re-sizing from the per-gap demand table (g2_channels_v37q.json; width needed = bits / (0.6 * 36.4 tr/um)).
  hg* ectl  qkd_ectlk reshaped 881.28 x 216 -> 1226.88 x 155.52 (same area, full width between the W/E bands, so its
            E face reaches the E o_ectl_tN window and the bottom-right empty block is used); ectl | head row gap
            60.48 -> 120.96 (2.7k b needs ~125).  Head rows unchanged.
  pc*       FIX (3): kvpc2/kvpc3 moved up into the empty upper half: S band 34.56 -> 60.48 (1.2k b), kvpc1 | kvpc2 row
            gap 138.24 -> 241.92 (5.3k b chain + hsl glue); kvpc3 -> N windows now ~490 um.
  pv*       FIX (4): cores moved up into the free top band: S band 34.56 -> 69.12 (1.5k b, L2045 band stays core-free),
            p0|p1 77.76 -> 138.24 (2.9k b), p1|J 69.12 -> 103.68 (2.2k b), J|p2 69.12 -> 86.4, p2|p3 77.76 -> 86.4;
            top band 259.2 -> 103.68.
NOT here (die-level): hg astk N/S strip-chain + ft3 re-window to the mid channel / head1 side (head0_e2|e3 3.3k b) and
the hgi W-band turn-down (3.5k b in 43.2 um): every hg/hgi column is full width-wise, so these need the die windows
moved (FIX (1)/(2)).
usage: post_v37r.py die_plan_v37p.json > die_plan.json"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post_v37q as Q   # noqa: E402

L = Q.L


def ectl(t):
    for h in t['hard_cores']:
        if h['inst'] == 'ectl':
            assert h['outline_um'] == [881.28, 216.0], h['outline_um']
            h['outline_um'] = [1226.88, 155.52]
            h['origin_um'] = [25.92, 25.92]
            h['note'] += '; v3.7r outline 1226.88 x 155.52 (same area; full width, ectl|head gap 120.96)'
            return 1
    return 0


def pc(t):
    hs = {h['inst']: h for h in t['hard_cores']}
    hgt = hs['kvpc0']['outline_um'][1]
    xs, ys = [60.48, 561.6], [60.48, L(60.48 + hgt + 241.92)]
    n = 0
    for k, (c, r) in dict(kvpc0=(0, 0), kvpc1=(1, 0), kvpc2=(1, 1), kvpc3=(0, 1)).items():
        if k in hs:
            hs[k]['origin_um'] = [xs[c], ys[r]]
            n += 1
    return n


def pv(t):
    hs = {h['inst']: h for h in t['hard_cores']}
    ph, jh = 190.08, 172.8
    y = [69.12]
    for gap, hgt in ((138.24, ph), (103.68, ph), (86.4, jh), (86.4, ph)):
        y.append(L(y[-1] + hgt + gap))
    assert y[-1] + ph <= t['outline_um'][1] - 103.68 + 1e-6
    n = 0
    for g in range(4):
        x = L(60.48 + g * (380.16 + 86.4))
        for k, yy in enumerate((y[0], y[1], y[3], y[4])):
            hs[f'pvg{g}_p{k}']['origin_um'] = [x, yy]
            n += 1
        j = hs.get(f'pv__u_g{g}_j')
        if j:
            j['origin_um'] = [L(x + (380.16 - 172.8) / 2), y[2]]
            n += 1
    return n


def main():
    P = json.load(open(sys.argv[1]))
    sys.argv = sys.argv[:1] + [sys.argv[1]]
    n = 0
    for tn, t in P['partition_types'].items():
        if not t.get('hard_cores'):
            continue
        if re.match(r'kv3_hgi?(_|$)', tn):
            e = any(h['inst'] == 'ectl' for h in t['hard_cores'])
            n += Q.hg(t, e)
            if e:
                ectl(t)
        elif re.match(r'kv3_pc(_|$)', tn):
            n += pc(t)
        elif re.match(r'kv3_pv(_|$)', tn):
            n += pv(t)
        else:
            continue
        for h in t['hard_cores']:
            if not h.get('lef'):
                h.pop('pins_file', None)
                h['orient'] = 'R0'
                h['note'] = h.get('note', '').replace('lef/lib pending; pins top-down (KV-P6-PINS)', 'lef/lib/pins pending')
    P['note'] += (f' | v3.7r (KV-P7-V38 10-23, GEOM-REVIEW8 FIX (3)(4) + ectl gap): {n} hg/hgi/pc/pv cores re-placed '
                  '(post_v37r.py: ectl full-width 155.52 tall, pc rows 60.48/241.92 gaps, pv cores up into the top band); '
                  'pins re-assigned (core_pins_v37q.py)')
    sys.stderr.write(f'post_v37r: {n} cores re-placed\n')
    json.dump(P, sys.stdout, indent=1)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
