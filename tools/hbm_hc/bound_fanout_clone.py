"""Bounded-fanout cell graph by driver cloning (HBM-HCROOT6 10-20; method of results/rtl/fp32_add_native_clone_1020/
svc7_bound_graph.py, rewritten with an incremental worklist so it scales to ~10^5-cell tiles).

Input: a Yosys write_json of a MAPPED, flattened netlist (Liberty cells read with read_liberty -lib).  BUF/INV cells
are canonicalised to (net, inverted) edges; then every driver (logic AND state) whose net has more than --limit loads
is cloned: each clone is the same primitive with the same input functions (same nets, same clock / reset), and the
loads are split between the original and its clones.  Cloning adds loads to the clone's own inputs, which are bounded
in turn (recursive).  Clock pins (CLK) are not loads (actual clock nets are CTS's job).  An input port with more than
--limit loads, or a multi-output primitive, is a frontier: the RTL must register / distribute it (reported, no output).
A structural ledger proves, before anything is emitted, that every primitive's type and every input function equal its
origin's, and that every output port function is unchanged.  Unreset clones equal their origin after the first active
edge (same D); reset clones are equal at all times after reset.  No buffer hides a load (BUF/INV are transparent to the
native census; this tool emits only real replicated drivers and one INVx1 per inverted edge family).
"""
import argparse, hashlib, json, sys
from collections import defaultdict
from pathlib import Path

BUFINV = ('BUF', 'INV', 'CKINV', 'HB')
CLOCK_PINS = {'CLK'}


