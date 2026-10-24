"""Bit-level connectivity of a generated KV partition netlist (tools/die_plan/bind.py output)."""
import re

DECL = re.compile(r'^\s*(input|output|inout|wire|logic|reg)\s+(?:wire\s+|logic\s+)?(?:\[(\d+):(\d+)\]\s*)?([A-Za-z_]\w*)\s*[,;)]?')
INST = re.compile(r'^\s*([A-Za-z_]\w*)\s*(?:#\(.*\))?\s+([A-Za-z_]\w*)\s*\(\s*$')
PORT = re.compile(r'^\s*\.(\w+)\s*\((.*)\)\s*,?\s*(//.*)?$')
INST1 = re.compile(r'^\s*([A-Za-z_]\w*)\s*(?:#\(.*?\))?\s+([A-Za-z_]\w*)\s*\((\s*\..*)\)\s*;\s*(//.*)?$')
ASSIGN = re.compile(r'^\s*assign\s+(.+?)\s*=\s*(.+?)\s*;')


def split_top(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch == ',' and depth == 0:
            out.append(cur); cur = ''
            continue
        depth += ch in '{('; depth -= ch in '})'
        cur += ch
    out.append(cur)
    return out


def split_concat(e):
    e = e.strip()
    if e.startswith('{') and e.endswith('}'):
        inner, out, depth, cur = e[1:-1], [], 0, ''
        for ch in inner:
            if ch == ',' and depth == 0:
                out.append(cur); cur = ''
                continue
            depth += ch in '{('; depth -= ch in '})'
            cur += ch
        out.append(cur)
        r = []
        for x in out:
            r += split_concat(x)
        return r
    return [e]


class Net:
    def __init__(self, path):
        self.width, self.ports, self.insts = {}, {}, {}
        self.alias = []
        cur = None
        for ln in open(path):
            m = DECL.match(ln)
            if m and cur is None:
                k, a, b, nm = m.groups()
                self.width[nm] = (int(a) - int(b) + 1) if a else 1
                if k in ('input', 'output', 'inout'):
                    self.ports[nm] = k
                continue
            m = INST1.match(ln)
            if m and cur is None and m.group(1) not in ('module', 'assign'):
                pm = {}
                for x in split_top(m.group(3)):
                    mm = re.match(r'^\s*\.(\w+)\s*\((.*)\)\s*$', x)
                    if mm and mm.group(2).strip():
                        pm[mm.group(1)] = mm.group(2).strip()
                self.insts[m.group(2)] = (m.group(1), pm)
                continue
            m = INST.match(ln)
            if m and cur is None and m.group(1) not in ('module',):
                cur = (m.group(2), m.group(1), {})
                continue
            if cur is not None:
                m = PORT.match(ln)
                if m:
                    if m.group(2).strip():
                        cur[2][m.group(1)] = m.group(2).strip()
                elif ln.strip().startswith(');'):
                    self.insts[cur[0]] = (cur[1], cur[2]); cur = None
                continue
            m = ASSIGN.match(ln)
            if m:
                self.alias.append((m.group(1), m.group(2)))

    def bits(self, e):
        """MSB-first list of (net, bit) or None (constant / param)."""
        out = []
        for t in split_concat(e):
            t = t.strip()
            m = re.match(r"^(\d+)?'[bdh]", t) or re.match(r'^\d+$', t)
            if m or t.startswith('S_') or not t:
                n = 1
                mm = re.match(r"^(\d+)'", t)
                if mm:
                    n = int(mm.group(1))
                mm = re.match(r'^(\w+)\[(\d+):(\d+)\]$', t)
                if mm:
                    n = int(mm.group(2)) - int(mm.group(3)) + 1
                out += [None] * n
                continue
            mm = re.match(r'^(\w+)\[(\d+):(\d+)\]$', t)
            if mm:
                a, b = int(mm.group(2)), int(mm.group(3))
                out += [(mm.group(1), i) for i in range(a, b - 1, -1)]
                continue
            mm = re.match(r'^(\w+)\[(\d+)\]$', t)
            if mm:
                out.append((mm.group(1), int(mm.group(2))))
                continue
            mm = re.match(r'^(\w+)$', t)
            if mm:
                w = self.width.get(t, 1)
                out += [(t, i) for i in range(w - 1, -1, -1)]
                continue
            out.append(None)
        return out

    def graph(self):
        """netbit(root) -> [(inst, port, bit)], with assigns merged; partition ports appear as ('<port>', name, bit)."""
        par = {}

        def f(x):
            while par.get(x, x) != x:
                x = par[x]
            return x
        for l, r in self.alias:
            for a, b in zip(self.bits(l), self.bits(r)):
                if a and b:
                    par[f(a)] = f(b)
        self.find = f
        g = {}
        for inst, (mod, pm) in self.insts.items():
            for p, e in pm.items():
                bs = self.bits(e)
                n = len(bs)
                for i, nb in enumerate(bs):
                    if nb:
                        g.setdefault(f(nb), []).append((inst, p, n - 1 - i))
        for p in self.ports:
            for i in range(self.width[p]):
                g.setdefault(f((p, i)), []).append(('<port>', p, i))
        return g
