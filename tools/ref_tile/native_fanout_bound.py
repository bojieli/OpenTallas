#!/usr/bin/env python3
"""Standard pre-floorplan fanout bound of a MAPPED tile netlist (FLOW-CONSTFOLD 2026-10-21).

Why: main 45386657d (rule native-liberty-constant-identities) makes the pre-gate native census
(tools/ref_tile/native_census.py) see through cells whose PROVEN constant inputs reduce them to an
identity / inverse of one dynamic input.  Kept-hierarchy leaf modules (ot_keep_regs / keep_hierarchy copies) and
per-module ABC maps are mapped with their constant ports still tied (TIEHI/TIELO or literals), so a driver
that feeds many such cells carries all their loads (HBM HC tail k4: 290 drivers > 32, max 181; S81 dsdv_eng_rr
33 drivers at 33-34).  The census rule stays: a real fanout is split by the flow, never waived.

What (on a yosys write_json of the FLATTENED mapped top, Liberty cells read with read_liberty -lib):
 1 FOLD   every combinational single-output cell with >= 1 proven constant input (literal, TIE cell or folded
          constant) is reduced over its other inputs by its actual Liberty function (truth table):
            constant      -> cell removed, its loads tied to a TIE cell of that value (ORFS repair_tie_fanout splits ties)
            identity of X -> cell removed, loads moved to X (an output-port bit keeps a BUF on X)
            inverse of X  -> cell becomes INVx1 (A = X)
            otherwise     -> kept.
          Iterated to a fixed point.  Sequential cells, clock-network cells and keep/dont_touch cells are never folded.
 2 CLONE  every cell-driven net whose census load count (through actual unary BUF/INV cells, clock pins excluded)
          exceeds --limit ONLY because of step 1 (its count was <= --limit before the fold) or of clone-added loads is
          split: its BUF/INV tree is dissolved and the driver is replicated (same type, same input
          nets incl. clock/reset, same attributes) so each copy drives <= --target endpoints (an inverted endpoint
          group gets one INVx1 per copy).  Copies load their own inputs, which are bounded in turn (worklist).
          A driver already over --limit before the fold (real RTL fanout), an over-limit input port, a multi-output /
          unknown / macro driver or a clock net is a FRONTIER: the netlist is left unchanged and the census refuses it;
          RTL must register / distribute it.  A netlist with no driver over --limit is left untouched (NO_CHANGE).
 Function is unchanged by construction (identical replicas; truth-table reductions); the tile's own bench on the
 resulting netlist and the native census are the witnesses.
usage: native_fanout_bound.py IN.json OUT.json --top TOP --liberty L.lib [...] [--limit 32] [--target 24] [--report R.json]
exit 0 = written (status in report), 3 = no change needed (OUT not written), 2 = frontier left (OUT not written unless --force)
"""
import argparse
import collections
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_census as NC  # noqa: E402  (Liberty roles + Boolean function parser of the census itself)


def truthy(v):
    if isinstance(v, str):
        s = v.strip().strip('"').lower()
        if set(s) <= {'0', '1'} and s:
            return int(s, 2) != 0
        return s in ('true', 'yes')
    return bool(v)


