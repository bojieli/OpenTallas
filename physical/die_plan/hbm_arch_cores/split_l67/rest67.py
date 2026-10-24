#!/usr/bin/env python3
"""ELEM-HBM/RECIPES2 2026-10-24: canonical remainder core of a bankq lanes6_7_bank split piece.

Input: ext.sh output (yosys: scoped as-built master @d34578d6f, params of the die_r18h5 instance, proc, leaf
ot_hdc_v41x_hcp_lanes__d4g_<v> kept, flatten, splitnets, splitcells + opt_merge -share_all (identical cells merged: the
as-built netlist the plan was cut from shares the replicated keep regs sss/ss into one net), submod of every cell except the
member leaves g_grp[0..5].u_lg = the lanes0_2 / lanes3_5 pieces).
Naming = the plan pin table (netcut labels): a cut net takes the first plan bus among its candidate labels
  (master port name; x_<member path>_<port> of each member pin on the net; the public hierarchical net names);
bus bit order = member pin bit order (distinct nets in first-use order) / master port bits in index order (compressed).
Emits <core>.sv = the extracted remainder (module <core>_x) + wrapper <core> whose ports are EXACTLY the plan buses,
and <core>.map.json (bus -> [[net, ...]], member pin -> source, ties) for the composition check.

  rest67.py --ext DIR --top MASTER --plan PINS.json --core NAME --out DIR [--hdr TEXT]"""
import argparse, collections, json, re
ap = argparse.ArgumentParser()
for k in ('ext', 'top', 'plan', 'core', 'out'):
    ap.add_argument('--' + k, required=True)
ap.add_argument('--hdr', default='')
a = ap.parse_args()
J = json.load(open(f'{a.ext}/parent.json'))['modules']
T, RM = J[a.top], J['REM']
cl = lambda s: re.sub(r'_+', '_', re.sub(r'[^A-Za-z0-9]+', '_', s)).strip('_')
rem_cell = next(c for c in T['cells'].values() if c['type'] == 'REM')
leaves = sorted([(n, c) for n, c in T['cells'].items() if c['type'] != 'REM'],
                key=lambda x: int(re.search(r'g_grp\[(\d+)\]', x[0]).group(1)))
top_bits = {}
for pn, p in T['ports'].items():
    for i, b in enumerate(p['bits']):
        if isinstance(b, int):
            top_bits.setdefault(b, (pn, i, p['direction']))
pubnames = collections.defaultdict(list)
for nn, nv in T['netnames'].items():
    if nv.get('hide_name'):
        continue
    for i, b in enumerate(nv['bits']):
        if isinstance(b, int):
            pubnames[b].append(nn)
plan = json.load(open(a.plan))
pw = collections.OrderedDict()
for q in plan:
    m = re.match(r'^(.*?)(?:\[(\d+)\])?$', q['name'])
    pw.setdefault(m.group(1), set()).add(int(m.group(2)) if m.group(2) else 0)
pw = {k: max(v) + 1 for k, v in pw.items()}
mem = collections.defaultdict(list)          # net -> member pin uses in (g, port order)
memsrc, ties = {}, {}
for n, c in leaves:
    g = int(re.search(r'g_grp\[(\d+)\]', n).group(1))
    lab = 'x_' + cl(n)
    for pn, bl in c['connections'].items():
        for i, b in enumerate(bl):
            memsrc[(g, pn, i)] = b
            if isinstance(b, int):
                mem[b].append((lab + '_' + pn, g, pn, i, c['port_directions'][pn]))
            else:
                ties[(g, pn, i)] = b
rdir = {pn: p['direction'] for pn, p in RM['ports'].items()}
rport = {}                                   # net -> [(rem port, bit)]
for pn, bl in rem_cell['connections'].items():
    for i, b in enumerate(bl):
        rport.setdefault(b, []).append((pn, i))
