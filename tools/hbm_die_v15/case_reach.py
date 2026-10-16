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


def multicast_relay_ages(contract):
    """Trace explicit one-cycle hbfd relay RTL only; opaque units need compiler timing proof."""
    links = defaultdict(list)
    for e in contract['edges']:
        si, sp, slo, _ = e['source']; ti, tp, tlo, _ = e['sink']
        for bit in range(e['bits']):
            links[(si, sp, slo + bit)].append((ti, tp, tlo + bit))
    masters = {n: d['master'] for n, d in contract['instances'].items()}
    result = []
    for driver, sinks in links.items():
        if len(sinks) < 2:
            continue
        terminal, failures = [], []
        todo = [(s, 0, frozenset()) for s in sinks]
        while todo:
            sink, age, visited = todo.pop()
            if sink in visited:
                failures.append(dict(endpoint=list(sink), reason='relay cycle'))
                continue
            if masters.get(sink[0], '').startswith('hbfd_rly_') and sink[1] == 'i':
                next_ = links.get((sink[0], 'o', sink[2]), [])
                if not next_:
                    failures.append(dict(endpoint=list(sink), reason='undriven relay output continuation'))
                todo.extend((s, age + 1, visited | {sink}) for s in next_)
            else:
                terminal.append(dict(endpoint=list(sink), explicit_relay_cycles=age))
        ages = [x['explicit_relay_cycles'] for x in terminal]
        result.append(dict(driver=list(driver), direct_sinks=len(sinks), terminals=terminal, failures=failures,
                           relay_age_equal=bool(ages) and not failures and min(ages) == max(ages),
                           min_relay_cycles=min(ages, default=None), max_relay_cycles=max(ages, default=None),
                           compiled_equal_age_calendar='UNPROVEN: source relay depth alone does not prove reserved cycles'))
    return dict(qualification='SOURCE_GRAPH_ONLY; no hidden opaque-unit latency or calendar proof',
                multicast_driver_bits=len(result), unequal_relay_age=sum(not r['relay_age_equal'] for r in result),
                rows=result)


def typed_clock_pins(contract):
    result = set()
    for entry in contract.get('clock_resets', []):
        if entry['kind'] != 'clock':
            continue
        width = contract['instances'][entry['instance']]['ports'][entry['port']]['bits']
        result.update((entry['instance'], f"{entry['port']}[{k}]" if width > 1 else entry['port'])
                      for k in range(entry['bits']))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('case'); ap.add_argument('--reach', type=float, default=500.0)
    ap.add_argument('--paths', nargs='*', default=[]); ap.add_argument('--out')
    ap.add_argument('--contract', help='frozen source contract for explicit multicast relay-depth/calendar audit')
    a = ap.parse_args()
    contract = json.loads(Path(a.contract).read_text()) if a.contract else None
    clock_pins = typed_clock_pins(contract) if contract else set()
    c = Path(a.case)
    man = json.loads((c / 'manifest.json').read_text())
    L = {}
    for f in (c / 'views').glob('*.lef'):
        L.update(lef(f))
    pl = {n: dict(v, orient=v.get('orient', v.get('o')), master=v.get('master', v.get('m')))
          for n, v in man['placement'].items()}
    # nets from die.v: instance blocks with .port({...}) or .port(net)
    txt = (c / 'die.v').read_text()
    top_inputs = set()
    for hi, lo, name in re.findall(r'\binput\s+(?:wire\s+)?(?:\[(\d+):(\d+)\]\s*)?(\w+)', txt):
        top_inputs.update([f'{name}[{k}]' for k in range(int(lo), int(hi) + 1)] if hi else [name])
    pinloc, directions, skipped = {}, {}, []
    excluded = Counter()
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
                        excluded['explicit_unconnected_nc'] += 1
                        continue
                    bit = n - 1 - i
                    pn = f'{p}[{bit}]'
                    if pn in lv['pins'] and lv['uses'][pn] != 'CLOCK' and (inst, pn) not in clock_pins:
                        nets[s].append((inst, pn, xf(v, lv['w'], lv['h'], *lv['pins'][pn])))
                        directions[(inst, pn)] = lv['directions'][pn]
                    elif pn in lv['pins']:
                        excluded['typed_or_LEF_clock_pin'] += 1
            elif e and not e.startswith('nc_'):
                if p in lv['pins'] and lv['uses'][p] != 'CLOCK' and (inst, p) not in clock_pins:
                    nets[e].append((inst, p, xf(v, lv['w'], lv['h'], *lv['pins'][p])))
                    directions[(inst, p)] = lv['directions'][p]
                elif p in lv['pins']:
                    excluded['typed_or_LEF_clock_pin'] += 1
    length, all_branches, ambiguous, top_driven = {}, {}, {}, {}
    for n, ends in nets.items():
        if n in top_inputs:
            top_driven[n] = dict(loads=[dict(instance=e[0], pin=e[1], xy_um=e[2]) for e in ends],
                                 coverage='UNMEASURED_TOP_ENTRY_LOCATION: cannot infer a branch from sinks alone',
                                 reset_forest='UNQUALIFIED' if re.search(r'rst|reset|por', n, re.I) else 'not classified reset')
            continue
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
               clock_exclusion=dict(typed_clock_pins=len(clock_pins),
                                    rule='Frozen contract clock ABI plus LEF USE CLOCK; actual routed LEFs may label clocks USE SIGNAL.'),
               branches=sum(len(b) for b in all_branches.values()),
               branches_over_reach=sum(d > a.reach for bs in all_branches.values() for _, _, d in bs),
               ambiguous_nets=ambiguous, skipped_instances=skipped,
               declared_top_input_bits=len(top_inputs), top_driven_nets=top_driven,
               excluded_endpoint_counts=dict(excluded),
               qualification='GEOMETRY_ONLY; top-driven nets, unresolved directions/instances and calendars remain explicit. No full reset-forest qualification.',
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
    if a.contract:
        res['source_multicast_relay_ages'] = multicast_relay_ages(contract)
    out = Path(a.out) if a.out else c / 'reach.json'
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ('nets', 'over_reach', 'max_um', 'mean_um')}))
    print(json.dumps(res['by_class'])[:3000])


if __name__ == '__main__':
    main()
