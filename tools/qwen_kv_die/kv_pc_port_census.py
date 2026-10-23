#!/usr/bin/env python3
"""KVPC-R 10-23: per-port registration / clock-domain census of a flattened tile (yosys write_json after proc; flatten).

For every top port bit: input -> the set of cells it reaches through pure wiring / buffers ($buf/$pos), and whether ALL of
them are flip-flop D pins (flop-direct) ; output -> its driver, flop-direct when the driver is a flip-flop Q.  The port's
clock domain = the clock nets of the flip-flops reached through combinational logic (any depth, stopping at flops).
Usage: kv_pc_port_census.py FLAT.json TOP OUT.json
"""
import json
import sys
from collections import defaultdict, deque

FF = {'$dff', '$adff', '$dffe', '$adffe', '$sdff', '$sdffe', '$sdffce', '$aldff', '$aldffe', '$dffsr', '$dffsre'}
WIRE = {'$buf', '$pos'}


def main(fn, top, out):
    d = json.load(open(fn))
    m = d['modules'][top]
    names = {}
    for n, v in m['netnames'].items():
        for b in v['bits']:
            if isinstance(b, int) and (b not in names or n.startswith(('ck', 'hck'))):
                names.setdefault(b, n)
    port_bit = {}
    for p, v in m['ports'].items():
        for i, b in enumerate(v['bits']):
            port_bit[(p, i)] = b
    clk_names = {}
    for p in ('ck', 'hck'):
        if p in m['ports']:
            clk_names[m['ports'][p]['bits'][0]] = p
    sinks = defaultdict(list)    # bit -> [(cell, pin)]
    driver = {}                  # bit -> (cell, pin)
    cells = m['cells']
    for cn, c in cells.items():
        for pin, bits in c['connections'].items():
            dirn = c.get('port_directions', {}).get(pin, 'input')
            for b in bits:
                if not isinstance(b, int):
                    continue
                if dirn == 'output':
                    driver[b] = (cn, pin)
                else:
                    sinks[b].append((cn, pin))

    def clk_of(cn):
        c = cells[cn]
        b = c['connections'].get('CLK', [None])[0]
        if b is None:
            return 'macro:' + c['type']
        return clk_names.get(b, 'net:%s' % names.get(b, b))

    def fwd(b0):
        """input bit: (flop_direct, domains)"""
        direct, doms, seen, q = True, set(), {b0}, deque([(b0, 0)])
        while q:
            b, depth = q.popleft()
            for cn, pin in sinks.get(b, []):
                t = cells[cn]['type']
                if t in FF:
                    if pin != 'D' or depth:
                        direct = direct and pin == 'D' and not depth
                    doms.add(clk_of(cn))
                    continue
                if not t.startswith('$'):
                    direct = False
                    doms.add('macro:' + t if 'sram' in t else 'cell:' + t)
                    continue
                if t not in WIRE:
                    direct = False
                for opin, obits in cells[cn]['connections'].items():
                    if cells[cn].get('port_directions', {}).get(opin) == 'output':
                        for ob in obits:
                            if isinstance(ob, int) and ob not in seen:
                                seen.add(ob)
                                q.append((ob, depth + (t not in WIRE)))
        return direct, doms

    def bwd(b0):
        direct, doms, seen, q, first = True, set(), {b0}, deque([b0]), True
        while q:
            b = q.popleft()
            dv = driver.get(b)
            if dv is None:
                if b in [port_bit[k] for k in ()]:
                    pass
                direct = False
                doms.add('port_or_const')
                first = False
                continue
            cn, pin = dv
            t = cells[cn]['type']
            if t in FF:
                doms.add(clk_of(cn))
                first = False
                continue
            if not t.startswith('$'):
                doms.add('macro:' + t)
                direct = False
                first = False
                continue
            if t not in WIRE:
                direct = False
            first = False
            for ipin, ibits in cells[cn]['connections'].items():
                if cells[cn].get('port_directions', {}).get(ipin) != 'output':
                    for ib in ibits:
                        if isinstance(ib, int) and ib not in seen:
                            seen.add(ib)
                            q.append(ib)
        return direct, doms

    res = {}
    inbits = set(b for (p, i), b in port_bit.items() if m['ports'][p]['direction'] == 'input')
    for p, v in m['ports'].items():
        rows = []
        for i, b in enumerate(v['bits']):
            if not isinstance(b, int):
                rows.append((True, {'const'}))
                continue
            if v['direction'] == 'input':
                rows.append(fwd(b))
            else:
                dr, ds = bwd(b)
                if b in inbits:
                    dr, ds = False, {'feedthrough'}
                rows.append((dr, ds))
        doms = sorted(set().union(*[r[1] for r in rows])) if rows else []
        res[p] = dict(dir=v['direction'], width=len(rows), flop_direct=sum(1 for r in rows if r[0]), domains=doms)
    json.dump(res, open(out, 'w'), indent=1, sort_keys=True)
    for p, r in sorted(res.items()):
        print(f"{p:24s} {r['dir']:6s} w={r['width']:4d} direct={r['flop_direct']:4d} dom={','.join(r['domains'])[:120]}")


if __name__ == '__main__':
    main(*sys.argv[1:4])
