#!/usr/bin/env python3
"""Prepare the synthesized netlist for lock-step co-simulation against the RTL (LEC-ICG-2).
 - renames the top module to gl_<top> (the RTL keeps <top>);
 - adds a debug vector `dbg_g` in the top built from the state of every named compare point (the LEC's failing and
   unproven ff points + a sample of proved points as a mapping control), read straight from the DFF cell's QN (inverted)
   or from a kept submodule instance's q port;
 - writes the matching RTL-side vector (hierarchical refs under the bench instance) as an include file.
 - optional --mutant-icg NAME: tie that ICG instance's ENA to 1 (negative control: the bench must FAIL).
usage: prep_gate.py NETLIST TOP LEC_JSON OUT_NETLIST OUT_RTL_VEC_SVH OUT_NAMES [--controls N] [--mutant-icg INST]"""
import json, random, re, sys

args = sys.argv[1:]
mut = None; ncontrol = 300; drop = set()
if '--drop' in args:
    i = args.index('--drop'); drop = set(l.strip() for l in open(args[i + 1]) if l.strip()); del args[i:i + 2]
if '--mutant-icg' in args:
    i = args.index('--mutant-icg'); mut = args[i + 1]; del args[i:i + 2]
if '--controls' in args:
    i = args.index('--controls'); ncontrol = int(args[i + 1]); del args[i:i + 2]
net, top, lecj, out_net, out_svh, out_names = args

lec = json.load(open(lecj))
points = [f['point'] for f in lec['failing'] + lec['unproven_points']]
fail = set(points)

src = open(net).read()
# instances in the top module: TYPE \name ( ... );  -> (type, name, body)
mtop = re.search(r'\nmodule %s\((.*?)\nendmodule' % re.escape(top), src, re.S)
assert mtop, 'top not found'
tb = mtop.group(0)
inst = {}
for m in re.finditer(r'\n  (\S+) +(\\\S+|[A-Za-z_][\w$]*) +\((.*?)\);', tb, re.S):
    inst[m.group(2).lstrip('\\')] = (m.group(1), m.group(3))

def conn(body, pin):
    m = re.search(r'\.%s\(\s*(.*?)\s*\)\s*(,|$)' % pin, body, re.S)
    return m.group(1).strip() if m else None

# DFF state per flop-bit name: instance "<bit>$<celltag>"
dff = {}
for name, (typ, body) in inst.items():
    if typ.startswith('DFF') and '$' in name:
        bit = name.split('$')[0]
        q = conn(body, 'QN')
        if q and bit not in dff:
            dff[bit] = '~' + q
def gate_expr(pt):
    n = pt[len('ff:u_dut.'):]
    if n in dff:
        return dff[n]
    if n.endswith('.q'):
        i = n[:-2]
        if i in inst and not inst[i][0].endswith('_ASAP7_75t_R'):
            return conn(inst[i][1], 'q')
    return None

# controls: proved ff points whose names map (compare-point names in the gold keep list are not needed: use dff names)
random.seed(1)
ctrl_pool = sorted(b for b in dff if 'ff:u_dut.' + b not in fail and '#' not in b and b.startswith('u_e.'))
controls = ['ff:u_dut.' + b for b in random.sample(ctrl_pool, min(ncontrol, len(ctrl_pool)))]
sel, miss = [], []
for p in points + controls:
    if p in drop:
        miss.append((p, 'NO_RTL_NAME')); continue
    e = gate_expr(p)
    (sel if e else miss).append((p, e))
def rtl_ref(pt):
    n = pt[len('ff:u_dut.'):]
    # yosys flattened names: hierarchy dots stay, generate-block indices g_mac[1] stay, the last [k] is the bit
    return 'ref_e.' + n
W = len(sel)
lines = [f'  wire [{W - 1}:0] dbg_g /*verilator public_flat_rd*/;']
lines += [f'  assign dbg_g[{k}] = {e} ;' for k, (p, e) in enumerate(sel)]
tb2 = tb.replace('\nendmodule', '\n' + '\n'.join(lines) + '\nendmodule')
tb2 = tb2.replace('\nmodule %s(' % top, '\nmodule gl_%s(' % top, 1)
if mut:
    k = mut.lstrip('\\')
    typ, body = inst[k]
    e = conn(body, 'ENA')
    nb = re.sub(r'\.ENA\(\s*%s\s*\)' % re.escape(e), ".ENA(1'b1)", body, count=1)
    assert nb != body
    tb2 = tb2.replace(body, nb, 1)
    print('MUTANT: ENA of', k, 'tied 1 (was', e + ')')
src = src.replace(tb, tb2)
open(out_net, 'w').write(src)
with open(out_svh, 'w') as f:
    f.write(f'localparam integer NDBG = {W};\n')
    f.write(f'wire [{W - 1}:0] dbg_r;\n')
    for k, (p, e) in enumerate(sel):
        f.write(f'assign dbg_r[{k}] = {rtl_ref(p)};\n')
with open(out_names, 'w') as f:
    for k, (p, e) in enumerate(sel):
        f.write(f'{k}\t{"FAILPT" if p in fail else "CONTROL"}\t{p}\n')
print(f'debug bits {W} (failing/unproven mapped {sum(1 for p, _ in sel if p in fail)}/{len(points)}, controls '
      f'{sum(1 for p, _ in sel if p not in fail)}); unmapped: {len(miss)}')
for p, e in miss:
    print('  UNMAPPED', p, e or 'NO_GATE_FLOP')