class Net:
    """Mapped flat module with per-bit load index."""

    def __init__(self, mod, roles):
        self.mod, self.roles = mod, roles
        self.cells = {n: c for n, c in mod['cells'].items() if not c['type'].startswith('$scopeinfo')}
        mod['cells'] = self.cells
        self.next_bit = 2 + max([b for c in self.cells.values() for bs in c['connections'].values() for b in bs
                                 if isinstance(b, int)] + [b for p in mod['ports'].values() for b in p['bits']
                                                          if isinstance(b, int)] + [0])
        self.out_port_bits = {b for p in mod['ports'].values() if p['direction'] == 'output' for b in p['bits']
                              if isinstance(b, int)}
        self.in_port_bits = {b: f'{pn}[{i}]' for pn, p in mod['ports'].items() if p['direction'] == 'input'
                             for i, b in enumerate(p['bits']) if isinstance(b, int)}
        self.loads = collections.defaultdict(set)    # bit -> {(cell, pin, idx)}
        self.driver = {}                             # bit -> (cell, pin)
        for n in self.cells:
            self._index(n, +1)

    def pin_role(self, cell, pin):
        r = self.roles.get(self.cells[cell]['type'])
        return r['pins'].get(pin) if r else None

    def direction(self, cell, pin):
        c = self.cells[cell]
        d = c.get('port_directions', {}).get(pin)
        if d is None:
            pr = self.pin_role(cell, pin)
            d = pr['direction'] if pr else 'input'   # unknown: conservative = load
        return d

    def is_clock_pin(self, cell, pin):
        pr = self.pin_role(cell, pin)
        return bool(pr and pr['clock'])

    def _index(self, n, sign):
        c = self.cells[n]
        for pn, bits in c['connections'].items():
            d = self.direction(n, pn)
            for k, b in enumerate(bits):
                if not isinstance(b, int):
                    continue
                if d == 'output':
                    if sign > 0:
                        self.driver[b] = (n, pn)
                    elif self.driver.get(b, (None,))[0] == n:
                        del self.driver[b]
                else:
                    if sign > 0:
                        self.loads[b].add((n, pn, k))
                    else:
                        self.loads[b].discard((n, pn, k))

    def remove(self, n):
        self._index(n, -1)
        del self.cells[n]

    def add(self, n, cell):
        assert n not in self.cells, n
        self.cells[n] = cell
        self._index(n, +1)

    def set_pin(self, n, pn, k, new):
        c = self.cells[n]
        old = c['connections'][pn][k]
        if isinstance(old, int):
            self.loads[old].discard((n, pn, k))
        c['connections'][pn][k] = new
        if isinstance(new, int):
            self.loads[new].add((n, pn, k))

    def fresh(self, name):
        b = self.next_bit
        self.next_bit += 1
        self.mod['netnames'][name] = {'hide_name': 0, 'bits': [b], 'attributes': {}}
        return b


def comb_single(net, n):
    """(input pins, output pin, tree) of a combinational single-output single-bit Liberty cell, else None."""
    c = net.cells[n]
    role = net.roles.get(c['type'])
    if role is None or role['sequential'] or role['bus_order']:
        return None
    ins, outs = [], []
    for pn, bits in c['connections'].items():
        pr = role['pins'].get(pn)
        if pr is None or len(bits) != 1 or pr['clock']:
            return None
        (outs if pr['direction'] == 'output' else ins).append(pn)
    if len(outs) != 1:
        return None
    tree = NC.boolean_function(role['pins'][outs[0]]['function'])
    if tree is None:
        return None
    return ins, outs[0], tree


def reduce_kind(tree, const, dyn):
    tt = []
    for vals in itertools.product((0, 1), repeat=len(dyn)):
        env = dict(const)
        env.update(zip(dyn, vals))
        try:
            tt.append(NC.function_value(tree, env))
        except (KeyError, RecursionError):
            return None
    if all(t == tt[0] for t in tt):
        return ('const', tt[0])
    for i, pn in enumerate(dyn):
        col = [vals[i] for vals in itertools.product((0, 1), repeat=len(dyn))]
        if tt == col:
            return ('id', pn)
        if tt == [1 - v for v in col]:
            return ('inv', pn)
    return None


def pick_cell(roles, want):
    """Smallest-drive library cell by function: 'inv', 'buf', 'tie0', 'tie1'."""
    best = []
    for name, r in roles.items():
        if r['sequential'] or r['bus_order']:
            continue
        ins = [p for p, x in r['pins'].items() if x['direction'] == 'input']
        outs = [p for p, x in r['pins'].items() if x['direction'] == 'output']
        if len(outs) != 1 or any(x['clock'] for x in r['pins'].values()):
            continue
        tree = NC.boolean_function(r['pins'][outs[0]]['function'])
        if tree is None:
            continue
        try:
            if want.startswith('tie'):
                if ins or NC.function_value(tree, {}) != int(want[-1]):
                    continue
            else:
                if len(ins) != 1:
                    continue
                tt = [NC.function_value(tree, {ins[0]: v}) for v in (0, 1)]
                if tt != ([1, 0] if want == 'inv' else [0, 1]):
                    continue
        except (KeyError, RecursionError):
            continue
        if want in ('inv', 'buf') and not name.startswith(('INVx1_', 'BUFx2_')):
            continue
        best.append((name, ins[0] if ins else None, outs[0]))
    if not best:
        raise ValueError(f'no Liberty cell for {want}')
    return sorted(best)[0]


