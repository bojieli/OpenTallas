#!/usr/bin/env python3
"""KV plan v3.9 (KV-P8-PLAN 10-23): hard-core re-place of the hg / hgi / pc / pv types on the widened v3.9 lattice
(COORD KV-P8 rulings: no squeezing; hg/hgi wider; pc/pv cores spread over the FULL height of the type).  Origins and
(planned-core) outlines only; modules, members and instances are unchanged.  Runs on the v3.8h-equivalent plan of
run_v39.sh (die_plan_v38h.json); core_pins_v37q.py then re-assigns the top-down pins for the new sites and post_v37p.py
applies them.  Every outline / origin is on the 8.64-um lattice; cores keep >= 17.28 um from the type faces.

Measured flows (tools flow on the bound partition netlists, kv39) that set the layouts:
  hg / hgi  per head: the hst glue (hst<h>_g / _t1 / _t2, head_u_ftg: 1.5-1.6k-b buses) feeds every EVEN eighth
            (808 b each, broadcast); e0 -> e2/e4/e6 621 b, e2/e4/e6 553 b among themselves; odd e(2k+1) talks only to
            its even partner e(2k) (468-536 b).  hgi: i_ectl tN (1559 b, W face) -> hst2_g AND hst3_g; hg: qkd_ectlk
            <-> hst0_g / hst1_g (1576 b each), ectl -> o_ectl tN (1559 b, E face), i_slg krsp (1062 b, W face) -> ectl,
            astk strip glue (N/S chain).
     ->     SPINE layout: the two heads' EVEN columns face a central vertical spine (hst glue + head ftg, the N/S
            pass-through and the tN fan-out), ODD columns outside next to their partners:
              W band | h<a> odd | pair gap | h<a> even | SPINE | h<b> even | pair gap | h<b> odd | E band
            four head rows (e0/e1 bottom ... e6/e7 top) spread over the height with equal row channels; hg adds the
            qkd_ectlk core as a full-width service row at the bottom (its tN / krsp faces reach the E / W faces
            directly, the hst glue sits on top of it at the spine foot).
  pc        4 kvs_pc (397.44 x 362.88) 2 x 2, rows spread over the full height (equal S band / row gap / N band),
            columns with equal W band / mid channel / E band; serpentine kvpc0 SW -> 1 SE -> 2 NE -> 3 NW kept.
  pv        4 group columns (pairs 380.16 x 190.08 + the 172.8 join) with equal channels; rows p0 p1 J p2 p3 spread
            over the full height with equal gaps (the ctlv4 V / slg rsp trunk crosses pv_*_3|4 vertically, so the
            channels carry it, not a top band).
Gap sizes come from the per-gap demand table (g2_channels_v37q.py, ratio <= 0.6) iterated on this plan.

usage: post_v39p.py die_plan_v38h.json > die_plan.json      (env OT_V39P_* overrides, see PARAMS)"""
import json
import os
import re
import sys

