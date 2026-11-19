#!/usr/bin/env python3
"""depth_opt.py IN.json TOP OUT.json [--report]     (FABLE-FIX-S81-GLUE 2026-11-19)

Arrival-aware re-association of the generic gate netlist of one flattened module (yosys `synth -flatten -noabc` JSON:
$_AND_ $_OR_ $_XOR_ $_XNOR_ $_NOT_ $_MUX_ and flops), same function, same flops, 0 cycles.

Every maximal AND/OR cone whose interior nets have exactly one user (looked through single-user inverters, De Morgan)
and every such XOR/XNOR cone is collected into its leaf literals and rebuilt as a Huffman tree on the leaf arrival
levels (the earliest two literals are joined first), which is depth-optimal for a tree with fixed leaf arrivals.
Same-polarity pairs become single-stage NAND / NOR (polarity alternates by level); a mixed pair becomes ANDNOT.
Multi-user nets, muxes and flops are never touched, so sharing and the register set are exactly the input's.

Used before tools/qwen_split/record32/bound_record_graph.py (which bounds fanout and retains every gate as its own
cell); the result is proven against the readable source by prove_rewrite.py / prove_transition.py.
--report prints the per-register level histogram of IN (before) and OUT (after)."""
import heapq, json, sys
from collections import Counter

COST = {'$_AND_': 1.0, '$_OR_': 1.0, '$_NAND_': 0.6, '$_NOR_': 0.6, '$_ANDNOT_': 1.0, '$_ORNOT_': 1.0,
        '$_XOR_': 1.3, '$_XNOR_': 1.3, '$_NOT_': 0.4, '$_MUX_': 1.5}
ANDOR = ('$_AND_', '$_OR_')
XORS = ('$_XOR_', '$_XNOR_')


def is_ff(c):
    return c['type'].startswith(('$_DFF', '$_SDFF'))


class Net:
    def __init__(self, m):
        self.cells = {n: c for n, c in m['cells'].items() if c['type'] != '$scopeinfo'}
        self.ports = m['ports']
        self.index()

    def index(self):
        self.drv = {}
        self.users = Counter()
        for n, c in self.cells.items():
            for p, bs in c['connections'].items():
                for b in bs:
                    if not isinstance(b, int):
                        continue
                    if c['port_directions'][p] == 'output':
                        self.drv[b] = n
                    else:
                        self.users[b] += 1
        for p in self.ports.values():
            if p['direction'] == 'output':
                for b in p['bits']:
                    if isinstance(b, int):
                        self.users[b] += 2      # a port bit is never an interior net

    def levels(self, cost=None):
        """-> {bit: arrival}; a flop output, an input and a constant arrive at 0"""
        memo = {}
        cells, drv = self.cells, self.drv
        order = []
        for b0 in list(drv):
            if b0 in memo:
                continue
            stack = [(b0, False)]
            while stack:
                b, done = stack.pop()
                if b in memo:
                    continue
                n = drv.get(b)
                if n is None or is_ff(cells[n]):
                    memo[b] = 0.0
                    continue
                c = cells[n]
                ins = [x for p, bs in c['connections'].items() if c['port_directions'][p] == 'input' for x in bs if isinstance(x, int)]
                if done:
                    w = (cost or COST).get(c['type'], 1.0)
                    memo[b] = w + max([memo[x] for x in ins] or [0.0])
                else:
                    stack.append((b, True))
                    stack.extend((x, False) for x in ins if x not in memo)
        return memo


def ff_depths(net, cost=None):
    lv = net.levels(cost)
    out = []
    for n, c in net.cells.items():
        if is_ff(c):
            out.append(max(lv.get(b, 0.0) for p in ('D', 'E') if p in c['connections'] for b in c['connections'][p] if isinstance(b, int)) if any(isinstance(b, int) for p in ('D', 'E') if p in c['connections'] for b in c['connections'][p]) else 0.0)
    for p in net.ports.values():
        if p['direction'] == 'output':
            out.extend(lv.get(b, 0.0) for b in p['bits'] if isinstance(b, int))
    return out


UNIT = {k: (0.0 if k == '$_NOT_' else 1.0) for k in COST}


