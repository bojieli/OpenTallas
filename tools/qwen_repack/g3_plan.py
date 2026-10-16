#!/usr/bin/env python3
"""Q-TILE45 r6: 3-soft-root re-partition of the repacked Qwen compute tile (NK and its node-less twin NL).

Measured motive (E1/E2 on the r5 placed ODB, results/arch/qwen_tile_repack_2115/r6_e1):
  * 26 soft roots on the r5 placement: rp/tx roots spread 70-362 ps (relay stages wander), CTS knobs change nothing;
  * every ROM was its own die entry: 150 ps cross-entry setup reserve on top of the 590 ps ROM clk->q failed the ROM
    capture at TT (1032 endpoints, -151 ps); ROM clock pins on their bank root remove that class entirely.
Structure (same outline 457.92 x 820.8, same data pins, same RTL body, 0 cycles):
  ck    core control + 8 TX relay banks, fenced next to the core (TX -> LSL is the long, cross-entry hop)
  ck_rs south bank group (banks 0..2): 6 ROM clock pins + pair pipelines + RQR south, fenced in the col-B hole
  ck_rn north bank group (banks 3..4): 4 ROM clock pins + pair pipelines + RQR north, fenced in the widened N band
  face roots and the LSL/node hard entries unchanged.
ROM rows move down ~14 um (20 um channel to the LSL row kept; N band grows 19 -> ~34 um); the north row turns to face the N band.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'ref_tile'))
sys.path.insert(0, str(ROOT / 'tools'))
import check_macro_track_alignment as cmta  # noqa: E402

ROM_VIEW = 'physical/asap7_memory_macros/ot_rom_4096x266_m8'
ROM_W, ROM_H = 121.824, 62.91
HALO = 5.4
OLD_ROW = {542.16: 0, 605.082: 1, 668.01: 2, 730.944: 3}
TARGET_ROW = [527.80, 590.74, 653.68, 716.62]   # ROM bottom >= LSL top 507.7 + 20 um channel rule
FACE_UP = {'R0': 'MX', 'MY': 'R180', 'MX': 'MX', 'R180': 'R180'}
SOUTH_BANKS = (0, 1, 2)          # RTL SB = (CODE_BANKS + 1) / 2


def rom_tm():
    ms = cmta.parse_lef((ROOT / ROM_VIEW / 'ot_rom_4096x266_m8.lef').read_text())
    return next(m for m in ms if m['name'] == 'ot_rom_4096x266_m8')


def on_track_y(tm, orient, x, y, lo, hi):
    """first y in [lo, hi] (nm steps from y outward) that puts every ROM pin on track at x"""
    best = None
    for d in range(0, 4000):
        for yy in ((y + d), (y - d)) if d else (y,):
            if not lo <= yy <= hi:
                continue
            r = cmta.check_placement(tm, orient, round(x * 1000), yy)
            if sum(v['offtrack'] for v in r['layers'].values()) == 0:
                return yy
    return best


def track(v):
    return round(.012 + .048 * round((v - .012) / .048), 3)


def build(nl):
    src_name = 'qfd_tile_nl_rp2_45_a2' if nl else 'qfd_tile_nk_rp2_45_a2'
    name = 'qfd_tile_nl_rp2_g3' if nl else 'qfd_tile_nk_rp2_g3'
    top = name
    s = json.loads((ROOT / 'physical/ref_tile' / src_name / 'spec.json').read_text())
    grant = json.loads((ROOT / 'physical/ref_tile' / src_name / 'held_grant.json').read_text())
    faces = ['ck_fa2', 'ck_fa4'] if nl else ['ck_fa0', 'ck_fa1', 'ck_fa2', 'ck_fa3', 'ck_fa4']
    hard = ['ck_lsl%d' % i for i in range(8)] + ([] if nl else ['ck_node'])
    soft = ['ck', 'ck_rs', 'ck_rn'] + faces
    ports = soft[:3] + faces + hard
    tm = rom_tm()
    # ---- ROM macros: rows down, north row faces up, clock pins on their group root ------------------------------
    macros = []
    ytop = None
    for m in s['macros']:
        m = copy.deepcopy(m)
        row = OLD_ROW[m['at'][1]]
        k = int(m['clock_entry']['port'][len('ck_rom'):])
        bank = k % 5
        m.pop('clock_entry')
        m['inst'] = 'u_g.' + m['inst']
        if row == 3:
            m['orient'] = FACE_UP[m['orient']]
        y0 = round(TARGET_ROW[row] * 1000)
        lo = y0 if row == 0 else None
        macros.append((row, m, y0, bank))
    # rows in order: each row on track, abutted pitch >= ROM_H + 0.024 above the previous row
    placed = []
    prev = {}
    for row in range(4):
        for r, m, y0, bank in [t for t in macros if t[0] == row]:
            x = m['at'][0]
            below = prev.get(x)
            lo_nm = round((below + ROM_H + .024) * 1000) if below is not None else y0 - 600
            y = on_track_y(tm, m['orient'], x, max(y0, lo_nm), lo_nm, lo_nm + 3000)
            assert y is not None, (m['inst'], row)
            m['at'] = [x, round(y / 1000, 3)]
            m['at_exact'] = True
            prev[x] = m['at'][1]
            placed.append((m, bank))
    ytop = max(m['at'][1] for m, _ in placed) + ROM_H
    ybot = min(m['at'][1] for m, _ in placed)
    s['macros'] = [m for m, _ in placed]
    for c in s['children']:
        c['inst'] = 'u_g.' + c['inst']
    # ---- fences (exclusive regions: root registers + exclusive fan-in cones, via localize45.tcl) ------------------
    hole_x0, hole_x1 = 22.464 + ROM_W + HALO, 313.632 - HALO
    col_b = [m['at'][1] for m, _ in placed if abs(m['at'][0] - 168.048) < .01]
    hole_y0, hole_y1 = 507.6 + HALO, min(col_b) - HALO
    regions = {
        'ck_rs': [[round(hole_x0, 3), round(hole_y0, 3), round(hole_x1, 3), round(hole_y1, 3)]],
        'ck_rn': [[22.464, round(ytop + HALO, 3), 435.456, 818.64]],
        'ck': [[335.016, 342.6, 435.456, 507.6]],
    }
    why = {f: 'pin_anchored: every sink is a pin flop fixed FIRM at its pin by io_flop_at_pins' for f in faces}
    for f in faces:
        regions[f] = []
    # ---- pins: data pins unchanged; clock entries re-planned -------------------------------------------------------
    keep = [p for p in grant['pins'] if not (p['clock'] and p['name'] not in faces + hard)]
    used = {(p['face'], p['coordinate_um']) for p in keep}

    def place(nm, face, v):
        v = track(v)
        for d in range(0, 400):
            for at in ((v + d * .048), (v - d * .048)) if d else (v,):
                at = round(at, 3)
                if all(p['face'] != face or abs(p['coordinate_um'] - at) >= .0959 for p in keep):
                    xy = {'W': [.096, at], 'E': [457.824, at], 'N': [at, 820.704], 'S': [at, .096]}[face]
                    keep.append(dict(name=nm, face=face, layer='M4' if face in 'WE' else 'M5', coordinate_um=at, xy_um=xy, clock=True))
                    return at
        raise ValueError(nm)
    place('ck', 'E', 425.0)                                   # mid-height of the core fence (E side)
    place('ck_rs', 'E', (hole_y0 + hole_y1) / 2)              # hole centre height, E face (W face is the node/face side)
    place('ck_rn', 'N', 229.0)                                # N band centre
    pins = keep
    assert sum(1 for p in pins if p['clock']) == len(ports), (len(ports), sum(1 for p in pins if p['clock']))
    # fences avoid macro/child halos and each other
    obstacles = []
    for m in s['children'] + s['macros']:
        x, y = m['at']
        w, h = (ROM_W, ROM_H) if 'ot_rom' in m['view'] else (47.52, 432) if 'u_node' in m['inst'] else (99.792, 140.4)
        obstacles.append([x - HALO, y - HALO, x + w + HALO, y + h + HALO])
    for nm, rects in regions.items():
        for b in rects:
            for o in obstacles:
                assert not (min(b[2], o[2]) - max(b[0], o[0]) > 1e-6 and min(b[3], o[3]) - max(b[1], o[1]) > 1e-6), (nm, b, o)
    out = ROOT / 'physical/ref_tile' / name
    out.mkdir(parents=True, exist_ok=True)
    (out / 'assigned_pins.tcl').write_text('# Q-TILE45 r6 g3: data pins as the a2 grant; clock entries re-planned (3 soft + faces + hard).\n'
                                          + ''.join('place_pin -pin_name {%s} -layer %s -location {%.3f %.3f}\n' % (p['name'], p['layer'], *p['xy_um']) for p in pins))
    (out / 'regions.tcl').write_text('# Q-TILE45 r6 g3 fences. No timing exceptions.\nset q45_max_sinks 15000\nset q45_boxes [dict create]\nset q45_why [dict create]\n'
                                     + ''.join('dict set q45_why %s {%s}\n' % (c, w) for c, w in why.items())
                                     + ''.join('dict set q45_boxes %s {%s}\n' % (n, ' '.join('{%s}' % ' '.join(map(str, b)) for b in r)) for n, r in regions.items())
                                     + 'source /src/tools/qwen_repack/localize45.tcl\n')
    g = dict(schema='qwen.tile.held_machine_grant.v1', state='HELD structural candidate (Q-TILE45 r6 g3); physical proof required',
             home_um=[457.92, 820.8], top=top, normal_edges_added=0, clocks=ports, pins=pins, regions=regions,
             rom_rows=[[m['inst'], m['at'], m['orient']] for m in s['macros']])
    (out / 'held_grant.json').write_text(json.dumps(g, indent=1) + '\n')
    s['name'] = name
    s['top'] = top
    s['clock_port'] = 'ck'
    s['clock_ports'] = ports
    s['clock_cts_roots'] = soft
    s['soft_root_macro_masters'] = ['ot_rom_4096x266_m8']
    s['required_hybrid_roots'] = dict(standard_cell_cts=soft,
                                      hard_child_entry={k: 'u_g.' + v for k, v in s['required_hybrid_roots']['hard_child_entry'].items()})
    body = 'rtl/physical/%s.sv' % ('qfd_tile_nl_rp2_45' if nl else 'qfd_tile_nk_rp2_45')
    s['sources'] = [p for p in s['sources']] + ['rtl/physical/%s.sv' % top]
    assert body in s['sources']
    s['pins'] = {f: sorted(set(p['name'].split('[')[0] for p in pins if p['face'] == f)) for f in 'WENS' if any(p['face'] == f for p in pins)}
    s['io_tcl'] = f'physical/ref_tile/{name}/assigned_pins.tcl'
    s['pin_hook_before_flops'] = [f'physical/ref_tile/{name}/regions.tcl']
    s['structural_change'] = ('Q-TILE45 r6 g3: %d clock entries (was %d): ck = core + 8 TX banks fenced at the core; ck_rs / ck_rn = '
                              'south / north ROM bank groups with their ROM clock pins (raw memory macros on the soft root, '
                              'soft_root_macro_masters), pair pipelines and RQR register, fenced in the col-B hole / widened N band; '
                              'ROM rows 23.49 um lower, north row facing N. Same outline, data pins, RTL body and cycles.'
                              % (len(ports), 41 if nl else 45))
    s['slot_change_request'] = ('%s slot keeps 457.92 x 820.8 and its data pins; clock entries change to %s (die must deliver '
                                'phi - R for %d entries per tile instead of %d).' % ('qfd_tile_nl' if nl else 'qfd_tile_nk', ' '.join(ports), len(ports), 41 if nl else 45))
    job = s['job']
    job.update(owner='Claude:q_tile45_r6', branch='claude/qtile45-r6', tag='g3', purpose=s['structural_change'],
               views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}', cycles_added=0)
    tb = 'rtl/test/tb_qwen_repack_g3%s_native.sv' % ('_nl' if nl else '')
    job['extra_paths'] = sorted(set(job['extra_paths'] + [tb, body, 'rtl/physical/qfd_tile_nk_rp1.sv', 'rtl/test/tb_qwen_repack45_nl_native.sv' if nl else 'rtl/test/tb_qwen_repack45_native.sv']))
    tag = 'g3nl' if nl else 'g3'
    marker = 'REPACKG3NL_NATIVE' if nl else 'REPACKG3_NATIVE'
    job['benches'] = [dict(name=f'native_{tag}_{n}', cmd=f'bash tools/qwen_repack/{tag}_bench.sh {{RUN}}/bench/native_{tag}_{n} {n}',
                           expect='pass' if n == 0 else 'fail', threads=8, peak_ram_gb=8, needs=['verilator'],
                           **({'pass_regex': f'^{marker}_PASS checks6399 valids2560 nonzero2560'} if n == 0 else {'fail_regex': f'{marker}_FAIL|^FAIL rph'}))
                      for n in range(4)]
    (ROOT / 'tools/ref_tile/specs_q_tile_repack' / (name + '.json')).write_text(json.dumps(s, indent=1) + '\n')
    print(f'G3_PLAN_PASS {name} ports={len(ports)} pins={len(pins)} rom_rows={sorted(set(m["at"][1] for m in s["macros"]))} '
          f'rs={regions["ck_rs"]} rn={regions["ck_rn"]} ck={regions["ck"]}')


if __name__ == '__main__':
    build(nl='--nl' in sys.argv[1:])
