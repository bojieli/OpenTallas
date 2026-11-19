#!/usr/bin/env python3
"""prove_relay.py OLD.json NEW.json TOP OUT.sv [--no-relay]   (FABLE-FIX-S81-GLUE 2026-11-19)
Unbounded proof that NEW = OLD with a one-cycle relay on tt_pw and dh_prog (seq_dh[186:44]) and nothing else.
Both are yosys `synth -noabc -nofsm` JSON of the SAME top with every submodule / macro a blackbox.
Free vector v = OLD state bits + OLD inputs + every blackbox output bit (keyed by instance name / port / index).
NEW registers pair with OLD registers of the same name; tt_pw_a / dh_prog_a pair with OLD tt_pw / dh_prog.
The NEW registers named tt_pw / dh_prog are the relay: each must be a plain D flop of the same clock whose D is the
Q of the _a register with the same index (checked structurally here, not by SAT), valid bits with the same reset.
bad = OR of: next-state mismatch of every paired register, mismatch of every output except tt_pw / seq_dh[186:44],
mismatch of every blackbox input bit.  bad == 0 for all v  =>  by induction NEW(t) outputs == OLD(t) outputs except the
relayed ones, which equal OLD's one cycle earlier."""
import json, re, sys
EXPR = {'$_AND_': 'A & B', '$_OR_': 'A | B', '$_XOR_': 'A ^ B', '$_XNOR_': '~(A ^ B)', '$_NOT_': '~A', '$_MUX_': 'S ? B : A',
        '$_NAND_': '~(A & B)', '$_NOR_': '~(A | B)', '$_ANDNOT_': 'A & ~B', '$_ORNOT_': 'A | ~B'}
old = json.load(open(sys.argv[1]))['modules'][sys.argv[3]]; new = json.load(open(sys.argv[2]))['modules'][sys.argv[3]]
ff = lambda c: c['type'].startswith(('$_DFF', '$_SDFF', '$_DFFE', '$_SDFFE', '$_DFFSR'))
def names(m):
    o = {}
    for nn, v in m['netnames'].items():
        if v.get('hide_name', 0): continue
        for i, b in enumerate(v['bits']):
            if isinstance(b, int): o.setdefault(b, set()).add(f'{nn}[{i}]')
    return o
def split(m):
    g, f, bb = {}, {}, {}
    for n, c in m['cells'].items():
        if c['type'] == '$scopeinfo': continue
        if ff(c): f[n] = c
        elif c['type'] in EXPR: g[n] = c
        else: bb[n] = c
    return g, f, bb
og, of, ob = split(old); ng, nf, nb = split(new)
assert set(ob) == set(nb), ('blackbox instances differ', sorted(set(ob) ^ set(nb))[:5])
on, nn = names(old), names(new)
oname = {}
for n, c in of.items():
    for x in on.get(c['connections']['Q'][0], ()): oname[x] = n
RELAY = re.compile(r'^(tt_pw|dh_prog)\[(\d+)\]$'); A = re.compile(r'^(tt_pw|dh_prog)_a\[(\d+)\]$')
pair, relay, areg = {}, {}, {}
for n, c in nf.items():
    ns = nn.get(c['connections']['Q'][0], set())
    r = [] if '--no-relay' in sys.argv else [x for x in ns if RELAY.match(x)]; a = [x for x in ns if A.match(x)]
    if a:      # yosys merges identical registers (tt_pw[i] and dh_prog[i], i <= 74, on both sides): one cell, several names
        hit = set()
        for x in a:
            k = A.match(x); hit.add(oname[f'{k[1]}[{k[2]}]']); areg[(k[1], int(k[2]))] = n
        assert len(hit) == 1, ('merged _a register pairs with several old registers', n); pair[n] = hit.pop()
    elif r:
        for x in r:
            k = RELAY.match(x); relay[(k[1], int(k[2]))] = n
    else:
        hit = {oname[x] for x in ns if x in oname}
        assert len(hit) == 1, ('unpaired register', n, sorted(ns)[:3]); pair[n] = hit.pop()
assert len(set(pair.values())) == len(pair) == len(of), (len(pair), len(of))
NR = 0 if '--no-relay' in sys.argv else 75 + 143   # --no-relay: NEW must equal OLD exactly (define off)
assert set(relay) == set(areg) and len(relay) == NR, (len(relay), len(areg))
ck = {c['connections']['C'][0] for c in nf.values()}
for k, n in relay.items():
    c = nf[n]; a = nf[areg[k]]
    assert c['connections']['D'] == a['connections']['Q'], ('relay D is not the _a register', k)
    assert 'E' not in c['connections'] and c['connections']['C'] == a['connections']['C'], ('relay has an enable / other clock', k)
    valid = k in (('tt_pw', 74), ('dh_prog', 142), ('dh_prog', 74))
    assert ('R' in c['connections']) == valid, ('relay reset shape', k)
    if valid: assert c['connections']['R'] == a['connections']['R'] and re.search(r'PN0', c['type']), k
