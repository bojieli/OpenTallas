#!/usr/bin/env python3
"""DIE-CLOCK: build + measure + trim physical die clock trees in an actual die ODB (Claude DIE-CLOCK 2026-10-16).

Run inside the ORFS container:
  openroad -python -no_init -exit build.py --odb IN.odb --spec spec.json --libs libs_tt.txt --out DIR
      [--targets kit.json] [--iters 3] [--write-odb]
  openroad -python -no_init -exit build.py --measure DIR/manifest.json --odb DIR/clock.odb --libs libs_ff.txt
      --corner ff --out DIR                           (re-measure the final ODB at another corner)

spec.json: {"trees": [{"name": N, "root": "inst/pin", "period": ps, "balance_group": G (optional, shared target),
                        "select": {"master_prefix": [...]} | {"exclude_master_prefix": [...]} | "all"},
                       {"name": "col", "root_master_prefix": "dsfd_cfifo", "root_port": "co[0]", "period": ps}, ...],
             "rc_layer": "M8", "leaf_um": 60, "leaf_max": 12}
  a tree with root_master_prefix expands to one tree per instance of that master (name = <name>_<inst>).
targets: the die kit's kit.json (masters[m].insertion_per_clock_pin_ps / insertion_in_arcs_ps, [ss, ff, tt]):
  the in-arc insertion R of each sink pin.  The trim balances arrival + R (flop arrival), i.e. pin at phi - R.
Every clock cell is a real ASAP7 buffer on a legal site outside every hard block; arrivals are OpenSTA propagated
clock arrivals with placement parasitics (set_wire_rc -clock -layer rc_layer); nothing is ideal or modelled at the end.
Outputs: manifest.json (trees, cells, topology parent map, leaves, per-iteration stats), arrivals_<corner>.tsv
(pin, late, early, slew) for every sink AND every clock-cell output, drv_<corner>.rpt, clock.odb (--write-odb).
"""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import regtree as rt  # noqa: E402

XPITCH, YPITCH = 1.620, 0.270
PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


class Sites:
    """legal 1.62 x 0.27 sites outside hard blocks (10-um grid, conservative) and outside existing std cells."""

    def __init__(self, grid, W, H, taken):
        self.g, self.W, self.H = grid, W, H
        self.nx, self.ny = int(W / XPITCH), int(H / YPITCH)
        self.occ = set(taken)
        self._search = None

    def legal(self, ix, iy):
        x, y = ix * XPITCH, iy * YPITCH
        if (ix, iy) in self.occ or x + XPITCH > self.W or y + YPITCH > self.H:
            return False
        G = rt.GRID
        for ci in range(int(x / G), int((x + XPITCH - 1e-9) / G) + 1):
            for cj in range(int(y / G), int((y + YPITCH - 1e-9) / G) + 1):
                if not (0 <= ci < self.g.nx and 0 <= cj < self.g.ny and self.g.free((ci, cj))):
                    return False
        return True

    def take(self, x0, y0):
        import heapq
        s = (min(self.nx - 1, max(0, round(x0 / XPITCH))), min(self.ny - 1, max(0, round(y0 / YPITCH))))
        # Trim pads arrive consecutively at the same leaf coordinate. Resume
        # that search rather than revisiting every pad already placed there.
        # Keep only the last origin, so unique tree-buffer origins do not retain
        # one frontier each. Obstacles are fixed and occupancy only increases.
        key = (x0, y0)
        if self._search is None or self._search[0] != key:
            self._search = (key, [(0.0, s)], {s})
        _, q, seen = self._search
        while q:
            _, (ix, iy) = heapq.heappop(q)
            available = self.legal(ix, iy)
            # Expand the chosen site too: on a restarted search it is occupied,
            # and its neighbours must still participate in the next choice.
            for n in ((ix - 1, iy), (ix + 1, iy), (ix, iy - 1), (ix, iy + 1)):
                if 0 <= n[0] < self.nx and 0 <= n[1] < self.ny and n not in seen:
                    seen.add(n)
                    heapq.heappush(q, (abs(n[0] * XPITCH - x0) + abs(n[1] * YPITCH - y0), n))
            if available:
                self.occ.add((ix, iy))
                return round(ix * XPITCH, 3), round(iy * YPITCH, 3)
        raise ValueError(f'no legal clock site near {x0},{y0}')


