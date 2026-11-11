#!/usr/bin/env python3
"""trace_conns.py BOUND.sv PLAN TYPE CC_IN CC_OUT : bind-traced core_conns for one pv type.
For each hard-core port: nets driven through ot_dp_dly delay lines (pd<D>_<bus>_<bit>) or *_q landing regs resolve to
the face bus they come from; w_* nets resolve to the other core(s) on the same net; anything else -> glue.
Replaces the over-merged entry (every pin -> every face bus) of TYPE in CC_IN."""
import json, re, sys, collections
sv, plan, tn, cin, cout = sys.argv[1:6]
P = json.load(open(plan)); T = P['partition_types'][tn]
buses = {b['name'] for b in T['buses']}
mang = {re.sub(r'_+', '_', b): b for b in buses}
cores = {h['inst'] for h in T['hard_cores']}
cm = {re.sub(r'_+', '_', c): c for c in cores}
txt = open(sv).read()
inst_re = re.compile(r'^\s*(\w+)\s+(?:#\(.*?\)\s*)?u_(\w+)\s*\((.*?)\n\s*\);', re.M | re.S)
port_re = re.compile(r'\.(\w+)\s*\((.*?)\)\s*(?:,|$)', re.S)
def bus_of(tok):
    tok = tok.strip()
    m = re.match(r'pd\d+_(\w+?)_\d+(?:\[\d+\])?$', tok)
    if m:
        b = mang.get(m.group(1))
        return ('bus:' + b) if b else None
    m = re.match(r'(\w+)_q(?:\[\d+(?::\d+)?\])?$', tok)
    if m and m.group(1) in buses: return 'bus:' + m.group(1)
    return None
netcores = collections.defaultdict(set); ports = {}
for m in inst_re.finditer(txt):
    mod, inst, body = m.groups()
    inst = cm.get(re.sub(r'_+', '_', inst))
    if inst is None: continue
    for pm in port_re.finditer(body):
        pn, expr = pm.group(1), pm.group(2)
        toks = [t for t in re.split(r'[{},\s]+', expr) if t]
        ports[(inst, pn)] = toks
        for t in toks:
            w = re.match(r'(w_\w+?)(?:\[\d+(?::\d+)?\])?$', t)
            if w: netcores[w.group(1)].add(inst)
cc = {}
stat = collections.Counter()
for (inst, pn), toks in ports.items():
    if pn.endswith('clk'): continue
    d = set()
    for t in toks:
        b = bus_of(t)
        if b: d.add(b); continue
        w = re.match(r'(w_\w+?)(?:\[\d+(?::\d+)?\])?$', t)
        if w:
            for o in netcores[w.group(1)] - {inst}: d.add('core:' + o)
            continue
    if not d and pn == 'y':
        g = int(re.search(r'_g(\d)_j', inst).group(1)); d = {'bus:o_pvw__u_TNQN_N_rN_b' + ('' if g == 0 else '_d%d' % g)}; stat['y_est'] += 1
    if not d: d = {'glue'}
    stat[len(d)] += 1
    cc.setdefault(inst, {})[pn] = sorted(d)
C = json.load(open(cin)); C[tn] = cc
json.dump(C, open(cout, 'w'), indent=0)
print(tn, 'cores', len(cc), 'ports', sum(len(v) for v in cc.values()), 'dest-count hist', dict(stat))
for k in ('pvg0_p0', 'pv__u_g0_j'):
    print(k, {p: v[:3] for p, v in cc.get(k, {}).items()})
