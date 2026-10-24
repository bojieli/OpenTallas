#!/usr/bin/env python3
"""CORE-HBM-SPLIT (2026-10-23): bit-level connectivity of a planned hard core cut out of its as-built master.

netcut.py gives the core boundary as bit COUNTS per label.  This module keeps the identity of every member-pin bit:

  analyse(netlist, top, include, exclude=()) -> Piece
    Piece.members  [(path, netlist type, role)]  role = instance base name, ordinal-suffixed when repeated in the core
    Piece.pins     {(role, port): [cls per bit, lsb first]}  cls = ('P', k) boundary bit k, ('I', k) member<->member
                   net k, ('K', '0'|'1'|'x') constant, ('N',) unconnected
    Piece.bnd      [k] -> dict(dir, cut=<cut bus name (busify of the netcut label)>, can=(role_port label))
    Piece.cut_bits {'inp': n, 'out': n}   (equals netcut.cut, asserted)

Canonical port names are member-relative (<role>_<port>), so every replica of a core (lane k, tile k ...) gets the same
names; constants that differ between replicas (a lane index tied at the parent) become strap inputs.
"""
import re, collections, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'pins_cut'))
import netcut                                                     # noqa: E402
import gen_core_ports                                             # noqa: E402


def cbits(n, mod, expr):
    """Netlist.bits with constant values kept: 'C0' / 'C1' / 'Cx' per bit (msb first)."""
    out = []
    for e in netcut.split_concat(expr):
        e = e.strip()
        m = re.match(r"^(\d+)'([bhdo])([0-9a-fA-FxXzZ_]+)$", e)
        if m:
            w, b, v = int(m.group(1)), m.group(2), m.group(3).replace('_', '').lower()
            if b == 'b':
                s = v
            elif b == 'h':
                s = ''.join('xxxx' if ch in 'xz' else format(int(ch, 16), '04b') for ch in v)
            elif b == 'o':
                s = ''.join('xxx' if ch in 'xz' else format(int(ch, 8), '03b') for ch in v)
            else:
                s = format(int(v), 'b')
            s = s[-w:].rjust(w, '0' if s[0] in '01' else s[0])
            out += ['C' + ('x' if ch in 'xz' else ch) for ch in s]
            continue
        out += n.bits(mod, e)
    return out


def view(n, top, expand):
    top = n.resolve(top)
    insts, unions = [], []
    m = n.mods[top]

    def pfx(pre, b):
        return b if b.startswith('C') and b in ('C0', 'C1', 'Cx') else pre + b

    def emit(mod, pre):
        for l, r in mod.assigns:
            for a, b in zip(cbits(n, mod, l), cbits(n, mod, r)):
                unions.append((pfx(pre, a), pfx(pre, b)))
        for t, i, conns in mod.insts:
            name = pre + i
            cb = {pn: [pfx(pre, b) for b in cbits(n, mod, ex)] for pn, ex in conns.items()}
            if name in expand and t in n.mods:
                sub = n.mods[t]
                for pn, bl in cb.items():
                    sb = [name + '/' + b for b in n.bits(sub, pn)]
                    for a, b in zip(sb, bl):
                        unions.append((a, b))
                emit(sub, name + '/')
            else:
                insts.append((name, t, cb))
    emit(m, '')
    return insts, unions


class Piece:
    pass


def _nat(p):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', p)]


def roles_of(paths):
    """role = instance base name; repeated base names get ordinals in natural path order (g_lane[8] before [10])."""
    base = [re.split(r'[/.]', p)[-1] for p in paths]
    cnt = collections.Counter(base)
    out = [None] * len(paths)
    seen = collections.Counter()
    for i in sorted(range(len(paths)), key=lambda i: _nat(paths[i])):
        b = base[i]
        if cnt[b] > 1:
            out[i] = f'{b}{seen[b]}'; seen[b] += 1
        else:
            out[i] = b
    return out


