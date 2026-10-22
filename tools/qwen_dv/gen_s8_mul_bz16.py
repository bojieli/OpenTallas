#!/usr/bin/env python3
"""SQ-TAIL1 10-21: bf16-scale specialisation of the generated station multiplier (b[15:0] == 0).

station_tail1 multiplies every lane by {bf16 scale, 16'd0}.  The generic netlist qfd_dv_s8s_station_mul_data_g keeps
its flops / fan-out copies in keep_hierarchy modules, so synthesis cannot propagate the 16 zero bits into them: the
kept fan-out copies (u_dup_*) of nets that are constant-reduced in this context map to proven constant-input identity
cells (native census 45386657d counts them as transparent), and kept sdff copies with a constant D become dead
endpoints.  Result at p7a/p7b: n_7344 75 / _19030_ 73 / _14346_ 40 loads in g_sc[0..1].u_mul.

This tool performs the constant propagation at SOURCE level instead (b[15:0] = 0, through comb assigns AND kept
flops: a flop with a constant next-state is that constant after its first edge, which no valid result observes since
LAT >= 6), and re-emits module qfd_dv_s8s_station_mul_data_gz:
  * constant nets vanish (no constant ever reaches a kept module port -> no constant-input identity cell);
  * kept sdff with a constant D / R are reduced to a plain kept dff (or removed);
  * a kept fan-out copy whose function collapses to a single net (identity / inverse) is rebuilt as a REAL copy:
    the defining cone is cloned until the copy has >= 2 dynamic inputs, or, when the root is a flop, the flop itself is
    duplicated (registered fan-out, same D);
  * every comb net that loses its fan-out split is re-split by kept copies (<= PER loads each).
The cut tool (gen_s8_mul_cut.py --src qfd_dv_s8s_station_mul_data_gz) then builds the LAT 7 module from it.
Usage: gen_s8_mul_bz16.py [--report]   (rewrites the gz block in qfd_dv_s8_station_math_g.sv)"""
import re, sys
from collections import defaultdict
from pathlib import Path
R = Path(__file__).resolve().parents[2]
F = R / 'rtl/qwen_dv/s5/s8/qfd_dv_s8_station_math_g.sv'
SRC, DST = 'qfd_dv_s8s_station_mul_data_g', 'qfd_dv_s8s_station_mul_data_gz'
NET = r'n_\d+(?:_[gsp]\d+)*'
PER = 16          # kept-copy load cap for re-split nets (census limit 32)
CAP = 24          # re-split any comb/flop net whose identity-collapsed fan-out exceeds this
BEGIN, END = '// SQ-TAIL1 BZ16 BEGIN', '// SQ-TAIL1 BZ16 END'


# ---------------------------------------------------------------- expressions: ('c',v) ('n',name) ('not',x) ('and'|'or'|'xor',x,y) ('mux',s,a,b)
def parse_expr(t):
    t = t.strip()
    m = re.fullmatch(r"1'b([01])", t)
    if m: return ('c', int(m[1]))
    if re.fullmatch(NET, t): return ('n', t)
    m = re.fullmatch(r'i\[(\d+)\]', t)
    if m: return ('i', int(m[1]))
    if t.startswith('~(') and t.endswith(')') and balanced(t[2:-1]): return ('not', parse_expr(t[2:-1]))
    if t.startswith('(') and t.endswith(')') and balanced(t[1:-1]): return parse_expr(t[1:-1])
    # top-level binary / ternary split
    depth = 0
    for k, ch in enumerate(t):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif depth == 0 and ch == '?':
            rest = t[k + 1:]; d2 = 0
            for j, c2 in enumerate(rest):
                if c2 == '(':
                    d2 += 1
                elif c2 == ')':
                    d2 -= 1
                elif d2 == 0 and c2 == ':':
                    return ('mux', parse_expr(t[:k]), parse_expr(rest[:j]), parse_expr(rest[j + 1:]))
        elif depth == 0 and ch in '&|^':
            return ({'&': 'and', '|': 'or', '^': 'xor'}[ch], parse_expr(t[:k]), parse_expr(t[k + 1:]))
    raise ValueError('unparsed ' + t)