def optimize(m):
    """re-associates in place; -> (trees rebuilt, gates removed, gates added)"""
    net = Net(m)
    cells, drv, users = net.cells, net.drv, net.users
    nextbit = 1 + max([b for c in cells.values() for bs in c['connections'].values() for b in bs if isinstance(b, int)]
                      + [b for p in net.ports.values() for b in p['bits'] if isinstance(b, int)])
    consumed = set()
    trees = {}          # root cell -> ('andor', leaves [(bit|const, inv)], out_inv) | ('xor', leaves, parity)

    def collect_and(bit, inv, leaves, root):
        """the literal (bit ^ inv) as a factor of an AND; absorb single-user AND / !OR / NOT below it"""
        n = drv.get(bit) if isinstance(bit, int) else None
        if n is not None and (users[bit] == 1 or n == root) and n not in consumed:
            c = cells[n]
            t = c['type']
            if t == '$_NOT_' and n != root:
                consumed.add(n)
                return collect_and(c['connections']['A'][0], inv ^ 1, leaves, root)
            if (t == '$_AND_' and inv == 0) or (t == '$_OR_' and inv == 1):
                consumed.add(n)
                collect_and(c['connections']['A'][0], inv, leaves, root)
                collect_and(c['connections']['B'][0], inv, leaves, root)
                return
        leaves.append((bit, inv))

    def collect_xor(bit, leaves, root):
        n = drv.get(bit) if isinstance(bit, int) else None
        if n is not None and (users[bit] == 1 or n == root) and n not in consumed:
            c = cells[n]
            t = c['type']
            if t == '$_NOT_' and n != root:
                consumed.add(n)
                return 1 ^ collect_xor(c['connections']['A'][0], leaves, root)
            if t in XORS:
                consumed.add(n)
                return (t == '$_XNOR_') ^ collect_xor(c['connections']['A'][0], leaves, root) ^ collect_xor(c['connections']['B'][0], leaves, root)
        leaves.append(bit)
        return 0

    # roots: reverse topological order (consumers first), so a gate is a root only if no consumer absorbed it
    lv = net.levels(UNIT)
    order = sorted((n for n, c in cells.items() if c['type'] in ANDOR + XORS), key=lambda n: -lv[cells[n]['connections']['Y'][0]])
    for n in order:
        if n in consumed:
            continue
        c = cells[n]
        y = c['connections']['Y'][0]
        if c['type'] in ANDOR:
            leaves = []
            inv = 1 if c['type'] == '$_OR_' else 0
            collect_and(y, inv, leaves, n)
            trees[n] = ('andor', leaves, inv, y)
        else:
            leaves = []
            par = collect_xor(y, leaves, n)
            trees[n] = ('xor', leaves, par, y)
    root_of = {t[3]: n for n, t in trees.items()}
    for n in consumed:
        del cells[n]
    arr = {}
    counter = [0]
    stats = [0, len(consumed), 0]

    def new_cell(root, typ, a, b, y=None):
        nonlocal nextbit
        if y is None:
            y = nextbit
            nextbit += 1
        counter[0] += 1
        stats[2] += 1
        cells[f'{root}__dopt{counter[0]}'] = {'hide_name': 1, 'type': typ, 'parameters': {}, 'attributes': {},
                                             'port_directions': {'A': 'input', 'B': 'input', 'Y': 'output'},
                                             'connections': {'A': [a], 'B': [b], 'Y': [y]}}
        return y

    def new_not(root, a, y=None):
        nonlocal nextbit
        if y is None:
            y = nextbit
            nextbit += 1
        counter[0] += 1
        stats[2] += 1
        cells[f'{root}__dopt{counter[0]}'] = {'hide_name': 1, 'type': '$_NOT_', 'parameters': {}, 'attributes': {},
                                             'port_directions': {'A': 'input', 'Y': 'output'}, 'connections': {'A': [a], 'Y': [y]}}
        return y

    def arrival(bit):
        """arrival of a net in the REBUILT netlist (iterative; rebuilds the tree that drives it first)"""
        stack = [bit]
        while stack:
            b = stack[-1]
            if b in arr or not isinstance(b, int):
                stack.pop()
                continue
            if b in root_of:
                kind, leaves, _, _ = trees[root_of[b]]
                need = [x for x in ((l if kind == 'xor' else l[0]) for l in leaves) if isinstance(x, int) and x not in arr]
                if need:
                    stack.extend(need)
                    continue
                rebuild(root_of[b])
                stack.pop()
                continue
            n = drv.get(b)
            if n is None or n not in cells or is_ff(cells[n]):
                arr[b] = 0.0
                stack.pop()
                continue
            c = cells[n]
            ins = [x for p, bs in c['connections'].items() if c['port_directions'][p] == 'input' for x in bs if isinstance(x, int)]
            need = [x for x in ins if x not in arr]
            if need:
                stack.extend(need)
                continue
            arr[b] = COST.get(c['type'], 1.0) + max([arr[x] for x in ins] or [0.0])
            stack.pop()

    def a_of(x):
        return arr[x] if isinstance(x, int) else 0.0

    def rebuild(root):
        kind, leaves, pol, y = trees[root]
        stats[0] += 1
        seq = 0
        if kind == 'xor':
            heap = []
            for x in leaves:
                heap.append((a_of(x), seq, x)); seq += 1
            heapq.heapify(heap)
            assert len(heap) >= 2
            while len(heap) > 2:
                a = heapq.heappop(heap); b = heapq.heappop(heap)
                nb = new_cell(root, '$_XOR_', a[2], b[2])
                arr[nb] = max(a[0], b[0]) + COST['$_XOR_']
                heapq.heappush(heap, (arr[nb], seq, nb)); seq += 1
            a = heapq.heappop(heap); b = heapq.heappop(heap)
            new_cell(root, '$_XNOR_' if pol else '$_XOR_', a[2], b[2], y)
            arr[y] = max(a[0], b[0]) + COST['$_XOR_']
            return
        # AND of literals; item = (arrival, seq, bit, inv): the factor is bit ^ inv
        heaps = {0: [], 1: []}
        for x, inv in leaves:
            heapq.heappush(heaps[inv], (a_of(x), seq, x)); seq += 1
        assert len(leaves) >= 2

        def total():
            return len(heaps[0]) + len(heaps[1])

        def pick():
            """-> (typ, a, b, inv_out, arrival) for the next join: the earliest literal with its best partner"""
            cands = []
            for p in (0, 1):
                if len(heaps[p]) >= 2:
                    a, b = heapq.nsmallest(2, heaps[p])
                    cands.append((max(a[0], b[0]) + COST['$_NAND_'], 0, p, p))
            if heaps[0] and heaps[1]:
                a, b = heaps[0][0], heaps[1][0]
                cands.append((max(a[0], b[0]) + COST['$_ANDNOT_'], 1, 0, 1))
            # join the pair that contains the earliest literal, cheapest first
            first = min((h[0][0], p) for p, h in heaps.items() if h)[1]
            cands = [c for c in cands if first in (c[2], c[3])]
            return min(cands)

        while True:
            t, _, p, q = pick()
            a = heapq.heappop(heaps[p]); b = heapq.heappop(heaps[q])
            final = total() == 0
            if p == q:
                # pos,pos: a&b = !NAND -> literal inv 1 ; neg,neg: !a&!b = NOR -> literal inv 0
                typ, inv_out = ('$_NAND_', 1) if p == 0 else ('$_NOR_', 0)
                if final and inv_out != pol:        # the root net must carry AND(leaves) ^ pol
                    typ, inv_out, t = ('$_AND_', 0, t + 0.4) if p == 0 else ('$_OR_', 1, t + 0.4)
                nb = new_cell(root, typ, a[2], b[2], y if final else None)
            else:
                # a & !b
                typ, inv_out = '$_ANDNOT_', 0
                if final and pol == 1:
                    nb = new_cell(root, '$_ORNOT_', b[2], a[2], y)      # b | !a = !(a & !b)
                    inv_out = 1
                else:
                    nb = new_cell(root, typ, a[2], b[2], y if final else None)
            arr[nb] = t
            if final:
                assert inv_out == pol, (root, typ, inv_out, pol)
                return
            heapq.heappush(heaps[inv_out], (t, seq, nb)); seq += 1

    for n in list(trees):
        arrival(trees[n][3])
    m['cells'] = {**{n: c for n, c in m['cells'].items() if c['type'] == '$scopeinfo'}, **cells}
    return tuple(stats)


def hist(vals):
    return sorted(Counter(int(v + 0.999) for v in vals).items())


def main(argv):
    src, top, dst = argv[1:4]
    d = json.load(open(src))
    m = d['modules'][top]
    before = ff_depths(Net(m), UNIT)
    beforew = ff_depths(Net(m))
    st = optimize(m)
    net = Net(m)
    after = ff_depths(net, UNIT)
    afterw = ff_depths(net)
    json.dump(d, open(dst, 'w'))
    print(f'depth_opt: trees {st[0]} gates removed {st[1]} added {st[2]}; register max levels {max(before):.0f} -> {max(after):.0f} '
          f'(weighted {max(beforew):.1f} -> {max(afterw):.1f}); cells {dict(Counter(c["type"] for c in net.cells.values()))}')
    if '--report' in argv:
        print('before', hist(before))
        print('after ', hist(after))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