def clock_bits(net):
    """Nets that reach a clock pin through combinational cells (never folded, never cloned)."""
    seen, todo = set(), []
    for n, c in net.cells.items():
        for pn, bits in c['connections'].items():
            if net.is_clock_pin(n, pn):
                todo += [b for b in bits if isinstance(b, int)]
    while todo:
        b = todo.pop()
        if b in seen:
            continue
        seen.add(b)
        d = net.driver.get(b)
        if d is None:
            continue
        r = net.roles.get(net.cells[d[0]]['type'])
        if r is None or r['sequential']:
            continue
        for pn, bits in net.cells[d[0]]['connections'].items():
            if net.direction(d[0], pn) != 'output':
                todo += [x for x in bits if isinstance(x, int)]
    return seen


def kept(c):
    a = c.get('attributes', {})
    return truthy(a.get('keep', 0)) or truthy(a.get('dont_touch', 0))


def fold(net, clk, stats):
    roles = net.roles
    values = {}                    # bit -> 0/1 proven constant
    tie_bits = {0: None, 1: None}
    for n, c in list(net.cells.items()):
        cs = comb_single(net, n)
        if cs and not cs[0]:
            try:
                v = NC.function_value(cs[2], {})
            except (KeyError, RecursionError):
                continue
            b = c['connections'][cs[1]][0]
            if isinstance(b, int):
                values[b] = v
                if tie_bits[v] is None:
                    tie_bits[v] = b

    def val(b):
        if isinstance(b, str) and b in ('0', '1'):
            return int(b)
        return values.get(b)

    def tie(v):
        if tie_bits[v] is None:
            name, _, op = pick_cell(roles, f'tie{v}')
            b = net.fresh(f'ot_fold_tie{v}')
            net.add(f'ot_fold_tie{v}_c', {'hide_name': 0, 'type': name, 'parameters': {}, 'attributes': {},
                                          'port_directions': {op: 'output'}, 'connections': {op: [b]}})
            values[b] = v
            tie_bits[v] = b
            stats['tie_cells_added'] += 1
        return tie_bits[v]

    inv_cell = pick_cell(roles, 'inv')
    buf_cell = pick_cell(roles, 'buf')
    work = sorted(net.cells)
    while work:
        nxt = set()
        for n in work:
            c = net.cells.get(n)
            if c is None or kept(c):
                continue
            cs = comb_single(net, n)
            if cs is None or not cs[0]:
                continue
            ins, op, tree = cs
            ob = c['connections'][op][0]
            if not isinstance(ob, int) or ob in clk:
                continue
            const = {p: val(c['connections'][p][0]) for p in ins if val(c['connections'][p][0]) is not None}
            if not const:
                continue
            dyn = [p for p in ins if p not in const]
            kind = reduce_kind(tree, const, dyn)
            if kind is None:
                stats['kept_multi_input'] += 1
                continue
            loads = sorted(net.loads.get(ob, ()))
            if kind[0] == 'const':
                if ob in net.out_port_bits:
                    stats['const_port_kept'] += 1
                    values[ob] = kind[1]
                    continue
                net.remove(n)
                t = tie(kind[1])
                for ln, lp, k in loads:
                    net.set_pin(ln, lp, k, t)
                    nxt.add(ln)
                values.pop(ob, None)
                stats['removed_const'] += 1
                continue
            x = c['connections'][kind[1]][0]
            if kind[0] == 'inv' or ob in net.out_port_bits:
                master, ip, opn = inv_cell if kind[0] == 'inv' else buf_cell
                if c['type'] == master:
                    continue
                attrs = c.get('attributes', {})
                net.remove(n)
                net.add(n, {'hide_name': c.get('hide_name', 0), 'type': master, 'parameters': {}, 'attributes': attrs,
                            'port_directions': {ip: 'input', opn: 'output'}, 'connections': {ip: [x], opn: [ob]}})
                stats['to_inv' if kind[0] == 'inv' else 'to_buf_port'] += 1
                continue
            net.remove(n)
            for ln, lp, k in loads:
                net.set_pin(ln, lp, k, x)
                nxt.add(ln)
            stats['removed_identity'] += 1
        work = sorted(nxt)
    return values


