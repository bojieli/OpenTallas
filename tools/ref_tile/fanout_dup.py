#!/usr/bin/env python3
"""fanout_dup.py -- drivers within the native-census load limit BY CONSTRUCTION (S81-SVCRS-3, COORD 11-10).

    fanout_dup.py --netlist 1_2_yosys.v --top TOP --liberty LIB [--liberty LIB ...] --out fixed.v --report fdup.json
                  [--limit 64] [--max-iter 12]
    exit 0 = every dynamic driver <= limit in the written netlist; 1 = residual drivers (listed); 2 = input error.

A deterministic pass on the flat ORFS Yosys netlist of a kit.  The kit then runs P&R with
--orfs-var SYNTH_NETLIST_FILES=<fixed.v> (ORFS synth_preamble copies it to 1_2_yosys.v and skips Yosys), so the
mandatory native census (PRE_FLOORPLAN, reads 1_2_yosys.v), the synthesis ODB and the routed LEC all see this netlist.

LOAD MODEL = tools/ref_tile/native_census.py, by import (census(..., expose=...)): Liberty roles, constant and clock
pins excluded, transparent unary cells (BUF / INV and constant-reduced cells) traced through, reset and macro data pins
counted, output ports counted.  Nothing is re-derived here.

TRANSFORM, per driver above --limit (input ports excepted): its endpoints (leaf pins reached through the transparent
tree, in DFS order with children sorted by instance name, output-port endpoints first) are split into G = ceil(n/limit)
balanced groups.  Group 0 keeps the original cells.  For each group k >= 1 the driver cell is cloned (same master, the
same nets on every input pin incl. clock and reset), every transparent cell on that group's paths is cloned once
(<inst>__fdup<k>), and the group's endpoint pins are moved onto the cloned path.  Clones add one load to each of their
input nets, so the pass repeats to a fixpoint (--max-iter).  Output ports and input-port drivers cannot be cloned: an
input port above the limit is reported as residual (exit 1), never silently kept.  Functionally the clones are twins
of the original cell (same inputs, same function): a combinational clone is equal by construction, a register clone
is equal from the first clock edge on (it loads the same D), which the routed LEC reports as a merged twin.
The 33..limit band is reported, not changed (COORD 11-09 s81svc census admission).
"""
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import native_census as NC  # noqa: E402
import textbook_lint as TL  # noqa: E402

SIMPLE = re.compile(r'^[A-Za-z_][A-Za-z0-9_$]*$')
PORT_BIT = re.compile(r'^([A-Za-z_][A-Za-z0-9_$]*)(\[\d+\])?$')


def esc(name):
    return name if SIMPLE.match(name) else '\\' + name + ' '


def load_graph(text, top, roles):
    mods = TL.parse_verilog(text)
    if top not in mods:
        raise ValueError(f'mapped top absent: {top}')
    mods = {k: v for k, v in mods.items() if k == top or k not in roles}
    if len(mods) != 1:
        raise ValueError(f'flat netlist expected (one module): {sorted(mods)[:8]}')
    g, top = TL.flatten(mods, top)
    return g, mods[top]


def model(g, roles):
    ex = {}
    rep = NC.census(g, roles, expose=ex)
    return rep, ex


def endpoints_of(g, ex, net):
    """census endpoints of one driver net, DFS order; parent[x] = transparent cell index that drives net x"""
    loads, ports, transp = ex['loads'], ex['ports'], ex['transparent']
    order, parent, seen = [], {net: None}, set()

    def name_of(end):
        return g.cells[end[0]][1] if end[0] != 'port' else ''

    stack = [net]
    while stack:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        for pe in sorted(ports.get(x, ()), key=str):
            order.append(('port', pe, x))
        kids = []
        for end in sorted(loads.get(x, ()), key=lambda e: (name_of(e), e[1], e[2])):
            ci = end[0]
            if ci in transp and transp[ci][0] == x:
                dst = transp[ci][1]
                if dst not in parent:
                    parent[dst] = ci
                    kids.append(dst)
            else:
                order.append(('pin', end, x))
        stack.extend(reversed(kids))
    return order, parent


