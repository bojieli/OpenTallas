#!/usr/bin/env python3
"""Local ROM-pair roots and compact RQR groups within the frozen tall tile outline.

The legal g3t ODB measures 950--990 um2 per pair, including its exclusive cones;
a 126.144 x 15.12 um read-gutter half provides <=52% initial fill. No data
logic, pipeline edge, hard child, macro placement, outline or data pin changes.
"""
import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build(nl=False):
    kind = 'nl' if nl else 'nk'
    old = f'qfd_tile_{kind}_rp2_g3t'
    name = f'qfd_tile_{kind}_rp2_g4t'
    top = f'qfd_tile_{kind}_rp2_g4'
    s = json.loads((ROOT / f'physical/ref_tile/{old}/spec.json').read_text())
    g = json.loads((ROOT / f'physical/ref_tile/{old}/held_grant.json').read_text())
    base_top = s['top']
    rtl = (ROOT / f'rtl/physical/{base_top}.sv').read_text()
    rtl = rtl[rtl.index('module '):].replace(base_top, top).replace('G3_ROOTS', 'G4_ROOTS')
    extra_ports = ''.join(f'    input  wire          ck_rp{i},\n' for i in range(10))
    rtl = rtl.replace('    input  wire          ck_rs,\n', extra_ports + '    input  wire          ck_rs,\n')
    for i in range(10):
        rtl = re.sub(rf'\.ck_rp{i}\(ck_r[sn]\)', f'.ck_rp{i}(ck_rp{i})', rtl)
        rtl = re.sub(rf'\.ck_rom{i}\(ck_r[sn]\)', f'.ck_rom{i}(ck_rp{i})', rtl)
    rtl = ('`timescale 1ns/1ps\n// Local ROM-pair clock roots: each raw ROM shares a root with its capture and\n'
           '// complete expansion/return pipeline. RQR north/south each has a compact root.\n'
           '// Pure clock rewiring around the unchanged rp2_45 body: zero added edges.\n' + rtl)
    (ROOT / f'rtl/physical/{top}.sv').write_text(rtl)
    regions = {'ck': copy.deepcopy(g['regions']['ck']),
               # Q-TILE45b r2: route 9d426ea6d measured post-repair RQR ownership 1227 (rn) / 1558 (rs) um2 against 931 um2
               # rows (NL fresh gate rn 1297): each RQR fence is 129.6 x 32.4 um (~4,190 um2 rows, fill <=0.37) in the col-B hole.
               'ck_rn': [[164.16, 552.96, 293.76, 585.36]],
               'ck_rs': [[164.16, 587.52, 293.76, 619.92]]}
    # Each macro's read-facing half-gutter. A 2.16 um shared-logic corridor
    # separates the halves; column gutters and outer bands also stay unfenced.
    row_gutters = {3: (639.312, 654.432), 4: (656.616, 671.736),
                   0: (808.416, 823.536), 1: (825.720, 840.840)}
    macro_by_root = {}
    for m in s['macros']:
        match = re.search(r'g_col\[([01])\]\.g_bank\[([0-4])\]', m['inst'])
        if not match:
            raise ValueError(m['inst'])
        pair, bank = map(int, match.groups())
        i = pair * 5 + bank
        y0, y1 = row_gutters[bank if bank != 2 else (0 if pair == 0 else 1)]
        x = m['at'][0]
        regions[f'ck_rp{i}'] = [[round(x - 2.16, 3), y0, round(x + 121.824 + 2.16, 3), y1]]
        macro_by_root[f'ck_rp{i}'] = m['inst']
    faces = [c for c in s['clock_cts_roots'] if c.startswith('ck_fa')]
    for c in faces:
        regions[c] = []
    # Every fence must be disjoint from every hard block halo and every other fence.
    obstacles = []
    for m in s['children'] + s['macros']:
        x, y = m['at']
        w, h = (121.824, 62.91) if 'ot_rom' in m['view'] else (47.52, 432) if 'u_node' in m['inst'] else (99.792, 140.4)
        obstacles.append([x - 5.4, y - 5.4, x + w + 5.4, y + h + 5.4])
    # Bound every complete-pair -> RQR and RQR -> core incident leg,
    # including every point of the assigned rectangles (actual routes remain required).
    def span(a, b):
        return max(abs(x-u)+abs(y-v) for x in (a[0],a[2]) for y in (a[1],a[3])
                   for u in (b[0],b[2]) for v in (b[1],b[3]))
    reach = {}
    for i in range(10):
        bank = i % 5
        target = 'ck_rs' if bank < 3 else 'ck_rn'
        reach[f'ck_rp{i}->{target}'] = round(span(regions[f'ck_rp{i}'][0], regions[target][0]), 3)
    for root in ('ck_rs', 'ck_rn'):
        reach[f'{root}->ck'] = round(span(regions[root][0], regions['ck'][0]), 3)
    assert max(reach.values()) <= 560, reach  # registered pair->RQR / RQR->core legs (Q-TILE45b r2 RQR resize)
    boxes = []
    for key, rs in regions.items():
        for box in rs:
            for other in obstacles + boxes:
                if min(box[2], other[2]) - max(box[0], other[0]) > 1e-6 and min(box[3], other[3]) - max(box[1], other[1]) > 1e-6:
                    raise ValueError(('overlap', key, box, other))
            boxes.append(box)
    pins = [copy.deepcopy(p) for p in g['pins'] if p['name'] not in ('ck_rs', 'ck_rn')]
    def pin(nm, y):
        v = round(.012 + .048 * round((y - .012) / .048), 3)
        for d in range(400):
            for at in ([v] if d == 0 else [v + d * .048, v - d * .048]):
                at = round(at, 3)
                if all(p['face'] != 'E' or abs(p['coordinate_um'] - at) >= .0959 for p in pins):
                    pins.append(dict(name=nm, face='E', layer='M4', coordinate_um=at, xy_um=[457.824, at], clock=True))
                    return
        raise ValueError(('no clock pin', nm))
    for nm in ['ck_rs', 'ck_rn'] + [f'ck_rp{i}' for i in range(10)]:
        b = regions[nm][0]
        pin(nm, (b[1] + b[3]) / 2)
    out = ROOT / f'physical/ref_tile/{name}'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'assigned_pins.tcl').write_text('# Local ROM-pair roots; all data pins and hard entries unchanged.\n' + ''.join(
        'place_pin -pin_name {%s} -layer %s -location {%.3f %.3f}\n' % (p['name'], p['layer'], *p['xy_um']) for p in pins))
    (out / 'regions.tcl').write_text('# Compact actual sink groups; unchanged timing and placement checks.\n'
        'set q45_max_sinks 15000\nset q45_boxes [dict create]\nset q45_why [dict create]\n' + ''.join(
        f'dict set q45_why {c} {{pin_anchored: fixed FIRM boundary registers}}\n' for c in faces) + ''.join(
        'dict set q45_boxes %s {%s}\n' % (k, ' '.join('{%s}' % ' '.join(map(str, b)) for b in bs)) for k, bs in regions.items())
        + 'source /src/tools/qwen_repack/localize45.tcl\n')
    clocks = ['ck', 'ck_rs', 'ck_rn'] + [f'ck_rp{i}' for i in range(10)] + faces + [f'ck_lsl{i}' for i in range(8)] + ([] if nl else ['ck_node'])
    soft = list(regions)
    assert set(clocks) == {p['name'] for p in pins if p['clock']}
    g.update(top=top, clocks=clocks, pins=pins, regions=regions,
             state='HELD local ROM-pair candidate; source, capacity and physical proof required',
             macro_clock_roots=macro_by_root, normal_edges_added=0, critical_region_span_bound_um=reach)
    (out / 'held_grant.json').write_text(json.dumps(g, indent=1) + '\n')
    s.update(name=name, top=top, clock_ports=clocks, clock_cts_roots=soft,
             io_tcl=f'physical/ref_tile/{name}/assigned_pins.tcl',
             pin_hook_before_flops=[f'physical/ref_tile/{name}/regions.tcl'],
             pre_dpl_extra=['tools/qwen_repack/reconcile_sink_owners.tcl'])
    # exact raw-ROM CTS bindings (main raw_macro_clocks): each ROM clk is a sink of its own pair root
    s['soft_root_macro_bindings'] = {inst.replace('\\', ''): {'master': 'ot_rom_4096x266_m8', 'clock_pin': 'clk', 'root': r}
                                     for r, inst in macro_by_root.items()}
    s['sources'] = [p.replace(f'{base_top}.sv', f'{top}.sv') for p in s['sources']]
    s['pins'] = {f: sorted({p['name'].split('[')[0] for p in pins if p['face'] == f}) for f in 'WENS' if any(p['face'] == f for p in pins)}
    s['required_hybrid_roots']['standard_cell_cts'] = soft
    s['structural_change'] = ('Localize ten actual ROM capture/expansion/return pipelines to their own read-facing gutter halves '
        '(each measured 950-990 um2 mapped area, 126.144x15.12 um fence, about 50-52% initial fill); each ROM clock shares '
        'its local pair root. Compact independent RQR north/south groups. Preserves tall457.92x950.4, every data pin, '
        f'all hard children and ROM placements, full arithmetic/workload and zero added edges. {len(clocks)} clock entries. '
        'Reconcile actual post-repair exclusive data/reset/output sink ownership and actual-row capacity before ordinary DPL.')
    s['slot_change_request'] = f'{name}: unchanged tall outline/data pins; source-bound {len(clocks)} clock entries and per-root phi-minus-R delivery required.'
    s['job'].update(owner='Claude:Q-TILE45b', branch='claude/qtile45-r6', tag='g4t', purpose=s['structural_change'],
        views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}', cycles_added=0)
    tag = 'g4nl' if nl else 'g4'
    marker = 'REPACKG4NL_NATIVE' if nl else 'REPACKG4_NATIVE'
    tb = f'rtl/test/tb_qwen_repack_g4{"_nl" if nl else ""}_native.sv'
    s['job']['extra_paths'] = sorted(set(s['job']['extra_paths'] + [tb, f'tools/qwen_repack/{tag}_bench.sh']))
    s['job']['benches'] = [dict(name=f'native_{tag}_{n}', cmd=f'bash tools/qwen_repack/{tag}_bench.sh {{RUN}}/bench/native_{tag}_{n} {n}',
        expect='pass' if n == 0 else 'fail', threads=8, peak_ram_gb=8, needs=['verilator'], **(
        {'pass_regex': f'^{marker}_PASS checks6399 valids2560 nonzero2560'} if n == 0 else {'fail_regex': f'{marker}_FAIL|^FAIL rph'})) for n in range(4)]
    (ROOT / f'tools/ref_tile/specs_q_tile_repack/{name}.json').write_text(json.dumps(s, indent=1) + '\n')
    print('LOCAL_PAIR_PLAN_PASS', name, len(clocks), 'entries', len(regions), 'soft roots')


if __name__ == '__main__':
    build()
    build(nl=True)
