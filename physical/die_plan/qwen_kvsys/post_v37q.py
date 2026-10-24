#!/usr/bin/env python3
"""KV plan v3.7q (KV-P7-V38 10-23, GEOM-REVIEW7 v3.7-cores 19:49 + v3.7p 20:38 FAIL fixes): re-place the hg / hgi / pc /
pv hard cores of a v3.7p plan with demand-sized window-face bands and channels.  Origins only (outlines, modules and
instances unchanged); the top-down pins are then re-assigned for the new sites (core_pins_v37q.py) and applied with
post_v37p.py.  Every origin is on the 8.64-um lattice.  Channel / band demand: g2_channels_v37q.py (MACRO-BOUND table).

  head_eighth outlines from the measured cells at e0's fill (71 %): e0 285.12, e2/e4/e6 250.56, odd 233.28 (planned
            cores; was 285.12 for all 8).  The ~100 um freed per axis goes to the channels.
  hg* (ectl types)  qkd_ectlk moves from the top band to the BOTTOM: its big flows are E-face o_ectl_tN (1559 b, E window
            y 10-310) and W-face i_slg_krsp (1062 b, W window y 12-217), both at the bottom of the type.  Columns: W band
            25.92 | even 285.12 | 60.48 | odd 233.28 | mid 69.12 | even | 60.48 | odd | E band 25.92 (even cores
            right-aligned toward their odd partner).  Rows: S band 25.92, ectl 216, 60.48, head rows with 51.84 gaps,
            N band 25.92.
  hgi*      no ectl: W band 43.2 (i_ectl_tN 1559 b + ft windows on W) | even | 51.84 | odd | 69.12 | even | 51.84 |
            odd | E 25.92; rows from S band 25.92 with 138.24 gaps, N band 43.2 (no N/S windows).
  pc*       2 x 2 kvs_pc in the LOWER half beside the W (y 2-500) and E (y 2-428) windows: W band 60.48 | 397.44 |
            mid 103.68 | 397.44 | E band 77.76; S band 34.56, row gap 138.24 (kvpc1 -> kvpc2 chain + hsl glue);
            serpentine kvpc0 (SW) -> 1 (SE) -> 2 (NE) -> 3 (NW); upper half (y > 900) keeps the glue / N-window lanes.
  pv*       W/E bands 60.48, group channels 86.4; rows p0 / 77.76 / p1 / 69.12 / join / 69.12 / p2 / 77.76 / p3 from
            the 34.56 S band (pv_v12 L2045 bottom crossing band stays core-free); top band 449 -> 259.2 um.
Band / gap widths were iterated against g2_channels_v37q.py (routed-demand estimate, bits / tracks <= 0.6).
Planned cores lose their v3.7p pins_file / orient here; core_pins_v37q.py re-assigns them for the new sites.
usage: post_v37q.py die_plan_v37p.json > die_plan.json"""
import json
import re
import sys

G = 8.64


def L(v):
    return round(round(v / G) * G, 6)


# head_eighth outlines from the measured cells (percore: e0 383k, e2/e4/e6 291k, odd 255k) at e0's fill (58.1k um2 of
# cell area in 285.12^2 = 71 %): e0 285.12, e2/e4/e6 250.56 (70 %), odd 233.28 (71 %).  The ~100 um this frees per
# axis goes to the channels / gaps the demand table needs.
EDGE = {0: 285.12, 2: 250.56, 4: 250.56, 6: 250.56, 1: 233.28, 3: 233.28, 5: 233.28, 7: 233.28}
#            W band | even col 285.12 | ch | odd 233.28 | mid | even | ch | odd | E band
XS = {True: (25.92, 60.48, 69.12, 25.92), False: (43.2, 51.84, 69.12, 25.92)}   # ectl types / hgi