class Cloner:
    def __init__(self, g):
        self.g = g
        self.names = {c[1] for c in g.cells}

    def name(self, base):
        k = 1
        while f'{base}__fdup{k}' in self.names:
            k += 1
        n = f'{base}__fdup{k}'
        self.names.add(n)
        return n

    def clone(self, ci, in_map, keep_out):
        """clone cell ci: input bits remapped by in_map; output bit keep_out -> fresh net returned; other outputs fresh"""
        g = self.g
        master, name, pins = g.cells[ci]
        new = self.name(name)
        out_nets, fresh = {}, None
        npins = {}
        drv_out = self.outs.get(ci, ())
        for pn, nets in pins.items():
            row = []
            for b, x in enumerate(nets):
                if x in drv_out:
                    y = g.net(f'{new}.{pn}' + (f'[{b}]' if len(nets) > 1 else ''))
                    g.parent[y] = y
                    out_nets[x] = y
                    row.append(y)
                    if x == keep_out:
                        fresh = y
                else:
                    row.append(in_map.get(x, x))
            npins[pn] = row
        g.cells.append((master, new, npins))
        return len(g.cells) - 1, fresh


def strip_dead_unary(g, roles):
    """--strip-dead-unary: remove transparent unary cells (BUF / INV in the census model) whose output net has no load and
    no port, to a fixpoint.  ORFS synthesis turns the pin-register wrapper's `assign o = o__ot_q` into a loadless BUFx2 on
    the output port net; P&R deletes it (absent from 6_final.v), but face_guard reads 1_2_yosys.v and counted it as a
    second load on the port net ('shared').  Dead logic only, so the netlist function is unchanged.  -> removed names"""
    removed = []
    while True:
        _rep, ex = model(g, roles)
        # raw pin references, NOT the census load model (that one skips clock and constant pins): a net is unread only
        # when the dead cell's own output pin is its single reference and no top port is on it
        refs = {}
        for _m, _n, pins in g.cells:
            for nets in pins.values():
                for x in nets:
                    r = g.find(x)
                    refs[r] = refs.get(r, 0) + 1
        port_nets = {g.find(x) for _d, x in g.ports.values()}
        dead = sorted(ci for ci, (_i, o) in ex['transparent'].items()
                      if refs.get(g.find(o), 0) == 1 and g.find(o) not in port_nets)
        if not dead:
            return removed
        ds = set(dead)
        removed += [g.cells[ci][1] for ci in dead]
        g.cells[:] = [c for i, c in enumerate(g.cells) if i not in ds]


def replica_pin_regs(g):
    """{input port bit: D} for input bits whose net feeds the D pin of more than one register: a pin register that the
    split copied (its clones load the same D).  Read from the written netlist (clones connect D to the port net)."""
    is_reg = lambda m: m.upper().startswith(("DFF", "SDF", "$_DFF", "$_SDFF"))
    cnt = {}
    for b, (d, x) in g.ports.items():
        if d != 'input':
            continue
        r = g.find(x)
        n = sum(1 for m, _n, pins in g.cells if is_reg(m) for x2 in pins.get('D', ()) if g.find(x2) == r)
        if n > 1:
            cnt[b] = n
    return cnt


def land_slots(rep, plan):
    """face_guard land_slots.json of the copied pin registers: a bus = per-bit D map, a scalar port = uniform D"""
    buses = {}
    for b, n in sorted(rep.items()):
        m = PORT_BIT.match(b)
        name, idx = m.group(1), m.group(2)
        if idx is None:
            buses[name] = {"D": n, "form": "replica", "plan": plan}
        else:
            buses.setdefault(name, {"bits": {}, "form": "replica", "plan": plan})["bits"][idx[1:-1]] = n
    return {"schema": "opentallas.face_guard.land_slots.v1", "source": "tools/ref_tile/fanout_dup.py --land-slots",
            "buses": buses}


