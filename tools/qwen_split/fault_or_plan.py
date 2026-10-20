#!/usr/bin/env python3
"""Plan the Qwen compute die fault-observability OR tree (Q.BIND.1) on an emitted GEN.

Input : fault_inventory.py JSON (unused fault bits with their clock root), the GEN place.tcl and LEFs.
Output: a geometry plan of qfd_fault_or nodes (rtl/qwen_split/qfd_fault_or.sv):
  * leaves: <= FANIN bits each, every source pin <= REACH um (manhattan) from the leaf; one clock root per leaf;
  * region roots: OR of the region's leaves (+ landed child regions), relay hops on any wire > REACH;
  * region tree toward the sink (sys_face, n_clk_d2d): every region->region edge is a different clock, so it is a
    forwarded 1-bit lane with a LANDING (qfd_landh0_1, fixed latency, no handshake); its own fault feeds the receiver;
  * a per-path latency bound source -> sink (edges) for the STATUS observation calendar.
Fails closed (exit 1) on: a source without a placed instance, an inventory/clock mismatch, a node over FANIN.
Planning only: physical_qualification_eligible=false. The GEN binder (next GEN) emits the instances from this plan.
"""
import argparse
import collections
import hashlib
import json
import math
import re
import sys
from pathlib import Path

LAND_EDGES = 5          # landing ring D4 + capture (qfd_landh0_1, D=4)
NODE_EDGES = 3          # qfd_fault_or f -> o


def parse_place(path):
    pl = {}
    for m in re.finditer(r'findInst (\S+)\] ([\d.]+) ([\d.]+) (\S+)', Path(path).read_text()):
        pl[m[1]] = (float(m[2]), float(m[3]), m[4])
    return pl


def parse_lef(paths, want_masters):
    """macro -> (w, h, {pin: (cx, cy)}) for the masters we need (pin centroid of the first RECT)."""
    out = {}
    for path in paths:
        cur = pin = None
        for line in Path(path).read_text().splitlines():
            t = line.split()
            if not t:
                continue
            if t[0] == 'MACRO':
                cur = t[1] if t[1] in want_masters else None
                if cur:
                    out[cur] = [0.0, 0.0, {}]
                pin = None
            elif cur is None:
                continue
            elif t[0] == 'SIZE':
                out[cur][0], out[cur][1] = float(t[1]), float(t[3])
            elif t[0] == 'PIN':
                pin = t[1]
            elif t[0] == 'RECT' and pin and pin not in out[cur][2]:
                x1, y1, x2, y2 = map(float, t[1:5])
                out[cur][2][pin] = ((x1 + x2) / 2, (y1 + y2) / 2)
            elif t[0] == 'END' and len(t) > 1 and t[1] == pin:
                pin = None
    return out