def analyse(n, top, include, exclude=(), strip=''):
    exp = set()
    for p in list(include) + list(exclude):
        parts = p.split('/')
        for k in range(1, len(parts)):
            exp.add('/'.join(parts[:k]))
    insts, unions = view(n, top, exp)

    def ism(nm):
        inc = any(nm == p or nm.startswith(p + '/') for p in include) or ('' in include)
        exc = any(nm == p or nm.startswith(p + '/') for p in exclude)
        return inc and not exc
    uf = {}

    def find(x):
        r = x
        while uf.get(r, r) != r:
            r = uf[r]
        while uf.get(x, x) != r:
            uf[x], x = r, uf[x]
        return r
    for a, b in unions:
        ra, rb = find(a), find(b)
        if ra != rb:
            uf[ra] = rb
    consts = {find(c): c[1] for c in ('C0', 'C1', 'Cx')}
    users = collections.defaultdict(set)
    drv, lab_m, lab_p = {}, {}, {}
    m = n.mods[n.resolve(top)]
    for p in m.ports:
        for b in n.bits(m, p[0]):
            c = find(b); users[c].add('o'); lab_p.setdefault(c, p[0])
    mem = []
    for name, t, cb in insts:
        mm = ism(name)
        pd = n.port_dirs(t)
        if mm:
            if t not in n.mods:
                raise ValueError(f'member {name} is a std cell ({t}): not a member-set core')
            mem.append((name, t, cb))
        for pn, bl in cb.items():
            d = (pd or {}).get(pn) or ('output' if pn in netcut.STD_OUT else 'input')
            for b in bl:
                if b in ('C0', 'C1', 'Cx'):
                    continue
                c = find(b)
                if c in consts:
                    continue
                users[c].add('m' if mm else 'o')
                if mm:
                    lab_m.setdefault(c, f'{name}.{pn}')
                    if d == 'output':
                        drv[c] = True
    P = Piece()
    paths = [x[0] for x in mem]
    roles = roles_of(paths)
    order = sorted(range(len(mem)), key=lambda i: roles[i])
    P.members = [(mem[i][0], mem[i][1], roles[i]) for i in order]
    P.pins, P.bnd = {}, []
    bidx, iidx = {}, {}
    canon_label = {}
    for i in order:
        name, t, cb = mem[i]
        role = roles[i]
        for pn, pdir, w, lsb in n.mods[t].ports:
            bl = cb.get(pn)
            cls = []
            if bl is None:
                cls = [('N',)] * w
            else:
                for b in reversed(bl):               # lsb first
                    if b in ('C0', 'C1', 'Cx'):
                        cls.append(('K', b[1])); continue
                    c = find(b)
                    if c in consts:
                        cls.append(('K', consts[c])); continue
                    u = users[c]
                    if 'o' in u:
                        if c not in bidx:
                            bidx[c] = len(P.bnd)
                            P.bnd.append(dict(dir='output' if c in drv else 'input', can=f'{role}_{pn}', c=c))
                        if pdir == 'output' and not P.bnd[bidx[c]].get('drv_lab'):
                            P.bnd[bidx[c]]['drv_lab'] = True; P.bnd[bidx[c]]['can'] = f'{role}_{pn}'
                        cls.append(('P', bidx[c]))
                    elif c in drv and sum(1 for _ in [0]) and _multi(c, mem, find, ism):
                        iidx.setdefault(c, len(iidx)); cls.append(('I', iidx[c]))
                    else:
                        # net only on this member pin (output unused / input undriven) or member->member
                        iidx.setdefault(c, len(iidx)); cls.append(('I', iidx[c]))
            P.pins[(role, pn)] = (pdir, cls)
    # nets touching a single member pin bit are unconnected, not internal
    icount = collections.Counter(k for (_, cls) in P.pins.values() for cl in cls if cl[0] == 'I' for k in [cl[1]])
    for key, (pdir, cls) in P.pins.items():
        P.pins[key] = (pdir, [('N',) if cl[0] == 'I' and icount[cl[1]] == 1 else cl for cl in cls])
    # cut bus names exactly as gen_core_ports.busify names them
    lab = {}
    for b in P.bnd:
        c = b['c']
        lab[c] = lab_p.get(c) or lab_m[c]
    res = dict(inp=collections.Counter(), out=collections.Counter())
    for b in P.bnd:
        res['out' if b['dir'] == 'output' else 'inp'][lab[b['c']]] += 1
    names = gen_core_ports.busify(res, strip)
    lbls = [l for key in ('inp', 'out') for l in sorted(res[key])]
    l2n = {l: nm[0] for l, nm in zip(lbls, names)}
    for b in P.bnd:
        b['cut'] = l2n[lab[b['c']]]
    P.cut_ports = names
    P.cut_bits = dict(inp=sum(res['inp'].values()), out=sum(res['out'].values()))
    for b in P.bnd:
        del b['c']
        b.pop('drv_lab', None)
    return P


def _multi(c, mem, find, ism):
    return True


def signature(P):
    """Replica-independent structure: member types/roles, per-pin classes with net ids renumbered, boundary labels."""
    ren, k = {}, 0
    sig = []
    for _, t, role in P.members:
        sig.append(('M', role, re.sub(r'__d4g_\w+$', '', t)))   # full type: a parameter difference is a type difference
    for key in sorted(P.pins):
        pdir, cls = P.pins[key]
        row = []
        for cl in cls:
            if cl[0] in ('P', 'I'):
                tag = (cl[0], cl[1])
                if tag not in ren:
                    ren[tag] = k; k += 1
                row.append((cl[0], ren[tag]) if cl[0] == 'I' else ('P', P.bnd[cl[1]]['can'], P.bnd[cl[1]]['dir']))
            else:
                row.append(cl)
        sig.append((key, pdir, tuple(row)))
    return sig


def canon_name(can):
    role, _, port = can.partition('_') if not can.startswith('u_') else (None, None, None)
    return can[2:] if can.startswith('u_') else can