def split_once(g, roles, limit, cl, log):
    rep, ex = model(g, roles)
    cl.outs = {}
    for n_, d_ in ex['drivers'].items():
        if d_[0] != 'port':
            cl.outs.setdefault(d_[0], set()).add(n_)
    work, residual = [], []
    for v in rep['violations']:
        if v['loads'] <= limit:
            continue
        net = g.find(g.net_id[v['net']])
        d = ex['drivers'][net]
        if d[0] == 'port':
            residual.append(dict(driver=v['driver'], net=v['net'], loads=v['loads'], why='input port: cannot clone'))
            continue
        work.append((v['driver'], net, d[0], v['loads']))
    for who, net, ci, n in sorted(work):
        order, parent = endpoints_of(g, ex, net)
        assert len(order) == n, (who, len(order), n)
        G = math.ceil(n / limit)
        size = math.ceil(n / G)
        groups = [order[i:i + size] for i in range(0, n, size)]
        if any(e[0] == 'port' for grp in groups[1:] for e in grp):
            residual.append(dict(driver=who, net=g.net_name[net], loads=n, why='output ports beyond one group'))
            continue
        clones = 0
        for grp in groups[1:]:
            k_ci, root = cl.clone(ci, {}, net)
            clones += 1
            netmap = {net: root}

            def mapped(x):
                if x in netmap:
                    return netmap[x]
                t = parent[x]
                tin = ex['transparent'][t][0]
                up = mapped(tin)
                _, y = cl.clone(t, {tin: up}, x)
                netmap[x] = y
                return y
            for kind, end, x in grp:
                ci2, pn, bit = end
                tgt = mapped(x)
                assert g.cells[ci2][2][pn][bit] == x
                g.cells[ci2][2][pn][bit] = tgt
        log.append(dict(driver=who, net=g.net_name[net], loads_before=n, groups=G, group_size=size,
                        driver_clones=clones))
    return len(work), residual


def emit(g, tm, top):
    """flat structural Verilog of the (mutated) graph; top ports declared as in the source"""
    zero, one = g.find(g.net_id["1'0"]), g.find(g.net_id["1'1"])
    xs = {g.find(g.net_id[c]) for c in ("1'x", "1'z")}
    port_of = {}
    for b, (d, x) in sorted(g.ports.items(), key=lambda t: (t[1][0] != 'input', t[0])):
        port_of.setdefault(g.find(x), b)
    assigns = []
    for b, (d, x) in sorted(g.ports.items()):
        r = g.find(x)
        if r in (zero, one) or r in xs:
            if d != 'output':
                raise ValueError(f'input port tied to a constant: {b}')
            assigns.append((b, "1'b0" if r == zero else "1'b1" if r == one else "1'bx"))
        elif port_of[r] != b:
            assigns.append((b, port_of[r]))
    used = set()

    def nm(x):
        r = g.find(x)
        if r == zero:
            return "1'b0"
        if r == one:
            return "1'b1"
        if r in xs:
            return "1'bx"
        if r in port_of:
            return port_of[r]
        used.add(r)
        return esc(g.net_name[r])

    body = []
    for master, name, pins in g.cells:
        conns = []
        for pn, nets in pins.items():
            if not nets:
                conns.append(f'.{esc(pn)}()')
            elif len(nets) == 1:
                conns.append(f'.{esc(pn)}({nm(nets[0])})')
            else:
                conns.append(f'.{esc(pn)}({{ {", ".join(nm(x) for x in nets)} }})')
        body.append(f'  {esc(master)} {esc(name)} ( ' + ', '.join(conns) + ' );')
    out = [f'module {esc(top)}(' + ', '.join(esc(p) for p in tm.ports) + ');']
    for p in tm.ports:
        d = tm.dirs.get(p, 'input')
        w = tm.widths.get(p)
        out.append(f'  {d} ' + (f'[{w[0]}:{w[1]}] ' if w else '') + esc(p) + ';')
    for r in sorted(used):
        out.append(f'  wire {esc(g.net_name[r])};')
    out += body
    for b, s in assigns:
        out.append(f'  assign {b} = {s};')
    out.append('endmodule')
    return '\n'.join(out) + '\n'


