#!/usr/bin/env python3
"""S81 die c5 diagnosis, part 2: worst-path classes behind the die STA result.

Inputs (all produced by the c5 chain or by a read-only re-run of the same kit STA with
`report_checks -slack_max 0 -fields {fanout capacitance net}`):
  --viol   full path report of every violating endpoint (one corner)
  --def    placed die DEF (instance origins / orientation, nets)
  --lef    LEFs with the tile pin shapes (repeatable)
  --wl     GRT wirelength csv (report_wire_length -global_route)
  --sens   name=end-report pairs (format end) to follow each class through the sensitivity runs
  --libs   liberty list (pin directions, interim-cell set)
Sub-commands:
  paths     class every violating endpoint launch -> capture and decompose the worst path per class
  worklist  every die net (failing or not): pin-to-pin Manhattan vs the 500-um registered-hop rule

A class is  launch instance kind (master).pin base -> capture instance kind (master).pin base  with every
decimal index replaced by '#'.  Lengths: routed = GRT wirelength of the path's net; Manhattan = |dx|+|dy|
between the LEF pin-shape centres of the launch and capture pins on the placed instances.
"""
import argparse, array, collections, gzip, json, math, re, sys

T_CLK = 833.333
HOP_UM = 500.0
NUM = re.compile(r'\d+')
IDX = re.compile(r'\[\d+\]')


def kind(inst):
    return NUM.sub('#', inst)


def pbase(pin):
    return IDX.sub('', pin)


def read_lef(paths):
    """master -> (w, h, {pin: (cx, cy)})"""
    out = {}
    for p in paths:
        cur = None
        pin = None
        with open(p) as f:
            for ln in f:
                s = ln.split()
                if not s:
                    continue
                if s[0] == 'MACRO':
                    cur = [0.0, 0.0, {}]
                    out[s[1]] = cur
                    pin = None
                elif cur is None:
                    continue
                elif s[0] == 'SIZE':
                    cur[0] = float(s[1]); cur[1] = float(s[3])
                elif s[0] == 'PIN':
                    pin = s[1]
                elif s[0] == 'RECT' and pin is not None and pin not in cur[2]:
                    cur[2][pin] = ((float(s[1]) + float(s[3])) / 2, (float(s[2]) + float(s[4])) / 2)
                elif s[0] == 'OBS':
                    pin = None
    return out


def read_def_components(path):
    """inst -> (master, x_um, y_um, orient)"""
    comp = {}
    inside = False
    with open(path) as f:
        for ln in f:
            if ln.startswith('COMPONENTS'):
                inside = True
                continue
            if ln.startswith('END COMPONENTS'):
                break
            if inside and ln.lstrip().startswith('- '):
                s = ln.split()
                try:
                    i = s.index('(')
                    comp[s[1]] = (s[2], int(s[i + 1]) / 1000.0, int(s[i + 2]) / 1000.0, s[i + 4])
                except (ValueError, IndexError):
                    pass
    return comp


def pin_xy(comp, lef, inst, pin):
    c = comp.get(inst)
    if c is None:
        return None
    m = lef.get(c[0])
    if m is None:
        return None
    w, h, pins = m
    q = pins.get(pin)
    if q is None:
        q = pins.get(pin + '[0]') or pins.get(pbase(pin))
        if q is None:
            return (c[1] + w / 2, c[2] + h / 2)
    px, py = q
    o = c[3]
    if o == 'N':
        dx, dy = px, py
    elif o == 'S':
        dx, dy = w - px, h - py
    elif o == 'FN':
        dx, dy = w - px, py
    elif o == 'FS':
        dx, dy = px, h - py
    elif o == 'W':
        dx, dy = h - py, px
    elif o == 'E':
        dx, dy = py, w - px
    elif o == 'FW':
        dx, dy = py, px
    else:  # FE
        dx, dy = h - py, w - px
    return (c[1] + dx, c[2] + dy)


def read_wl(path, want=None):
    wl = {}
    with open(path) as f:
        next(f)
        for ln in f:
            s = ln.split()
            if len(s) >= 4 and (want is None or s[1] in want):
                wl[s[1]] = (float(s[2]), int(s[3]))
    return wl