# reads of each REM input port bit inside REM (a top port wire stays whole: bits REM never reads are not pins)
rem_read = set()
for c in RM['cells'].values():
    for pn, bl in c['connections'].items():
        if c.get('port_directions', {}).get(pn, 'input') != 'output':
            rem_read.update(b for b in bl if isinstance(b, int))
for cn, nv in RM['netnames'].items():
    pass
rem_out_drv = {}
rbits = {pn: p['bits'] for pn, p in RM['ports'].items()}
# REM output ports driven by REM internal connections (assign) count as read for an input bit feeding them
for pn, p in RM['ports'].items():
    if p['direction'] == 'output':
        rem_read.update(b for b in p['bits'] if isinstance(b, int))
bus = collections.defaultdict(list)          # plan bus -> [(order key, net, dir)]
unread_in, undriven = [], []
for b, rp in rport.items():
    if not isinstance(b, int):
        continue
    d = rdir[rp[0][0]]
    if b in top_bits:
        pn, i, _ = top_bits[b]
        if d == 'input':
            ib = RM['ports'][rp[0][0]]['bits'][rp[0][1]]
            if ib not in rem_read:
                unread_in.append(f'{pn}[{i}]'); continue
        bus[pn].append(((i,), b, d))
        continue
    if b not in mem:
        if d == 'input':
            undriven.append(rp)
        continue
    cands = [u[0] for u in mem[b]] + [cl(x) for x in pubnames[b]] + [cl(re.sub(r'\[\d+\]$', '', x)) for x in pubnames[b]]
    name = next((x for x in cands if x in pw), None)
    if name is None:
        raise SystemExit(f'NO_PLAN_NAME net {b}: candidates {cands[:6]}')
    u = next((u for u in mem[b] if u[0] == name), mem[b][0])
    bus[name].append(((u[1], u[3]), b, d))
if undriven:
    raise SystemExit(f'UNDRIVEN remainder inputs {undriven[:5]}')
# a master input port the plan pins at FULL width although the remainder reads only some bits (the as-built hierarchical
# netlist registers them in the stage's descriptor taps, then never uses them): identity bit order, unread bits are
# plan pins kept as registered sinks (recipe retain_unused_input_bits), not logic
retain = {}
for pn, p in T['ports'].items():
    if p['direction'] == 'input' and pn in pw and pn in bus and pw[pn] == len(p['bits']) and len(bus[pn]) < pw[pn]:
        have = {k[0] for k, _, _ in bus[pn]}
        retain[pn] = [i for i in range(pw[pn]) if i not in have]
        for i in retain[pn]:
            bus[pn].append(((i,), ('unread', pn, i), 'input'))
mine = {k: len(v) for k, v in bus.items()}
diff = [(k, mine.get(k), pw.get(k)) for k in sorted(set(mine) | set(pw)) if mine.get(k) != pw.get(k)]
ins = sum(len(v) for v in bus.values() if v[0][2] == 'input'); outs = sum(len(v) for v in bus.values() if v[0][2] == 'output')
pin_in = sum(pw[k] for k in pw if k in bus and bus[k][0][2] == 'input')
rep = dict(retain_unused_input_bits=retain, cut_bits=[ins, outs], plan_pins=sum(pw.values()), bus_diffs=diff, unread_master_bits=len(unread_in),
           leaf_ties=collections.Counter(f'{pn}={v}' for (g, pn, i), v in ties.items()))
print(json.dumps(rep, default=str))
if diff:
    raise SystemExit('PORT_CHECK FAIL')
order = {k: [b for _, b, _ in sorted(v)] for k, v in bus.items()}
bdir = {k: v[0][2] for k, v in bus.items()}
# ---- emit
rem = open(f'{a.ext}/rem.v').read()
rem = re.sub(r'^module REM\(', f'module {a.core}_x(', rem, count=1, flags=re.M)
assert f'module {a.core}_x(' in rem
net_of = {}
for k, bl in order.items():
    for i, b in enumerate(bl):
        net_of[b] = (k, i)
