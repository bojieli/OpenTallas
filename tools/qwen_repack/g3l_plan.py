#!/usr/bin/env python3
"""Q-TILE45 r6 g3L: the 3-soft-root tile (g3_plan.py) on a LARGER outline (owner 07:30 10-16: grow the slot rather
than tune; die area is not the constraint; 64 lanes kept).

Outline 522.72 x 907.2 um (was 457.92 x 820.8): +43.2 um W pin-face glue band (every hard block shifts +43.2 um,
one child lattice step), +21.6 um E band, and two 43.2 um ROM read gutters.  The ROM rows pair face to face
(MX below / R0 above) across each gutter, so every ROM's read pins open into a gutter:
  gutter 1 (rows 1|2): A1 A2 C1 C2  -> north group banks 3-4 (ck_rn), with the col-B hole below it
  gutter 2 (rows 3|4): A3 A4 B3 B4 C3 C4 -> south group banks 0-2 (ck_rs), with the 39 um N band above it
Same RTL top (qfd_tile_n[kl]_rp2_g3), data pins, cycles; clock entries as g3.
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g3_plan as G  # noqa: E402

ROOT = G.ROOT
W, H = 522.72, 907.2
DX = 43.2
GUT = 43.2
COLX = {'A': 22.464 + DX, 'B': 168.048 + DX, 'C': 313.632 + DX}
R1 = 527.80
# (column, row) -> (pair p, bank b, orient)
SLOTS = {
    ('A', 1): (0, 3, 'MX'), ('C', 1): (1, 3, 'MX'),
    ('A', 2): (0, 4, 'R0'), ('C', 2): (1, 4, 'R0'),
    ('A', 3): (0, 0, 'MX'), ('C', 3): (1, 0, 'MX'),
    ('A', 4): (0, 1, 'R0'), ('C', 4): (1, 1, 'R0'),
    ('B', 3): (0, 2, 'MX'), ('B', 4): (1, 2, 'R0'),
}


VARIANTS = {'l': dict(W=522.72, H=907.2, DX=43.2, R1=527.80), 't': dict(W=457.92, H=950.4, DX=0.0, R1=571.00)}


def build(nl, v='l'):
    global W, H, DX, R1, COLX
    W, H, DX, R1 = (VARIANTS[v][k] for k in ('W', 'H', 'DX', 'R1'))
    COLX = {'A': 22.464 + DX, 'B': 168.048 + DX, 'C': 313.632 + DX}
    src = 'qfd_tile_nl_rp2_g3' if nl else 'qfd_tile_nk_rp2_g3'
    name = src + v
    s = json.loads((ROOT / 'tools/ref_tile/specs_q_tile_repack' / (src + '.json')).read_text())
    grant = json.loads((ROOT / 'physical/ref_tile' / src / 'held_grant.json').read_text())
    tm = G.rom_tm()
    view = s['macros'][0]['view']
    # rows: r1, r2 = r1 + H + gutter, r3 abutted, r4 = r3 + H + gutter (each on track)
    rows = {}
    macros = []
    lo = round(R1 * 1000)
    for row in (1, 2, 3, 4):
        ys = []
        for col in 'ABC':
            if (col, row) not in SLOTS:
                continue
            p, b, orient = SLOTS[(col, row)]
            y = G.on_track_y(tm, orient, COLX[col], lo, lo, lo + 3000)
            assert y is not None, (col, row)
            ys.append(y)
            macros.append(dict(view=view, count=1, inst=f'u_g.u_tile.u_tile.g_col[{p}].g_bank[{b}].u_rom',
                               at=[round(COLX[col], 3), round(y / 1000, 3)], at_exact=True, orient=orient))
        rows[row] = max(ys) / 1000
        lo = round((rows[row] + G.ROM_H + (GUT if row in (1, 3) else .024)) * 1000)
    s['macros'] = macros
    for c in s['children']:
        c['at'] = [round(c['at'][0] + DX, 3), c['at'][1]]
    top_rom = rows[4] + G.ROM_H
    assert top_rom + G.HALO + 20 < H, top_rom
    xa1 = COLX['A'] + G.ROM_W + G.HALO          # col A east halo
    xc0 = COLX['C'] - G.HALO                    # col C west halo
    g1 = [round(COLX['A'] - G.HALO, 3), round(rows[1] + G.ROM_H + G.HALO, 3), round(COLX['C'] + G.ROM_W + G.HALO, 3), round(rows[2] - G.HALO, 3)]
    g2 = [round(COLX['A'] - G.HALO, 3), round(rows[3] + G.ROM_H + G.HALO, 3), round(COLX['C'] + G.ROM_W + G.HALO, 3), round(rows[4] - G.HALO, 3)]
    hole = [round(xa1, 3), round(507.6 + G.HALO, 3), round(xc0, 3), round(rows[3] - G.HALO, 3)]
    nband = [round(COLX['A'], 3), round(top_rom + G.HALO, 3), round(COLX['C'] + G.ROM_W, 3), round(H - 2.16, 3)]
    # gutters are 43.2 - 2 x 5.4 halo = 32.4 um placeable; the hole joins gutter 1 (disjoint rectangles)
    regions = {
        'ck_rn': [hole, [g1[0], g1[1], hole[0], g1[3]], [hole[2], g1[1], g1[2], g1[3]]],
        'ck_rs': [g2, nband],
        'ck': [[round(335.016 + DX, 3), 342.6, round(435.456 + DX, 3), round(R1 - 20.0, 3) if not DX else 507.6]],
    }
    faces = [c for c in s['clock_cts_roots'] if c.startswith('ck_fa')]
    for f in faces:
        regions[f] = []
    why = {f: 'pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins' for f in faces}
    obstacles = []
    for m in s['children'] + s['macros']:
        x, y = m['at']
        w, h = (G.ROM_W, G.ROM_H) if 'ot_rom' in m['view'] else (47.52, 432) if 'u_node' in m['inst'] else (99.792, 140.4)
        obstacles.append([x - G.HALO, y - G.HALO, x + w + G.HALO, y + h + G.HALO])
    boxes = []
    for nm, rects in regions.items():
        for b in rects:
            for o in obstacles:
                assert not (min(b[2], o[2]) - max(b[0], o[0]) > 1e-6 and min(b[3], o[3]) - max(b[1], o[1]) > 1e-6), (nm, b, o)
            for on, ob in boxes:
                assert not (min(b[2], ob[2]) - max(b[0], ob[0]) > 1e-6 and min(b[3], ob[3]) - max(b[1], ob[1]) > 1e-6), (nm, b, on, ob)
            boxes.append((nm, b))
    # pins: data + face/hard clocks keep their y on W/E (E moves to the new edge); soft entries re-planned
    pins = []
    for p in grant['pins']:
        if p['clock'] and p['name'] in ('ck', 'ck_rs', 'ck_rn'):
            continue
        p = copy.deepcopy(p)
        if p['face'] == 'E':
            p['xy_um'] = [round(W - .096, 3), p['xy_um'][1]]
        elif p['face'] == 'N':
            p['xy_um'] = [round(p['xy_um'][0] + DX, 3), round(H - .096, 3)]; p['coordinate_um'] = p['xy_um'][0]
        pins.append(p)

    def place(nm, face, v):
        v = G.track(v)
        for d in range(0, 400):
            for at in ((v + d * .048), (v - d * .048)) if d else (v,):
                at = round(at, 3)
                if all(q['face'] != face or abs(q['coordinate_um'] - at) >= .0959 for q in pins):
                    xy = {'W': [.096, at], 'E': [round(W - .096, 3), at], 'N': [at, round(H - .096, 3)]}[face]
                    pins.append(dict(name=nm, face=face, layer='M4' if face in 'WE' else 'M5', coordinate_um=at, xy_um=xy, clock=True))
                    return
        raise ValueError(nm)
    place('ck', 'E', 425.0)
    place('ck_rn', 'E', (g1[1] + g1[3]) / 2)
    place('ck_rs', 'E', (g2[1] + g2[3]) / 2)
    out = ROOT / 'physical/ref_tile' / name
    out.mkdir(parents=True, exist_ok=True)
    (out / 'assigned_pins.tcl').write_text(f'# Q-TILE45 r6 g3{v.upper()}: {W} x {H}; data pins as a2 (E face on the new edge); soft entries at their fences.\n'
                                          + ''.join('place_pin -pin_name {%s} -layer %s -location {%.3f %.3f}\n' % (p['name'], p['layer'], *p['xy_um']) for p in pins))
    (out / 'regions.tcl').write_text('# Q-TILE45 r6 g3L fences. No timing exceptions.\nset q45_max_sinks 15000\nset q45_boxes [dict create]\nset q45_why [dict create]\n'
                                     + ''.join('dict set q45_why %s {%s}\n' % (c, w) for c, w in why.items())
                                     + ''.join('dict set q45_boxes %s {%s}\n' % (n, ' '.join('{%s}' % ' '.join(map(str, b)) for b in r)) for n, r in regions.items())
                                     + 'source /src/tools/qwen_repack/localize45.tcl\n')
    g = dict(grant, state=f'HELD structural candidate (Q-TILE45 r6 g3{v.upper()} {W}x{H}); physical proof required', home_um=[W, H],
             pins=pins, regions=regions, rom_rows=[[m['inst'], m['at'], m['orient']] for m in macros])
    (out / 'held_grant.json').write_text(json.dumps(g, indent=1) + '\n')
    s['name'] = name
    s['outline'] = dict(w=W, h=H, exact=True)
    s['io_tcl'] = f'physical/ref_tile/{name}/assigned_pins.tcl'
    s['pin_hook_before_flops'] = [f'physical/ref_tile/{name}/regions.tcl']
    s['pins'] = {f: sorted(set(p['name'].split('[')[0] for p in pins if p['face'] == f)) for f in 'WENS' if any(p['face'] == f for p in pins)}
    s['structural_change'] = s['structural_change'].replace('Same outline', (f'Outline {W} x {H} (' + ('W +43.2 glue band, E +21.6, ' if DX else '43.2 um glue band above the LSL row, ') + 'two 43.2 um ROM read gutters: every ROM face opens into a gutter; north group gutter 1 + col-B hole, south group gutter 2 + N band); same'))
    s['slot_change_request'] = s['slot_change_request'].replace('keeps 457.92 x 820.8 and its data pins', f'-> {W} x {H} (owner 07:30 grow-to-close), data pins same y, E face on the new edge')
    s['job'].update(views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}', purpose=s['structural_change'], tag='g3'+v)
    (ROOT / 'tools/ref_tile/specs_q_tile_repack' / (name + '.json')).write_text(json.dumps(s, indent=1) + '\n')
    print(f'G3L_PLAN_PASS {name} {W}x{H} rows={rows} regions={json.dumps(regions)}')


if __name__ == '__main__':
    build(nl='--nl' in sys.argv[1:], v='t' if '--tall' in sys.argv[1:] else 'l')