def balanced(s):
    d = 0
    for ch in s:
        d += ch == '('; d -= ch == ')'
        if d < 0: return False
    return d == 0


def simp(e, val):
    """substitute known constants (val: net -> 0/1) and simplify. Returns expr."""
    op = e[0]
    if op == 'c': return e
    if op == 'n': return ('c', val[e[1]]) if e[1] in val else e
    if op == 'not':
        x = simp(e[1], val)
        if x[0] == 'c': return ('c', 1 - x[1])
        if x[0] == 'not': return x[1]
        return ('not', x)
    if op == 'mux':
        s, a, b = simp(e[1], val), simp(e[2], val), simp(e[3], val)
        if s[0] == 'c': return a if s[1] else b
        if a == b: return a
        if a[0] == 'c' and b[0] == 'c': return s if a[1] else ('not', s)
        if a[0] == 'c': return simp(('or', s, b), {}) if a[1] else simp(('and', ('not', s), b), {})
        if b[0] == 'c': return simp(('or', ('not', s), a), {}) if b[1] else simp(('and', s, a), {})
        return ('mux', s, a, b)
    a, b = simp(e[1], val), simp(e[2], val)
    if a[0] == 'c' and b[0] == 'c':
        return ('c', {'and': a[1] & b[1], 'or': a[1] | b[1], 'xor': a[1] ^ b[1]}[op])
    if b[0] == 'c': a, b = b, a
    if a[0] == 'c':
        if op == 'and': return b if a[1] else ('c', 0)
        if op == 'or': return ('c', 1) if a[1] else b
        return simp(('not', b), {}) if a[1] else b
    return (op, a, b)


def leaves(e, out=None):
    out = [] if out is None else out
    if e[0] == 'n': out.append(e[1])
    elif e[0] in ('not', 'and', 'or', 'xor', 'mux'):
        for x in e[1:]: leaves(x, out)
    return out


def emit(e):
    op = e[0]
    if op == 'c': return f"1'b{e[1]}"
    if op == 'n': return e[1]
    if op == 'i': return f'i[{e[1]}]'
    if op == 'not': return f'~({emit(e[1])})'
    if op == 'mux': return f'({emit(e[1])}) ? ({emit(e[2])}) : ({emit(e[3])})'
    return f'({emit(e[1])}) {dict(_and="&", _or="|", _xor="^")["_" + op]} ({emit(e[2])})'


def subst(e, m):
    """replace leaf nets by expressions m[net] (dict)"""
    if e[0] == 'n': return m.get(e[1], e)
    if e[0] in ('c', 'i'): return e
    return (e[0],) + tuple(subst(x, m) for x in e[1:])


def ident(e):
    """('n',x) or ('not',('n',x)) -> (x, inverted) else None"""
    if e[0] == 'n': return e[1], False
    if e[0] == 'not' and e[1][0] == 'n': return e[1][1], True
    return None


# ---------------------------------------------------------------- netlist model
def load():
    src = F.read_text()
    if BEGIN in src:
        a = src.index(BEGIN); b = src.index(END) + len(END) + 1
        src = src[:a] + src[b:]
    a = src.index(f'module {SRC}('); b = src.index('endmodule', a) + len('endmodule')
    dupdef = {}
    for m in re.finditer(r'module (qfd_s8s_dup_n_\d+) #\(parameter integer ID=0\)\(input wire \[(\d+):0\] i,output wire y\);\nassign y = (.*);', src):
        dupdef[m[1]] = (int(m[2]) + 1, parse_expr(m[3]))
    return src, src[a:b], dupdef