def xform(x0, y0, orient, w, h, px, py):
    if orient in ('R0', 'N'):
        return x0 + px, y0 + py
    if orient in ('MX', 'FS'):
        return x0 + px, y0 + h - py
    if orient in ('MY', 'FN'):
        return x0 + w - px, y0 + py
    if orient in ('R180', 'S'):
        return x0 + w - px, y0 + h - py
    raise ValueError(f'orient {orient}')


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def hops(d, reach):
    return max(0, math.ceil(d / reach) - 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inventory', required=True, type=Path)
    ap.add_argument('--place', required=True, type=Path)
    ap.add_argument('--lef', action='append', required=True, type=Path)
    ap.add_argument('--sink-inst', default='sys_face')
    ap.add_argument('--sink-clock', default='n_clk_d2d')
    ap.add_argument('--reach', type=float, default=405.0)
    ap.add_argument('--fanin', type=int, default=16)
    ap.add_argument('--xpen', type=float, default=5000.0, help='um-equivalent cost of a clock change (landing)')
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    inv = json.loads(a.inventory.read_text())
    pl = parse_place(a.place)
    lef = parse_lef(a.lef, {r['master'] for r in inv['rows']} | {'qfd_sys_face'})
    errors = []
    srcs = []          # (clock, (x, y), id, pin_exact)
    for r in inv['rows']:
        if r['instance'] not in pl:
            errors.append(f"unplaced {r['instance']}")
            continue
        x0, y0, ori = pl[r['instance']]
        w, h, pins = lef.get(r['master'], (0, 0, {}))
        for b in r['unused_bits']:
            key = r['port'] if r['port_width'] == 1 else f"{r['port']}[{b}]"
            exact = key in pins or r['port'] in pins
            px, py = pins.get(key) or pins.get(r['port']) or (w / 2, h / 2)
            srcs.append((r['clock'], xform(x0, y0, ori, w, h, px, py), f"{r['instance']}.{key}", exact))
    if a.sink_inst not in pl:
        errors.append('sink not placed')
    sx, sy, so = pl[a.sink_inst]
    sw, sh, _ = lef.get('qfd_sys_face', (0, 0, {}))
    sink = (sx + sw / 2, sy)        # planning point: sys_face S face centre (port is owed; see README)

    groups = collections.defaultdict(list)
    for s in srcs:
        groups[s[0]].append(s)
    leaves = []
    for ck, members in sorted(groups.items()):
        todo = sorted(members, key=lambda s: (s[1][0], s[1][1]))
        k = 0
        while todo:
            seed = todo[0]
            near = sorted(todo, key=lambda s: dist(s[1], seed[1]))
            take = [s for s in near if dist(s[1], seed[1]) <= a.reach][:a.fanin - 2]   # 2 inputs kept for tree children
            ids = {s[2] for s in take}
            todo = [s for s in todo if s[2] not in ids]
            leaves.append(dict(id=f"flt_{re.sub(r'^n_clk_', '', ck)}_{k}", clock=ck, at=[round(seed[1][0], 3), round(seed[1][1], 3)],
                               n=len(take), max_src_um=round(max(dist(s[1], seed[1]) for s in take), 3),
                               sources=[s[2] for s in take], pins_absent=sum(not s[3] for s in take),
                               children=[], parent=None))
            k += 1
    # one tree over every node, Prim from the sink root; an edge between two clocks is a landed 1-bit lane and costs
    # XPEN um extra, so regions are merged locally first and cross only where they must.
    root = dict(id='flt_sink', clock=a.sink_clock, at=[round(v, 3) for v in sink], n=0, max_src_um=0.0, sources=[],
                pins_absent=0, children=[], parent=None)
    nodes = [root] + leaves
    byid = {n['id']: n for n in nodes}
    if len(byid) != len(nodes):
        raise ValueError('fault_or_plan: duplicate node id')

    def cap(n):        # remaining OR inputs: each child is 1 bit, a landed child also brings its landing fault
        used = n['n'] + sum(2 if byid[c]['clock'] != n['clock'] else 1 for c in n['children'])
        return a.fanin - used

    def cost(c, p):
        return dist(c['at'], p['at']) + (a.xpen if c['clock'] != p['clock'] else 0)
    intree = [root]
    rest = {n['id'] for n in leaves}
    best = {i: (cost(byid[i], root), root['id']) for i in rest}
    while rest:
        i = min(sorted(rest), key=lambda j: best[j][0])
        c, p = byid[i], byid[best[i][1]]
        need = 2 if c['clock'] != p['clock'] else 1
        if cap(p) < need:   # parent full: recompute this child's best parent among nodes with room
            cand = [q for q in intree if cap(q) >= (2 if c['clock'] != q['clock'] else 1)]
            if not cand:
                errors.append('tree: no parent with room'); break
            q = min(cand, key=lambda q: cost(c, q)); best[i] = (cost(c, q), q['id']); continue
        c['parent'] = p['id']; p['children'].append(i)
        d = dist(c['at'], p['at']); c['up_um'] = round(d, 3); c['up_relays'] = hops(d, a.reach)
        c['up_landed'] = c['clock'] != p['clock']
        intree.append(c); rest.discard(i)
        for j in sorted(rest):
            cc = cost(byid[j], c)
            if cc < best[j][0] and cap(c) >= 1:
                best[j] = (cc, i)
    sink_hop = hops(dist(root['at'], sink), a.reach)
    worst = 0
    depth = 0
    for n in leaves:
        lat, m, dpt = NODE_EDGES, n, 0
        while m['parent'] is not None:
            lat += m['up_relays'] + (LAND_EDGES if m['up_landed'] else 0) + NODE_EDGES
            m = byid[m['parent']]; dpt += 1
        n['latency_edges'] = lat + sink_hop + 1
        worst = max(worst, n['latency_edges']); depth = max(depth, dpt)
    for n in nodes:
        if a.fanin - cap(n) > a.fanin:
            errors.append(f"{n['id']} fanin {a.fanin - cap(n)}")
    bits = sum(l['n'] for l in leaves)
    if bits != inv['actual_unused_bits']:
        errors.append(f'bits {bits} != inventory {inv["actual_unused_bits"]}')
    absent = collections.Counter()
    for s in srcs:
        if not s[3]:
            inst = s[2].split('.')[0]
            m = next(r['master'] for r in inv['rows'] if r['instance'] == inst)
            absent['GEN_GLUE_PIN_OWED' if m.startswith('qfd_land') else 'CLOSED_VIEW_PIN_ABSENT:' + m] += 1
    summary = dict(bits=bits, source_pins_present=sum(s[3] for s in srcs), source_pins_absent=dict(absent),
                   leaves=len(leaves), nodes=len(nodes), landings=sum(1 for n in leaves if n.get('up_landed')),
                   relays=sum(n.get('up_relays', 0) for n in leaves) + sink_hop, tree_depth=depth,
                   max_leaf_src_um=max(l['max_src_um'] for l in leaves), max_node_fanin=max(a.fanin - cap(n) for n in nodes),
                   worst_latency_edges=worst, reach_um=a.reach, fanin_cap=a.fanin, clock_change_penalty_um=a.xpen,
                   errors=len(errors))
    out = dict(schema='opentallas.qw_fault_or_plan.v2', physical_qualification_eligible=False,
               scope='Planning geometry for the Q.BIND.1 fault OR tree; the GEN binder, native census, routing and STA '
                     'of the emitted tree are still owed.',
               sources={str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [a.inventory, a.place, *a.lef]},
               sink=dict(inst=a.sink_inst, clock=a.sink_clock, at=[round(v, 3) for v in sink], sink_relays=sink_hop,
                         port='OWED: qfd_sys_face input obs_fault (OR into tt_fab / result_cause face class)'),
               summary=summary, errors=errors, nodes=nodes)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    print('FAULT_OR_PLAN', 'PASS' if not errors else 'FAIL', json.dumps(summary))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
