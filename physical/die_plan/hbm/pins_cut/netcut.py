#!/usr/bin/env python3
"""HBM-P5-PINS: exact core boundaries from a hierarchical yosys netlist (write_verilog -noattr, HIER=1).

A planned hard core is a set of instances inside one parent module of the as-built master (the parent may itself be
nested: members are given as instance paths from the master top; the common parent is inlined down to the members'
parents).  The core boundary is every net bit that touches a member pin AND something outside the member set (another
cell's pin, a parent port, a non-member child).  Constants on member inputs are tie cells inside the core (no pin).

  load(netlist) -> Netlist
  Netlist.children(mod) -> [(inst, cell type)] of hierarchical (non std-cell) children
  Netlist.cut(top, member_paths) -> {'inp': [(net, bits)], 'out': [...]} grouped by member port
"""
import re, collections

STD_OUT = {'Y', 'Q', 'QN', 'CON', 'SN', 'YS', 'YC', 'CO', 'S'}
RX_MOD = re.compile(r'^\s*module\s+(\S+)\s*\(')
RX_DECL = re.compile(r'^\s*(input|output|inout|wire)\s+(?:signed\s+)?(?:\[(-?\d+):(-?\d+)\]\s*)?(\S+?)\s*;')
RX_INST = re.compile(r'^\s*(\S+)\s+(\S+)\s*\($')
RX_PORT = re.compile(r'^\s*\.(\S+?)\((.*)\),?\s*$')
RX_ASSIGN = re.compile(r'^\s*assign\s+(.+?)\s*=\s*(.+?)\s*;\s*$')


def unesc(s):
    return s[1:] if s.startswith('\\') else s


class Module:
    def __init__(self, name):
        self.name = name
        self.ports = []            # (name, dir, width, lsb)
        self.wires = {}            # name -> (msb, lsb)
        self.insts = []            # (type, inst, {port: [bit]})
        self.assigns = []          # ([bit], [bit])


def split_concat(expr):
    expr = expr.strip()
    if expr.startswith('{') and expr.endswith('}'):
        inner = expr[1:-1]
        out, depth, cur = [], 0, ''
        i = 0
        while i < len(inner):
            ch = inner[i]
            if ch == '\\':                       # escaped id runs to the next space
                j = inner.find(' ', i)
                j = len(inner) if j < 0 else j
                cur += inner[i:j]; i = j; continue
            if ch == '{': depth += 1
            if ch == '}': depth -= 1
            if ch == ',' and depth == 0:
                out.append(cur.strip()); cur = ''
            else:
                cur += ch
            i += 1
        if cur.strip():
            out.append(cur.strip())
        return out
    return [expr]


