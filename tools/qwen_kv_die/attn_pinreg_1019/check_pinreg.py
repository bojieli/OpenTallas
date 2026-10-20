#!/usr/bin/env python3
"""Independent re-read of a native netlist: every input port's first contacts are flop D pins (clock: CLK only; constants
excluded), every output port is driven by a flop or a tie cell, max non-clock fanout, max reg->reg comb levels.
Usage: check_pinreg.py <netlist.v> [--json out]"""
import re, sys, json, collections
src = open(sys.argv[1]).read()
CELL = re.compile(r'^\s*(?:\(\*[^*]*\*\)\s*)?(\w+)\s+(c\w+)\s*\((.*)\);\s*$', re.M)
OUTS = {'Y', 'QN', 'Q', 'H', 'L', 'CON', 'SN'}
cells = {n: (ms, {k: v.strip() for k, v in re.findall(r'\.(\w+)\(([^()]*)\)', c)}) for ms, n, c in CELL.findall(src)}
asg = re.findall(r'^\s*assign\s+(\S+)\s*=\s*(\S+?)\s*;', src, re.M)
inp = {l: r for l, r in asg if re.fullmatch(r'n\d+', l)}
outp = {l: r for l, r in asg if not re.fullmatch(r'n\d+', l)}
drv, loads = {}, collections.defaultdict(list)
for n, (ms, p) in cells.items():
    for k, v in p.items():
        (drv.__setitem__(v, (n, k)) if k in OUTS else loads[v].append((n, k)))
isff = lambda ms: ms.startswith('DFF')
bad_in, bad_out = [], []
for net, port in inp.items():
    for c, k in loads.get(net, []):
        ms = cells[c][0]
        if port == 'ck':
            ok = isff(ms) and k == 'CLK'
        else:
            ok = isff(ms) and k == 'D'
        if not ok:
            bad_in.append((port, c, ms, k))
for port, net in outp.items():
    if net in inp:
        bad_out.append((port, 'feedthrough')); continue
    c, k = drv.get(net, (None, None))
    while c is not None and cells[c][0].startswith(('BUF', 'INV')):   # transparent buffer/inverter at the face
        c, k = drv.get(cells[c][1]['A'], (None, None))
    if c is None or not (isff(cells[c][0]) or cells[c][0].startswith('TIE')):
        bad_out.append((port, c, cells[c][0] if c else None))
clk_net = next(n for n, p in inp.items() if p == 'ck')
direct_fo = {n: len(l) for n, l in loads.items() if n != clk_net}
# Count real logical endpoint pins through every transparent BUF/INV chain.
# Direct counts hid eight reset FF roots with 42..131 native RESETN loads.
port_loads = collections.defaultdict(set)
for port, net in outp.items():
    port_loads[net].add(('PORT', port))
memo_ends = {}
def endpoints(net, seen=frozenset()):
    if net in memo_ends: return memo_ends[net]
    if net in seen: raise RuntimeError('transparent cycle: ' + net)
    result = set(port_loads[net])
    for name, pin in loads.get(net, []):
        ms, ps = cells[name]
        if ms.startswith(('BUF', 'INV', 'HB')):
            ys = [v for p, v in ps.items() if p in OUTS]
            if len(ys) != 1: raise RuntimeError('unknown transparent cell: ' + name)
            result.update(endpoints(ys[0], seen | {net}))
        elif pin not in ('CLK', 'CK'):
            result.add((name, pin))
    memo_ends[net] = frozenset(result)
    return memo_ends[net]
fo = {n: len(endpoints(n)) for n in set(drv) | set(inp) if n != clk_net}
over_fo = sorted(((n, count) for n, count in fo.items() if count > 32), key=lambda x: -x[1])
fo_max = max(fo.values())
# comb levels: longest path (cells) from FF/port to FF D / port
memo = {}
sys.setrecursionlimit(100000)
def lv(net):
    if net in memo: return memo[net]
    if net in inp or net not in drv: memo[net] = 0; return 0
    c, _ = drv[net]; ms, p = cells[c]
    if isff(ms) or ms.startswith('TIE'): memo[net] = 0; return 0
    memo[net] = 1 + max([lv(v) for k, v in p.items() if k not in OUTS] or [0]); return memo[net]
dl = [(lv(p['D']), c) for c, (ms, p) in cells.items() if isff(ms)]
undriven = sorted(n for n in loads if n not in drv and n not in inp and not n.startswith("1'"))
undriven += sorted(n for n in outp.values() if n not in drv and n not in inp)
res = dict(undriven=len(undriven), undriven_examples=undriven[:10], cells=len(cells), ff=sum(isff(m) for m, _ in cells.values()), bad_inputs=len(bad_in), bad_outputs=len(bad_out),
           bad_input_examples=bad_in[:10], bad_output_examples=bad_out[:10], tie_outputs=sum(1 for p, n in outp.items() if n in drv and cells[drv[n][0]][0].startswith('TIE')),
           fanout_max_nonclock=fo_max, fanout_max_net=max(fo, key=fo.get), fanout_method='all_driver_BUF_INV_transparent_native_pins', fanout_over32=over_fo, direct_fanout_max_nonclock=max(direct_fo.values()), ff_d_levels_max=max(dl)[0], ff_d_levels_worst=sorted(dl)[-5:])
print(json.dumps(res))
if len(sys.argv) > 3 and sys.argv[2] == '--json': json.dump(res, open(sys.argv[3], 'w'), indent=1)
ok = not bad_in and not bad_out and not undriven and not over_fo
print('CHECK_PINREG', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
