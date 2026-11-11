#!/usr/bin/env python3
"""CPL-QC-2 (11-11): apply a clean-slate positions/orients delta {type: {inst: [x, y, orient]}} to a plan.  ADVISORY.

Changes ONLY placement-derived fields of the named types; nets, register counts, pins, outlines, faces, buses, ft slots
and the type clock tap are untouched, so EQ holds by construction:
  hard_cores[].origin_um/orient (+ the contents[] mirror), clock.taps[] named <inst>.<pin> (re-derived from the core pin),
  clock.landing_contract.collector_tree.core_resets[].pin_um/xy (pin re-derived, the xy offset mirrored with the pin),
  internal_stations[]: the core end (to_um/from_um/leaf_um at the launch/capture pin) re-derived and the SAME number of
  FIRM registers re-placed at equal arc length on the street-first path (cslate.restation).
usage: cslate_apply.py PLAN DELTA OUT [--graph TYPE=G.json ...] [--detail MODULE=LEF ...]
"""
import argparse, copy, hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cslate as C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan'); ap.add_argument('delta'); ap.add_argument('out')
    ap.add_argument('--graph', action='append', default=[])
    ap.add_argument('--detail', action='append', default=[])
    a = ap.parse_args()
    delta = C.load(a.delta)
    graphs = dict(g.split('=', 1) for g in a.graph)
    plan = C.load(a.plan)
    report = {}
    for tn, d in delta.items():
        gp = graphs.get(tn, 'g_%s.json' % tn)
        ty = C.Type(a.plan, tn, gp)
        st_old = ty.place()
        st = ty.place(d)
        t = plan['partition_types'][tn]
        cores = {c['inst']: c for c in t['hard_cores']}
        moved = []
        for inst, (x, y, o) in d.items():
            c = cores[inst]
            if [c['origin_um'][0], c['origin_um'][1], c.get('orient', 'R0')] != [x, y, o]:
                moved.append(inst)
            c['origin_um'] = [x, y]; c['orient'] = o
        for e in t.get('contents', []):
            if e.get('inst') in d and 'origin_um' in e:
                e['origin_um'] = [d[e['inst']][0], d[e['inst']][1]]
                if 'orient' in e or d[e['inst']][2] != 'R0':
                    e['orient'] = d[e['inst']][2]

        def pin_xy(stt, inst, pin):
            c = ty.cores[inst]
            pp = [p for p in ty.pins(c) if p['name'] == pin]
            if not pp:
                return None
            return C.xform(stt[inst][0], c['outline_um'], stt[inst][1], pp[0]['x'], pp[0]['y'])
        ntap = 0
        for tp in t.get('clock', {}).get('taps', []):
            n = tp.get('name', '')
            if '.' in n and n.split('.')[0] in moved:
                inst, pin = n.split('.', 1)
                new = pin_xy(st, inst, pin)
                if new:
                    tp['xy'] = [round(new[0], 3), round(new[1], 3)]; ntap += 1
        nrst = 0
        ct = ((t.get('clock', {}).get('landing_contract') or {}).get('collector_tree') or {})
        for cr in ct.get('core_resets', []):
            inst = cr.get('inst')
            if inst in moved:
                old = pin_xy(st_old, inst, cr['pin']); new = pin_xy(st, inst, cr['pin'])
                if old and new:
                    ox, oy = cr['xy'][0] - cr['pin_um'][0], cr['xy'][1] - cr['pin_um'][1]
                    fx = -1 if (st_old[inst][1] in ('MY', 'R180')) != (st[inst][1] in ('MY', 'R180')) else 1
                    fy = -1 if (st_old[inst][1] in ('MX', 'R180')) != (st[inst][1] in ('MX', 'R180')) else 1
                    cr['pin_um'] = [round(new[0], 3), round(new[1], 3)]
                    cr['xy'] = [round(new[0] + fx * ox, 3), round(new[1] + fy * oy, 3)]
                    nrst += 1
        regs, info = C.restation(ty, st)
        nst = 0
        for s in t.get('internal_stations', []):
            c = s['conn'].split(':', 1)[-1]
            if c not in info:
                continue
            i = info[c]
            n = len(s['regs_um'])
            assert len(i['regs']) == n, (tn, c)
            onf = lambda p: p[0] < 0.6 or p[1] < 0.6 or p[0] > ty.W - 0.6 or p[1] > ty.H - 0.6
            if onf(s['from_um']):
                s['to_um'] = [round(i['to'][0], 3), round(i['to'][1], 3)]
                s['regs_um'] = [list(r) for r in i['regs']]
            else:
                s['from_um'] = [round(i['from'][0], 3), round(i['from'][1], 3)] if not onf(i['from']) else s['from_um']
                s['regs_um'] = [list(r) for r in i['regs']]
            if 'leaf_um' in s:
                s['leaf_um'] = s['to_um'] if onf(s['from_um']) else s['from_um']
            s['note'] = (s.get('note', '') + ' | CPL-QC-2 11-11 clean slate: same %d FIRM regs re-placed street-first' % n).strip(' |')
            nst += 1
        t['note'] = (t.get('note', '') + ' | CPL-QC-2 11-11 clean-slate core placement (positions/orients only)').strip(' |')
        report[tn] = {'moved': moved, 'clock_taps': ntap, 'core_resets': nrst, 'stations': nst,
                      'hops': {k: v['hop_um'] for k, v in info.items()}}
    with open(a.out, 'w') as f:
        json.dump(plan, f, separators=(',', ':')); f.write('\n')
    print(json.dumps(report, indent=1))
    print('out', a.out, hashlib.sha256(open(a.out, 'rb').read()).hexdigest()[:12])


if __name__ == '__main__':
    main()
