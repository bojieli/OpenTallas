#!/usr/bin/env python3
"""qwendie-1011: write a Qwen die contract in the opentallas.hier_contract.v1 schema (tools/hier_contract/).

Inputs: the provisional contract (qwen-hier-contract/0: decisions, hierarchy, seam check, deltas) and the die case it was
exported from (elements.lef / die.v / place.tcl, re-read for per-bit pin faces).  Output: one slot per hard instance
(relay placeholders are die-top logic, summarised in 'die_top_logic', not slots), pins as contiguous bus ranges per
(face, layer), the decided deltas applied:
  D1 clock entry = a FACE pin on M6 (schema: N/S/E/W; no area pins): tile E face (q-tile plan), others the N face centre
  D2 qfd_tile_nk tree words t_out/n_a/n_b/n_y(+v*) -> W face M5/M6 bands (n_* 300-600, t_*/n_y 600-880)
  remaining M8 signal pins -> nearest face, layer kept, listed under 'open_items' (D4 review)
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hier_contract_export import parse_lef  # noqa: E402

RELAY = re.compile(r'^qfd_rly_|^qkd_rly_|_rly_')
LN = lambda l: int(l[1:])


def face(w, h, r):
    x0, y0, x1, y1 = r
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    d = {'W': cx, 'E': w - cx, 'S': cy, 'N': h - cy}
    f = min(d, key=d.get)
    return f, (cy if f in 'WE' else cx), d[f] > 0.25 * min(w, h)


def bus_ranges(entries):
    """entries: [(base, idx|None, face, layer, off)] -> pin dicts with contiguous index ranges per (base, face, layer)"""
    g = defaultdict(list)
    for b, i, f, l, off in entries:
        g[(b, f, l)].append((i, off))
    out = []
    for (b, f, l), xs in sorted(g.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        idx = sorted(i for i, _ in xs if i is not None)
        if not idx:
            out.append(dict(name=b, face=f, layer=l, offset=round(xs[0][1], 3)))
            continue
        offs = [o for _, o in xs]
        s = p = idx[0]
        for i in idx[1:] + [None]:
            if i is not None and i == p + 1:
                p = i
                continue
            out.append(dict(name=f'{b}[{p}:{s}]' if p != s else f'{b}[{s}]', face=f, layer=l,
                            span_um=[round(min(offs), 3), round(max(offs), 3)]))
            if i is not None:
                s = p = i
    return out


def tile_d2(base, f, l, off):
    if base in ('n_a', 'n_b', 'n_va'):
        return 'W', 'M5', 450.0
    if base in ('t_out', 't_vout', 'n_y', 'n_vy'):
        return 'W', 'M6', 740.0
    return f, l, off


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('provisional'); ap.add_argument('case'); ap.add_argument('--out', required=True)
    ap.add_argument('--version', type=int, required=True); ap.add_argument('--change', required=True)
    a = ap.parse_args()
    P = json.load(open(a.provisional))
    c = Path(a.case)
    lef = {}
    for f in sorted(c.glob('*.lef')):
        parse_lef(f, lef)
    master = {}
    for line in open(c / 'die.v'):
        m = re.match(r'\s*(\w+)\s+(\\?\S+)\s*\(', line)
        if m and m.group(1) in lef:
            master[m.group(2).lstrip('\\')] = m.group(1)
    pos = {}
    for line in open(c / 'place.tcl'):
        m = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', line)
        if m:
            pos[m.group(1)] = (float(m.group(2)), float(m.group(3)), m.group(4))
    cellpins, cellinfo, open_items = {}, {}, defaultdict(set)
    for cell in sorted(set(master.values())):
        if RELAY.search(cell):
            continue
        M = lef[cell]; w, h = M['w'], M['h']
        ents, pg, sig = [], set(), set()
        for pn, p in M['pins'].items():
            if not p['shapes']:
                continue
            if p['use'] in ('POWER', 'GROUND'):
                pg |= {s[0] for s in p['shapes'] if s[0]}
                continue
            m = re.match(r'^(.*)\[(\d+)\]$', pn)
            base, idx = (m.group(1), int(m.group(2))) if m else (pn, None)
            if base in ('ck', 'clk', 'clk_i'):
                continue
            l, *r = p['shapes'][0]
            f, off, area = face(w, h, r)
            if cell == 'qfd_tile_nk':
                f, l, off = tile_d2(base, f, l, off)
            elif area or LN(l) > 7:
                open_items[cell].add(f'{base}: {l} {"area" if area else "face"} pin -> {f} face (D4 review)')
            sig.add(l)
            ents.append((base, idx, f, l, off))
        pgl = max(pg, key=LN) if pg else 'M7'
        cellpins[cell] = bus_ranges(ents)
        ck = dict(pin='clk' if 'clk' in M['pins'] else 'ck', face='E', layer='M6',
                  offset=round(h / 2, 3)) if cell == 'qfd_tile_nk' else \
            dict(pin='clk' if 'clk' in M['pins'] else 'ck', face='N', layer='M6', offset=round(w / 2, 3))
        cellinfo[cell] = dict(w=w, h=h, pg=pgl, sigmax=max(sig, key=LN) if sig else 'M6', ck=ck)
    hier = {n: s.get('hierarchy') for n, s in P['slots'].items() if s.get('hierarchy')}
    pend = {n: s.get('pending') for n, s in P['slots'].items() if s.get('pending')}
    ev = {n: s.get('evidence') for n, s in P['slots'].items() if s.get('evidence')}
    do = P.get('die_outline')
    if not isinstance(do, dict):
        mf = json.load(open(c / 'manifest.json'))
        do = dict(w=mf['die_um'][0], h=mf['die_um'][1])
    slots = [dict(name=P['die'], cell=P['die'], kind='die', parent=None,
                  outline=dict(w=do['w'], h=do['h']), origin=dict(x=0.0, y=0.0, orient='R0'),
                  io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2), clock_entry=dict(pin='ref', face='S', layer='M9'),
                  pg_layer='M9', strap_layer='M9', signal_max_layer='M9', version=a.version,
                  notes='die top: M8/M9 only; relays (die_top_logic) are its only logic')]
    relays = defaultdict(int)
    for inst in sorted(master, key=lambda n: (master[n], n)):
        cell = master[inst]
        if cell not in cellinfo:
            relays[cell] += 1
            continue
        I = cellinfo[cell]; x, y, o = pos.get(inst, (None, None, 'R0'))
        pgl = I['pg']
        s = dict(name=inst, cell=cell, kind='element', parent=P['die'], outline=dict(w=I['w'], h=I['h']),
                 origin=dict(x=x, y=y, orient=o if o in ('R0', 'MX', 'MY', 'R180') else 'R0'), pins=cellpins[cell],
                 io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2, registered_in=True, registered_out=True),
                 clock_entry=I['ck'], pg_layer=pgl, strap_layer=f'M{min(LN(pgl) + 1, 9)}',
                 signal_max_layer='M6' if cell in ('qfd_tile_nk', 'qfd_io_collective') else I['sigmax'], version=a.version)
        if cell == 'qfd_tile_nk':
            s['target_insertion_ps'] = 175.0
        n = []
        if cell in hier:
            n.append('hierarchy: ' + json.dumps(hier[cell]))
        if cell in pend:
            n.append('pending: ' + pend[cell])
        if cell in ev:
            n.append('evidence: ' + json.dumps(ev[cell]))
        if n:
            s['notes'] = ' | '.join(n)
        slots.append(s)
    chg = [dict(version=v['version'], when=v['date'], change=v['note']) for v in P.get('versions', [])]
    chg.append(dict(version=a.version, when='2026-10-11', change=a.change))
    out = {'schema': 'opentallas.hier_contract.v1', 'die': P['die'], 'version': a.version, 'updated': '2026-10-11',
           'owner': 'qwendie-1011', 'clock_period_ps': P.get('period_ps', 833.333),
           'layer_defaults': dict(pg_layer='M6', strap_layer='M7', signal_max_layer='M6'), 'changelog': chg,
           'slots': slots, 'source': P.get('source'), 'fixed': P.get('fixed'), 'deltas': P.get('deltas'),
           'seam_check': P.get('seam_check'), 'die_closure': P.get('die_closure'),
           'die_top_logic': dict(relays=dict(sorted(relays.items())), total=sum(relays.values())),
           'open_items': {k: sorted(v) for k, v in sorted(open_items.items())}}
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(dict(slots=len(slots), relays=sum(relays.values()), cells=len(cellinfo), open_cells=len(open_items))))


if __name__ == '__main__':
    main()