def band(rep, lo, hi):
    return sum(1 for c in rep['driver_counts'] if lo < c['loads'] <= hi)


def summary(rep, limit):
    return dict(status=rep['status'], max_loads=rep['max_dynamic_loads'],
                over_limit=band(rep, limit, 10 ** 9), band_33_limit=band(rep, 32, limit),
                role_errors=len(rep['role_errors']))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--netlist', required=True)
    p.add_argument('--top', required=True)
    p.add_argument('--liberty', action='append', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--limit', type=int, default=64)
    p.add_argument('--max-iter', type=int, default=12)
    p.add_argument('--land-slots', help='write face_guard land_slots.json of copied pin registers here (replica form)')
    p.add_argument('--land-plan', help='plan event keying the replica form (face_guard.REPLICA_PLANS)')
    p.add_argument('--strip-dead-unary', action='store_true', help='remove loadless BUF / INV cells first (see strip_dead_unary)')
    a = p.parse_args(argv)
    roles, libs = NC.liberty_roles(a.liberty)
    raw = Path(a.netlist).read_bytes()
    g, tm = load_graph(raw.decode(), a.top, roles)
    cells0 = len(g.cells)
    before, _ = model(g, roles)
    if before['role_errors']:
        print('fanout_dup: role errors in the input netlist', before['role_errors'][:5], file=sys.stderr)
        return 2
    dead = strip_dead_unary(g, roles) if a.strip_dead_unary else []
    log, residual, it = [], [], 0
    cl = Cloner(g)
    while it < a.max_iter:
        it += 1
        n, residual = split_once(g, roles, a.limit, cl, log)
        if n == 0:
            break
    # nothing split: the input bytes pass through unchanged (same netlist sha, so every receipt of it stays valid)
    text = emit(g, tm, a.top) if (log or dead) else raw.decode()
    Path(a.out).write_text(text)
    # verification = the census itself on the WRITTEN netlist, parsed exactly like native_census.main
    g2, _ = load_graph(text, a.top, roles)
    after = NC.census(g2, roles)
    final_over = [dict(driver=v['driver'], net=v['net'], loads=v['loads']) for v in after['violations']
                  if v['loads'] > a.limit]
    rec = dict(schema='opentallas.fanout_dup.v1', tool='tools/ref_tile/fanout_dup.py', top=a.top, limit=a.limit,
               load_model='tools/ref_tile/native_census.py census() (imported)',
               input=dict(path=a.netlist, sha256=hashlib.sha256(raw).hexdigest()),
               output=dict(path=a.out, sha256=hashlib.sha256(text.encode()).hexdigest()),
               liberty=libs, iterations=it, cells_before=cells0, cells_after=len(g2.cells),
               cells_added=len(g2.cells) - cells0, before=summary(before, a.limit), after=summary(after, a.limit),
               splits=log, residual=residual if final_over else [], residual_after=final_over,
               dead_unary_removed=dict(n=len(dead), cells=dead[:200]))
    reps = replica_pin_regs(g2)
    rec['replica_pin_regs'] = reps
    if a.land_slots:
        if reps and not a.land_plan:
            print('fanout_dup: copied pin registers need --land-plan', file=sys.stderr)
            return 2
        if reps:
            Path(a.land_slots).write_text(json.dumps(land_slots(reps, a.land_plan), indent=1) + '\n')
        elif Path(a.land_slots).exists():
            Path(a.land_slots).unlink()
    Path(a.report).write_text(json.dumps(rec, indent=1) + '\n')
    print(f"FANOUT_DUP {'PASS' if not final_over and not after['role_errors'] else 'FAIL'} "
          f"max {rec['before']['max_loads']} -> {rec['after']['max_loads']}, >{a.limit} "
          f"{rec['before']['over_limit']} -> {rec['after']['over_limit']}, cells +{rec['cells_added']}, iter {it}, dead unary removed {len(dead)}")
    return 0 if not final_over and not after['role_errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
