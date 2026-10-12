#!/usr/bin/env python3
"""qwendie-1011: provisional top-down hierarchy contract for a Qwen die (ROM r22ko4 / KV) from a generated die case.

Reads the case's elements.lef (+ phy LEFs), die.v (instance -> master) and place.tcl (positions), and writes, per
master slot: outline, instances (position / orient), pins grouped per bus (face, layer, offset span along the face,
bits, direction), clock entry, PG pins (layer, stripe count), the I/O budget (default 0.2 T in / 0.2 T out, registered
boundaries) and the layer contract.  Optional --registry adds each slot's closed-route evidence (TT/FF/job).
Provisional schema 'qwen-hier-contract/0'; migrate to tools/hier_contract/ when it lands.
"""
import argparse, json, re, sys, urllib.request
from collections import defaultdict
from pathlib import Path

PERIOD_PS = 833.333


def parse_lef(path, out):
    cur = pin = None
    for line in open(path):
        t = line.split()
        if not t:
            continue
        if t[0] == 'MACRO':
            cur = out.setdefault(t[1], dict(w=0, h=0, pins={}))
        elif cur is None:
            continue
        elif t[0] == 'SIZE':
            cur['w'], cur['h'] = float(t[1]), float(t[3])
        elif t[0] == 'PIN':
            pin = cur['pins'].setdefault(t[1], dict(dir='', use='SIGNAL', shapes=[]))
        elif pin is not None and t[0] == 'DIRECTION':
            pin['dir'] = t[1]
        elif pin is not None and t[0] == 'USE':
            pin['use'] = t[1]
        elif pin is not None and t[0] == 'LAYER':
            pin['_l'] = t[1]
        elif pin is not None and t[0] == 'RECT':
            pin['shapes'].append((pin.get('_l'), *map(float, t[1:5])))
        elif t[0] == 'END' and len(t) > 1:
            if pin is not None and t[1] in cur['pins']:
                pin = None
            elif t[1] in out and out[t[1]] is cur:
                cur = pin = None
    return out


def face_of(w, h, r):
    x0, y0, x1, y1 = r
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    d = {'W': cx, 'E': w - cx, 'S': cy, 'N': h - cy}
    f = min(d, key=d.get)
    if d[f] > 0.25 * min(w, h):
        return 'AREA', None
    return f, (cy if f in 'WE' else cx)


def slot(name, m, insts, evidence):
    w, h = m['w'], m['h']
    buses, pg, clk = defaultdict(lambda: dict(bits=0, faces=set(), layers=set(), lo=1e18, hi=-1e18, dir='')), {}, []
    sig_layers = set()
    for pn, p in m['pins'].items():
        if not p['shapes']:
            continue
        if p['use'] in ('POWER', 'GROUND'):
            ls = sorted({s[0] for s in p['shapes']})
            pg[pn] = dict(layers=ls, shapes=len(p['shapes']))
            continue
        layer, *r = p['shapes'][0]
        f, off = face_of(w, h, r)
        sig_layers.add(layer)
        base = re.sub(r'\[\d+\]$', '', pn)
        if p['use'] == 'CLOCK' or base in ('clk', 'clk_i', 'ck', 'clock'):
            clk.append(dict(pin=pn, face=f, layer=layer, xy=[round((r[0] + r[2]) / 2, 3), round((r[1] + r[3]) / 2, 3)]))
        b = buses[base]
        b['bits'] += 1; b['faces'].add(f); b['layers'].add(layer); b['dir'] = p['dir']
        if off is not None:
            b['lo'], b['hi'] = min(b['lo'], off), max(b['hi'], off)
    lay_order = lambda s: sorted(s, key=lambda l: int(re.sub(r'\D', '', l) or 0))
    pins = {k: dict(bits=v['bits'], dir=v['dir'], face='/'.join(sorted(v['faces'])), layers=lay_order(v['layers']),
                    offset_um=[round(v['lo'], 3), round(v['hi'], 3)] if v['hi'] >= 0 else None) for k, v in sorted(buses.items())}
    pg_layers = lay_order({l for v in pg.values() for l in v['layers']})
    top_sig = lay_order(sig_layers)[-1] if sig_layers else None
    return dict(outline_um=[w, h], area_mm2=round(w * h / 1e6, 4), count=len(insts),
                instances=[dict(name=n, xy=[x, y], orient=o) for n, x, y, o in insts],
                clock_entry=clk[:4], pins=pins, pg=pg,
                io_budget=dict(input_delay_T=0.2, output_delay_T=0.2, period_ps=PERIOD_PS,
                               boundary='registered: pin flop on every input, flop on every output'),
                layers=dict(signal_top=top_sig, pg=pg_layers,
                            rule='signals stay below the parent strap layer; parent straps one layer above the PG layer; M8/M9 die top only',
                            violations=[v for v in (['signal on M8/M9'] if top_sig in ('M8', 'M9') else [])]),
                evidence=evidence.get(name))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('case'); ap.add_argument('--die', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--source', default=''); ap.add_argument('--version', type=int, default=1)
    ap.add_argument('--registry', default='http://127.0.0.1:8765/api/elements')
    ap.add_argument('--fixed', action='append', default=[], help='decided contract line (recorded verbatim)')
    a = ap.parse_args()
    c = Path(a.case)
    lef = {}
    for f in sorted(c.glob('*.lef')):
        parse_lef(f, lef)
    master = {}
    for line in open(c / 'die.v'):
        m = re.match(r'\s*(\w+)\s+(\\?\S+)\s*\(', line)
        if m and m.group(1) in lef:
            master[m.group(2).lstrip('\\')] = m.group(1)
    insts = defaultdict(list)
    for line in open(c / 'place.tcl'):
        m = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', line)
        if m and m.group(1) in master:
            insts[master[m.group(1)]].append((m.group(1), float(m.group(2)), float(m.group(3)), m.group(4)))
    ev = {}
    try:
        for r in json.load(urllib.request.urlopen(a.registry, timeout=20))['rows']:
            if r.get('best'):
                ev[r['element']] = dict(category=r.get('category'), **{k: r['best'].get(k) for k in ('tt', 'ff', 'drc', 'job', 'source_commit')})
    except Exception as e:  # registry optional
        print('registry unavailable:', e, file=sys.stderr)
    die = json.load(open(c / 'manifest.json')).get('die')
    slots = {n: slot(n, lef[n], insts.get(n, []), ev) for n in sorted(lef) if insts.get(n)}
    out = dict(schema='qwen-hier-contract/0 (provisional; migrate to tools/hier_contract/)', die=a.die, version=a.version,
               source=a.source, period_ps=PERIOD_PS, die_outline=die, fixed=a.fixed,
               layer_contract=dict(leaf_signals='M1-M6', leaf_pg='top layer stripes (M6 or M7 per slot)',
                                   parent_straps='one layer above children PG (M7 for qfd_tile / qfd_io_collective)',
                                   die_top='M8/M9 only'),
               slots=slots)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    viol = {n: s['layers']['violations'] for n, s in slots.items() if s['layers']['violations']}
    print(json.dumps(dict(slots=len(slots), instances=sum(s['count'] for s in slots.values()), layer_violations=len(viol))))


if __name__ == '__main__':
    main()