def hg(t, ectl):
    hs = {h['inst']: h for h in t['hard_cores']}
    heads = sorted({re.match(r'(head\d)_e\d', i).group(1) for i in hs if re.match(r'head\d_e\d', i)})
    wb, ch, mid, eb = XS[ectl]
    xe0 = [wb, wb + 285.12 + ch + 233.28 + mid]
    assert abs(xe0[1] + 285.12 + ch + 233.28 + eb - t['outline_um'][0]) < 1e-6
    if ectl:
        ys, gy = 25.92 + 216.0 + 60.48, 51.84
        hs['ectl']['origin_um'] = [25.92, 25.92]
        hs['ectl']['note'] = re.sub(r'qkd_ectlk leaf core under the N o_ectl windows',
                                    'qkd_ectlk leaf core at the bottom beside the E o_ectl_tN / W i_slg_krsp windows '
                                    '(v3.7q)', hs['ectl']['note'])
    else:
        ys, gy = 25.92, 138.24
    rowy = [ys]
    for r in range(1, 4):
        rowy.append(L(rowy[-1] + EDGE[2 * (r - 1)] + gy))
    for hi, hd in enumerate(heads):
        for e in range(8):
            r, ci = e // 2, e % 2
            h = hs[f'{hd}_e{e}']
            h['outline_um'] = [EDGE[e], EDGE[e]]
            # even cores right-aligned in the 285.12 column (toward their odd partner), odd cores beside the channel
            x = xe0[hi] + (285.12 - EDGE[e]) if ci == 0 else xe0[hi] + 285.12 + ch
            h['origin_um'] = [L(x), rowy[r]]
            h['note'] += f'; v3.7q outline {EDGE[e]:g}^2 from its measured cells at 71 % fill'
    return len(heads) * 8 + bool(ectl)


def pc(t):
    hs = {h['inst']: h for h in t['hard_cores']}
    xs, ys = [60.48, 561.6], [34.56, 535.68]     # W band 60.48 | 397.44 | 103.68 | 397.44 | E band 77.76; row gap 138.24
    site = dict(kvpc0=(0, 0), kvpc1=(1, 0), kvpc2=(1, 1), kvpc3=(0, 1))
    n = 0
    for k, (c, r) in site.items():
        if k in hs:
            hs[k]['origin_um'] = [xs[c], ys[r]]
            n += 1
    return n


def pv(t):
    hs = {h['inst']: h for h in t['hard_cores']}
    ph, jh = 190.08, 172.8
    y = [34.56]
    for gap, hgt in ((77.76, ph), (69.12, ph), (69.12, jh), (77.76, ph)):
        y.append(L(y[-1] + hgt + gap))
    yp0, yp1, yj, yp2, yp3 = y
    n = 0
    for g in range(4):
        x = L(60.48 + g * (380.16 + 86.4))          # W/E bands 60.48 (ft5/ft0 transit up the bands), channels 86.4
        for k, yy in enumerate((yp0, yp1, yp2, yp3)):
            h = hs[f'pvg{g}_p{k}']
            h['origin_um'] = [x, yy]
            n += 1
        j = hs.get(f'pv__u_g{g}_j')
        if j:
            j['origin_um'] = [L(x + (380.16 - 172.8) / 2), yj]
            n += 1
    return n


def main():
    P = json.load(open(sys.argv[1]))
    n = 0
    for tn, t in P['partition_types'].items():
        if not t.get('hard_cores'):
            continue
        if re.match(r'kv3_hgi?(_|$)', tn):
            n += hg(t, any(h['inst'] == 'ectl' for h in t['hard_cores']))
        elif re.match(r'kv3_pc(_|$)', tn):
            n += pc(t)
        elif re.match(r'kv3_pv(_|$)', tn):
            n += pv(t)
        else:
            continue
        for h in t['hard_cores']:      # planned cores: pins / orient re-assigned for the new sites (core_pins_v37q.py)
            if not h.get('lef'):
                h.pop('pins_file', None)
                h['orient'] = 'R0'
                h['note'] = h.get('note', '').replace('lef/lib pending; pins top-down (KV-P6-PINS)',
                                                      'lef/lib/pins pending')
    P['note'] += (f' | v3.7q (KV-P7-V38 10-23, GEOM-REVIEW7 v3.7-cores/v3.7p FAIL fixes): {n} hg/hgi/pc/pv hard cores '
                  're-placed (post_v37q.py: ectl at the bottom beside its E/W windows, >= 25.92-um window bands, pc 2x2 '
                  'beside the W/E windows, pv row gaps 77.76/51.84 from the top band); pins re-assigned '
                  '(core_pins_v37q.py); channel-demand table g2_channels_v37q.py')
    sys.stderr.write(f'post_v37q: {n} cores re-placed\n')
    json.dump(P, sys.stdout, indent=1)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