def model(body, dupdef):
    lines = body.split('\n')
    comb = {}            # net -> expr (assign)
    flops = {}           # Q -> dict(type, D, R, line, id, name)
    dups = {}            # y -> dict(type, ins(list, index order i[0]..), id, name, line)
    rings = []
    a_bits = b_bits = None; ynets = errnets = None; clk = rst = None
    order = []
    inst_re = re.compile(r'^\(\* keep_hierarchy="yes" \*\) (\w+) #\(\.ID\((\d+)\)\) (\w+)\((.*)\);$')
    for i, l in enumerate(lines):
        if l.startswith('assign {') and l.rstrip().endswith('= a;'):
            a_bits = re.findall(NET, l.split('=')[0]); continue
        if l.startswith('assign {') and l.rstrip().endswith('= b;'):
            b_bits = re.findall(NET, l.split('=')[0]); continue
        if l.startswith('assign y ='): ynets = re.findall(NET, l); continue
        if l.startswith('assign err ='): errnets = re.findall(NET, l); continue
        m = re.fullmatch(r'assign (' + NET + r') = (clk|rst_n);', l)
        if m:
            if m[2] == 'clk': clk = m[1]
            else: rst = m[1]
            continue
        m = re.fullmatch(r'assign (' + NET + r') = (.*);', l)
        if m:
            comb[m[1]] = parse_expr(m[2]); order.append(('c', m[1])); continue
        m = inst_re.match(l)
        if m:
            typ, iid, name, pins = m[1], int(m[2]), m[3], m[4]
            if typ.startswith('qfd_s8s_bmath_'):
                p = dict(re.findall(r'\.(\w+)\(([^()]*)\)', pins))
                if typ == 'qfd_s8s_bmath_not':
                    comb[p['Y']] = ('not', ('n', p['A'])); order.append(('c', p['Y'])); continue
                assert p['C'] == clk, l
                flops[p['Q']] = dict(type=typ[len('qfd_s8s_bmath_'):], D=p['D'], R=p.get('R'), id=iid, name=name)
                order.append(('f', p['Q'])); continue
            if typ.startswith('qfd_s8s_dup_'):
                mi = re.fullmatch(r'\.i\(\{(.*)\}\),\.y\((' + NET + r')\)', pins)
                ins = [x.strip() for x in mi[1].split(',')][::-1]   # i[0] = last in concat
                assert len(ins) == dupdef[typ][0], l
                dups[mi[2]] = dict(type=typ, ins=ins, id=iid, name=name)
                order.append(('d', mi[2])); continue
            raise ValueError(l)
        if l.startswith('qfd_dv_s8s_ring_delay'):
            m = re.match(r'qfd_dv_s8s_ring_delay #\(\.W\((\d+)\),\.D\((\d+)\),\.ID\((\d+)\)\) (\w+)\(\.clk\((\w+)\),\.rst_n\((\w+)\),\.d\(\{(.*?)\}\),\.q\(\{(.*?)\}\)\);', l)
            rings.append(dict(W=int(m[1]), D=int(m[2]), id=int(m[3]), name=m[4], d=re.findall(NET, m[7]), q=re.findall(NET, m[8])))
            continue
    return dict(comb=comb, flops=flops, dups=dups, rings=rings, a=a_bits, b=b_bits, y=ynets, err=errnets,
                clk=clk, rst=rst, order=order, head=[l for l in lines if l.startswith(('module', 'input', 'output'))])


def dup_expr(d, dupdef):
    n, e = dupdef[d['type']]
    return subst_i(e, d['ins'])


def subst_i(e, ins):
    if e[0] == 'i': return ('n', ins[e[1]])
    if e[0] in ('c', 'n'): return e
    return (e[0],) + tuple(subst_i(x, ins) for x in e[1:])


def flop_next(f):
    """next-state expr of a kept flop"""
    D, Rn = ('n', f['D']), ('n', f['R']) if f['R'] else None
    t = f['type']
    if t == 'dff_p': return D
    act = Rn if t[6] == 'p' else ('not', Rn)      # sdff_pXv: X = reset active level, v = reset value
    rv = ('c', int(t[7]))
    return ('mux', act, rv, D)