W = []
dec = [f"    {bdir[k]} wire {'' if pw[k] == 1 and k not in T['ports'] or pw[k] == 1 else f'[{pw[k]-1}:0] '}{k}" for k in pw]
W.append(f"module {a.core} (\n" + ",\n".join(dec) + "\n);")
conns = []
for pn, bl in rem_cell['connections'].items():
    terms = []
    for b in reversed(bl):                      # msb first
        if not isinstance(b, int):
            terms.append(f"1'b{b}" if b in '01' else "1'bx"); continue
        if b in net_of:
            k, i = net_of[b]
            terms.append(f'{k}[{i}]' if pw[k] > 1 else k)
        elif rdir[pn] == 'input':
            terms.append("1'b0")                 # master bit the remainder never reads (whole-wire port)
        else:
            terms.append('')                     # remainder output bit with no outside reader
    ref = pn if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', pn) else '\\' + pn + ' '
    if rdir[pn] == 'output' and all(t == '' for t in terms):
        conns.append(f'.{ref}()'); continue
    if rdir[pn] == 'output':
        w = len(bl)
        wn = f'o__{len(conns)}'
        W.append(f'    wire [{w-1}:0] {wn};')
        for j, b in enumerate(bl):
            if isinstance(b, int) and b in net_of:
                k, i = net_of[b]
                if (k, i) not in getattr(a, '_assigned', set()):
                    a.__dict__.setdefault('_assigned', set()).add((k, i))
                    W.append(f"    assign {k if pw[k] == 1 else f'{k}[{i}]'} = {wn}[{j}];")
        conns.append(f'.{ref}({wn})')
    else:
        conns.append(f'.{ref}({{' + ', '.join(terms) + '})')
W.append(f'    {a.core}_x u_x (\n        ' + ',\n        '.join(conns) + ');')
W.append('endmodule')
miss = [(k, i) for k in order for i in range(pw[k]) if bdir[k] == 'output' and (k, i) not in a.__dict__.get('_assigned', set())]
if miss:
    raise SystemExit(f'UNDRIVEN outputs {miss[:5]}')
hdr = '\n'.join('// ' + l for l in a.hdr.splitlines())
open(f'{a.out}/{a.core}.sv', 'w').write(hdr + '\n`timescale 1ns/1ps\n' + rem + '\n' + '\n'.join(W) + '\n')
# member pin -> source for the composition (plan bus bit / master port bit / constant)
src = {}
for (g, pn, i), b in memsrc.items():
    if not isinstance(b, int):
        src[f'{g}.{pn}.{i}'] = ['const', b]
    elif b in net_of:
        src[f'{g}.{pn}.{i}'] = ['pin', *net_of[b]]
    elif b in top_bits:
        src[f'{g}.{pn}.{i}'] = ['top', top_bits[b][0], top_bits[b][1]]
    else:
        src[f'{g}.{pn}.{i}'] = ['??', b]
tbb = {k: [(top_bits[b][1] if isinstance(b, int) else b[2]) for b in order[k]] for k in order if k in T['ports']}
feed = {}
for pn, p in T['ports'].items():
    if p['direction'] == 'output':
        for i, b in enumerate(p['bits']):
            if isinstance(b, int) and b in top_bits and top_bits[b][2] == 'input':
                feed.setdefault(pn, []).append((i, top_bits[b][0], top_bits[b][1]))   # master port-to-port wire (partition route)
top_const = {pn: [(i, b) for i, b in enumerate(p['bits']) if not isinstance(b, int)] for pn, p in T['ports'].items() if p['direction'] == 'output'}
json.dump(dict(report=rep, buses={k: [pw[k], bdir[k]] for k in pw}, member_src=src, top_bus_bits=tbb, top_const_out={k: v for k, v in top_const.items() if v}, top_feedthrough=feed,
               top_ports={pn: [p['direction'], len(p['bits'])] for pn, p in T['ports'].items()},
               unread_master_bits=unread_in), open(f'{a.out}/{a.core}.map.json', 'w'), indent=0, default=str)
print('wrote', f'{a.out}/{a.core}.sv')