def esc(n):
    return n.replace('[', '\\[').replace(']', '\\]')


def pin_key(p):
    inst, port = p.rsplit('/', 1)
    return inst, port[:-3] if port.endswith('[0]') else port


class Die:
    def __init__(self, a):
        from openroad import Tech, Design
        import odb
        self.odb = odb
        self.tech = Tech()
        for lib in Path(a.libs).read_text().split():
            self.tech.readLiberty(lib)
        self.design = Design(self.tech)
        log('read_db', a.odb)
        self.design.readDb(a.odb)
        self.block = self.design.getBlock()
        self.u = self.block.getDbUnitsPerMicron()
        die = self.block.getDieArea()
        self.W, self.H = die.xMax() / self.u, die.yMax() / self.u
        self.tcl = self.design.evalTclString

    def setup_sta(self, clocks, rc_layer):
        self.tcl(f'source {PLAT}/setRC.tcl')
        self.tcl(f'set_wire_rc -clock -layer {rc_layer}')
        for name, pin, per in clocks:
            self.tcl(f'set _n {{{pin}}}; create_clock -name {name} -period {per} [get_pins [string map {{[ \\[ ] \\]}} $_n]]')
        self.tcl('set_propagated_clock [all_clocks]')

    def measure(self, pins, out):
        Path(str(out) + '.pins').write_text('\n'.join(pins) + '\n')
        self.tcl('estimate_parasitics -placement')
        self.tcl('sta::find_timing_paths -path_delay max -group_path_count 1')
        self.tcl(f'''set fi [open {{{out}.pins}}]; set fo [open {{{out}}} w]
while {{[gets $fi n] >= 0}} {{
  set p [get_pins -quiet [string map {{[ \\[ ] \\]}} $n]]
  if {{[llength $p] != 1}} {{ puts $fo "$n\\tNA\\tNA\\tNA"; continue }}
  set s NA; catch {{set s [get_property $p slew_max_rise]}}
  puts $fo "$n\\t[get_property $p arrival_max_rise]\\t[get_property $p arrival_min_rise]\\t$s"
}}
close $fi; close $fo''')
        res = {}
        for ln in Path(out).read_text().splitlines():
            n, l_, e_, s_ = ln.split('\t')
            f = lambda v: None if v in ('NA', '', 'INF', '-INF') or 'e+' in v and abs(float(v)) > 1e20 else float(v)
            try:
                res[n] = (f(l_), f(e_), f(s_))
            except ValueError:
                res[n] = (None, None, None)
        return res


def load_targets(path):
    """(master, port) -> [ss, ff, tt] in-arc insertion; master -> scalar fallback."""
    if not path:
        return lambda m, p: [0.0, 0.0, 0.0]
    km = json.loads(Path(path).read_text())['masters']

    def v(m, p):
        r = km.get(m, {})
        pp = r.get('insertion_per_clock_pin_ps', {})
        if p in pp:
            return pp[p]
        return r.get('insertion_in_arcs_ps') or [0.0, 0.0, 0.0]
    return v