def propagate(M, dupdef):
    val = {}
    for k, n in enumerate(M['b'][::-1]):       # b[0] = last
        if k < 16: val[n] = 0
    defs = {}
    for n, e in M['comb'].items(): defs[n] = e
    for n, d in M['dups'].items(): defs[n] = dup_expr(d, dupdef)
    changed = True
    while changed:
        changed = False
        for n, e in defs.items():
            if n in val: continue
            s = simp(e, val)
            if s[0] == 'c': val[n] = s[1]; changed = True
        for q, f in M['flops'].items():
            if q in val: continue
            s = simp(flop_next(f), val)
            if s[0] == 'c': val[q] = s[1]; changed = True
        for r in M['rings']:
            for dn, qn in zip(r['d'], r['q']):
                if qn not in val and dn in val and val[dn] == 0:   # ring storage resets / initialises to 0
                    val[qn] = 0; changed = True
    return val, defs


def report():
    src, body, dupdef = load()
    M = model(body, dupdef)
    val, defs = propagate(M, dupdef)
    nd = sum(1 for n in M['dups'] if n in val)
    nf = sum(1 for n in M['flops'] if n in val)
    nc = sum(1 for n in M['comb'] if n in val)
    print(f'const: comb {nc}/{len(M["comb"])} flops {nf}/{len(M["flops"])} dups {nd}/{len(M["dups"])}')
    # dups that collapse to identity / constant-input
    kinds = defaultdict(int)
    for n, d in M['dups'].items():
        if n in val: kinds['const'] += 1; continue
        e = dup_expr(d, dupdef); s = simp(e, val)
        if any(x in val for x in d['ins']): kinds['ident' if ident(s) else 'reduced'] += 1
        else: kinds['clean'] += 1
    print('dups', dict(kinds))
    for r in M['rings']:
        print('ring', r['name'], [(dn, val.get(dn)) for dn in r['d']])
    print('outputs const', [n for n in M['y'] + M['err'] if n in val])
    return M, val



def build(M, val, dupdef):
    """constant-free netlist: returns dict(comb, flops, dups, rings, newmods)"""
    comb, flops, dups, rings, newmods = {}, {}, {}, [], {}
    seq = [0]
    def fresh(base, tag):
        seq[0] += 1
        return f'{base}_{tag}{9000 + seq[0]}'
    for n, e in M['comb'].items():
        if n not in val: comb[n] = simp(e, val)
    for q, f in M['flops'].items():
        if q in val: continue
        nx = simp(flop_next(f), val)
        if nx == simp(flop_next(f), {}):
            flops[q] = dict(f)
        elif nx[0] == 'n':
            flops[q] = dict(type='dff_p', D=nx[1], R=None, id=f['id'], name=f['name'])
        else:
            d = fresh(q, 'g'); comb[d] = nx
            flops[q] = dict(type='dff_p', D=d, R=None, id=f['id'], name=f['name'])
    def expand(e):
        # clone the defining cone of identity leaves until >= 2 distinct dynamic leaves (comb only)
        for _ in range(8):
            lv = sorted(set(leaves(e)))
            if len(lv) >= 2: return e
            x = lv[0]
            if x in comb: e = simp(subst(e, {x: comb[x]}), {}); continue
            return e
        return e
    for y, d in M['dups'].items():
        if y in val: continue
        e = dup_expr(d, dupdef); s = simp(e, val)
        if not any(x in val for x in d['ins']):
            dups[y] = dict(d); continue
        s = expand(s)
        lv = sorted(set(leaves(s)))
        if len(lv) >= 2:
            typ = 'qfd_s8s_dupz_' + d['type'][len('qfd_s8s_dup_'):]
            body = subst(s, {x: ('i', k) for k, x in enumerate(lv)})
            prev = newmods.get(typ)
            assert prev is None or prev == (len(lv), body), (typ, prev, body)
            newmods[typ] = (len(lv), body)
            dups[y] = dict(type=typ, ins=lv, id=d['id'], name=d['name'])
        else:
            # single root: a flop (or input) -> registered copy of the flop
            x = lv[0]; inv = s[0] == 'not'
            assert x in flops, ('dup root not a flop', y, s)
            c = fresh(x, 's'); f = dict(flops[x]); f['name'] = f['name'] + f'_c{seq[0]}'; f['id'] = 3000000 + seq[0]
            flops[c] = f
            comb[y] = ('not', ('n', c)) if inv else ('n', c)
    for r in M['rings']:
        keep = [(dn, qn) for dn, qn in zip(r['d'], r['q']) if qn not in val]
        if keep:
            assert all(dn not in val for dn, _ in keep), r
            rr = dict(r); rr['d'] = [k[0] for k in keep]; rr['q'] = [k[1] for k in keep]; rr['W'] = len(keep)
            rings.append(rr)
    return dict(comb=comb, flops=flops, dups=dups, rings=rings, newmods=newmods)


