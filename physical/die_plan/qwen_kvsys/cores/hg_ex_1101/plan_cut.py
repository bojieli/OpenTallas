#!/usr/bin/env python3
"""Common zero-cycle EX hard cut for the eight HG types; leaves their external ABI unchanged.

usage: plan_cut.py PLAN OUT [--hard 0,1,2,3] [--soft-master M] [--resite R.json]

Default (--hard 0,1,2,3) = the 11-01 HG-EX1101 form (4 hard EX per type).
KV-HG-SPLIT-1 11-12 (vF, cell cap): plan of record vF has landing band ft2_i/ft3_i (and monitor_0 on hg_v3) over slot 0,
so --hard 1,2,3 hardens EX 1..3 only; the EX left soft gets partition_types[T].soft_clones (kit-local renamed exact
copy, tools/die_plan/soft_clone.py) because the hard master qkd_astk_ex_s is black-boxed by name in the kit.  Every
hardened slot is checked against the type's other hard cores (+ halo), landing bands, internal stations, ft regs,
clock taps and the reset tap (fail closed).  Die clock island rects under a new core are removed from the type and
listed in --resite (die clock owner re-sites those die clock cells; the new core taps are new die clock sinks).
"""
import argparse, copy, json
from pathlib import Path
MODULE = 'qkd_astk_ex_s'
OUTLINE = [190.08, 112.32]
SLOTS = [([25.92, 561.6], 'R0'), ([371.52, 561.6], 'R0'), ([665.28, 561.6], 'MY'), ([984.96, 561.6], 'MY')]
PIN_FILE = 'pins/qkd_astk_ex_s_hg1101.json'
VIEW_DIR = 'physical/ref_tile/qkd_astk_ex_s_hg1101/views/qkd_astk_ex_s'
HALO = 4.32
# re-solvable infrastructure under a new core: reported (--resite), the reset/collector tree regen re-sites them
RESITE_KINDS = ('collector_relay',)


def inside(x, y, r, pad=0):
    a, b, w, h = r
    return a - pad <= x <= a + w + pad and b - pad <= y <= b + h + pad


def _ov(a, b, e=1e-6):
    """a, b = [x0, y0, x1, y1]; strict interior overlap"""
    return a[0] < b[2] - e and b[0] < a[2] - e and a[1] < b[3] - e and b[1] < a[3] - e


def pins():
    ps = [dict(name='ck', layer='M5', x=95.064, y=56.16), dict(name='rst_n', layer='M4', x=189.984, y=56.136)]
    ps += [dict(name=f'xa[{i}]', layer='M4', x=189.984, y=round(42.024 + .192 * i, 3)) for i in range(66)]
    ps += [dict(name=f'xe[{i}]', layer='M4', x=.096, y=round(62.088 + .192 * i, 3)) for i in range(34)]
    return dict(schema='opentallas.die_plan.core_pins.v1', core=MODULE, frame='core R0 origin(0,0),190.08x112.32',
                source='HG-EX common cut1101; exact existing xa/xe boundary; 0 added cycles',
                faces={'E': dict(pins=67, layers=['M4']), 'W': dict(pins=34, layers=['M4'])}, pins=ps)


def blockers(t, rect):
    """-> [(kind, name, rect)] plan objects a hard core at rect = [x0, y0, x1, y1] may not cover (rect incl. halo for
    other cores: their halos must not meet)"""
    out = []
    halo = [rect[0] - HALO, rect[1] - HALO, rect[2] + HALO, rect[3] + HALO]
    for h in t.get('hard_cores', []):
        x, y = h['origin_um']
        w, hh = h['outline_um']
        if h.get('orient') in ('R90', 'R270', 'MXR90', 'MYR90'):
            w, hh = hh, w
        hr = float(h.get('halo_um', 0) or 0)
        if _ov(halo, [x - hr, y - hr, x + w + hr, y + hh + hr]):
            out.append(('hard_core', h['inst'], [x, y, x + w, y + hh]))
    lc = t.get('clock', {}).get('landing_contract', {}) or {}
    for n, b in (lc.get('bands') or {}).items():
        if _ov(rect, b['rect_um']):
            out.append(('landing_band', n, b['rect_um']))
    for r in (lc.get('collector_tree') or {}).get('relays', []) or []:
        x, y = r['xy']
        if _ov(rect, [x - .5, y - .5, x + .5, y + .5]):
            out.append(('collector_relay', r.get('name', ''), [x, y, x, y]))
    for s in t.get('internal_stations', []) or []:
        for r in s.get('regs_um', []):
            if _ov(rect, [r[0] - .5, r[1] - .5, r[0] + .5, r[1] + .5]):
                out.append(('internal_station', s.get('name', ''), r))
    for f in t.get('ft_slots', []) or []:
        for r in f.get('regs_um', []) or []:
            if _ov(rect, [r[0] - .5, r[1] - .5, r[0] + .5, r[1] + .5]):
                out.append(('ft_reg', f.get('name', ''), r))
    for tp in t.get('clock', {}).get('taps', []) or []:
        x, y = tp['xy']
        if _ov(rect, [x - .5, y - .5, x + .5, y + .5]):
            out.append(('clock_tap', tp['name'], [x, y, x, y]))
    rt = (t.get('reset') or {}).get('tap_um')
    if rt and _ov(rect, [rt[0] - .5, rt[1] - .5, rt[0] + .5, rt[1] + .5]):
        out.append(('reset_tap', 'reset', rt))
    return out