def bound(m, limit, clock_ports):
    cells = {n: c for n, c in m['cells'].items() if c['type'] != '$scopeinfo'}
    aliases, removed = {}, set()
    for n, c in cells.items():
        if c['type'].startswith(BUFINV):
            ins = [b for p, bs in c['connections'].items() if c['port_directions'][p] == 'input' for b in bs]
            outs = [b for p, bs in c['connections'].items() if c['port_directions'][p] == 'output' for b in bs]
            assert len(ins) == len(outs) == 1, (n, c['type'])
            aliases[outs[0]] = (ins[0], c['type'].startswith(('INV', 'CKINV')))
            removed.add(n)
    memo = {}
    def norm(b):
        if b in memo: return memo[b]
        inv, x, seen = False, b, set()
        while x in aliases:
            assert x not in seen, 'BUF/INV cycle'
            seen.add(x); x, v = aliases[x]; inv ^= v
        if isinstance(x, str) and inv and x in ('0', '1'):
            x, inv = str(1 - int(x)), False
        memo[b] = (x, inv)
        return memo[b]
    cells = {n: c for n, c in cells.items() if n not in removed}
    origin = {n: n for n in cells}
    family = {}
    driver = {}
    inputs = {}
    outport = {}
    for n, c in cells.items():
        outs = [(p, b) for p, bs in c['connections'].items() if c['port_directions'][p] == 'output' for b in bs]
        for p, b in outs:
            driver[b] = n; family[b] = b
        outport[n] = outs
        inputs[n] = {p: [norm(b) for b in bs] for p, bs in c['connections'].items()
                     if c['port_directions'][p] == 'input'}
    outputs = {p: [norm(b) for b in v['bits']] for p, v in m['ports'].items() if v['direction'] == 'output'}
    clock = {b for p in clock_ports for b in m['ports'].get(p, {}).get('bits', [])}
    nextbit = max([b for c in cells.values() for bs in c['connections'].values() for b in bs if isinstance(b, int)]
                  + [b for v in m['ports'].values() for b in v['bits'] if isinstance(b, int)] + [1]) + 1
    loads = defaultdict(list)            # net -> [('cell', name, pin, idx) | ('port', None, pin, idx)]
    for n, ports in inputs.items():
        for p, bs in ports.items():
            if p in CLOCK_PINS: continue
            for i, (b, inv) in enumerate(bs):
                if isinstance(b, int) and b not in clock: loads[b].append(('cell', n, p, i))
    for p, bs in outputs.items():
        for i, (b, inv) in enumerate(bs):
            if isinstance(b, int): loads[b].append(('port', None, p, i))
    inport = {}
    for p, v in m['ports'].items():
        if v['direction'] == 'input':
            for i, pb in enumerate(v['bits']): inport[norm(pb)[0]] = '%s[%d]' % (p, i)
    work = [b for b, s in loads.items() if len(s) > limit]
    clones, frontier = 0, []
    while work:
        b = work.pop()
        sinks = loads[b]
        if len(sinks) <= limit: continue
        if b not in driver:
            frontier.append(dict(reason='input port needs RTL distribution (register it)', port=inport.get(b, str(b)),
                                 loads=len(sinks)))
            continue
        src = driver[b]
        if len(outport[src]) != 1:
            frontier.append(dict(reason='multi-output primitive', cell=src, type=cells[src]['type'], loads=len(sinks)))
            continue
        op = outport[src][0][0]
        k = (len(sinks) + limit - 1) // limit
        per = (len(sinks) + k - 1) // k
        keep, rest = sinks[:per], sinks[per:]
        loads[b] = keep
        for g in range(0, len(rest), per):
            fresh = nextbit; nextbit += 1; clones += 1
            name = 'bfc_%d' % clones
            cells[name] = {'type': cells[src]['type'], 'port_directions': cells[src]['port_directions'],
                           'connections': {**cells[src]['connections'], op: [fresh]}}
            origin[name] = origin[src]; family[fresh] = family[b]; driver[fresh] = name
            outport[name] = [(op, fresh)]
            inputs[name] = {p: list(bs) for p, bs in inputs[src].items()}
            for p, bs in inputs[name].items():
                if p in CLOCK_PINS: continue
                for i, (x, inv) in enumerate(bs):
                    if isinstance(x, int) and x not in clock:
                        loads[x].append(('cell', name, p, i))
                        if len(loads[x]) == limit + 1: work.append(x)
            grp = rest[g:g + per]
            loads[fresh] = grp
            for kind, n, p, i in grp:
                bs = inputs[n][p] if kind == 'cell' else outputs[p]
                _, inv = bs[i]; bs[i] = (fresh, inv)
    # structural ledger: same type, same input functions (families), same port functions
    orig_cells = m['cells']
    for n, c in cells.items():
        o = orig_cells[origin[n]]
        assert c['type'] == o['type'], n
        for p, bs in inputs[n].items():
            want = [norm(b) for b in o['connections'][p]]
            got = [(family.get(x, x), v) for x, v in bs]
            assert got == want, (n, p)
    for p, bs in outputs.items():
        assert [(family.get(x, x), v) for x, v in bs] == [norm(b) for b in m['ports'][p]['bits']], p
    maxl = max([len(s) for s in loads.values()] + [0])
    return cells, inputs, outputs, origin, clones, frontier, maxl