def fanout(N, M):
    """census-like estimate: loads per real driver, identity assigns transparent"""
    ref = defaultdict(list)       # net -> list of consumer keys
    alias = {}
    for n, e in N['comb'].items():
        if ident(e): alias[n] = ident(e)[0]; ref[ident(e)[0]].append(('alias', n)); continue
        for x in leaves(e): ref[x].append(('c', n))
    for q, f in N['flops'].items():
        ref[f['D']].append(('fD', q))
        if f['R']: ref[f['R']].append(('fR', q))
    for y, d in N['dups'].items():
        for x in d['ins']: ref[x].append(('d', y))
    for r in N['rings']:
        for x in r['d']: ref[x].append(('r', r['name']))
    for x in M['y'] + M['err']: ref[x].append(('o', x))
    memo = {}
    def loads(n):
        if n in memo: return memo[n]
        t = 0
        for k in ref.get(n, []):
            t += loads(k[1]) if k[0] == 'alias' else 1
        memo[n] = t; return t
    drivers = [n for n in list(N['comb']) + list(N['flops']) + list(N['dups']) if n not in alias]
    drivers += [q for r in N['rings'] for q in r['q']] + [x for x in M['a'] + M['b'][:16]]
    return {n: loads(n) for n in drivers}, ref, alias


def report2():
    src, body, dupdef = load()
    M = model(body, dupdef)
    val, _ = propagate(M, dupdef)
    N = build(M, val, dupdef)
    print('built comb', len(N['comb']), 'flops', len(N['flops']), 'dups', len(N['dups']), 'newmods', len(N['newmods']), 'rings', len(N['rings']))
    fo, ref, alias = fanout(N, M)
    top = sorted(fo.items(), key=lambda x: -x[1])[:25]
    print('top fanout', top)
    # compare with the unspecialised netlist
    N0 = build(M, {}, dupdef)
    fo0, _, _ = fanout(N0, M)
    print('orig top', sorted(fo0.items(), key=lambda x: -x[1])[:12])
    return M, val, N