def apply(p, hard=(0, 1, 2, 3), soft_master=None):
    """-> (plan, types, resite rows)"""
    p = copy.deepcopy(p)
    types, resite = [], []
    hard = sorted(set(hard))
    if not hard or any(k not in range(4) for k in hard):
        raise ValueError(f'--hard {hard}: EX indices 0..3')
    if len(hard) < 4 and not soft_master:
        raise ValueError('EX kept soft next to a hard qkd_astk_ex_s needs --soft-master (kit black-boxes by name)')
    for tn, t in p['partition_types'].items():
        leaves = [c for c in t.get('contents', []) if c.get('module') == MODULE]
        if not leaves:
            continue
        assert len(leaves) == 4, (tn, len(leaves))
        types.append(tn)
        assert not any(h['module'] == MODULE for h in t.get('hard_cores', [])), f'already cut: {tn}'
        rects, new = [], []
        for k, c in enumerate(leaves):
            inst = c['inst']
            physical = 'u_bound.u_' + inst.replace('__', '_')
            if k not in hard:
                t.setdefault('soft_clones', []).append(dict(physical_inst=physical, base=MODULE, master=soft_master))
                continue
            xy, orient = SLOTS[k]
            o = [round(int((v + 1e-6) / 8.64) * 8.64, 3) for v in xy]
            r = [o[0], o[1], o[0] + OUTLINE[0], o[1] + OUTLINE[1]]
            found = blockers(t, r)
            bad = [x for x in found if x[0] not in RESITE_KINDS]
            resite += [dict(type=tn, kind=k_, name=n_, xy_um=xy_, core=inst) for k_, n_, xy_ in found if k_ in RESITE_KINDS]
            if bad:
                raise ValueError(f'{tn} EX{k} slot {r}: covers {[(a, b) for a, b, _ in bad][:6]}')
            rects.append([*xy, *OUTLINE])
            new.append(dict(inst=inst, module=MODULE, origin_um=o,
                            track_offset_um=[round(v - ov, 3) for v, ov in zip(xy, o)], outline_um=OUTLINE,
                            orient=orient, halo_um=HALO, pins_file=PIN_FILE, physical_inst=physical,
                            physical_master=MODULE, lef=VIEW_DIR + '/' + MODULE + '.lef',
                            lib=VIEW_DIR + '/' + MODULE + '_tt.lib',
                            note=f'HG-EX1101 common native leaf{k}; mapped81000cells/10612um2; no RTL change or extra cycle; F70 native SIGNED+finalEQ qualified; parent actual glue/reach/clock gates pending'))
            cx = OUTLINE[0] - 95.064 if orient == 'MY' else 95.064
            t['clock'].setdefault('taps', []).append(dict(
                name=inst + '.ck', kind='core', xy=[round(xy[0] + cx, 3), round(xy[1] + 56.16, 3)],
                insertion_ps=189.33, insertion_ff_ps=152.40,
                budget_owner='F70 qualified native child; measured 101 boundary FF means TT189.33/FF152.40ps; results/ex_closure_1131/F70_qualified_leaf.json'))
        for a in new:      # new cores may not meet each other either
            for b in new:
                if a is not b and _ov([a['origin_um'][0] - HALO, a['origin_um'][1] - HALO, a['origin_um'][0] + OUTLINE[0] + HALO, a['origin_um'][1] + OUTLINE[1] + HALO],
                                      [b['origin_um'][0], b['origin_um'][1], b['origin_um'][0] + OUTLINE[0], b['origin_um'][1] + OUTLINE[1]]):
                    raise ValueError(f'{tn}: new cores {a["inst"]} / {b["inst"]} overlap')
        t.setdefault('hard_cores', []).extend(new)
        # Existing island shapes under the newly hardened logic cannot remain die-top drivers.
        # Parent infra and clocks must be regenerated before its prototype/release; this delta is not a freeze.
        ck = t['clock']
        islands = ck.get('die_islands_um', [])
        gone = [r for r in islands if any(inside((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, q, HALO) for q in rects)]
        ck['die_islands_um'] = [r for r in islands if r not in gone]
        resite += [dict(type=tn, kind='die_clock_island', rect_um=r) for r in gone]
        if len(hard) == 4:
            t['note'] += ' | HG-EX1101: 4 common native EX hard cuts; parent<=235487 mapped instances, 0 extra cycles; native stations unchanged; qualified HG-only explicit views; parent clock regeneration and actual glue/reach/clock gates pending'
        else:
            t['note'] += (f' | KV-HG-SPLIT-1 11-12: EX {",".join(map(str, hard))} hard (signed qkd_astk_ex_s_hg1101 view, 0 extra'
                          f' cycles), other EX soft as {soft_master} (soft_clones); {len(gone)} die clock islands under the'
                          ' new cores to re-site; new core taps = new die clock sinks')
    return p, types, resite


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('plan')
    a.add_argument('out')
    a.add_argument('--hard', default='0,1,2,3')
    a.add_argument('--soft-master')
    a.add_argument('--resite')
    a = a.parse_args()
    p, ts, rs = apply(json.load(open(a.plan)), [int(x) for x in a.hard.split(',')], a.soft_master)
    o = Path(a.out)
    o.write_text(json.dumps(p, indent=1) + '\n')
    q = o.parent / PIN_FILE
    q.parent.mkdir(exist_ok=True)
    q.write_text(json.dumps(pins(), indent=1) + '\n')
    if a.resite:
        Path(a.resite).write_text(json.dumps(dict(schema='opentallas.kv.hg_ex_island_resite.v1', rows=rs), indent=1) + '\n')
    print('HG_EX_CUT', len(ts), ts, 'islands_to_resite', len(rs))