class Netlist:
    def __init__(self, path):
        self.mods = {}
        cur = None
        pend = None
        for line in open(path):
            m = RX_MOD.match(line)
            if m:
                cur = Module(unesc(m.group(1))); self.mods[cur.name] = cur; pend = None; continue
            if cur is None:
                continue
            s = line.strip()
            if s.startswith('endmodule'):
                cur = None; continue
            m = RX_DECL.match(line)
            if m and pend is None:
                d, a, b, n = m.groups(); n = unesc(n)
                msb, lsb = (int(a), int(b)) if a is not None else (0, 0)
                if d == 'wire':
                    cur.wires.setdefault(n, (msb, lsb))
                else:
                    cur.wires[n] = (msb, lsb)
                    cur.ports.append((n, d, abs(msb - lsb) + 1, min(msb, lsb)))
                continue
            m = RX_ASSIGN.match(line)
            if m and pend is None:
                cur.assigns.append((m.group(1), m.group(2))); continue
            if pend is None:
                m = RX_INST.match(line)
                if m and not s.startswith(('assign', 'input', 'output', 'wire', 'reg')):
                    pend = (unesc(m.group(1)), unesc(m.group(2)), {}); continue
            else:
                if s.startswith(');'):
                    cur.insts.append(pend); pend = None; continue
                m = RX_PORT.match(line)
                if m:
                    pend[2][m.group(1)] = m.group(2)
        self.base = {k: base(k) for k in self.mods}

    def bits(self, mod, expr):
        """expr -> list of bit ids (msb first); constants -> 'C'."""
        out = []
        for e in split_concat(expr):
            e = e.strip()
            if re.match(r"^\d+'[bhd]", e):
                w = int(e.split("'")[0]); out += ['C'] * w; continue
            m = re.match(r'^(\\\S+|[A-Za-z_][\w$]*)\s*(?:\[(\d+)(?::(\d+))?\])?$', e)
            if not m:
                raise ValueError(f'{mod.name}: cannot parse {e!r}')
            n = unesc(m.group(1))
            if m.group(2) is None:
                msb, lsb = mod.wires.get(n, (0, 0))
                rng = range(msb, lsb - 1, -1) if msb >= lsb else range(msb, lsb + 1)
                out += [f'{n}[{i}]' if (n in mod.wires and mod.wires[n] != (0, 0)) else n for i in rng] \
                    if mod.wires.get(n, (0, 0)) != (0, 0) else [n]
            elif m.group(3) is None:
                out.append(f'{n}[{m.group(2)}]' if mod.wires.get(n, (0, 0)) != (0, 0) else n)
            else:
                a, b = int(m.group(2)), int(m.group(3))
                rng = range(a, b - 1, -1) if a >= b else range(a, b + 1)
                out += [f'{n}[{i}]' for i in rng]
        return out

    def children(self, mname):
        m = self.mods[mname]
        return [(i, t) for t, i, _ in m.insts if t in self.mods]

    def port_dirs(self, tname):
        if tname in self.mods:
            return {p[0]: p[1] for p in self.mods[tname].ports}
        return None

    def resolve(self, top):
        for k in self.mods:
            if k == top or self.base[k] == top:
                return k
        if 'v16w_' + top in self.mods:
            return 'v16w_' + top
        raise KeyError(top)

    def view(self, top, expand):
        """Inline the instance paths in `expand` (lists of instance names, '/'-joined) under module `top`.
        Returns (insts, unions, portbits): insts = [(name, type, {port: [bit]})] with '/'-prefixed names/bits."""
        top = self.resolve(top)
        insts, unions = [], []
        m = self.mods[top]
        portbits = []
        for p in m.ports:
            portbits += self.bits(m, p[0])

        def emit(mod, pre):
            for l, r in mod.assigns:
                for a, b in zip(self.bits(mod, l), self.bits(mod, r)):
                    unions.append((pre + a if a != 'C' else 'C', pre + b if b != 'C' else 'C'))
            for t, i, conns in mod.insts:
                name = pre + i
                cb = {pn: [pre + b if b != 'C' else 'C' for b in self.bits(mod, ex)] for pn, ex in conns.items()}
                if name in expand and t in self.mods:
                    sub = self.mods[t]
                    for pn, bl in cb.items():
                        sb = [name + '/' + b for b in self.bits(sub, pn)]
                        for a, b in zip(sb, bl):
                            unions.append((a, b))
                    emit(sub, name + '/')
                else:
                    insts.append((name, t, cb))
        emit(m, '')
        return insts, unions, portbits

    def cut(self, top, include, exclude=(), expand=None, std_out=None):
        """Boundary of the core = instances under `include` paths minus `exclude` paths (paths '/'-joined).
        Every path prefix is inlined.  Returns {'inp': Counter(member.port -> bits), 'out': ...}."""
        exp = set(expand or [])
        for p in list(include) + list(exclude):
            parts = p.split('/')
            for k in range(1, len(parts)):
                exp.add('/'.join(parts[:k]))
        insts, unions, portbits = self.view(top, exp)

        def ism(n):
            inc = any(n == p or n.startswith(p + '/') for p in include) or ('' in include)
            exc = any(n == p or n.startswith(p + '/') for p in exclude)
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
        cz = find('C')
        users = collections.defaultdict(set)      # canon -> {'m','o'} member / outside
        drv, lab_m, lab_o, lab_p = {}, {}, {}, {}
        m = self.mods[self.resolve(top)]
        for p in m.ports:
            for k, b in enumerate(self.bits(m, p[0])):
                c = find(b)
                users[c].add('o'); lab_p.setdefault(c, p[0])
        for name, t, cb in insts:
            mem = ism(name)
            hier = t in self.mods
            pd = self.port_dirs(t)
            for pn, bl in cb.items():
                d = (pd or {}).get(pn) or (std_out(t, pn) if std_out else ('output' if pn in STD_OUT else 'input'))
                for b in bl:
                    if b == 'C':
                        continue
                    c = find(b)
                    if c == cz:
                        continue
                    users[c].add('m' if mem else 'o')
                    if mem:
                        if hier:
                            lab_m.setdefault(c, f'{name}.{pn}')
                        else:
                            lab_m.setdefault(c, None)
                        if d == 'output':
                            drv[c] = True
                    elif hier:
                        lab_o.setdefault(c, f'{name}.{pn}')
        res = dict(inp=collections.Counter(), out=collections.Counter())
        for c in lab_m:
            if 'o' not in users[c]:
                continue
            lbl = lab_p.get(c) or lab_m[c] or (('~' + lab_o[c]) if c in lab_o else 'glue')
            res['out' if c in drv else 'inp'][lbl] += 1
        return res


def base(k):
    return re.sub(r'^\$paramod\$[0-9a-f]+\\', '', re.sub(r'^\$paramod\\([^\\]+)\\.*$', r'\1', k))