def write():
    src, body, dupdef = load()
    M = model(body, dupdef)
    val, _ = propagate(M, dupdef)
    N = build(M, val, dupdef)
    fo, _, _ = fanout(N, M)
    worst = max(fo.values())
    assert worst <= 32, sorted(fo.items(), key=lambda x: -x[1])[:5]
    out = [f'module {DST}(clk,a,b,y,err,rst_n);'] + [l for l in M['head'] if not l.startswith('module')]
    nets = set(N['comb']) | set(N['flops']) | set(N['dups']) | {q for r in N['rings'] for q in r['q']}
    nets |= set(M['a']) | set(M['b']) | set(M['y']) | set(M['err']) | {M['clk'], M['rst']}
    for f in N['flops'].values(): nets.add(f['D'])
    nets = sorted(nets, key=lambda n: [int(x) if x.isdigit() else x for x in re.findall(r'\d+|\D+', n)])
    out.append('wire ' + ', '.join(nets) + ';')
    out.append(f'assign {M["clk"]} = clk;')
    out.append('assign {' + ','.join(M['a']) + '} = a;')
    out.append('assign {' + ','.join(M['b']) + '} = b;   // b[15:0] == 0 by contract (BZ16): low nets unused')
    out.append('assign y = {' + ','.join(M['y']) + '};')
    out.append('assign err = {' + ','.join(M['err']) + '};')
    out.append(f'assign {M["rst"]} = rst_n;')
    for kind, n in M['order']:
        pass
    # deterministic order: original order first, then new nets
    done = set()
    def line_comb(n):
        e = N['comb'][n]
        return f'assign {n} = {emit(e)};'
    def line_flop(q):
        f = N['flops'][q]
        pins = f'.C({M["clk"]}),.D({f["D"]}),.Q({q})' + (f',.R({f["R"]})' if f['R'] else '')
        return f'(* keep_hierarchy="yes" *) qfd_s8s_bmath_{f["type"]} #(.ID({f["id"]})) {f["name"]}({pins});'
    def line_dup(y):
        d = N['dups'][y]
        return f'(* keep_hierarchy="yes" *) {d["type"]} #(.ID({d["id"]})) {d["name"]}(.i({{{",".join(d["ins"][::-1])}}}),.y({y}));'
    for kind, n in M['order']:
        if kind == 'c' and n in N['comb']: out.append(line_comb(n)); done.add(n)
        elif kind == 'f' and n in N['flops']: out.append(line_flop(n)); done.add(n)
        elif kind == 'd':
            if n in N['dups']: out.append(line_dup(n)); done.add(n)
            elif n in N['comb']: out.append(line_comb(n)); done.add(n)
    for n in N['comb']:
        if n not in done: out.append(line_comb(n))
    for q in N['flops']:
        if q not in done: out.append(line_flop(q))
    for r in N['rings']:
        out.append(f'qfd_dv_s8s_ring_delay #(.W({r["W"]}),.D({r["D"]}),.ID({r["id"]})) {r["name"]}(.clk({M["clk"]}),.rst_n({M["rst"]}),'
                   f'.d({{{",".join(r["d"])}}}),.q({{{",".join(r["q"])}}}));')
    out.append('endmodule')
    mods = []
    for typ, (k, e) in sorted(N['newmods'].items()):
        mods.append(f'(* keep_hierarchy="yes" *) module {typ} #(parameter integer ID=0)(input wire [{k-1}:0] i,output wire y);\nassign y = {emit(e)};\nendmodule')
    nconst = sum(1 for n in M['comb'] if n in val)
    hdr = (f'{BEGIN} (tools/qwen_dv/gen_s8_mul_bz16.py: {SRC} specialised for b[15:0]==0; {nconst} comb nets + '
           f'{sum(1 for n in M["flops"] if n in val)} kept flops constant-folded at source, {len(N["newmods"])} fan-out copy types '
           f'rebuilt as real copies; source fan-out max {worst})')
    blk = hdr + '\n' + '\n'.join(mods) + '\n' + '\n'.join(out) + '\n' + END + '\n'
    src = src.rstrip('\n') + '\n' + blk
    F.write_text(src)
    print(f'WROTE {DST}: comb {len(N["comb"])} flops {len(N["flops"])} dups {len(N["dups"])} newmods {sorted(N["newmods"])} fanout max {worst}')


if __name__ == '__main__' and len(sys.argv) == 1:
    write()

if __name__ == '__main__' and '--report' in sys.argv:
    report()

if __name__ == '__main__' and '--report2' in sys.argv:
    report2()