state = sorted({c['connections']['Q'][0] for c in of.values()})
ins = sorted({b for p in old['ports'].values() if p['direction'] == 'input' for b in p['bits'] if isinstance(b, int)})
bbout = [(n, p, i) for n, c in sorted(ob.items()) for p, bs in sorted(c['connections'].items()) if c['port_directions'][p] == 'output' for i in range(len(bs))]
nv = len(state) + len(ins) + len(bbout)
L = [f'module relay_miter(input [{nv - 1}:0] v, output bad);']
vid = {('s', b): i for i, b in enumerate(state)}; vid.update({('i', b): len(state) + i for i, b in enumerate(ins)}); vid.update({('b',) + k: len(state) + len(ins) + i for i, k in enumerate(bbout)})
bn = lambda pre, b: f'{pre}{b}' if isinstance(b, int) else "1'b" + ('0' if b == 'x' else b)
def emit(m, g, f, bbs, pre, alias):
    bits = {b for c in m['cells'].values() for bs in c.get('connections', {}).values() for b in bs if isinstance(b, int)} | {b for p in m['ports'].values() for b in p['bits'] if isinstance(b, int)}
    L.extend(f'wire {pre}{b};' for b in sorted(bits))
    for n, c in bbs.items():
        for p, bs in c['connections'].items():
            if c['port_directions'][p] == 'output':
                for i, b in enumerate(bs):
                    if isinstance(b, int): alias[b] = f"v[{vid[('b', n, p, i)]}]"
    L.extend(f'assign {pre}{b}={e};' for b, e in alias.items())
    for n, c in g.items():
        e = EXPR[c['type']]
        for pin in 'ABS':
            if pin in c['connections']: e = re.sub(r'\b' + pin + r'\b', '(' + bn(pre, c['connections'][pin][0]) + ')', e)
        L.append('assign ' + bn(pre, c['connections']['Y'][0]) + '=' + e + ';')
def nxt(c, pre):
    t = c['type']; d = bn(pre, c['connections']['D'][0]); q = bn(pre, c['connections']['Q'][0])
    if 'E' in c['connections']:
        e = bn(pre, c['connections']['E'][0]); pol = re.search(r'([PN])_$', t)[1]; d = f'({e}?{d}:{q})' if pol == 'P' else f'({e}?{q}:{d})'
    if 'R' in c['connections']:
        k = re.search(r'_P([NP])([01])', t); assert k, t
        if t.startswith('$_SDFF') or t.startswith('$_DFF'):
            r = bn(pre, c['connections']['R'][0]); d = f"({('!' + r) if k[1] == 'N' else r}?1'b{k[2]}:{d})"
    return d
emit(old, og, of, ob, 'o', {**{b: f"v[{vid[('s', b)]}]" for b in state}, **{b: f"v[{vid[('i', b)]}]" for b in ins}})
al = {}
for p, v in new['ports'].items():
    if v['direction'] == 'input':
        for x, y in zip(v['bits'], old['ports'][p]['bits']):
            if isinstance(x, int): al[x] = f"v[{vid[('i', y)]}]"
for n, c in nf.items():
    if n in pair: al[c['connections']['Q'][0]] = f"v[{vid[('s', of[pair[n]]['connections']['Q'][0])]}]"
relayq = {nf[n]['connections']['Q'][0] for n in relay.values()}
for b in relayq: al[b] = "1'b0"          # never compared: every reader of a relay Q is skipped below
emit(new, ng, nf, nb, 'n', al)
bad = ['(' + nxt(of[pair[n]], 'o') + '^' + nxt(c, 'n') + ')' for n, c in nf.items() if n in pair]
skipped = 0
for p, v in old['ports'].items():
    if v['direction'] != 'output': continue
    for i, (x, y) in enumerate(zip(v['bits'], new['ports'][p]['bits'])):
        if NR and (p == 'tt_pw' or (p == 'seq_dh' and i >= 44)):
            assert y in relayq, ('relayed output bit is not a relay Q', p, i); skipped += 1; continue
        assert y not in relayq, ('unrelayed output reads a relay Q', p, i)
        bad.append('(' + bn('o', x) + '^' + bn('n', y) + ')')
for n in ob:
    for p, bs in ob[n]['connections'].items():
        if ob[n]['port_directions'][p] == 'input':
            for x, y in zip(bs, nb[n]['connections'][p]):
                assert y not in relayq, ('a submodule reads a relay Q', n, p)
                bad.append('(' + bn('o', x) + '^' + bn('n', y) + ')')
for n, c in list(ng.items()) + [(n, c) for n, c in nf.items() if n in pair]:
    for p, bs in c['connections'].items():
        if c['port_directions'][p] == 'input': assert not (set(bs) & relayq), ('logic reads a relay Q', n, p)
assert skipped == NR, skipped
L.append('assign bad=|{' + ','.join(bad) + '};'); L.append('endmodule'); open(sys.argv[4], 'w').write('\n'.join(L) + '\n')
print('RELAY_MITER comparisons', len(bad), 'free bits', nv, 'registers paired', len(pair), 'relay flops', len(relay), 'blackboxes', len(ob), 'relayed output bits', skipped)