def build(a):
    spec = json.loads(Path(a.spec).read_text())
    rt.LEAF_UM = spec.get('leaf_um', rt.LEAF_UM)
    rt.LEAF_MAX = spec.get('leaf_max', rt.LEAF_MAX)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    D = Die(a)
    blk, u, odb = D.block, D.u, D.odb
    obstacles, taken = [], set()
    insts_by_master = defaultdict(list)
    for inst in blk.getInsts():
        m = inst.getMaster()
        insts_by_master[m.getName()].append(inst)
        b = inst.getBBox()
        if m.isBlock():
            obstacles.append((b.xMin() / u, b.yMin() / u, b.xMax() / u, b.yMax() / u))
        elif inst.isPlaced():
            for ix in range(int(b.xMin() / u / XPITCH), int(b.xMax() / u / XPITCH) + 1):
                for iy in range(int(b.yMin() / u / YPITCH), int(b.yMax() / u / YPITCH) + 1):
                    taken.add((ix, iy))
    log('obstacles', len(obstacles), 'std cell sites taken', len(taken))
    g = rt.dct.Grid(D.W, D.H, obstacles)
    sites = Sites(g, D.W, D.H, taken)
    target = load_targets(a.targets)
    # expand tree specs
    trees = []
    for t in spec['trees']:
        if 'root_master_prefix' in t:
            for m in sorted(insts_by_master):
                if not m.startswith(t['root_master_prefix']):
                    continue
                for inst in sorted(insts_by_master[m], key=lambda i: i.getName()):
                    trees.append(dict(t, name=f"{t['name']}_{inst.getName()}", root=f"{inst.getName()}/{t['root_port']}",
                                      select='all'))
        else:
            trees.append(t)
    if a.only:
        keep = set(a.only.split(','))
        trees = [t for t in trees if t['name'] in keep or t['name'].split('_')[0] in keep]
    rec = dict(schema='opentallas.die_clock.manifest.v1', odb=a.odb, spec=spec, trees={}, cells=[], parent={}, cell_tree={},
               leaves={}, iterations=[])
    clocks, sink_pins, builders = [], {}, {}
    tree_group = {t['name']: t['balance_group'] for t in trees if t.get('balance_group')}
    by_root = defaultdict(list)
    for t in trees:
        by_root[t['root']].append(t)
    for root, ts in by_root.items():
        it = blk.findITerm(root)
        if not it or not it.getNet():
            raise ValueError(f'clock root missing/unconnected: {root}')
        net = it.getNet()
        rb = it.getBBox(); rxy = ((rb.xMin() + rb.xMax()) / 2 / u, (rb.yMin() + rb.yMax()) / 2 / u)
        loads = [x for x in net.getITerms() if x.getIoType() == 'INPUT']
        claimed = set()
        clocks.append((ts[0]['name'], root, ts[0].get('period', 833.333)))
        for t in ts:
            sel = t.get('select', 'all')
            sinks = []
            for x in loads:
                mn = x.getInst().getMaster().getName()
                bx = x.getBBox(); px, py = (bx.xMin() + bx.xMax()) / 2 / u, (bx.yMin() + bx.yMax()) / 2 / u
                if sel != 'all' and 'bbox' in sel:
                    x0, y0, x1, y1 = sel['bbox']
                    if not (x0 <= px <= x1 and y0 <= py <= y1):
                        continue
                if sel != 'all' and 'outside_bbox' in sel:
                    x0, y0, x1, y1 = sel['outside_bbox']
                    if x0 <= px <= x1 and y0 <= py <= y1:
                        continue
                if sel != 'all':
                    if 'master_prefix' in sel and not mn.startswith(tuple(sel['master_prefix'])):
                        continue
                    if 'exclude_master_prefix' in sel and mn.startswith(tuple(sel['exclude_master_prefix'])):
                        continue
                pn = f'{x.getInst().getName()}/{x.getMTerm().getName()}'
                if pn in claimed:
                    continue
                claimed.add(pn)
                b = x.getBBox()
                port = pin_key(pn)[1]
                sinks.append((pn, mn, (b.xMin() + b.xMax()) / 2 / u, (b.yMin() + b.yMax()) / 2 / u, f'{mn}/{port}'))
            if not sinks:
                log('tree', t['name'], 'has no sinks; skipped')
                continue
            leaves = rt.cluster(sinks)
            b_ = rt.Builder(g, 'dc_' + t['name'])
            model = b_.build(root, rxy, leaves)
            for s in sinks:
                sink_pins[s[0]] = dict(tree=t['name'], master=s[1], x=round(s[2], 3), y=round(s[3], 3),
                                      R=target(s[1], pin_key(s[0])[1]))
            rec['trees'][t['name']] = dict(root=root, root_xy=[round(rxy[0], 3), round(rxy[1], 3)], sinks=len(sinks), model=model)
            builders[t['name']] = b_
            log('tree', t['name'], 'sinks', len(sinks), json.dumps(model))
        unclaimed = [x for x in loads if f'{x.getInst().getName()}/{x.getMTerm().getName()}' not in claimed]
        if unclaimed:
            raise ValueError(f'{root}: {len(unclaimed)} loads not claimed by any tree spec')
    # instantiate
    masters, cell_xy = {}, {}

    def mk(name, cell, x, y):
        if cell not in masters:
            masters[cell] = D.design.getDb().findMaster(cell)
            if not masters[cell]:
                raise ValueError(f'no master {cell}')
        sx, sy = sites.take(x, y)
        inst = odb.dbInst.create(blk, masters[cell], name)
        inst.setOrient('R0' if round(sy / YPITCH) % 2 == 0 else 'MX')
        inst.setLocation(round(sx * u), round(sy * u))
        inst.setPlacementStatus('PLACED')
        rec['cells'].append([name, cell, sx, sy])
        cell_xy[name] = (sx, sy)
        return inst

    insts = {}
    for t in trees:
        b_ = builders.get(t['name'])
        if not b_:
            continue
        for n, cell, x, y in b_.bufs:
            insts[n] = mk(n, cell, x, y)
            rec['cell_tree'][n] = t['name']
        root_it = blk.findITerm(t['root'])
        root_net = root_it.getNet()
        for n, drv, loads in b_.nets:
            if drv[0] == 'pin':
                net = root_net
            else:
                net = odb.dbNet.create(blk, f'n_{drv[1]}')
                net.setSigType('CLOCK')
                insts[drv[1]].findITerm('Y').connect(net)
            for ld in loads:
                if ld[0] == 'buf':
                    insts[ld[1]].findITerm('A').connect(net)
                else:
                    x = blk.findITerm(ld[1])
                    x.disconnect()
                    x.connect(net)
        rec['parent'].update(b_.parent)
        for lb, L in b_.leaves.items():
            rec['leaves'][lb] = dict(tree=t['name'], pins=L['pins'], key=L['key'])
    log('instantiated', len(rec['cells']), 'cells')
    D.setup_sta(clocks, spec.get('rc_layer', 'M8'))
    # measured trim
    pad_ps = rt.PAD_PS
    leaf_pads = defaultdict(int)
    pad_n = 0
    prev_added, prev_mean = {}, {}
    for it_ in range(a.iters + 1):
        arr = D.measure(sorted(sink_pins), out / f'arr_iter{it_}.tsv')
        flop = {}
        for p, s in sink_pins.items():
            if arr.get(p, (None,))[0] is not None:
                flop[p] = arr[p][0] + s['R'][2]
        stats = {}
        deficit = {}
        by_tree = defaultdict(dict)
        for lb, L in rec['leaves'].items():
            v = [flop[p] for p in L['pins'] if p in flop]
            if v:
                by_tree[L['tree']][lb] = statistics.mean(v)
        # balance groups: trees whose seams are timed synchronously (e.g. S81 stream 833.3 / serial 1111.1 ps, fixed
        # 3:4 schedule on the common 3.333 ns epoch) share ONE flop-arrival target, so a seam pair sees the same phase
        gT = defaultdict(float)
        for tn, lv in by_tree.items():
            k = tree_group.get(tn, tn)
            gT[k] = max(gT[k], max(lv.values()))
        root_deficit = {}
        for tn, lv in by_tree.items():
            Tt = max(lv.values())
            # group alignment goes on the tree's COMMON path (pads before its top buffer), leaf trim only within the
            # tree: a serial tree 1 ns faster than its seam partner must not carry 1 ns of pads at every leaf
            root_deficit[tn] = gT[tree_group.get(tn, tn)] - Tt
            pv = [flop[p] for p in flop if sink_pins[p]['tree'] == tn]
            pa = [arr[p][0] for p in flop if sink_pins[p]['tree'] == tn]
            stats[tn] = dict(flop_spread=round(max(pv) - min(pv), 1), pin_min=round(min(pa), 1), pin_max=round(max(pa), 1),
                             flop_max=round(max(pv), 1), group_offset=round(root_deficit[tn], 1))
            for lb, m in lv.items():
                deficit[lb] = Tt - m
        gstats = {}
        for tn, st in stats.items():
            k = tree_group.get(tn)
            if k:
                g_ = gstats.setdefault(k, dict(flop_min=1e18, flop_max=-1e18))
                pv = [flop[p] for p in flop if sink_pins[p]['tree'] == tn]
                g_['flop_min'] = min(g_['flop_min'], min(pv)); g_['flop_max'] = max(g_['flop_max'], max(pv))
        for g_ in gstats.values():
            g_['flop_spread'] = round(g_['flop_max'] - g_['flop_min'], 1)
        rec['iterations'].append(dict(iter=it_, pad_ps=round(pad_ps, 2), pads=pad_n, trees=stats, groups=gstats))
        worst = max([s['flop_spread'] for s in stats.values()] + [g_['flop_spread'] for g_ in gstats.values()], default=0)
        cols = [v['flop_spread'] for k, v in stats.items() if k.startswith('col_')]
        log('iter', it_, 'pad_ps', round(pad_ps, 1), 'pads', pad_n, 'worst flop spread', worst, 'groups', json.dumps(gstats),
            json.dumps({k: v for k, v in stats.items() if not k.startswith('col_')}),
            'col trees', len(cols), 'col flop spread max', max(cols, default=None))
        if it_ == a.iters or worst <= a.tol:
            break
        # calibrate the pad delay on the previous iteration's padded leaves
        if it_ and prev_added:
            ratios = []
            for lb, k in prev_added.items():
                v = [flop[p] for p in rec['leaves'][lb]['pins'] if p in flop]
                if v and k:
                    ratios.append((statistics.mean(v) - prev_mean[lb]) / k)
            if len(ratios) >= 3:
                pad_ps = max(5.0, statistics.median(ratios))
        prev_added, prev_mean = {}, {}
        def pad_before(bname, k, tree, tag):
            ai = insts[bname].findITerm('A')
            drv_net = ai.getNet()
            ai.disconnect()
            x, y = cell_xy[bname]
            for j in range(k):
                leaf_pads[bname] += 1
                pn = f'{bname}_{tag}{leaf_pads[bname]}'
                pi = mk(pn, rt.PAD, x, y)
                insts[pn] = pi
                rec['cell_tree'][pn] = tree
                pi.findITerm('A').connect(drv_net)
                nn = odb.dbNet.create(blk, f'n_{pn}')
                nn.setSigType('CLOCK')
                pi.findITerm('Y').connect(nn)
                rec['parent'][pn] = rec['parent'][bname]
                rec['parent'][bname] = pn
                drv_net = nn
            ai.connect(drv_net)

        for lb, d in deficit.items():
            k = int(d / pad_ps + 0.5)
            if k <= 0:
                continue
            pad_before(lb, k, rec['leaves'][lb]['tree'], 'tp')
            pad_n += k
            prev_added[lb] = k
            v = [flop[p] for p in rec['leaves'][lb]['pins'] if p in flop]
            prev_mean[lb] = statistics.mean(v) if v else 0.0
        for tn, d in root_deficit.items():
            k = int(d / pad_ps + 0.5)
            if k > 0:
                pad_before(rec['trees'][tn]['model']['top'], k, tn, 'gp')
                pad_n += k
                rec['trees'][tn]['group_pads'] = rec['trees'][tn].get('group_pads', 0) + k
    # final: arrivals at every sink and every clock-cell output, slews, DRV
    allpins = sorted(sink_pins) + [f'{c[0]}/Y' for c in rec['cells']]
    D.measure(allpins, out / f'arrivals_{a.corner}.tsv')
    D.tcl(f'report_check_types -max_slew -max_capacitance -violators > {out}/drv_{a.corner}.rpt')
    rec['sinks'] = sink_pins
    rec['clocks'] = clocks
    rec['leaf_pads'] = dict(leaf_pads)
    (out / 'manifest.json').write_text(json.dumps(rec) + '\n')
    if a.write_odb:
        log('write_db')
        D.design.writeDb(str(out / 'clock.odb'))
    log('DIE_CLOCK_BUILD_DONE', len(rec['cells']), 'cells')


def measure_only(a):
    rec = json.loads(Path(a.measure).read_text())
    out = Path(a.out)
    D = Die(a)
    D.setup_sta([tuple(c) for c in rec['clocks']], rec['spec'].get('rc_layer', 'M8'))
    allpins = sorted(rec['sinks']) + [f'{c[0]}/Y' for c in rec['cells']]
    D.measure(allpins, out / f'arrivals_{a.corner}.tsv')
    D.tcl(f'report_check_types -max_slew -max_capacitance -violators > {out}/drv_{a.corner}.rpt')
    log('DIE_CLOCK_MEASURE_DONE', a.corner)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--odb', required=True)
    ap.add_argument('--libs', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--spec')
    ap.add_argument('--targets')
    ap.add_argument('--iters', type=int, default=3)
    ap.add_argument('--tol', type=float, default=20.0, help='stop trimming when every tree flop spread <= tol ps')
    ap.add_argument('--corner', default='tt')
    ap.add_argument('--only', default='')
    ap.add_argument('--write-odb', action='store_true')
    ap.add_argument('--measure')
    a = ap.parse_args()
    if a.measure:
        measure_only(a)
    else:
        build(a)


if __name__ == '__main__':
    main()
