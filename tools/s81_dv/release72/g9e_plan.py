#!/usr/bin/env python3
"""S81 DIE72 G9e floorplan (STW-S81-DIE-PLAN 10-21): structural re-plan of the G9 pre-GEN plan (plan_unrouted_g9.json,
161 blocks / 819 links / 2 blockages, die 33000 x 26000 full reticle, seal 100).  Links, link classes, widths and every
block that is not listed below are unchanged; endpoints of a moved / resized block move with it (face-preserving affine
map), endpoints of the 10 wrapper slices are re-projected onto the kit pin faces/ranges.  Routing is NOT done here
(dv_route72c.py runs on the output, never hand-edited paths).

  1. slice column ORDER 1..6,0,7 -> 0..7 W->E (= the logical tier line: ot_s81sl_slice ri_w unused at column 0, ri_e at
     column 7).  G9's order put s_0 (frames f_0L/f_0R in the two W-most frame columns, SerDes lk_W*) second from the E end
     and s_4..s_6 (frames on the E side) W of the centre: every x_frame/xring/ret bundle of those slices crossed the whole
     centre channel (y 17389.4, ~20.5 kb on one line at x 17-21 mm, chan.py repeater demand 1.5-1.7x).  With 0..7 every
     bundle runs outward only; xring s_k ro_e (E) -> s_k+1 ri_w (W) is one street.
  2. the 10 die slices (9 HB=0 + s_4S HB=1) bind the parameter-free wrappers ot_s81sl_slice_c1x/c3x_k8_cap5r_w
     (claude/s81-slicep-k8c-1021 @6ff783251, kits k8c/k8e MAIN): plan masters dsdv_slice_c1x / dsdv_slice_c3x, slot =
     kit outline (c1x 1252.8 x 6868.8, c3x 1468.8 x 6868.8), endpoints on the kit faces (W: ri_w ro_w xc; E: ri_e ro_e vi vo
     bi bo rt) inside the kit pin_ranges.  Row pitch grows +129.6 per row.
  3. centre channel (lower row top -> upper row bottom) 172.8 / 86.4 -> CENTRE um (default 302.4) everywhere.
     Vertical room: gunit (950 x 1469, the only top-strip block taller than eng 1209.6) leaves the slice-column top strip
     for the free E inner column above the h10 frame f_4R01 (x 23847.04, top-aligned); eng / seqhost / bk_col stay in the
     strip above their partner columns (eng: s_6, seqhost: centre s_4, bk_col: s_1).
  4. bk_sel (dsdv_bk_sel_vmtx) slot 907.2 x 4190.4 -> 907.2 x BKSEL_H (default 4449.6), same origin (STW-S81-TOPK 19:11).
  5. seqhost slot 475.2 x 993.6 -> SEQ_W x SEQ_H (default 1080 x 1036.8: dsdv_seq_host_mux_h successor + hslot + hwin,
     S81-ELEM2-SEQ 17:30).
Checks: seal ring, >= 86.4 between every pair of bodies (blocks + blockages), every endpoint on its block face.
Usage: g9e_plan.py PLAN_UNROUTED_G9 SPEC_K8C SPEC_K8E OUT [--centre 302.4] [--top-street 129.6]
"""
import argparse, collections, copy, json
from pathlib import Path

SEAL, GAP = 100.0, 86.4
ORDER = [0, 1, 2, 3, 4, 5, 6, 7]
WRAP = {  # die instance -> (plan master, kit) ; s_4S is the only HB=1 normal slice
    **{f's_{k}{t}': ('dsdv_slice_c1x', 'c1x') for k in (1, 2, 4, 5, 6) for t in 'NS'},
    's_4S': ('dsdv_slice_c3x', 'c3x')}
# plan endpoint port class -> wrapper port (dsdv_slice master port map, G9 table)
PORT = {('xrE', 'o'): 'ro_e', ('xrE', 'i'): 'ri_w', ('xrW', 'o'): 'ro_w', ('xrW', 'i'): 'ri_e', ('vN', 'o'): 'vo',
        ('vS', 'o'): 'vo', ('vN', 'i'): 'vi', ('vS', 'i'): 'vi', ('xf', 'o'): 'xc', ('ret', 'i'): 'rt', ('q', 'o'): 'bo',
        ('pv', 'i'): 'bi'}


def kit_faces(spec):
    face = {p: f for f, ps in spec['pins'].items() for p in ps}
    return face, spec['pin_ranges'], (spec['outline']['w'], spec['outline']['h'])