def read_libs(listfile, remap=None):
    """cell -> {pin base: direction}; set of interim cells"""
    dirs = collections.defaultdict(dict)
    interim = set()
    cre = re.compile(r'^\s*cell\s*\(\s*"?([^")\s]+)"?\s*\)')
    pre = re.compile(r'^\s*(?:bus|pin)\s*\(\s*"?([^")\s]+)"?\s*\)')
    dre = re.compile(r'direction\s*:\s*"?(\w+)')
    for lp in open(listfile).read().split():
        isint = 'interim_' in lp
        if remap:
            for a, b in remap:
                if lp.startswith(a):
                    lp = b + lp[len(a):]
                    break
        try:
            f = open(lp)
        except OSError:
            print('WARN lib missing', lp, file=sys.stderr)
            continue
        cell = None
        pin = None
        for ln in f:
            m = cre.match(ln)
            if m:
                cell = m.group(1)
                pin = None
                if isint:
                    interim.add(cell)
            m = pre.match(ln)
            if m:
                pin = pbase(m.group(1))
            if pin is not None and cell is not None:
                m = dre.search(ln)
                if m and pin not in dirs[cell]:
                    dirs[cell][pin] = m.group(1)
        f.close()
    return dirs, interim


PINLINE = re.compile(r'(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+([\^v])\s+(\S+)\s+\((\S+)\)\s*$')
NETLINE = re.compile(r'^\s*(\d+)?\s*(-?\d+\.\d+)?\s+(\S+)\s+\(net\)\s*$')
VAL2 = re.compile(r'^\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(.*)$')


def iter_paths(path):
    """yield one dict per report_checks path"""
    op = gzip.open if path.endswith('.gz') else open
    with op(path, 'rt') as f:
        cur = None
        for ln in f:
            if ln.startswith('Startpoint:'):
                cur = {'pins': [], 'nets': [], 'lat': [], 'unc': 0.0, 'lib': 0.0, 'group': '', 'slack': None,
                       'arr': None, 'req': None}
                continue
            if cur is None:
                continue
            if ln.startswith('Path Group:'):
                cur['group'] = ln.split()[2]
                continue
            m = PINLINE.search(ln)
            if m and '/' in m.group(4):
                cur['pins'].append((m.group(4), m.group(5), float(m.group(1)), float(m.group(2)),
                                    len(cur['lat'])))
                continue
            if ln.rstrip().endswith('(net)'):
                m = NETLINE.match(ln)
                if m:
                    cur['nets'].append((m.group(3), int(m.group(1) or 0), float(m.group(2) or 0.0)))
                continue
            if 'clock network delay' in ln:
                m = VAL2.match(ln)
                if m:
                    cur['lat'].append(float(m.group(1)))
            elif 'clock uncertainty' in ln:
                cur['unc'] = float(ln.split()[0])
            elif 'library setup time' in ln or 'library hold time' in ln:
                cur['lib'] = float(ln.split()[0])
            elif 'data arrival time' in ln and cur['arr'] is None:
                cur['arr'] = float(ln.split()[0])
            elif 'data required time' in ln and cur['req'] is None:
                cur['req'] = float(ln.split()[0])
            elif 'slack (' in ln:
                cur['slack'] = float(ln.split()[0])
                yield cur
                cur = None


def decompose(p):
    """launch pin, capture pin, cq, wire, cell-through, hops"""
    pins = p['pins']
    data = [x for x in pins if x[4] <= 1]          # before the capture clock section
    cap_ck = [x for x in pins if x[4] >= 2]
    if len(data) < 2:
        return None
    d = {'launch_ck': data[0], 'cq': 0.0, 'wire': 0.0, 'cell': 0.0, 'hops': 0, 'maxwire': 0.0}
    prev = data[0]
    first_out = None
    wire_end = None
    for x in data[1:]:
        same = x[0].split('/')[0] == prev[0].split('/')[0]
        if same:
            if first_out is None:
                d['cq'] += x[2]
                first_out = x
            else:
                d['cell'] += x[2]
        else:
            d['wire'] += x[2]
            d['hops'] += 1
            if x[2] >= d['maxwire']:
                d['maxwire'] = x[2]
                wire_end = (prev, x)
        prev = x
    d['launch'] = first_out or data[0]
    d['capture'] = data[-1]
    d['wire_seg'] = wire_end
    d['cap_ck'] = cap_ck[0] if cap_ck else None
    return d


def pct(a, q):
    if not a:
        return None
    s = sorted(a)
    return round(s[min(len(s) - 1, int(q * len(s)))], 1)


