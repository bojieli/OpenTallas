#!/usr/bin/env python3
"""HBM-P7 completeness post-pass (COORD 10-23 G0C, plan-tool4 check.py --completeness).

Runs after taps_cores_v2.apply on a generated die_plan.json (in place):
  * die clock.common_latency_ps = 250 (R4 one die-wide target; every type clock.insertion_ps is already 250)
  * budgets.ft_station_max_um = 675 (COORD visual review: every hop <= 90% of the 750-um HBM reach)
  * type.cells = glue + hard-core cells from plan_notes_v2.json (EST/YOSYS basis there)
  * type.internal_stations[] (R3-INTERNAL): every face window -> leaf/core box and core <-> core net estimated longer
    than the limit gets FIRM stations evenly on the Manhattan L path (x first, then y), hops <= limit.  Each station
    is a reset-less data register (one cycle, like the die lane stations): the bus latency grows by len(regs_um).

    python3 complete_p7.py PLAN_DIR [--tool TOOLS_DIR_WITH_die_plan] [--smax 675]
"""
import argparse, json, math, os, sys
from collections import defaultdict


def l_path(a, b, smax):
    """FIRM station sites on the Manhattan L path a -> b (x leg, then y leg), hops <= smax."""
    d = abs(b[0] - a[0]) + abs(b[1] - a[1])
    n = max(0, math.ceil(d / smax - 1e-9) - 1)
    regs = []
    for k in range(1, n + 1):
        s = d * k / (n + 1)
        dx = abs(b[0] - a[0])
        if s <= dx:
            x = a[0] + math.copysign(s, b[0] - a[0]); y = a[1]
        else:
            x = b[0]; y = a[1] + math.copysign(s - dx, b[1] - a[1])
        regs.append([round(x / 0.216) * 0.216, round(y / 0.27) * 0.27])   # snapped to the site grid
    return regs


def near(pt, box):
    return [min(max(pt[0], box[0]), box[2]), min(max(pt[1], box[1]), box[3])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan_dir')
    ap.add_argument('--tool', default=os.environ.get('OT_PT4', os.path.expanduser('~/scratch/hbm-p7-1023/pt4')))
    ap.add_argument('--smax', type=float, default=675.0)
    ap.add_argument('--common', type=float, default=250.0)
    a = ap.parse_args()
    sys.path.insert(0, a.tool)
    from tools.die_plan import schema as S, check as C
    fn = os.path.join(a.plan_dir, 'die_plan.json')
    raw = json.load(open(fn))
    notes = json.load(open(os.path.join(a.plan_dir, 'plan_notes_v2.json')))
    raw.setdefault('clock', {})['common_latency_ps'] = a.common
    raw.setdefault('budgets', {})['ft_station_max_um'] = a.smax
    for tn, t in raw['partition_types'].items():
        ti = notes['types'].get(tn)
        if ti and not t.get('hard'):
            t['cells'] = int((ti.get('glue_cells') or 0) + (ti.get('core_cells_total') or 0))
    P = S.Plan(raw)
    smax = a.smax
    stats = defaultdict(lambda: [0, 0])
    for tn, t in raw['partition_types'].items():
        t.pop('internal_stations', None)
        if t.get('hard'):
            continue
        boxes = {}
        for hc in t.get('hard_cores', []):
            dx, dy = hc.get('track_offset_um', [0.0, 0.0])
            x0, y0 = hc['origin_um'][0] + dx, hc['origin_um'][1] + dy
            boxes[hc['inst']] = (x0, y0, x0 + hc['outline_um'][0], y0 + hc['outline_um'][1])
        for c in t.get('contents', []):
            if c['inst'] not in boxes and 'origin_um' in c and 'outline_um' in c:
                x0, y0 = c['origin_um']
                boxes[c['inst']] = (x0, y0, x0 + c['outline_um'][0], y0 + c['outline_um'][1])
        if not boxes:
            continue
        ist = []
        bt = C._bus_targets(P, tn)
        for b in t.get('buses', []):
            lf = b.get('leaf') or ''
            li = lf.split('.')[0]
            cand = [ci for ci in boxes if ci == li or ci.startswith(li + '_')] if li else []
            if not cand or b['name'] not in bt:
                continue
            p0 = bt[b['name']][1]
            ci = min(cand, key=lambda c_: C._box_dist(p0, boxes[c_]))
            d = C._box_dist(p0, boxes[ci])
            if d <= smax:
                continue
            q = near(p0, boxes[ci])
            src, dst = (p0, q) if b.get('dir', 'in') == 'in' else (q, p0)
            ist.append(dict(conn=f"bus:{b['name']}", from_um=[round(src[0], 3), round(src[1], 3)],
                            regs_um=l_path(src, dst, smax), to_um=[round(dst[0], 3), round(dst[1], 3)],
                            bits=int(b['width']) + 1, launch=('face' if b.get('dir', 'in') == 'in' else lf),
                            capture=(lf if b.get('dir', 'in') == 'in' else 'face'),
                            note=f'HBM-P7 R3-INTERNAL est {d:.0f} um (data + epoch bit)'))
        nets = defaultdict(set)
        for c in t.get('contents', []):
            for lp, v in c.get('bind', {}).items():
                if v.startswith('net:'):
                    nets[v[4:]].add(c['inst'])
        for nm, insts in nets.items():
            ins = sorted(i for i in insts if i in boxes)
            for i, x in enumerate(ins):
                for y in ins[i + 1:]:
                    bx, by = boxes[x], boxes[y]
                    d = max(bx[0] - by[2], by[0] - bx[2], 0) + max(bx[1] - by[3], by[1] - bx[3], 0)
                    if d > smax:
                        cx = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
                        p0 = near(((by[0] + by[2]) / 2, (by[1] + by[3]) / 2), bx); q = near(cx, by)
                        ist.append(dict(conn=f'{x}|{y}', from_um=p0, regs_um=l_path(p0, q, smax), to_um=q,
                                        launch=x, capture=y, note=f'HBM-P7 R3-INTERNAL net {nm} est {d:.0f} um'))
        for e in ist:
            assert C._hops_ok(e['from_um'], e['regs_um'], e['to_um'], smax + 1.0), (tn, e['conn'])
        if ist:
            t['internal_stations'] = ist
            stats[tn] = [len(ist), sum(len(e['regs_um']) for e in ist)]
    json.dump(raw, open(fn, 'w'), indent=None, separators=(',', ':'))
    tot = [sum(v[0] for v in stats.values()), sum(v[1] for v in stats.values())]
    print('internal_stations: types', len(stats), 'conns', tot[0], 'station regs (cycles on the conn)', tot[1])
    for tn, v in sorted(stats.items(), key=lambda kv: -kv[1][0])[:12]:
        print(' ', tn, v)
    json.dump(dict(stats), open(os.path.join(a.plan_dir, 'internal_stations_p7.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
