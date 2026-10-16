#!/usr/bin/env python3
"""Pin-to-pin reach of every signal net of a view case (H-DIE r3, 2026-10-15).

    case_reach.py CASE_DIR [--reach 500] [--paths CASE_DIR/out/paths_tt_max.txt ...] [--out CASE_DIR/reach.json]

Reads CASE_DIR/manifest.json (placement), CASE_DIR/views/*.lef (pin rectangles) and die.v (nets), and gives every net
its placed driver -> load Manhattan length.  With --paths (die STA endpoint dumps "<start> <end> <slack>"), every
failing endpoint is classified: hop_over_reach (> reach: needs a relay home = die contract / floorplan work, owner H-DIE)
or in_reach (a tile launch/capture or wire defect, owner = the tile), grouped by (launch master.port -> capture
master.port).
"""
import argparse, json, re
from collections import defaultdict, Counter
from pathlib import Path


def lef(path):
    t = Path(path).read_text()
    out = {}
    for m in re.finditer(r'^MACRO (\S+)(.*?)^END \1', t, re.M | re.S):
        body = m.group(2)
        w, h = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', body).groups())
        pins, directions, uses = {}, {}, {}
        for pm in re.finditer(r'^\s*PIN (\S+)(.*?)^\s*END \1', body, re.M | re.S):
            r = re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', pm.group(2))
            if r:
                x0, y0, x1, y1 = map(float, r.groups())
                pins[pm.group(1)] = ((x0 + x1) / 2, (y0 + y1) / 2)
                dm = re.search(r'DIRECTION\s+(\w+)', pm.group(2))
                directions[pm.group(1)] = dm.group(1) if dm else 'UNKNOWN'
                um = re.search(r'USE\s+(\w+)', pm.group(2))
                uses[pm.group(1)] = um.group(1) if um else 'SIGNAL'
        out[m.group(1)] = dict(w=w, h=h, pins=pins, directions=directions, uses=uses)
    return out


def xf(v, w, h, px, py):
    o = v['orient']
    if o == 'R0':
        return v['x'] + px, v['y'] + py
    if o == 'MX':
        return v['x'] + px, v['y'] + h - py
    if o == 'MY':
        return v['x'] + w - px, v['y'] + py
    if o == 'R180':
        return v['x'] + w - px, v['y'] + h - py
    if o == 'R90':
        return v['x'] + h - py, v['y'] + px
    if o == 'R270':
        return v['x'] + py, v['y'] + w - px
    if o == 'MXR90':
        return v['x'] + py, v['y'] + px
    if o == 'MYR90':
        return v['x'] + h - py, v['y'] + w - px
    raise SystemExit(o)


