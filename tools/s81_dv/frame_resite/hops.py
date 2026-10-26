#!/usr/bin/env python3
"""S81-P8-C hop model: macros at sites (+LEF pin offsets), ports at window positions, soft register nodes at the
L1-minimax centre of their terminals (iterated; = midpoint of source and sink for a 2-terminal relay), pushed out of
macro boxes.  Hop = Manhattan pin-to-pin (max over bits of an instance pair)."""
import numpy as np
from collections import defaultdict
import netgraph as g

class Model:
    def __init__(self, master, k, macros, ptype):
        self.nodes, edges, self.info = g.build(master, k, macros, ptype)
        self.macros = {}
        for e in macros:
            n = e['inst'].split('.', 1)[1].replace('.u_view', '')
            self.macros[n] = e
        self.site = {n: tuple(e['origin_um']) for n, e in self.macros.items()}
        # group edges by unordered (a, b) with direction kept for labels
        grp = defaultdict(list)
        for a, ao, b, bo, la, lb in edges:
            grp[(a, b)].append((ao, bo, la, lb))
        self.groups = []
        for (a, b), lst in grp.items():
            ao = np.array([x[0] if x[0] is not None else (0.0, 0.0) for x in lst])
            bo = np.array([x[1] if x[1] is not None else (0.0, 0.0) for x in lst])
            la = sorted(set(x[2] for x in lst)); lb = sorted(set(x[3] for x in lst))
            self.groups.append(dict(a=a, b=b, ao=ao, bo=bo, bits=len(lst), la=la, lb=lb))
        self.soft = [n for n, v in self.nodes.items() if v['kind'] == 'S']
        self.inc = defaultdict(list)
        for i, gr in enumerate(self.groups):
            self.inc[gr['a']].append(i); self.inc[gr['b']].append(i)
        self.spos = {}

    def base(self, n):
        v = self.nodes[n]
        if v['kind'] == 'M':
            return np.array(self.site[n])
        if v['kind'] == 'P':
            return np.zeros(2)
        return np.array(self.spos.get(n, (721.0, 613.0)))

    def boxes(self):
        return [(s[0], s[1], s[0] + self.macros[n]['size_um'][0], s[1] + self.macros[n]['size_um'][1]) for n, s in self.site.items()]

    def terminals(self, n):
        pts = []
        for i in self.inc[n]:
            gr = self.groups[i]
            if gr['a'] == n:
                pts.append(self.base(gr['b']) + gr['bo'])
            if gr['b'] == n:
                pts.append(self.base(gr['a']) + gr['ao'])
        return np.vstack(pts) if pts else np.zeros((0, 2))

    def solve(self, iters=60):
        bx = np.array(self.boxes())
        for it in range(iters):
            mv = 0.0
            for n in self.soft:
                t = self.terminals(n)
                if not len(t):
                    continue
                u = t[:, 0] + t[:, 1]; v = t[:, 0] - t[:, 1]
                uc = (u.min() + u.max()) / 2; vc = (v.min() + v.max()) / 2
                x, y = (uc + vc) / 2, (uc - vc) / 2
                # push out of macro boxes (std cells cannot sit inside a hard macro)
                for _ in range(3):
                    ins = (bx[:, 0] < x) & (x < bx[:, 2]) & (bx[:, 1] < y) & (y < bx[:, 3])
                    if not ins.any():
                        break
                    b = bx[np.argmax(ins)]
                    c = [(abs(x - b[0]), b[0] - 1, y), (abs(b[2] - x), b[2] + 1, y), (abs(y - b[1]), x, b[1] - 1), (abs(b[3] - y), x, b[3] + 1)]
                    _, x, y = min(c)
                x = min(max(x, 1.0), g.OUTLINE[0] - 1); y = min(max(y, 1.0), g.OUTLINE[1] - 1)
                old = self.spos.get(n)
                if old is not None:
                    mv = max(mv, abs(old[0] - x) + abs(old[1] - y))
                self.spos[n] = (x, y)
            if it > 5 and mv < 0.5:
                break

    def hop(self, gr):
        d = np.abs((self.base(gr['a']) + gr['ao']) - (self.base(gr['b']) + gr['bo'])).sum(1)
        return float(d.max()), float(d.sum())

    def hops(self):
        out = []
        for gr in self.groups:
            mx, tot = self.hop(gr)
            out.append((mx, tot, gr))
        return out
