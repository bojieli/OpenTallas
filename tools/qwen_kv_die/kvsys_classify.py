#!/usr/bin/env python3
"""qwen-split/kvsys: classified die STA endpoint table of a KV/system die chain (die_chain.sh kv + kvsys_prep.sh).

Per corner, every endpoint's worst path (sta_kv_<c>/grt_<c>_summary.rpt: startpoint, endpoint, slack) is classified by
what its two ends are bound to:
  real      a CLOSED view bound by bind_views (libs/views.json: its own ETM + measured insertion R, phi - R clock)
  frame     a generated placeholder (ASSUMED single-flop constants, ideal clock): unclosed master, cluster parent frame
  relay     a die relay frame (ASSUMED single-flop), the bus it stages (and its two real ends) named
  phy       a hard PHY abstract (vendor Liberty)
cause = '<launch kind> -> <capture kind>'; rows are aggregated per (cause, launch master, capture master.port) with
endpoints / violators / worst slack and one example, plus the pin-to-pin hop length of the example (instance placement +
LEF pin centres) so a long-hop geometry defect is not mistaken for a view problem.  TT decides setup, FF hold; SS is
reported as a sensitivity only (owner option B).

    kvsys_classify.py --run RUN --out OUT.json [--top 60]
"""
import argparse
import collections
import json
import re
from pathlib import Path


def lef_pins(paths):
    out, cur, pin, size = {}, None, None, {}
    for p in paths:
        for ln in open(p):
            t = ln.split()
            if not t:
                continue
            if t[0] == 'MACRO':
                cur, pin = t[1], None
                out.setdefault(cur, {})
            elif cur and t[0] == 'SIZE':
                size[cur] = (float(t[1]), float(t[3]))
            elif cur and t[0] == 'PIN':
                pin = t[1]
            elif cur and pin and t[0] == 'RECT' and pin not in out[cur]:
                x0, y0, x1, y1 = map(float, t[1:5])
                out[cur][pin] = ((x0 + x1) / 2, (y0 + y1) / 2)
            elif t[0] == 'END' and len(t) > 1 and t[1] == pin:
                pin = None
    return out, size


def place(path):
    out = {}
    for ln in open(path):
        m = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', ln)
        if m:
            out[m.group(1)] = (float(m.group(2)), float(m.group(3)), m.group(4))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--top', type=int, default=60)
    a = ap.parse_args(argv)
    c = a.run / 'case_kv'
    master = {}
    for ln in open(c / 'die.v'):
        m = re.match(r'\s*(\w+)\s+(\S+)\s*\(', ln)
        if m and m.group(1) not in ('module', 'wire', 'assign'):
            master[m.group(2)] = m.group(1)
    views = json.loads((a.run / 'libs/views.json').read_text())['views']
    real = {m for m, r in views.items() if r.get('bound')}
    pins, size = lef_pins([c / 'elements.lef'] + list(c.glob('phy*.lef')))
    plc = place(c / 'place.tcl')

    def kind(inst):
        m = master.get(inst, '?')
        if m in real:
            return 'real'
        if m.startswith('qkd_rly'):
            return 'relay'
        if m.startswith('ot_'):
            return 'phy'
        return 'frame' if m != '?' else 'top'

    def xy(inst, pin):
        m = master.get(inst)
        if m is None or inst not in plc:
            return None
        p = pins.get(m, {}).get(pin)
        if p is None:
            return None
        x0, y0, o = plc[inst]
        w, h = size.get(m, (0.0, 0.0))
        x, y = p
        if o in ('FN', 'MY', 'S', 'R180'):
            x = w - x
        if o in ('FS', 'MX', 'S', 'R180'):
            y = h - y
        return x0 + x, y0 + y
    res = {}
    for corner in ('tt', 'ff', 'ss'):
        f = a.run / f'sta_kv_{corner}' / f'grt_{corner}_summary.rpt'
        if not f.exists():
            continue
        agg = collections.defaultdict(lambda: dict(endpoints=0, violators=0, worst_ps=1e9, example=None))
        n = 0
        for ln in open(f):
            t = ln.split()
            if len(t) < 3:
                continue
            try:
                slack = float(t[-1])
            except ValueError:
                continue
            # summary rows: '<start pin> (<cell>) <end pin> (<cell>) <slack>'
            toks = [x for x in t[:-1] if not x.startswith('(')]
            if len(toks) < 2:
                continue
            sp, ep = toks[0], toks[1]
            if '/' not in ep:
                continue
            n += 1
            si = sp.rsplit('/', 1)[0] if '/' in sp else sp
            ei, eport = ep.rsplit('/', 1)
            sm, em = master.get(si, '?'), master.get(ei, '?')
            cause = f'{kind(si)} -> {kind(ei)}'
            if re.match(r'(rst|rsi|rs\b|c_arst|h_arst|hrst)', eport):
                cause = 'reset -> ' + kind(ei)
            key = (cause, sm, em + '.' + re.sub(r'\[\d+\]$', '', eport))
            r = agg[key]
            r['endpoints'] += 1
            r['violators'] += slack < 0
            if slack < r['worst_ps']:
                r['worst_ps'] = slack
                r['example'] = dict(start=sp, end=ep)
        rows = []
        for (cause, sm, ec), r in sorted(agg.items(), key=lambda kv: kv[1]['worst_ps']):
            ex = r['example']
            si = ex['start'].rsplit('/', 1)[0]
            ei, eport = ex['end'].rsplit('/', 1)
            # hop: from the launch instance's pins on the same net is not known here; use the capture pin to the nearest
            # launch-instance pin centre of the same bus name (frames name die ports), else the instance centres
            a_ = None
            p_e = xy(ei, eport)
            if p_e is not None and master.get(si) in pins:
                best = None
                for pn in pins[master[si]]:
                    q = xy(si, pn)
                    if q is not None:
                        d = abs(q[0] - p_e[0]) + abs(q[1] - p_e[1])
                        best = d if best is None or d < best else best
                a_ = round(best, 1) if best is not None else None
            rows.append(dict(cause=cause, launch=sm, capture=ec, nearest_pin_um=a_, **r))
        causes = collections.defaultdict(lambda: dict(endpoints=0, violators=0, worst_ps=1e9))
        for r in rows:
            x = causes[r['cause']]
            x['endpoints'] += r['endpoints']
            x['violators'] += r['violators']
            x['worst_ps'] = min(x['worst_ps'], r['worst_ps'])
        res[corner] = dict(endpoints=n, causes=dict(sorted(causes.items(), key=lambda kv: kv[1]['worst_ps'])),
                           rows=rows[:a.top], rows_total=len(rows))
    out = dict(schema='opentallas.qwen_kvsys_sta_classes.v1', run=str(a.run), real_views=sorted(real),
               rule='TT setup + FF hold decide; SS sensitivity only. real = closed view (own ETM, phi - R clock); frame / relay = '
                    'ASSUMED single-flop placeholders (ideal clock)', corners=res)
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    for corner, r in res.items():
        print(corner, r['endpoints'], json.dumps(r['causes']))


if __name__ == '__main__':
    main()