def branches(ends, directions):
    """Use actual LEF directions, independent of instance order, and retain every sink."""
    drivers = [e for e in ends if directions.get(e[:2]) == 'OUTPUT']
    loads = [e for e in ends if directions.get(e[:2]) == 'INPUT']
    if len(drivers) != 1 or len(drivers) + len(loads) != len(ends):
        return None
    driver = drivers[0]
    return [(driver, load, abs(driver[2][0] - load[2][0]) + abs(driver[2][1] - load[2][1])) for load in loads]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('case'); ap.add_argument('--reach', type=float, default=500.0)
    ap.add_argument('--paths', nargs='*', default=[]); ap.add_argument('--out')
    a = ap.parse_args()
    c = Path(a.case)
    man = json.loads((c / 'manifest.json').read_text())
    L = {}
    for f in (c / 'views').glob('*.lef'):
        L.update(lef(f))
    pl = man['placement']
    # nets from die.v: instance blocks with .port({...}) or .port(net)
    txt = (c / 'die.v').read_text()
    pinloc, directions, skipped = {}, {}, []
    nets = defaultdict(list)
    for m in re.finditer(r'^\s+(\w+) (\w+) \(\n(.*?)\n\s+\);', txt, re.M | re.S):
        mas, inst = m.group(1), m.group(2)
        if inst not in pl or mas not in L:
            skipped.append(dict(instance=inst, master=mas))
            continue
        v = pl[inst]; lv = L[mas]
        for pm in re.finditer(r'\.(\w+)\((.*?)\)(?:,|$)', m.group(3), re.S):
            p, e = pm.group(1), pm.group(2).strip()
            if e.startswith('{'):
                parts = [s.strip() for s in e[1:-1].split(',')]
                n = len(parts)
                for i, s in enumerate(parts):
                    if s.startswith('nc_'):
                        continue
                    bit = n - 1 - i
                    pn = f'{p}[{bit}]'
                    if pn in lv['pins'] and lv['uses'][pn] != 'CLOCK':
                        nets[s].append((inst, pn, xf(v, lv['w'], lv['h'], *lv['pins'][pn])))
                        directions[(inst, pn)] = lv['directions'][pn]
            elif e and not e.startswith('nc_') and e not in ('clk_hbm', 'rst_n'):
                if p in lv['pins'] and lv['uses'][p] != 'CLOCK':
                    nets[e].append((inst, p, xf(v, lv['w'], lv['h'], *lv['pins'][p])))
                    directions[(inst, p)] = lv['directions'][p]
    length, all_branches, ambiguous = {}, {}, {}
    for n, ends in nets.items():
        if len(ends) < 2:
            continue
        bs = branches(ends, directions)
        if not bs:
            ambiguous[n] = [dict(instance=e[0], pin=e[1], direction=directions.get(e[:2])) for e in ends]
            continue
        all_branches[n] = bs
        length[n] = max(b[2] for b in bs)
    over = {n: d for n, d in length.items() if d > a.reach}
    by = defaultdict(list)
    for n, d in length.items():
        e = re.match(r'n_(svc_\w\w_s\d)_(\w+?)_\d+$', n)
        key = (e.group(1)[:6], re.sub(r'\d+$', '', e.group(2))) if e else ('?', n)
        by[key].append(d)
    res = dict(case=str(c), reach_um=a.reach, nets=len(length), over_reach=len(over),
               max_um=round(max(length.values(), default=0), 1), mean_um=round(sum(length.values()) / max(1, len(length)), 1),
               branch_coverage='Every typed driver-to-sink branch; LEF directions identify the driver.',
               branches=sum(len(b) for b in all_branches.values()),
               branches_over_reach=sum(d > a.reach for bs in all_branches.values() for _, _, d in bs),
               ambiguous_nets=ambiguous, skipped_instances=skipped,
               qualification='GEOMETRY_ONLY; unresolved directions/instances and calendar ages remain explicit.',
               multicast={n: dict(sinks=len(bs), longest_um=max(b[2] for b in bs),
                                  branches=[dict(driver=f'{d[0]}/{d[1]}', sink=f'{l[0]}/{l[1]}', length_um=v)
                                            for d, l, v in bs],
                                  equal_age_calendar='UNPROVEN: requires compiler/source-bound stage and slot audit')
                          for n, bs in all_branches.items() if len(bs) > 1},
               hist={f'<{b}': sum(1 for d in length.values() if b - 250 <= d < b) for b in range(250, 3001, 250)},
               by_class={f'{k[0]}:{k[1]}': dict(n=len(v), max=round(max(v), 1), over=sum(1 for d in v if d > a.reach))
                         for k, v in sorted(by.items())})
    if a.paths:
        # endpoint pin -> net length: an endpoint "inst/pin" is a load pin
        loadlen = {}
        for n, bs in all_branches.items():
            for driver, load, dist in bs:
                loadlen[f'{load[0]}/{load[1]}'] = (dist, driver[0], driver[1])
            driver, worst, dist = max(bs, key=lambda b: b[2])
            loadlen[f'{driver[0]}/{driver[1]}'] = (dist, worst[0], worst[1])
        classes = {}
        for pf in a.paths:
            rows = [l.split() for l in Path(pf).read_text().splitlines() if l.strip()]
            cls = defaultdict(lambda: dict(n=0, viol=0, worst=1e9, tns=0.0, max_len=0.0, example=None))
            for sp, ep, sl in rows:
                s = float(sl)
                ln = loadlen.get(ep) or loadlen.get(sp)
                cause = 'no_die_net' if ln is None else ('hop_over_reach' if ln[0] > a.reach else 'in_reach')
                lm = pl.get(ep.split('/')[0], {}).get('master', '?')
                sm = pl.get(sp.split('/')[0], {}).get('master', '?')
                bp = lambda x: re.sub(r'[\[\d\]]+$', '', x.split('/')[-1])
                k = f'{cause} | {sm}.{bp(sp)} -> {lm}.{bp(ep)}'
                r = cls[k]; r['n'] += 1
                if s < 0:
                    r['viol'] += 1; r['tns'] += s
                if s < r['worst']:
                    r['worst'] = s; r['example'] = f'{sp} -> {ep} ({ln[0]:.0f} um)' if ln else f'{sp} -> {ep}'
                if ln:
                    r['max_len'] = max(r['max_len'], ln[0])
            classes[Path(pf).name] = dict(sorted(cls.items(), key=lambda kv: kv[1]['worst']))
        res['sta_classes'] = classes
    out = Path(a.out) if a.out else c / 'reach.json'
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ('nets', 'over_reach', 'max_um', 'mean_um')}))
    print(json.dumps(res['by_class'])[:3000])


if __name__ == '__main__':
    main()