def canonical(P, straps=()):
    """Canonical port list [[name, dir, width, 0]] and per-boundary-bit (name, bit).  straps = {(role, port)}: member
    inputs tied to replica-specific constants that become strap input ports <role>_<port> (full port width)."""
    pos = collections.Counter()
    where = {}
    order = []
    for key, (pdir, cls) in P.pins.items():
        for cl in cls:
            if cl[0] == 'P' and cl[1] not in where:
                nm = canon_name(P.bnd[cl[1]]['can'])
                where[cl[1]] = (nm, pos[nm]); pos[nm] += 1
                if nm not in order:
                    order.append(nm)
    dirs = {canon_name(b['can']): b['dir'] for b in P.bnd}
    ports = [[nm, dirs[nm], pos[nm], 0] for nm in order]
    for role, port in straps:
        pdir, cls = P.pins[(role, port)]
        ports.append([canon_name(f'{role}_{port}'), 'input', len(cls), 0])
    ports.sort(key=lambda p: (p[1] != 'input', ))
    return ports, where


def _runs(pairs):
    """[(i, j)] sorted by i -> [(i0, i1, j0, j1)] runs with i and j both consecutive."""
    out = []
    for i, j in pairs:
        if out and out[-1][1] == i - 1 and isinstance(j, int) and isinstance(out[-1][3], int) and out[-1][3] == j - 1:
            out[-1][1] = i; out[-1][3] = j
        else:
            out.append([i, i, j, j])
    return out


def _sl(nm, a, b, w):
    if w == 1 and a == 0 and b == 0:
        return nm
    return f'{nm}[{a}]' if a == b else f'{nm}[{b}:{a}]'


def emit_wrapper(P, top, rtl, straps=(), header=''):
    """rtl = {role: (module, '#(...)' or '')}.  Returns (verilog text, canonical ports, boundary map)."""
    ports, where = canonical(P, straps)
    pw = {p[0]: p[2] for p in ports}
    L = [header.rstrip(), '`timescale 1ns/1ps', '`default_nettype none', f'module {top} (']
    L.append(',\n'.join(f'    {d} wire {"[%d:0] " % (w - 1) if w > 1 else ""}{nm}' for nm, d, w, _ in ports))
    L.append(');')
    nets = collections.defaultdict(list)
    for (role, port), (pdir, cls) in P.pins.items():
        for i, cl in enumerate(cls):
            if cl[0] == 'I':
                nets[cl[1]].append((role, port, i, pdir))
    if nets:
        L.append(f'    wire [{len(nets) - 1}:0] n_int;   // member<->member nets of the master')
    ni = {k: x for x, k in enumerate(sorted(nets))}
    roles = []
    for path, t, role in P.members:
        roles.append(role)
    for role in roles:
        mod, prm = rtl[role]
        conns = []
        for (r, port), (pdir, cls) in P.pins.items():
            if r != role:
                continue
            w = len(cls)
            L.append(f'    wire {"[%d:0] " % (w - 1) if w > 1 else ""}{role}__{port};')
            conns.append(f'.{port}({role}__{port})')
        L.append(f'    {mod} {prm + " " if prm else ""}{role} (\n        ' + ',\n        '.join(conns) + ');')
    for (role, port), (pdir, cls) in P.pins.items():
        w = len(cls)
        sig = f'{role}__{port}'
        if (role, port) in straps:
            L.append(f'    assign {sig} = {canon_name(role + "_" + port)};   // strap (replica constant at the parent)')
            continue
        pin_pairs = collections.defaultdict(list)
        for i, cl in enumerate(cls):
            if cl[0] == 'P':
                nm, j = where[cl[1]]
                bdir = P.bnd[cl[1]]['dir']
                if pdir == 'output' and bdir == 'output':
                    pin_pairs[('o', nm)].append((i, j))
                elif pdir == 'input':
                    pin_pairs[('i', nm)].append((i, j))
            elif cl[0] == 'I':
                pin_pairs[('o' if pdir == 'output' else 'i', 'n_int')].append((i, ni[cl[1]]))
            elif cl[0] == 'K' and pdir == 'input':
                pin_pairs[('k', None)].append((i, cl[1]))
        for (kind, nm), pr in pin_pairs.items():
            if kind == 'k':
                for i, v in pr:
                    L.append(f"    assign {_sl(sig, i, i, w)} = 1'b{v};")
                continue
            for a, b, ja, jb in _runs(sorted(pr)):
                tw = pw.get(nm, len(nets))
                if kind == 'i':
                    L.append(f'    assign {_sl(sig, a, b, w)} = {_sl(nm, ja, jb, tw)};')
                else:
                    L.append(f'    assign {_sl(nm, ja, jb, tw)} = {_sl(sig, a, b, w)};')
    L += ['endmodule', '`default_nettype wire', '']
    bmap = collections.defaultdict(lambda: collections.Counter())
    for k, b in enumerate(P.bnd):
        bmap[b['cut']][where[k][0]] += 1
    return '\n'.join(L), ports, {c: dict(v) for c, v in bmap.items()}