def iter_end(path):
    op = gzip.open if path.endswith('.gz') else open
    with op(path, 'rt') as f:
        for ln in f:
            if ln.endswith('(VIOLATED)\n') or ln.endswith('(MET)\n'):
                s = ln.split()
                yield s[0], float(s[-2])


def cmd_paths(a):
    lef = read_lef(a.lef)
    comp = read_def_components(a.deff)
    dirs, interim = read_libs(a.libs, [x.split('=') for x in a.remap]) if a.libs else ({}, set())
    wl = read_wl(a.wl)
    setup = a.kind == 'setup'
    cls = {}
    epc = {}
    order = []
    tot_n = 0
    tot_tns = 0.0
    skipped = 0
    cats = {}
    lenbin = {}
    for p in iter_paths(a.viol):
        d = decompose(p)
        if d is None or p['slack'] is None:
            skipped += 1
            continue
        lp, lm = d['launch'][0], d['launch'][1]
        cp, cm = d['capture'][0], d['capture'][1]
        li, lpin = lp.split('/', 1)
        ci, cpin = cp.split('/', 1)
        key = '%s(%s).%s -> %s(%s).%s' % (kind(li), lm, pbase(lpin), kind(ci), cm, pbase(cpin))
        c = cls.get(key)
        if c is None:
            c = cls[key] = {'n': 0, 'tns': 0.0, 'wns': 0.0, 'worst': None, 'wire': array.array('f'),
                            'len': array.array('f'), 'man': array.array('f'), 'skew': array.array('f'),
                            'cq': array.array('f'), 'slk': array.array('f'), 'lib': array.array('f'),
                            'id': len(order), 'multi': 0, 'cellthru': 0, 'whatif': array.array('f'),
                            'whatif2': array.array('f'), 'cats': collections.Counter(),
                            'lmaster': lm, 'cmaster': cm, 'groups': collections.Counter()}
            order.append(key)
        s = p['slack']
        c['n'] += 1
        c['tns'] += s
        tot_n += 1
        tot_tns += s
        lat_l = p['lat'][0] if p['lat'] else 0.0
        lat_c = p['lat'][1] if len(p['lat']) > 1 else 0.0
        skew = lat_c - lat_l
        seg = d['wire_seg']
        net = p['nets'][-1] if p['nets'] else None
        rl = pc = None
        man = None
        if seg:
            a0 = pin_xy(comp, lef, *seg[0][0].split('/', 1))
            a1 = pin_xy(comp, lef, *seg[1][0].split('/', 1))
            if a0 and a1:
                man = abs(a0[0] - a1[0]) + abs(a0[1] - a1[1])
        if net:
            # the net feeding the longest wire arc: nets are listed in path order, one per driver
            names = [n for n in p['nets']]
            pick = names[-1]
            if seg and len(names) > 1:
                for n in names:
                    if n[0].split('[')[0].endswith(pbase(seg[0][0].split('/', 1)[1])):
                        pick = n
            w = wl.get(pick[0])
            if w:
                rl, pc = w
            net = pick
        c['wire'].append(d['wire'])
        c['len'].append(rl if rl is not None else -1.0)
        c['man'].append(man if man is not None else -1.0)
        c['skew'].append(skew)
        c['cq'].append(d['cq'])
        c['slk'].append(s)
        c['lib'].append(p['lib'])
        c['groups'][p['group']] += 1
        if d['hops'] > 1:
            c['multi'] += 1
        if d['cell'] != 0.0:
            c['cellthru'] += 1
        if setup and rl is not None and pc == 2 and d['hops'] == 1:
            lenbin.setdefault(int(rl // 100), array.array('f')).append(d['wire'])
        if not setup:
            # what-if: relay masters launch with L (cq) and need H (hold) instead of the interim values
            dl = (a.relay_l - d['cq']) if (lm.startswith('dsfd_rly_') and lm in interim) else 0.0
            dh = (p['lib'] - a.relay_h) if (cm.startswith('dsfd_rly_') and cm in interim) else 0.0
            c['whatif'].append(s + dl + dh)
            dl2 = (a.relay_l - d['cq']) if lm in interim else 0.0
            dh2 = (p['lib'] - a.relay_h) if cm in interim else 0.0
            c['whatif2'].append(s + dl2 + dh2)
            real = not (lm in interim and cm in interim)
            if skew > a.skew_thr:
                cat = 'planned_skew_real_view' if real else 'planned_skew_interim'
            elif real:
                cat = 'real_view'
            elif d['wire'] <= a.zero_wire_ps:
                cat = 'interim_zero_wire'
            else:
                cat = 'interim_short_wire'
            c['cats'][cat] += 1
            g = cats.setdefault(cat, [0, 0.0, 0.0, 0, 0])
            g[0] += 1; g[2] += s; g[1] = min(g[1], s)
            g[3] += (s + dl + dh) < 0
            g[4] += (s + dl2 + dh2) < 0
            if rl is not None and pc == 2 and d['hops'] == 1:
                lenbin.setdefault(int(rl // 100), array.array('f')).append(d['wire'])
        epc[cp] = c['id']
        if (c['worst'] is None) or s < c['wns']:
            c['wns'] = s
            c['worst'] = {
                'slack': s, 'group': p['group'], 'launch_pin': lp, 'capture_pin': cp,
                'launch_clock_insertion': lat_l, 'capture_clock_insertion': lat_c, 'skew_capture_minus_launch': round(skew, 1),
                'clock_to_out': round(d['cq'], 1), 'wire_delay': round(d['wire'], 1), 'cell_through': round(d['cell'], 1),
                'wire_hops': d['hops'], 'uncertainty': p['unc'], 'lib_setup_or_hold': p['lib'],
                'arrival': p['arr'], 'required': p['req'],
                'net': net[0] if net else None,
                'routed_um': rl, 'net_pins': pc, 'manhattan_um': round(man, 1) if man is not None else None,
                'launch_interim': lm in interim, 'capture_interim': cm in interim,
            }
    # sensitivity: follow the class of each nominal violator through the other end reports
    sens = {}
    for spec in a.sens:
        name, path = spec.split('=', 1)
        agg = collections.defaultdict(lambda: [0, 0.0, 0.0, 0, 0.0])  # nviol wns tns n_seen sum_slack
        other = [0, 0.0, 0.0]
        for ep, s in iter_end(path):
            cid = epc.get(ep)
            if cid is None:
                if s < 0:
                    other[0] += 1; other[2] += s; other[1] = min(other[1], s)
                continue
            g = agg[cid]
            g[3] += 1; g[4] += s
            if s < 0:
                g[0] += 1; g[2] += s
                if s < g[1]:
                    g[1] = s
        sens[name] = (agg, other)
    out = {'kind': a.kind, 'corner': a.corner, 'viol_report': a.viol, 'endpoints': tot_n, 'tns': round(tot_tns, 1),
           'skipped_paths': skipped, 'classes': [], 'sens_unclassed': {k: {'endpoints': v[1][0], 'wns': v[1][1], 'tns': round(v[1][2], 1)} for k, v in sens.items()}}
    wi_total = 0
    for key in order:
        c = cls[key]
        ln = [x for x in c['len'] if x >= 0]
        mn = [x for x in c['man'] if x >= 0]
        w = c['worst']
        e = {'class': key, 'endpoints': c['n'], 'wns': round(c['wns'], 1), 'tns': round(c['tns'], 1),
             'tns_share': round(c['tns'] / tot_tns, 4) if tot_tns else 0.0,
             'launch_master': c['lmaster'], 'capture_master': c['cmaster'],
             'launch_interim': c['lmaster'] in interim, 'capture_interim': c['cmaster'] in interim,
             'groups': len(c['groups']), 'top_group': c['groups'].most_common(1)[0][0],
             'wire_delay': {'min': pct(c['wire'], 0), 'p50': pct(c['wire'], .5), 'max': pct(c['wire'], 1)},
             'routed_um': {'min': pct(ln, 0), 'p50': pct(ln, .5), 'max': pct(ln, 1)},
             'manhattan_um': {'min': pct(mn, 0), 'p50': pct(mn, .5), 'max': pct(mn, 1)},
             'skew': {'min': pct(c['skew'], 0), 'p50': pct(c['skew'], .5), 'max': pct(c['skew'], 1)},
             'cq': {'min': pct(c['cq'], 0), 'p50': pct(c['cq'], .5), 'max': pct(c['cq'], 1)},
             'lib_check': {'min': pct(c['lib'], 0), 'max': pct(c['lib'], 1)},
             'multi_hop_paths': c['multi'], 'cell_through_paths': c['cellthru'], 'worst': w}
        if not setup:
            rem = sum(1 for x in c['whatif'] if x < 0)
            e['whatif_relay_remaining'] = rem
            e['whatif_relay_wns'] = round(min(c['whatif']), 1)
            e['whatif_all_interim_remaining'] = sum(1 for x in c['whatif2'] if x < 0)
            e['whatif_all_interim_wns'] = round(min(c['whatif2']), 1)
            e['categories'] = dict(c['cats'])
            wi_total += rem
        e['sens'] = {}
        for name, (agg, _) in sens.items():
            g = agg.get(c['id'])
            if g:
                e['sens'][name] = {'endpoints': g[0], 'wns': round(g[1], 1), 'tns': round(g[2], 1),
                                   'mean_slack': round(g[4] / g[3], 1) if g[3] else None}
        e['mean_slack'] = round(c['tns'] / c['n'], 1)
        out['classes'].append(e)
    out['classes'].sort(key=lambda e: e['tns'])
    out['wire_delay_vs_routed_um_2pin'] = [{'routed_um_from': k * 100, 'paths': len(v), 'wire_delay_min': pct(v, 0),
                                             'wire_delay_p50': pct(v, .5), 'wire_delay_max': pct(v, 1)} for k, v in sorted(lenbin.items())]
    if not setup:
        out['categories'] = {k: {'endpoints': v[0], 'wns': round(v[1], 1), 'tns': round(v[2], 1),
                                 'tns_share': round(v[2] / tot_tns, 4), 'whatif_relay_remaining': v[3],
                                 'whatif_all_interim_remaining': v[4]} for k, v in cats.items()}
        out['whatif_all_interim_remaining'] = sum(v[4] for v in cats.values())
        out['category_rule'] = {'skew_thr_ps': a.skew_thr, 'zero_wire_ps': a.zero_wire_ps}
        out['whatif_relay'] = {'L': a.relay_l, 'H': a.relay_h, 'remaining_endpoints': wi_total,
                               'applies_to': 'interim dsfd_rly_* masters (launch cq -> L, capture hold -> H)'}
    json.dump(out, open(a.out, 'w'), indent=1)
    print('classes', len(out['classes']), 'endpoints', tot_n, 'tns', round(tot_tns, 1), 'skipped', skipped)


def cmd_worklist(a):
    lef = read_lef(a.lef)
    comp = read_def_components(a.deff)
    dirs, interim = read_libs(a.libs, [x.split('=') for x in a.remap])
    wl = read_wl(a.wl)
    skip = re.compile(a.skip)
    cls = {}
    nets = 0
    nodrv = 0
    nd = collections.Counter()
    inside = False
    buf = ''
    pr = re.compile(r'\(\s*(\S+)\s+(\S+)\s*\)')
    with open(a.deff) as f:
        for ln in f:
            if not inside:
                if ln.startswith('NETS '):
                    inside = True
                continue
            if ln.startswith('END NETS'):
                break
            buf += ln
            if ';' not in ln:
                continue
            rec, buf = buf, ''
            s = rec.split(None, 2)
            if len(s) < 3 or s[0] != '-':
                continue
            net = s[1]
            if skip.search(net):
                continue
            pins = pr.findall(s[2])
            drv = None
            sinks = []
            for inst, pin in pins:
                c = comp.get(inst)
                if c is None:
                    continue
                d = dirs.get(c[0], {}).get(pbase(pin))
                if d == 'output' and drv is None:
                    drv = (inst, pin, c[0])
                else:
                    sinks.append((inst, pin, c[0]))
            if drv is None or not sinks:
                nodrv += 1
                nd[' | '.join(sorted(set('%s.%s' % (comp[i][0], pbase(q)) for i, q in pins if i in comp))[:4])] += 1
                continue
            nets += 1
            d0 = pin_xy(comp, lef, drv[0], drv[1])
            w = wl.get(net)
            rl = w[0] if w else -1.0
            for inst, pin, m in sinks:
                d1 = pin_xy(comp, lef, inst, pin)
                man = abs(d0[0] - d1[0]) + abs(d0[1] - d1[1])
                key = '%s(%s).%s -> %s(%s).%s' % (kind(drv[0]), drv[2], pbase(drv[1]), kind(inst), m, pbase(pin))
                c = cls.get(key)
                if c is None:
                    c = cls[key] = {'bits': 0, 'over': 0, 'man_max': 0.0, 'man_sum': 0.0, 'rl_max': 0.0, 'rl_over': 0,
                                    'detour_only': 0, 'ex': None, 'o110': 0, 'o150': 0, 'o200': 0, 'stages': collections.Counter(), 'fan': 0}
                c['bits'] += 1
                c['man_sum'] += man
                if len(sinks) > 1:
                    c['fan'] += 1
                if man > c['man_max']:
                    c['man_max'] = man
                    c['ex'] = (net, drv[0], inst)
                if rl > c['rl_max']:
                    c['rl_max'] = rl
                if man > a.hop * 1.1:
                    c['o110'] += 1
                if man > a.hop * 1.5:
                    c['o150'] += 1
                if man > a.hop * 2:
                    c['o200'] += 1
                if man > a.hop:
                    c['over'] += 1
                    c['stages'][int(math.ceil(man / a.hop)) - 1] += 1
                elif rl > a.hop * a.detour and len(sinks) == 1:
                    c['detour_only'] += 1
                if rl > a.hop:
                    c['rl_over'] += 1
    rows = []
    for k, c in cls.items():
        if c['over'] == 0 and c['detour_only'] == 0:
            continue
        rows.append({'class': k, 'bits': c['bits'], 'bits_over_hop': c['over'], 'bits_over_1p1_hop': c['o110'],
                     'bits_over_1p5_hop': c['o150'], 'bits_over_2_hop': c['o200'], 'manhattan_max_um': round(c['man_max'], 1),
                     'manhattan_mean_um': round(c['man_sum'] / c['bits'], 1), 'routed_max_um': round(c['rl_max'], 1),
                     'bits_routed_over_hop': c['rl_over'], 'bits_detour_only': c['detour_only'],
                     'multi_sink_bits': c['fan'],
                     'relay_stages_needed_max': int(math.ceil(c['man_max'] / a.hop)) - 1 if c['man_max'] > a.hop else 0,
                     'relay_stage_histogram': {str(k2): v for k2, v in sorted(c['stages'].items())},
                     'relay_registers_needed': sum(k2 * v for k2, v in c['stages'].items()),
                     'example': c['ex']})
    rows.sort(key=lambda r: -r['relay_registers_needed'])
    out = {'hop_um': a.hop, 'detour_factor': a.detour, 'nets_classed': nets, 'nets_without_lib_driver': nodrv,
           'nets_without_lib_driver_top': nd.most_common(25),
           'classes_total': len(cls), 'skip_regex': a.skip,
           'over_hop': {'classes': sum(1 for r in rows if r['bits_over_hop']), 'bits': sum(r['bits_over_hop'] for r in rows),
                        'relay_registers': sum(r['relay_registers_needed'] for r in rows)},
           'detour_only': {'classes': sum(1 for r in rows if r['bits_detour_only']), 'bits': sum(r['bits_detour_only'] for r in rows)},
           'rows': rows}
    json.dump(out, open(a.out, 'w'), indent=1)
    print('worklist classes', len(rows), 'of', len(cls), out['over_hop'], out['detour_only'], 'nodrv', nodrv)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    for n in ('paths', 'worklist'):
        s = sub.add_parser(n)
        s.add_argument('--def', dest='deff', required=True)
        s.add_argument('--lef', action='append', default=[])
        s.add_argument('--wl', required=True)
        s.add_argument('--libs')
        s.add_argument('--remap', action='append', default=[])
        s.add_argument('--out', required=True)
        if n == 'paths':
            s.add_argument('--viol', required=True)
            s.add_argument('--kind', choices=['setup', 'hold'], required=True)
            s.add_argument('--corner', default='')
            s.add_argument('--sens', action='append', default=[])
            s.add_argument('--relay-l', type=float, default=124.0)
            s.add_argument('--relay-h', type=float, default=-30.0)
            s.add_argument('--skew-thr', type=float, default=10.0)
            s.add_argument('--zero-wire-ps', type=float, default=5.0)
        else:
            s.add_argument('--hop', type=float, default=HOP_UM)
            s.add_argument('--detour', type=float, default=1.3)
            s.add_argument('--skip', default=r'^(n_ck|n_rst_|n_rs_col_|por_n|refclk)')
    a = ap.parse_args()
    (cmd_paths if a.cmd == 'paths' else cmd_worklist)(a)


if __name__ == '__main__':
    main()
