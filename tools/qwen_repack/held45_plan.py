#!/usr/bin/env python3
"""Issue the dielead's HELD a2 clock/placement grant; no physical qualification."""
import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME = 'qfd_tile_nk_rp2_45_a2'
OUT = ROOT / 'physical/ref_tile' / NAME
# Node-less twin (48 qfd_tile_nl slots): the same outline, faces and pin coordinates; the node leaf and the
# n_a/n_b/n_y faces are absent, so ck_node and the face roots ck_fa0/ck_fa1/ck_fa3 (which own only those faces) go.
NL_NAME = 'qfd_tile_nl_rp2_45_a2'
NL_DROP_CLOCKS = ('ck_node', 'ck_fa0', 'ck_fa1', 'ck_fa3')
NL_DROP_BUSES = ('n_a', 'n_b', 'n_y')


def track(v):
    return round(.012 + .048 * round((v - .012) / .048), 3)


def build(nl=False):
    global NAME, OUT
    if nl:
        NAME = NL_NAME; OUT = ROOT / 'physical/ref_tile' / NAME
    s = json.loads((ROOT / 'tools/ref_tile/specs_q_tile_repack/qfd_tile_nk_rp1_a2.json').read_text())
    ownership = json.loads((ROOT / 'results/arch/qwen_tile_repack_2115/clock_ownership.json').read_text())
    soft = ['ck'] + ['ck_rp%d' % n for n in range(10)] + ['ck_tx%d' % n for n in range(8)] + ['ck_rqr0', 'ck_rqr1'] + ['ck_fa%d' % n for n in range(5)]
    # Every rectangle lies in actual placeable space, excluding child/macro halo.
    # Noncontiguous bank regions reserve the nearest available facing channels.
    regions = {
        'ck': [[329.832, 367.2, 435.456, 507.6]],
        'ck_rp0': [[22.464, 513, 144.288, 536.76], [2.16, 542.16, 17.064, 599.682]],
        'ck_rp5': [[313.632, 513, 435.456, 536.76], [440.856, 542.16, 455.76, 599.682]],
        'ck_rp1': [[149.688, 542.16, 228.96, 599.682], [2.16, 605.082, 17.064, 662.61]],
        'ck_rp6': [[228.96, 542.16, 308.232, 599.682], [440.856, 605.082, 455.76, 662.61]],
        'ck_rp2': [[149.688, 605.082, 228.96, 662.61], [2.16, 668.01, 17.064, 725.544]],
        'ck_rp7': [[228.96, 605.082, 308.232, 636.93], [149.688, 668.01, 162.648, 725.544]],
        'ck_rp3': [[295.272, 668.01, 308.232, 725.544], [440.856, 668.01, 455.76, 725.544], [302, 799.254, 368, 818.64]],
        'ck_rp8': [[295.272, 730.944, 308.232, 793.854], [440.856, 730.944, 455.76, 793.854], [368, 799.254, 435.456, 818.64]],
        'ck_rp4': [[2.16, 730.944, 17.064, 793.854], [22.464, 799.254, 156, 818.64]],
        'ck_rp9': [[228.96, 636.93, 308.232, 662.61], [149.688, 730.944, 162.648, 793.854]],
        'ck_rqr0': [[149.688, 513, 308.232, 536.76]],
        'ck_rqr1': [[162.648, 799.254, 296.568, 818.64]],
    }
    leaf = {}
    for c in s['children']:
        if 'g_sl[' not in c['inst']:
            continue
        n = int(c['inst'].split('g_sl[')[1].split(']')[0]); x, y = c['at']
        leaf[n] = c
        if c['orient'] == 'MY':
            box = [75.384, y, x - 5.4, y + 140.4]
        elif n in (6, 7):
            box = [x + 99.792 + 5.4, y, 455.76, y + 140.4]
        else:
            box = [x + 99.792 + 5.4, y, 324.432, y + 140.4]
        regions['ck_tx%d' % n] = [box]
    # W-face roots: abutting fences split at the midpoint between adjacent bus ranges (disjoint).
    spans = [(61.66, 160.96), (162.26, 261.56), (262.76, 362.06), (363.26, 462.56)]
    cuts = [spans[0][0] - 1.08] + [round((spans[i][1] + spans[i + 1][0]) / 2, 3) for i in range(3)] + [spans[3][1] + 1.08]
    for n in range(4):
        regions['ck_fa%d' % n] = [[2.16, cuts[n], 17.064, cuts[n + 1]]]
    # ck_fa4 owns the E-face tap/tile_id/reset captures (437.2..485.872 tap pins fill every legal
    # .096 track there), so its entry sits on the first free track just above the tap range and the
    # fence runs past it: entry inside its own fence, <=~25 um from the farthest tap capture column.
    regions['ck_fa4'] = [[440.856, 429.2, 455.76, 495.0]]
    # Input face roots (ck_fa0 n_a, ck_fa1 n_b, ck_fa4 tap/tile_id/reset): every sink is an input pin flop that
    # io_flop_at_pins fixes FIRM at its pin together with its INHOLD cells, so the root is localized by the pin
    # anchor itself.  A fence would hold only FIRM cells: gate a9a2906e0 measured GPL-0306 'no placed instances'
    # on these three regions and GPL-0304 divergence (-nan step).  They stay registered roots without a fence.
    # Output face roots (ck_fa2 t_out, ck_fa3 n_y + fy/mis) keep movable launch flops and keep their fences.
    PIN_ANCHORED = ('ck_fa0', 'ck_fa1', 'ck_fa4')
    for c in PIN_ANCHORED:
        regions[c] = []
    pins = []
    moved = {}
    def place(name, face, value, clock=False):
        val = track(value)
        # Nearest unoccupied track, with >=96nm spacing to every same-face pin.
        for delta in [0] + [d * sign for d in range(1, 300) for sign in (1, -1)]:
            at = round(val + delta * .048, 3)
            end = 820.8 if face in 'WE' else 457.92
            if not .24 < at < end - .24:
                continue
            if all(p['face'] != face or abs(p['coordinate_um'] - at) >= .0959 for p in pins):
                break
        else:
            raise ValueError('no free pin track for ' + name)
        moved[name] = round(abs(at - val), 3)
        xy = {'W': [.096, at], 'E': [457.824, at], 'N': [at, 820.704], 'S': [at, .096]}[face]
        pins.append(dict(name=name, face=face, layer='M4' if face in 'WE' else 'M5', coordinate_um=at, xy_um=xy, clock=clock))
    # Existing data face ranges and order; bind every incident pin explicitly.
    widths = {'n_a': 514, 'n_b': 514, 't_out': 514, 'n_y': 514, 'tap': 508, 'tile_id': 16, 'rst_n': 1, 'tie_lo': 1, 'tie_hi': 1}
    for face in ('W', 'E'):
        for name in s['pins'][face]:
            if name not in widths:
                continue
            lo, hi = s['pin_ranges'][name]; width = widths[name]
            step = math.floor(((hi - lo) / max(1, width - 1)) / .048 + 1e-6) * .048
            for n in range(width):
                place(name if width == 1 else f'{name}[{n}]', face, lo + n * step)
    # Hard entries remain on their physically nearest usable face; the two
    # interior ROM entries must enter from N to keep raw wire reach <163um.
    for name in s['clock_ports']:
        if name in s['clock_cts_roots']:
            continue
        face = next(f for f, names in s['pins'].items() if name in names)
        place(name, face, sum(s['pin_ranges'][name]) / 2, True)
    entries = {'ck': ('E', 400), 'ck_rqr0': ('E', 525), 'ck_rqr1': ('N', 229)}
    for n in range(5):
        lo, hi = s['pin_ranges']['n_a' if n == 0 else 'n_b' if n == 1 else 't_out' if n == 2 else 'n_y' if n == 3 else 'tap']
        entries['ck_fa%d' % n] = ('W', (lo + hi) / 2) if n < 4 else ('E', hi + 2.0)
    for n, c in leaf.items():
        entries['ck_tx%d' % n] = ('W' if c['orient'] == 'MY' else 'E', c['at'][1] + 70.2)
    for n in range(10):
        macro = next(m for m in s['macros'] if m['clock_entry']['port'] == 'ck_rom%d' % n)
        x, y = macro['at']
        # bank-pair root enters on the face nearest its macro (rom3 = g_col[0].g_bank[3] sits in the E column)
        face = 'W' if x < 100 else 'E'
        if n in (7, 9):
            assert 150 < x < 300, (n, x)
            face, y = 'N', 200 if n == 9 else 260
        else:
            y += 31.455
        entries['ck_rp%d' % n] = (face, y)
    for name in soft:
        face, val = entries[name]; place(name, face, val, True)
    assert len([p for p in pins if p['clock']]) == 45
    far = {n: d for n, d in moved.items() if n in soft and d > 2.0}
    assert not far, ('soft clock entry displaced >2 um from its planned track', far)
    for p in pins:
        if p['clock']:
            assert 20.0 < p['coordinate_um'] < (820.8 if p['face'] in 'WE' else 457.92) - 20.0, ('corner clock entry', p)
    assert len(pins) == sum(widths.values()) + 45
    # Assert all fences avoid actual hard macro/child halos and other regions.
    obstacles = []
    for m in s['children'] + s['macros']:
        x, y = m['at']; w, h = (121.824, 62.91) if 'clock_entry' in m else (47.52, 432) if 'u_node' in m['inst'] else (99.792, 140.4)
        obstacles.append([x - 5.4, y - 5.4, x + w + 5.4, y + h + 5.4])
    def overlap(a, b):
        return min(a[2], b[2]) - max(a[0], b[0]) > 1e-6 and min(a[3], b[3]) - max(a[1], b[1]) > 1e-6
    boxes = []
    for name, rects in regions.items():
        for box in rects:
            assert all(not overlap(box, obs) for obs in obstacles), (name, box, 'macro halo')
            assert all(not overlap(box, other) for owner, other in boxes if owner != name), (name, box, 'other region')
            boxes.append((name, box))
    top = 'qfd_tile_nk_rp2_45'
    ports = list(ownership['ports'])
    if nl:
        # pin coordinates are taken from the nk plan unchanged (same footprint in the die): only removal
        top = 'qfd_tile_nl_rp2_45'
        pins = [p for p in pins if p['name'] not in NL_DROP_CLOCKS and p['name'].split('[')[0] not in NL_DROP_BUSES]
        for c in NL_DROP_CLOCKS:
            regions.pop(c, None)
        soft = [c for c in soft if c not in NL_DROP_CLOCKS]
        ports = [c for c in ports if c not in NL_DROP_CLOCKS]
        s['children'] = [c for c in s['children'] if 'u_node' not in c['inst']]
        s['required_hybrid_roots']['hard_child_entry'].pop('ck_node', None)
        assert len(ports) == 41 and len([p for p in pins if p['clock']]) == 41 and len(soft) == 23
        assert len(pins) == 41 + 514 + 508 + 16 + 3
    OUT.mkdir(parents=True, exist_ok=True)
    grant = dict(schema='qwen.tile.held_machine_grant.v1', state='HELD structural candidate; physical proof required', issuer='Q-TILE45 (Claude) from Codex Qwen dielead draft under root authorization 2026-10-15', home_um=[457.92, 820.8], top=top, normal_edges_added=0, clocks=ports, pins=pins, regions=regions, checks=dict(all_signal_pins_explicit=True, **{'all%d_clock_pins' % len(ports): True}, actual_track_phase_um=.012, track_pitch_um=.048, minimum_same_face_center_spacing_um=.096, fences_exclude_actual_macro_and_child_5p4um_halos=True, disjoint_root_fences=True), pending=['Actual mapped FF/exclusive-comb area and <60% per-region capacity', 'Actual pin PG access, CTS, route, TT>=0 FF>=0 DRC0', 'Native launch<=220 capture<=190 spread<=80 and phi-R per entry', ownership['die_clock_obligation']])
    (OUT / 'held_grant.json').write_text(json.dumps(grant, indent=1) + '\n')
    (OUT / 'assigned_pins.tcl').write_text('# HELD machine grant: all data and clock pins on actual routing tracks.\n' + ''.join('place_pin -pin_name {%s} -layer %s -location {%.3f %.3f}\n' % (p['name'], p['layer'], *p['xy_um']) for p in pins))
    (OUT / 'regions.tcl').write_text('# HELD geometry only. No timing exceptions.\nset q45_boxes [dict create]\n' + ''.join('dict set q45_boxes %s {%s}\n' % (name, ' '.join('{%s}' % ' '.join(map(str, b)) for b in rects)) for name, rects in regions.items()) + 'source /src/tools/qwen_repack/localize45.tcl\n')
    s.update(name=NAME, top=top, clock_ports=ports, clock_cts_roots=soft, recipe=3, io_tcl=f'physical/ref_tile/{NAME}/assigned_pins.tcl', pin_hook_before_flops=[f'physical/ref_tile/{NAME}/regions.tcl'])
    s['required_hybrid_roots']['standard_cell_cts'] = soft
    s['sources'] = [p.replace('rtl/physical/qfd_tile_nk_rp1.sv', 'rtl/physical/%s.sv' % top) for p in s['sources']]
    s['pins'] = {f: sorted(set(p['name'].split('[')[0] for p in pins if p['face'] == f)) for f in 'WENS' if any(p['face'] == f for p in pins)}
    s.pop('pin_ranges', None)
    s['structural_change'] = 'HELD45-clock structural successor to measured unqualified25-entry spread268ps: eight per-LSL TX roots, five face roots, ten bank-pair roots, two RQR roots, residual core root,19 unchanged hard entries. Actual endpoint/exclusive-comb fences and per-root area checks; all64MAC/10mappedROM/8closedLSL/node retained; normal data calendar unchanged. Same actual a2 outline and hard geometry; all incident pins assigned on .012+.048k tracks.'
    s['slot_change_request'] = 'HELD candidate machine grant in held_grant.json; existing457.92x820.8a2 home,45 clock entries. Production die contract adoption requires measured local and regional clock proof.'
    s['job'].update(owner='Claude:q_tile45', branch='claude/qtile45-2210', tag='lc45', purpose=s['structural_change'], views_to=f'physical/ref_tile/{NAME}/views', record_to=f'results/rtl/ref_tile/{NAME}', cycles_added=0)
    s['job']['extra_paths'] = ['tools/qwen_repack', 'tools/ref_tile/specs_q_tile_repack/qfd_tile_nk_rp1_a1.json', 'rtl/physical/qfd_tile_nk_rp1.sv', 'rtl/test/tb_qwen_repack45_native.sv', 'rtl/physical/ot_qwen_tile_lsl_fp1.sv', 'rtl/physical/ot_qwen_tile_node.sv', 'rtl/lib/ot_rst_relay.sv', 'physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v', 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
    s['job']['benches'] = [dict(name=f'native45_{n}', cmd=f'bash tools/qwen_repack/native45_bench.sh {{RUN}}/bench/native45_{n} {n}', expect='pass' if n == 0 else 'fail', threads=8, peak_ram_gb=8, needs=['verilator'], **({'pass_regex': '^REPACK45_NATIVE_PASS checks6399 valids2560 nonzero2560'} if n == 0 else {'fail_regex': 'REPACK45_NATIVE_FAIL|^FAIL rph'})) for n in range(4)]
    if nl:
        s['structural_change'] = ('Q-TILE45 node-less twin of qfd_tile_nk_rp2_45_a2 for the 48 qfd_tile_nl slots: NODE 0 (no node leaf, no '
                                  'n_a/n_b/n_y faces), 41 entries = the 45 minus ck_node/ck_fa0/ck_fa1/ck_fa3; same 457.92x820.8 outline, '
                                  'macro/LSL geometry, fences and pin coordinates as the nk kit; t_out TOREG on ck (same edge/value as the nk node feed-through).')
        s['slot_change_request'] = 'qfd_tile_nl slot -> 457.92 x 820.8 (same footprint as qfd_tile_nk_rp2_45_a2); 41 clock entries at the nk coordinates.'
        s['job'].update(tag='lc41', purpose=s['structural_change'])
        s['job']['extra_paths'] = [x.replace('rtl/test/tb_qwen_repack45_native.sv', 'rtl/test/tb_qwen_repack45_nl_native.sv') for x in s['job']['extra_paths']]
        s['job']['benches'] = [dict(name=f'native45nl_{n}', cmd=f'bash tools/qwen_repack/native45nl_bench.sh {{RUN}}/bench/native45nl_{n} {n}', expect='pass' if n == 0 else 'fail', threads=8, peak_ram_gb=8, needs=['verilator'], **({'pass_regex': '^REPACK45NL_NATIVE_PASS checks6399 valids2560 nonzero2560'} if n == 0 else {'fail_regex': 'REPACK45NL_NATIVE_FAIL|^FAIL rph'})) for n in range(4)]
    (ROOT / 'tools/ref_tile/specs_q_tile_repack' / (NAME + '.json')).write_text(json.dumps(s, indent=1) + '\n')
    print(f'HELD45_PLAN_PASS {NAME} pins={len(pins)} clocks{len(ports)} disjoint_regions={len(regions)} halo_overlap0')


if __name__ == '__main__':
    import sys
    build(nl='--nl' in sys.argv[1:])
