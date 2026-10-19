#!/usr/bin/env python3
"""L2H-PGVM 10-19: mapped-netlist boundary check (checklist item 1) on yosys write_json of the FLATTENED mapped top.
Every non-clock input port bit must reach only FF D pins (BUF/INV transparent); every output port bit must be driven by
an FF output (BUF/INV transparent).  Counts are exact (no cutoff); constant outputs are listed separately."""
import json, sys, collections
mapped, out, top = sys.argv[1], sys.argv[2], sys.argv[3]
clocks = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else {'clk_ctl', 'pg_clk'}
m = json.load(open(mapped))['modules'][top]
def is_ff(t): return t.startswith('DFF') or t.startswith('SDF') or 'DFF' in t[:8]
def is_bi(t): return t.startswith('BUF') or t.startswith('INV') or t.startswith('HB')
loads = collections.defaultdict(list); drv = {}
for name, c in m['cells'].items():
    t = c['type']
    for pin, bits in c['connections'].items():
        d = c['port_directions'].get(pin, 'input')
        for b in bits:
            if isinstance(b, str): continue
            (drv.__setitem__(b, (name, t, pin)) if d == 'output' else loads[b].append((name, t, pin)))
def first_loads(b, seen=None):
    seen = seen or set(); res = []
    for name, t, pin in loads.get(b, []):
        if is_bi(t):
            c = m['cells'][name]
            for p2, bits in c['connections'].items():
                if c['port_directions'].get(p2) == 'output':
                    for b2 in bits:
                        if b2 not in seen: seen.add(b2); res += first_loads(b2, seen)
        else: res.append((name, t, pin))
    return res
def src(b):
    while b in drv and is_bi(drv[b][1]):
        c = m['cells'][drv[b][0]]
        b = [x for p, bits in c['connections'].items() if c['port_directions'].get(p) == 'input' for x in bits][0]
    return drv.get(b)
bad_in, bad_out, const_out = [], [], []
for pn, p in m['ports'].items():
    if pn in clocks: continue
    for i, b in enumerate(p['bits']):
        if p['direction'] == 'input':
            if isinstance(b, str): continue
            nf = [(n, t, pin) for n, t, pin in first_loads(b) if not (is_ff(t) and pin == 'D')]
            if nf: bad_in.append(dict(port=f'{pn}[{i}]', non_ff_loads=len(nf), e=nf[0][1] + '/' + nf[0][2]))
        else:
            if isinstance(b, str): const_out.append(f'{pn}[{i}]'); continue
            s = src(b)
            if s is None or not is_ff(s[1]): bad_out.append(dict(port=f'{pn}[{i}]', driver=(s[1] + '/' + s[2]) if s else 'none'))
res = dict(top=top, inputs_reaching_logic=len(bad_in), outputs_from_logic=len(bad_out), constant_outputs=len(const_out),
           by_port_in=collections.Counter(x['port'].split('[')[0] for x in bad_in),
           by_port_out=collections.Counter(x['port'].split('[')[0] for x in bad_out),
           examples_in=bad_in[:10], examples_out=bad_out[:10])
json.dump(res, open(out, 'w'), indent=2)
print(json.dumps({k: res[k] for k in ('inputs_reaching_logic', 'outputs_from_logic', 'constant_outputs', 'by_port_in', 'by_port_out')}))