G = 8.64
EDGE = {0: 285.12, 2: 250.56, 4: 250.56, 6: 250.56, 1: 233.28, 3: 233.28, 5: 233.28, 7: 233.28}  # v3.7q measured
PARAMS = dict(
    # hg/hgi columns: weights of the free width for W band, pair gap, spine, pair gap, E band
    HG_XW=(1.0, 1.2, 3.0, 1.2, 1.0),
    # hgi rows: weights of the free height for S band, 3 row gaps, N band
    HGI_YW=(1.0, 1.4, 1.4, 1.4, 1.0),
    # hg rows (after ectl): S band, ectl|row0 gap, 3 row gaps, N band
    HG_YW=(0.6, 1.6, 1.2, 1.2, 1.2, 1.0),
    # 'col' = vertical spine (head columns), 'row' = horizontal spine (head rows: odd / even | spine | even / odd)
    HG_MODE=('row',), HGI_MODE=('row',),
    # row mode: weights of the free height for S band, pair gap, spine gap(s), pair gap, N band  (hg: 2 spine gaps
    # around the ectl service row; hgi: 1 spine channel)
    HGI_RW=(0.6, 1.0, 2.6, 1.0, 0.6), HG_RW=(0.5, 1.0, 1.2, 1.2, 1.0, 0.5),
    # row mode: weights of the free width for W band, 3 column gaps, E band (even row; odd row centred on it)
    ROW_XW=(1.0, 1.0, 1.0, 1.0, 1.0),
    PC_XW=(1.0, 1.2, 1.0), PC_YW=(1.0, 1.4, 1.0),
    PV_XW=(1.0, 1.0, 1.0, 1.0, 1.0), PV_YW=(1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
)
for k in list(PARAMS):
    if os.environ.get('OT_V39P_' + k):
        PARAMS[k] = tuple(float(x) for x in os.environ['OT_V39P_' + k].split(','))


def L(v):
    return round(round(v / G) * G, 6)


def Lf(v):
    return round(int(v / G + 1e-9) * G, 6)


def spread(total, sizes, weights, lo_min=17.28):
    """positions of `sizes` along `total` with free space split by `weights` (len(sizes)+1), on the 8.64 lattice."""
    assert len(weights) == len(sizes) + 1
    free = total - sum(sizes)
    assert free >= 2 * lo_min, (total, sizes)
    sw = sum(weights)
    gaps = [Lf(free * w / sw) for w in weights]
    gaps[0] = max(gaps[0], lo_min)
    pos, cur = [], gaps[0]
    for s, g in zip(sizes, gaps[1:]):
        pos.append(L(cur))
        cur += s + g
    assert pos[-1] + sizes[-1] <= total - lo_min + 1e-6, (total, sizes, pos)
    return pos


def heads_of(t):
    return sorted({re.match(r'(head\d)_e\d', h['inst']).group(1) for h in t['hard_cores']
                   if re.match(r'head\d_e\d', h['inst'])})


def place_heads(t, rows_y):
    """spine layout; rows_y = y of the 4 head rows (row r holds e2r / e2r+1)."""
    W = t['outline_um'][0]
    hs = {h['inst']: h for h in t['hard_cores']}
    ha, hb = heads_of(t)
    E, O = 285.12, 233.28                 # column widths (even column sized for e0)
    xs = spread(W, [O, E, E, O], PARAMS['HG_XW'])
    x_odd_a, x_even_a, x_even_b, x_odd_b = xs
    n = 0
    for hd, xe, xo, toward_spine in ((ha, x_even_a, x_odd_a, +1), (hb, x_even_b, x_odd_b, -1)):
        for e in range(8):
            r, odd = e // 2, e % 2
            h = hs[f'{hd}_e{e}']
            s = EDGE[e]
            h['outline_um'] = [s, s]
            if odd:   # odd cores flush against their pair gap (toward the even partner)
                x = xo + (O - s) if toward_spine > 0 else xo
            else:     # even cores flush against the spine
                x = xe + (E - s) if toward_spine > 0 else xe
            h['origin_um'] = [L(x), L(rows_y[r])]
            h['note'] = re.sub(r'; v3\.9 .*$', '', h.get('note', '')) + \
                f'; v3.9 spine layout ({hd} {"odd" if odd else "even"} column), outline {s:g}^2 (v3.7q measured cells)'
            n += 1
    return n


def place_rows(t, y_odd_a, y_even_a, y_even_b, y_odd_b):
    """row layout: head a below the spine (odd row outer, even row next to the spine), head b above it (mirror).
    Columns: e0/e1 at the W end ... e6/e7 at the E end; odd e(2k+1) right above / below its even partner e(2k)."""
    W = t['outline_um'][0]
    hs = {h['inst']: h for h in t['hard_cores']}
    ha, hb = heads_of(t)
    xs = spread(W, [EDGE[0], EDGE[2], EDGE[4], EDGE[6]], PARAMS['ROW_XW'])
    n = 0
    for hd, ye, yo, up in ((ha, y_even_a, y_odd_a, True), (hb, y_even_b, y_odd_b, False)):
        for e in range(8):
            k, odd = e // 2, e % 2
            s = EDGE[e]
            h = hs[f'{hd}_e{e}']
            h['outline_um'] = [s, s]
            x = xs[k] + (EDGE[2 * k] - s) / 2
            if odd:      # outer row, flush to the pair gap
                y = yo + (233.28 - s) if up else yo
            else:        # spine row, flush to the spine
                y = ye + (285.12 - s) if up else ye
            h['origin_um'] = [L(x), L(y)]
            h['note'] = re.sub(r'; v3\.9 .*$', '', h.get('note', '')) + \
                f'; v3.9 row layout ({hd} {"odd" if odd else "even"} row), outline {s:g}^2 (v3.7q measured cells)'
            n += 1
    return n


def hgi(t):
    H = t['outline_um'][1]
    if PARAMS['HGI_MODE'][0] == 'row':
        ys = spread(H, [233.28, 285.12, 285.12, 233.28], PARAMS['HGI_RW'])
        return place_rows(t, *ys)
    rows = spread(H, [EDGE[0], EDGE[2], EDGE[4], EDGE[6]], PARAMS['HGI_YW'])
    return place_heads(t, rows)


def hg(t):
    W, H = t['outline_um']
    hs = {h['inst']: h for h in t['hard_cores']}
    ec = hs['ectl']
    area = 881.28 * 216.0                       # v3.7c planned outline area (190k um2)
    ew = L(W - 2 * 43.2)                         # full width between 43.2-um W / E bands
    eh = L(area / ew + G / 2)
    ec['outline_um'] = [ew, eh]
    if PARAMS['HG_MODE'][0] == 'row':
        ys = spread(H, [233.28, 285.12, eh, 285.12, 233.28], PARAMS['HG_RW'])
        ec['origin_um'] = [L((W - ew) / 2), ys[2]]
        ec['note'] = re.sub(r'; v3\.9 .*$', '', ec.get('note', '')) + \
            f'; v3.9 full-width service row in the spine {ew:g} x {eh:g} (same area as the v3.7c 881.28 x 216 plan)'
        return 1 + place_rows(t, ys[0], ys[1], ys[3], ys[4])
    ys = spread(H, [eh, EDGE[0], EDGE[2], EDGE[4], EDGE[6]], PARAMS['HG_YW'])
    ec['origin_um'] = [L((W - ew) / 2), ys[0]]
    ec['note'] = re.sub(r'; v3\.9 .*$', '', ec.get('note', '')) + \
        f'; v3.9 full-width service row at the bottom {ew:g} x {eh:g} (same area as the v3.7c 881.28 x 216 plan)'
    return 1 + place_heads(t, ys[1:])


def pc(t):
    W, H = t['outline_um']
    hs = {h['inst']: h for h in t['hard_cores']}
    cw, ch = hs['kvpc0']['outline_um']
    xs = spread(W, [cw, cw], PARAMS['PC_XW'])
    ys = spread(H, [ch, ch], PARAMS['PC_YW'])
    n = 0
    for k, (c, r) in dict(kvpc0=(0, 0), kvpc1=(1, 0), kvpc2=(1, 1), kvpc3=(0, 1)).items():
        if k in hs:
            hs[k]['origin_um'] = [xs[c], ys[r]]
            n += 1
    return n


def pv(t):
    W, H = t['outline_um']
    hs = {h['inst']: h for h in t['hard_cores']}
    pw, ph = 380.16, 190.08
    jw = 172.8
    xs = spread(W, [pw] * 4, PARAMS['PV_XW'])
    ys = spread(H, [ph, ph, jw, ph, ph], PARAMS['PV_YW'])
    n = 0
    for g, x in enumerate(xs):
        for k, yy in enumerate((ys[0], ys[1], ys[3], ys[4])):
            hs[f'pvg{g}_p{k}']['origin_um'] = [x, yy]
            n += 1
        j = hs.get(f'pv__u_g{g}_j')
        if j:
            j['origin_um'] = [L(x + (pw - jw) / 2), ys[2]]
            n += 1
    return n


def main():
    P = json.load(open(sys.argv[1]))
    n = 0
    for tn, t in P['partition_types'].items():
        if not t.get('hard_cores'):
            continue
        if re.match(r'kv3_hgi(_|$)', tn):
            n += hgi(t)
        elif re.match(r'kv3_hg(_|$)', tn):
            n += hg(t)
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
    P['note'] += (f' | v3.9p (KV-P8-PLAN 10-23): {n} hg/hgi/pc/pv hard cores re-placed on the widened lattice '
                  '(post_v39p.py: hg/hgi spine layout, ectl full-width service row, pc/pv spread over the full height); '
                  'pins re-assigned (core_pins_v37q.py)')
    sys.stderr.write(f'post_v39p: {n} cores re-placed\n')
    json.dump(P, sys.stdout, indent=1)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