def unary(net, n):
    """(in bit, out bit, inverted) if n is an actual unary BUF/INV-function cell (census transparency)."""
    cs = comb_single(net, n)
    if cs is None or len(cs[0]) != 1:
        return None
    ins, op, tree = cs
    try:
        tt = [NC.function_value(tree, {ins[0]: v}) for v in (0, 1)]
    except (KeyError, RecursionError):
        return None
    if tt not in ([0, 1], [1, 0]):
        return None
    c = net.cells[n]
    return c['connections'][ins[0]][0], c['connections'][op][0], tt == [1, 0]


def endpoints(net, b, clk):
    """Census endpoints of net b through unary cells: [(cell, pin, idx, inverted)], port bits, tree cells, opaque."""
    ends, ports, tree, opaque = [], [], [], False
    stack, seen = [(b, False)], set()
    while stack:
        x, inv = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        if x in net.out_port_bits:
            ports.append((x, inv))
        for ln, lp, k in sorted(net.loads.get(x, ())):
            if net.is_clock_pin(ln, lp):
                continue
            u = unary(net, ln)
            if u is not None and u[0] == x and isinstance(u[1], int):
                tree.append(ln)
                if kept(net.cells[ln]) or u[1] in clk:
                    opaque = True
                stack.append((u[1], inv ^ u[2]))
            else:
                ends.append((ln, lp, k, inv))
    return ends, ports, tree, opaque