def main():
    a = argparse.ArgumentParser(); a.add_argument('plan'); a.add_argument('k8c'); a.add_argument('k8e'); a.add_argument('out')
    a.add_argument('--centre', type=float, default=302.4); a.add_argument('--top-street', type=float, default=129.6)
    a.add_argument('--east-frame-relief', action='store_true', help='move f_4R01 to the free East inner slot, opening the measured6.016um throat')
    a.add_argument('--east-service-strip', action='store_true', help='move eng/seqhost/bk_col into the free east inner column; releases the top strip for a wider center')
    a.add_argument('--bksel-h', type=float, default=4536.0); a.add_argument('--seq', type=float, nargs=2, default=[1080.0, 1036.8])
    a.add_argument('--streets', type=float, nargs=7, default=[172.8, 129.6, 129.6, 129.6, 129.6, 129.6, 172.8])
    v = a.parse_args()
    p = json.load(open(v.plan)); old = copy.deepcopy(p['blocks'])
    W, H = p['facts']['die_um']
    kits = {'c1x': kit_faces(json.load(open(v.k8c))), 'c3x': kit_faces(json.load(open(v.k8e)))}
    by = {b['name']: b for b in p['blocks']}
    # ---------------- slice row: column order, widths, row heights, centre channel
    lower = {k: by[f's_{k}{"S" if k in (0, 7) else "N"}'] for k in range(8)}   # G9: s_0S/s_7S + s_1N..s_6N in the lower row
    upper = {k: by[f's_{k}{"N" if k in (0, 7) else "S"}'] for k in range(8)}
    y_lo = lower[1]['y']; assert all(abs(b['y'] - y_lo) < 1e-3 for b in lower.values())
    x0 = min(b['x'] for b in lower.values()); x_end = max(b['x'] + b['w'] for b in lower.values())
    for b in list(lower.values()) + list(upper.values()):
        if b['name'] in WRAP:
            b['master'], kit = WRAP[b['name']]; b['w'], b['h'] = kits[kit][2]
            b['scope'] = f'G9e: parameter-free k8_cap5r wrapper ({kit}, kit outline {b["w"]} x {b["h"]}, 10 regional clocks)'
    colw = {k: max(lower[k]['w'], upper[k]['w']) for k in range(8)}
    x = x0; colx = {}
    for i, k in enumerate(ORDER):
        colx[k] = x; x += colw[k] + (v.streets[i] if i < 7 else 0)
    assert x <= x_end + 1e-3, ('slice row wider than the G9 row', x, x_end)
    lo_top = max(lower[k]['y'] + lower[k]['h'] for k in range(8))
    y_up = round(lo_top + v.centre, 4)
    for k in range(8):
        lower[k]['x'] = round(colx[k], 4); upper[k]['x'] = round(colx[k], 4); upper[k]['y'] = y_up
    up_top = max(b['y'] + b['h'] for b in upper.values())
    # ---------------- top strip (eng / seqhost / bk_col) + gunit to the E inner column
    strip_y = round(up_top + v.top_street, 4)
    by['seqhost']['w'], by['seqhost']['h'] = v.seq
    by['seqhost']['scope'] = 'G9e: slot 1080 x 1036.8 for the dsdv_seq_host_mux_h successor (S81-ELEM2-SEQ 17:30)'
    for n, k in (('bk_col', 1), ('seqhost', 4), ('eng', 6)):
        by[n]['x'] = round(colx[k], 4); by[n]['y'] = strip_y
    f4 = by['f_4R01']; g = by['gunit']
    g['x'] = f4['x']; g['y'] = round(H - SEAL - g['h'], 4)
    g['scope'] = 'G9e: E inner column above h10 frame f_4R01 (frees the slice-column top strip for the centre channel)'
    assert not (v.east_frame_relief and v.east_service_strip), 'East slot cannot hold both relocation choices'
    if v.east_frame_relief:
        f4['y'] = round(f4['y'] + f4['h'] + GAP, 4)
        f4['scope'] = 'G9e capacity successor: move intact f_4R01 north into free East slot; open its former East throat'
    if v.east_service_strip:
        y = round(f4['y'] + f4['h'] + GAP, 4)
        for name in ('eng', 'seqhost', 'bk_col'):
            b = by[name]; b['x'] = f4['x']; b['y'] = y
            b['scope'] = 'G9e wide FB: existing body in east inner column; top strip released without shrinking'
            y = round(y + b['h'] + GAP, 4)
        assert y <= g['y'] + 1e-3, ('east service strip exceeds the gap below gunit', y, g['y'])

    by['bk_sel']['h'] = v.bksel_h
    by['bk_sel']['scope'] = f'G9e: dsdv_bk_sel_vmtx successor slot 907.2 x {v.bksel_h} (STW-S81-TOPK 19:11)'
    # ---------------- endpoints
    ob = {b['name']: b for b in old}
    eps = collections.defaultdict(list)
    for l in p['links']:
        for j, (e, f) in enumerate(zip(l['e'], l['endpoint_faces'])):
            eps[p['blocks'][e[0]]['name']].append((l, j))
    moved = 0
    for n, b in by.items():
        o = ob[n]
        if all(abs(o[k] - b[k]) < 1e-9 for k in 'xywh'):
            continue
        moved += 1
        if n in WRAP:
            face, rng, _ = kits[WRAP[n][1]]
            grp = collections.defaultdict(list)
            for l, j in eps[n]:
                e = l['e'][j]; d = 'o' if j == 0 else 'i'
                port = PORT[(e[1], d)]; grp[port].append((l, j))
            for port, lst in grp.items():
                f = face[port]; lo, hi = rng[port]; lst.sort(key=lambda t: t[0]['i'])
                for m, (l, j) in enumerate(lst):
                    yy = lo + (m + 0.5) * (hi - lo) / len(lst)
                    l['e'][j][2] = round(b['x'] + (b['w'] if f == 'E' else 0.0), 4)
                    l['e'][j][3] = round(b['y'] + yy, 4)
                    l['endpoint_faces'][j] = f
            continue
        for l, j in eps[n]:
            e = l['e'][j]
            e[2] = round(b['x'] + (e[2] - o['x']) * (b['w'] / o['w']), 4)
            e[3] = round(b['y'] + (e[3] - o['y']) * (b['h'] / o['h']), 4)
    # ---------------- checks
    for l in p['links']:
        for e, f in zip(l['e'], l['endpoint_faces']):
            b = p['blocks'][e[0]]
            assert {'W': abs(e[2] - b['x']) < 1e-3, 'E': abs(e[2] - b['x'] - b['w']) < 1e-3, 'S': abs(e[3] - b['y']) < 1e-3,
                    'N': abs(e[3] - b['y'] - b['h']) < 1e-3}[f], (l['i'], e, f)
            assert b['x'] - 1e-3 <= e[2] <= b['x'] + b['w'] + 1e-3 and b['y'] - 1e-3 <= e[3] <= b['y'] + b['h'] + 1e-3, (l['i'], e)
    allr = p['blocks'] + p.get('blockages', [])
    for b in allr:
        assert min(b['x'], b['y']) >= SEAL - 1e-6 and b['x'] + b['w'] <= W - SEAL + 1e-6 and b['y'] + b['h'] <= H - SEAL + 1e-6, b['name']
    seps = {}
    for i, b in enumerate(allr):
        for c in allr[i + 1:]:
            sep = max(c['x'] - (b['x'] + b['w']), b['x'] - (c['x'] + c['w']), c['y'] - (b['y'] + b['h']), b['y'] - (c['y'] + c['h']))
            assert sep >= GAP - 0.25, (b['name'], c['name'], round(sep, 3))
            seps[(b['name'], c['name'])] = sep
    centre = round(y_up - lo_top, 3)
    ch = dict(order_w_to_e=[f's_{k}' for k in ORDER], column_x={f's_{k}': round(colx[k], 3) for k in ORDER},
              column_w={f's_{k}': colw[k] for k in ORDER}, streets_um=v.streets, centre_channel_um=centre,
              lower_row_y=y_lo, upper_row_y=y_up, top_strip_y=strip_y, top_street_um=v.top_street,
              wrappers={n: w[0] for n, w in sorted(WRAP.items())}, wrapper_ref='claude/s81-slicep-k8c-1021 6ff783251 (k8c / k8e)',
              east_frame_relief=v.east_frame_relief, east_service_strip=v.east_service_strip, gunit=[g['x'], g['y']], bk_sel=[by['bk_sel'][k] for k in 'xywh'], seqhost=[by['seqhost'][k] for k in 'xywh'],
              moved_or_resized=moved, row_right_edge=round(x, 3), row_right_limit=x_end)
    p['facts']['physical72']['g9e'] = ch
    p['facts']['physical72']['routing'] = 'G9e unrouted: dv_route72c.py required'
    for k in ('routing_failures', 'grid', 'relay_station_count'):
        p['facts']['physical72'].pop(k, None)
    for l in p['links']:
        for k in ('h', 'sp', 's', 'L', 'station_dirs'):
            l.pop(k, None)
    Path(v.out).write_text(json.dumps(p, indent=1))
    print('G9E_PLAN', json.dumps(ch))


if __name__ == '__main__':
    main()