def emit(m, cells, inputs, outputs, top, origin=None, tags=()):
    # --tag PREFIX=SUBSTR (HBM-HCROOT8 10-20): a cell whose ORIGIN name contains SUBSTR is emitted as PREFIX + 'c<i>', so a
    # kit SDC can name a group (e.g. the Sinkhorn registers of a declared multicycle) after the cell names are gone.
    def cname(n, i):
        o = (origin or {}).get(n, n)
        for pre, sub in tags:
            if sub in o: return '%sc%d' % (pre, i)
        return 'c%d' % i
    L = ['// GENERATED by tools/hbm_hc/bound_fanout_clone.py (bounded-fanout cell graph); do not edit.',
         'module ' + top + '(' + ','.join(m['ports']) + ');']
    for p, v in m['ports'].items():
        w = len(v['bits']); L.append(v['direction'] + ' wire ' + ('' if w == 1 else '[%d:0] ' % (w - 1)) + p + ';')
    wires, invs, body = set(), {}, []
    def bit(b):
        if isinstance(b, str): return "1'b" + b
        wires.add(b); return 'n%d' % b
    def edge(e):
        b, inv = e
        if not inv: return bit(b)
        if e not in invs: invs[e] = 'iv%d' % len(invs)
        bit(b); return invs[e]
    for p, v in m['ports'].items():
        if v['direction'] == 'input':
            for i, b in enumerate(v['bits']):
                body.append('assign %s = %s;' % (bit(b), p if len(v['bits']) == 1 else '%s[%d]' % (p, i)))
    for i, (n, c) in enumerate(cells.items()):
        pins = []
        for p, bs in c['connections'].items():
            conn = [edge(e) for e in inputs[n][p]] if p in inputs[n] else [bit(b) for b in bs]
            pins.append('.%s(%s)' % (p, conn[0] if len(conn) == 1 else '{' + ','.join(reversed(conn)) + '}'))
        body.append('(* keep = 1, dont_touch = 1 *) %s %s (%s);' % (c['type'], cname(n, i), ','.join(pins)))
    for p, bs in outputs.items():
        for i, e in enumerate(bs):
            body.append('assign %s = %s;' % (p if len(bs) == 1 else '%s[%d]' % (p, i), edge(e)))
    L += ['wire n%d;' % b for b in sorted(wires)] + ['wire %s;' % v for v in invs.values()]
    for (b, _), o in invs.items():
        L.append('(* keep = 1, dont_touch = 1 *) INVx1_ASAP7_75t_R %s_c (.A(%s),.Y(%s));' % (o, bit(b), o))
    return '\n'.join(L + body + ['endmodule']) + '\n'


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('mapped_json'); a.add_argument('--top', required=True); a.add_argument('--name', required=True)
    a.add_argument('--out', required=True); a.add_argument('--limit', type=int, default=24)
    a.add_argument('--clock-port', action='append', default=['clk'])
    a.add_argument('--tag', action='append', default=[], help='PREFIX=SUBSTR: name cells whose origin contains SUBSTR PREFIXc<i>')
    args = a.parse_args()
    raw = Path(args.mapped_json).read_bytes(); d = json.loads(raw)
    m = d['modules'][args.top]
    cells, inputs, outputs, origin, n, frontier, maxl = bound(m, args.limit, args.clock_port)
    rep = dict(source_sha256=hashlib.sha256(raw).hexdigest(), source_top=args.top, output_top=args.name,
               limit=args.limit, original_cells=len(m['cells']), final_cells=len(cells), clones=n,
               max_loads_after=maxl, frontier=frontier[:200], frontier_count=len(frontier),
               invariant='every clone: same primitive type, same input functions (nets/clock/reset); port functions identical')
    if frontier:
        Path(args.out + '.blocked.json').write_text(json.dumps(rep, indent=2) + '\n')
        print('BFC BLOCKED frontier=%d clones=%d' % (len(frontier), n)); print(json.dumps(frontier[:20], indent=1))
        return 2
    tags = [tuple(t.split('=', 1)) for t in args.tag]
    text = emit(m, cells, inputs, outputs, args.name, origin, tags)
    if tags: rep['tags'] = {p: sum(1 for k in cells if any(sb in origin.get(k, k) for pp, sb in tags if pp == p)) for p, _ in tags}
    Path(args.out).write_text(text)
    rep['output_sha256'] = hashlib.sha256(text.encode()).hexdigest()
    by = defaultdict(int)
    for k, o in origin.items():
        if k != o: by[o] += 1
    rep['clones_by_origin_top'] = sorted(by.items(), key=lambda x: -x[1])[:100]
    Path(args.out + '.ledger.json').write_text(json.dumps(rep, indent=2) + '\n')
    print('BFC clones=%d final_cells=%d max_loads=%d structural_invariant=PASS' % (n, len(cells), maxl))
    return 0


if __name__ == '__main__':
    sys.exit(main())