def clone(net, clk, values, limit, target, stats, old_counts, clone_real=False):
    inv_cell = pick_cell(net.roles, 'inv')
    frontier, done_frontier = [], set()

    def count(b):
        e, p, _, _ = endpoints(net, b, clk)
        return len(e) + len(p)

    def is_root(b):
        d = net.driver.get(b)
        return d is None or unary(net, d[0]) is None   # a unary cell output is inside its driver's tree

    def root_of(b):
        seen = set()
        while b not in seen:
            seen.add(b)
            d = net.driver.get(b)
            u = unary(net, d[0]) if d is not None else None
            if u is None or not isinstance(u[0], int):
                return b
            b = u[0]
        return b

    work = sorted(b for b in set(net.loads) | set(net.driver) if isinstance(b, int))
    work = [b for b in work if b not in values and b not in clk and is_root(b) and count(b) > limit]
    guard = 0
    while work:
        guard += 1
        if guard > 2_000_000:
            raise RuntimeError('clone worklist did not converge')
        b = work.pop()
        if b in values or b in clk or not is_root(b):
            continue
        ends, ports, tree, opaque = endpoints(net, b, clk)
        n_end = len(ends) + len(ports)
        if n_end <= limit:
            continue
        d = net.driver.get(b)
        why = None
        if old_counts.get(b, 0) > limit and not clone_real:
            why = 'real fanout (> limit before the constant fold): distribute it in RTL (kept copies / registered tree)'
        elif d is None:
            why = 'input port: register / distribute it in RTL' if b in net.in_port_bits else 'undriven net'
        else:
            c = net.cells[d[0]]
            role = net.roles.get(c['type'])
            outs = [p for p in c['connections'] if net.direction(d[0], p) == 'output']
            if role is None:
                why = 'driver is not a Liberty cell (macro / unknown)'
            elif len(outs) != 1 or len(c['connections'][outs[0]]) != 1:
                why = 'multi-output driver'
            elif opaque:
                why = 'kept BUF/INV in the fanout tree'
            elif any(p[0] != b for p in ports):
                why = 'output port behind a BUF/INV of the tree'
        if why:
            key = (b, why)
            if key not in done_frontier:
                done_frontier.add(key)
                who = net.in_port_bits.get(b) or (d and f'{d[0]}/{d[1]}') or str(b)
                frontier.append({'driver': who, 'loads': n_end, 'reason': why})
            continue
        src, op = d
        c = net.cells[src]
        for t in tree:                                  # dissolve the BUF/INV tree of this driver
            net.remove(t)
            stats['tree_bufinv_removed'] += 1
        k = -(-n_end // target)
        per = -(-n_end // k)
        order = sorted(ends, key=lambda e: (e[3], e[0], e[1], e[2]))
        port_n = len(ports)
        groups, cur = [], []
        cap0 = per - port_n                                # output-port bits stay on the original net b
        for e in order:
            lim = cap0 if not groups else per
            if len(cur) >= lim:
                groups.append(cur)
                cur = []
            cur.append(e)
        groups.append(cur)
        for gi, grp in enumerate(groups):
            if gi == 0:
                gb = b
            else:
                base = f'{src}_ofc{gi}'
                while base in net.cells:
                    base += '_'
                gb = net.fresh(base + '_q')
                conns = {p: list(bs) for p, bs in c['connections'].items()}
                conns[op] = [gb]
                net.add(base, {'hide_name': c.get('hide_name', 0), 'type': c['type'],
                               'parameters': dict(c.get('parameters', {})), 'attributes': dict(c.get('attributes', {})),
                               'port_directions': dict(c.get('port_directions', {})), 'connections': conns})
                stats['clones'] += 1
                for p, bs in conns.items():
                    if p == op or net.is_clock_pin(base, p):
                        continue
                    for x in bs:
                        if isinstance(x, int) and x not in values and x not in clk:
                            work.append(root_of(x))
            ib = None
            for ln, lp, kk, inv in grp:
                if inv:
                    if ib is None:
                        name = f'{src}_ofi{gi}'
                        while name in net.cells:
                            name += '_'
                        ib = net.fresh(name + '_y')
                        im, ip, iop = inv_cell
                        net.add(name, {'hide_name': 0, 'type': im, 'parameters': {}, 'attributes': {},
                                       'port_directions': {ip: 'input', iop: 'output'},
                                       'connections': {ip: [gb], iop: [ib]}})
                        stats['inv_added'] += 1
                    net.set_pin(ln, lp, kk, ib)
                else:
                    net.set_pin(ln, lp, kk, gb)
        # the driver's own inputs: unchanged on the original; the copies were queued above
    return frontier


def root_counts(net, clk, values):
    out = {}
    for b in sorted(set(net.driver) | set(net.in_port_bits)):
        if b in values or b in clk:
            continue
        d = net.driver.get(b)
        if d is not None and unary(net, d[0]) is not None:
            continue
        e, p, _, _ = endpoints(net, b, clk)
        out[b] = len(e) + len(p)
    return out


def census_max(net, clk, values):
    worst, over = 0, 0
    for b in set(net.driver) | set(net.in_port_bits):
        if b in values or b in clk:
            continue
        d = net.driver.get(b)
        if d is not None and unary(net, d[0]) is not None:
            continue
        e, p, _, _ = endpoints(net, b, clk)
        n = len(e) + len(p)
        worst = max(worst, n)
        over += n > 32
    return worst, over


def run(inp, out, top, liberty, limit=32, target=24, report=None, force=False, clone_real=False):
    roles, receipts = NC.liberty_roles(liberty)
    d = json.loads(Path(inp).read_text())
    if top not in d['modules']:
        raise SystemExit(f'top {top} absent')
    mod = d['modules'][top]
    net = Net(mod, roles)
    clk = clock_bits(net)
    stats = collections.Counter()
    # old-rule counts (transparency through BUF/INV only, constants excluded) on the unfolded netlist
    ovals = {}
    for n in sorted(net.cells):
        cs = comb_single(net, n)
        if cs and not cs[0]:
            try:
                ovals[net.cells[n]['connections'][cs[1]][0]] = NC.function_value(cs[2], {})
            except (KeyError, RecursionError):
                pass
    old_counts = root_counts(net, clk, ovals)
    probe = json.loads(json.dumps(mod))
    pnet = Net(probe, roles)
    pclk = clock_bits(pnet)
    pvals = fold(pnet, pclk, collections.Counter())
    pcounts = root_counts(pnet, pclk, pvals)
    over = sorted(b for b, n in pcounts.items() if n > limit)
    real = [b for b in over if old_counts.get(b, 0) > limit]
    rep = {'schema': 'opentallas.native_fanout_bound.v1', 'top': top, 'limit': limit, 'target': target,
           'liberty': receipts, 'input': str(inp), 'pre_max_dynamic_loads': max(pcounts.values(), default=0),
           'pre_drivers_over': len(over), 'pre_drivers_over_real': len(real),
           'old_rule_max_dynamic_loads': max(old_counts.values(), default=0)}
    del probe, pnet
    if not over:
        rep['status'] = 'NO_CHANGE'
        if report:
            Path(report).write_text(json.dumps(rep, indent=2) + '\n')
        print(f"NFB NO_CHANGE max={rep['pre_max_dynamic_loads']}")
        return 3
    if real and not (force or clone_real):
        rep['status'] = 'FRONTIER'
        rep['frontier_count'] = len(real)
        rep['frontier'] = [{'net': b, 'loads': pcounts[b], 'old_rule_loads': old_counts[b],
                            'driver': '/'.join(net.driver[b]) if b in net.driver else net.in_port_bits.get(b),
                            'reason': 'real fanout (> limit before the constant fold): distribute it in RTL'}
                           for b in real[:200]]
        if report:
            Path(report).write_text(json.dumps(rep, indent=2) + '\n')
        print(f"NFB FRONTIER real={len(real)} over={len(over)} (netlist unchanged; the census refuses the real fanout)")
        return 2
    values = fold(net, clk, stats)
    frontier = clone(net, clk, values, limit, target, stats, old_counts, clone_real)
    post_max, post_over = census_max(net, clk, values)
    rep.update(stats=dict(stats), frontier=frontier[:200], frontier_count=len(frontier),
               post_max_dynamic_loads=post_max, post_drivers_over=post_over,
               cells_after=len(net.cells))
    status = 'BOUNDED' if not frontier and post_over == 0 else 'FRONTIER'
    rep['status'] = status
    if report:
        Path(report).write_text(json.dumps(rep, indent=2) + '\n')
    print(f"NFB {status} pre_max={rep['pre_max_dynamic_loads']} pre_over={rep['pre_drivers_over']} "
          f'post_max={post_max} post_over={post_over} '
          f'frontier={len(frontier)} {dict(stats)}')
    if status != 'BOUNDED' and not force:
        return 2
    Path(out).write_text(json.dumps(d))
    return 0


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('inp')
    a.add_argument('out')
    a.add_argument('--top', required=True)
    a.add_argument('--liberty', action='append', required=True)
    a.add_argument('--limit', type=int, default=32)
    a.add_argument('--target', type=int, default=24)
    a.add_argument('--report')
    a.add_argument('--force', action='store_true', help='write OUT even when a frontier is left')
    a.add_argument('--clone-real', action='store_true',
                   help='also clone drivers already over the limit before the fold (diagnostic / tool proof only; '
                        'the flow never uses it: real fanout is an RTL fix)')
    args = a.parse_args()
    return run(args.inp, args.out, args.top, args.liberty, args.limit, args.target, args.report, args.force,
               args.clone_real)


if __name__ == '__main__':
    sys.exit(main())
