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
             "rc_layer": "M8", "leaf_um": 60, "leaf_max": 12,
             "neighbours": [[treeA, treeB], ...], "neighbour_budget_ps": 60}
  NEIGHBOUR-RELATIVE (owner 2026-10-16): trees without a shared balance_group are regions; each listed neighbour pair
  (communicating regions) is trimmed so that every flop arrival of one is within neighbour_budget_ps of every flop
  arrival of the other at TT and FF.  There is no die-wide target.  Pads are added only where a pair needs them.
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
import math
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
    return inst, port


class Die:
    def __init__(self, a):
        from openroad import Tech, Design
        import odb
        self.odb = odb
        self.tech = Tech()
        self.two = bool(getattr(a, 'libs_ff', None))
        if self.two:
            # TWO-CORNER mode: TT and FF libs in one STA; a pin's arrival_max = TT late (setup), arrival_min = FF
            # early (hold), so one measurement balances both sign-off corners (TT setup / FF hold, owner 10-07)
            self.design = Design(self.tech)
            self.design.evalTclString('define_corners tt ff')
            for c, lp in (('tt', a.libs), ('ff', a.libs_ff)):
                for lib in Path(lp).read_text().split():
                    self.design.evalTclString(f'read_liberty -corner {c} {lib}')
        else:
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
        candidates = (p, p[:-3] if p.endswith('[0]') else p + '[0]')
        value = None
        for field in ('physical_insertion_per_clock_pin_ps', 'insertion_per_clock_pin_ps'):
            pp = r.get(field, {})
            found = next((key for key in candidates if key in pp), None)
            if found is not None:
                value = pp[found]
                break
        if value is None:
            value = r.get('insertion_in_arcs_ps')
        if value is None:
            raise ValueError(f'missing native insertion R for {m}/{p} in {path}')
        if not isinstance(value, list) or len(value) != 3 or any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in value):
            raise ValueError(f'invalid insertion R for {m}/{p}: {value!r}')
        return value
    return v


def build(a):
    spec = json.loads(Path(a.spec).read_text())
    rt.LEAF_UM = spec.get('leaf_um', rt.LEAF_UM)
    rt.LEAF_MAX = spec.get('leaf_max', rt.LEAF_MAX)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    D = Die(a)
    blk, u, odb = D.block, D.u, D.odb
    obstacles, taken, fixed_rows = [], set(), []
    insts_by_master = defaultdict(list)
    for inst in blk.getInsts():
        m = inst.getMaster()
        insts_by_master[m.getName()].append(inst)
        b = inst.getBBox()
        if m.isBlock() or inst.isPlaced():
            fixed_rows.append((inst.getName(),(b.xMin()/u,b.yMin()/u,b.xMax()/u,b.yMax()/u)))
        if m.isBlock():
            obstacles.append((b.xMin() / u, b.yMin() / u, b.xMax() / u, b.yMax() / u))
        elif inst.isPlaced():
            for ix in range(int(b.xMin() / u / XPITCH), int(b.xMax() / u / XPITCH) + 1):
                for iy in range(int(b.yMin() / u / YPITCH), int(b.yMax() / u / YPITCH) + 1):
                    taken.add((ix, iy))
    log('obstacles', len(obstacles), 'std cell sites taken', len(taken))
    region_exact=bool(spec.get('exact_region_bays',False))
    if region_exact:
        from qwen_exact_corridor import ExactBayGrid,ExactRegionalBuilder
        g=ExactBayGrid(D.W,D.H,fixed_rows)
    else:
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
            builder_type=ExactRegionalBuilder if region_exact else rt.Builder
            b_ = builder_type(g, 'dc_' + t['name'], r_of=lambda key: (target(*key.rsplit('/', 1)) or [0, 0, 0])[2])
            txy = rxy
            if t.get('local_root'):
                # STAND-IN regional clock entry (landed-regions standard): the region tree starts at a local root
                # (sink median, or the given [x, y]) instead of the shared generator pin; the spine from the generator
                # to it is NOT built here (the GEN owes a regional clock entry / forwarded spine).  The clock is defined
                # at the local root buffer input, so only the region tree is measured.
                lr = t['local_root']
                if isinstance(lr, (list, tuple)):
                    txy = (float(lr[0]), float(lr[1]))
                else:
                    xs = sorted(z[2] for z in sinks); ys = sorted(z[3] for z in sinks)
                    txy = (xs[len(xs) // 2], ys[len(ys) // 2])
                if len(ts) != 1:
                    raise ValueError(f'local_root needs one tree per root ({root})')
                rec.setdefault('local_root_xy', {})[root] = [round(txy[0], 3), round(txy[1], 3)]
            model = b_.build(root, txy, leaves)
            for s in sinks:
                sink_pins[s[0]] = dict(tree=t['name'], master=s[1], x=round(s[2], 3), y=round(s[3], 3),
                                      R=target(s[1], pin_key(s[0])[1]))
            rec['trees'][t['name']] = dict(root=root, root_xy=[round(rxy[0], 3), round(rxy[1], 3)], sinks=len(sinks), model=model)
            builders[t['name']] = b_
            log('tree', t['name'], 'sinks', len(sinks), json.dumps(model))
        unclaimed = [x for x in loads if f'{x.getInst().getName()}/{x.getMTerm().getName()}' not in claimed]
        if unclaimed and spec.get('unclaimed') == 'disconnect_diagnostic':
            # DIAGNOSTIC partial clock (e.g. macro trees before relay stations are legal): the unclaimed loads are
            # disconnected from the root net and listed in the manifest; the result is never a complete die clock.
            for x in unclaimed:
                rec.setdefault('unclaimed_disconnected', []).append(
                    f'{x.getInst().getName()}/{x.getMTerm().getName()}')
                x.disconnect()
            log('DIAGNOSTIC', root, len(unclaimed), 'unclaimed loads disconnected (spec unclaimed=disconnect_diagnostic)')
        elif unclaimed:
            raise ValueError(f'{root}: {len(unclaimed)} loads not claimed by any tree spec')
    # instantiate
    masters, cell_xy = {}, {}

    def mk(name, cell, x, y, exact=False):
        if cell not in masters:
            masters[cell] = D.design.getDb().findMaster(cell)
            if not masters[cell]:
                raise ValueError(f'no master {cell}')
        if exact or region_exact:
            if masters[cell].getWidth()/u>XPITCH or masters[cell].getHeight()/u>YPITCH:
                raise ValueError(f'exact bay too small for {cell}')
        if exact:
            sx,sy=x,y
            sites.occ.add((round(sx/XPITCH),round(sy/YPITCH)))
        elif region_exact:
            sx,sy=g.reserve(g.nearest_free(x,y))
        else:
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
            insts[n] = mk(n, cell, x, y,exact=region_exact)
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
    # ROOT BUFFER: a root (PLL / generator output / region root pin) drives ONE BUFx24 next to it, which drives
    # the trees' first cells (HBM t4: the PLL pin driving five trunk inputs measured 351-388 ps slew > 320 limit).
    for root, ts in by_root.items():
        root_it = blk.findITerm(root)
        rnet = root_it.getNet()
        loads = [x for x in rnet.getITerms() if x.getIoType() == 'INPUT']
        if not loads:     # every root (also a single-tree root such as an S81 cfifo co: t3b T1/A slew 1.1 ns
            continue      # from co driving 350-460 um to the first trunk repeater) drives one buffer beside it
        rb = root_it.getBBox()
        rn = f"dc_root_{ts[0]['name']}"
        lxy = rec.get('local_root_xy', {}).get(root)
        ri = mk(rn, rt.BUF, *(lxy if lxy else ((rb.xMin() + rb.xMax()) / 2 / u, (rb.yMin() + rb.yMax()) / 2 / u)))
        insts[rn] = ri
        rec['cell_tree'][rn] = ''
        nn = odb.dbNet.create(blk, f'n_{rn}')
        nn.setSigType('CLOCK')
        for x in loads:
            x.disconnect()
            x.connect(nn)
            c = x.getInst().getName()
            if rec['parent'].get(c) == root:
                rec['parent'][c] = rn
        ri.findITerm('Y').connect(nn)
        if lxy:
            # local_root stand-in: the generator->region spine is not built; the root buffer input sits on its own
            # (undriven) net so STA sees an ideal clock source there, not a mm-long unbuffered wire from the generator
            sn = odb.dbNet.create(blk, f'n_{rn}_spine')
            sn.setSigType('CLOCK')
            ri.findITerm('A').connect(sn)
        else:
            ri.findITerm('A').connect(rnet)
        rec['parent'][rn] = root
        rec.setdefault('root_buffer', {})[root] = rn
        log('root buffer', rn, 'drives', len(loads), 'tree inputs of', root)
    # ITEM 5 (GEN16): a root buffer driving more than one trunk input gets one BUFx24 per trunk (HBM t4 / Qwen v0:
    # 5 trunk inputs at 382-413 ps slew > 320 when one driver fed several trunks)
    for root, rn in list(rec.get('root_buffer', {}).items()):
        if spec.get('split_root_fanout', True) is False:
            break
        nn = insts[rn].findITerm('Y').getNet()
        loads = [x for x in nn.getITerms() if x.getIoType() == 'INPUT']
        if len(loads) < 2:
            continue
        x0, y0 = cell_xy[rn]
        for j, x in enumerate(loads):
            tn = f'{rn}_t{j}'
            ti = mk(tn, rt.BUF, x0, y0)
            insts[tn] = ti
            rec['cell_tree'][tn] = rec['cell_tree'].get(x.getInst().getName(), '')
            tnet = odb.dbNet.create(blk, f'n_{tn}')
            tnet.setSigType('CLOCK')
            x.disconnect()
            x.connect(tnet)
            ti.findITerm('Y').connect(tnet)
            ti.findITerm('A').connect(nn)
            c = x.getInst().getName()
            if rec['parent'].get(c) == rn:
                rec['parent'][c] = tn
            rec['parent'][tn] = rn
        log('root buffer', rn, 'split: one buffer per trunk input,', len(loads), 'trunks')
    # ITEM 1 (GEN16): FORWARDED CLOCK SPINE.  spec "spine": {"source": "inst/pin", "period": ps, "trees": [..] (opt)}:
    # a real buffered DME spine (obstacle grid, repeaters, legal sites) from ONE generator pin to every member region's
    # entry (local-root buffer input); the clock is defined at the spine source, so every measured arrival = spine +
    # region tree.  The spine merge compensates each region tree's model insertion (key = tree name), and the measured
    # trim may add elements on spine nodes only for spec "neighbours" pairs: there is no die-wide balance target.
    spine_roots = set()
    sp_ = spec.get('spine')
    if region_exact or (sp_ and sp_.get('exact_footprint_bays')):
        # Preserve the expensive actual occupied regional geometry even if a
        # later strict spine guard rejects. These are diagnostics, not clocks.
        D.design.writeDb(str(out/'regional_geometry.odb'))
        (out/'regional_geometry_manifest.json').write_text(json.dumps(rec)+'\n')
    if sp_:
        src = sp_['source']
        members = rt.spine_members(trees, set(rec['trees']), rec.get('root_buffer', {}), sp_)
        if not members:
            raise ValueError(f'spine {src}: no member region trees')
        src_it = blk.findITerm(src)
        if not src_it:
            raise ValueError(f'spine source missing: {src}')
        src_net = src_it.getNet()
        if not src_net:
            src_net = odb.dbNet.create(blk, 'n_dc_spine_gen')
            src_net.setSigType('CLOCK')
            src_it.connect(src_net)
        mrb = {rb for _, rb in members}
        for x in [x for x in src_net.getITerms() if x.getIoType() == 'INPUT']:
            if x.getInst().getName() not in mrb:
                raise ValueError(f'spine source {src} also drives non-member {x.getInst().getName()}/{x.getMTerm().getName()}')
            x.disconnect()
        topology = sp_.get('topology', 'dme')
        if topology not in ('dme', 'forwarded'):
            raise ValueError(f'unknown spine topology {topology}')
        rmodel = {t['name']: rec['trees'][t['name']]['model'].get('model_insertion_ps', 0.0) for t, _ in members}
        # Forwarded delivery does not balance the entire die against regional
        # insertion estimates. Neighbour matching remains a measured obligation.
        exact=bool(sp_.get('exact_footprint_bays',False))
        if exact and topology!='forwarded':raise ValueError('exact bays require strict forwarded topology')
        if exact:
            from qwen_exact_corridor import ExactBayGrid,ExactForwardedBuilder,check_reach
            rows=[]
            for obj in blk.getInsts():
                if obj.getMaster().isBlock() or obj.isPlaced():
                    bx=obj.getBBox();rows.append((obj.getName(),(bx.xMin()/u,bx.yMin()/u,bx.xMax()/u,bx.yMax()/u)))
            eg=ExactBayGrid(D.W,D.H,rows)
            sb=ExactForwardedBuilder(eg,'dc_spine')
        else:
            sb = (rt.ForwardedBuilder(g, 'dc_spine') if topology == 'forwarded'
                  else rt.Builder(g, 'dc_spine', r_of=lambda key: rmodel.get(key, 0.0)))
        sxy = ((src_it.getBBox().xMin() + src_it.getBBox().xMax()) / 2 / u,
               (src_it.getBBox().yMin() + src_it.getBBox().yMax()) / 2 / u)
        source_xy=sxy
        sbn = 'dc_spine_src'
        if exact:
            source_xy=eg.reserve(eg.nearest_free(*sxy))
            insts[sbn]=mk(sbn,rt.BUF,*source_xy,exact=True)
            source_box=insts[sbn].findITerm('A').getBBox()
            source_input=((source_box.xMin()+source_box.xMax())/2/u,(source_box.yMin()+source_box.yMax())/2/u)
            source_reach=check_reach(eg.route_reserved(eg.cell(*sxy),eg.cell(*source_input)),sxy,source_input,eg)
        smodel = sb.build(src, source_xy, rt.spine_leaves(members, cell_xy))
        for n, cell, x, y in sb.bufs:
            insts[n] = mk(n, cell, x, y,exact=exact)
            rec['cell_tree'][n] = 'spine'
        # the generator pin drives ONE spine source buffer beside it (a generator model without output drive left the
        # first trunk input at 382-413 ps slew); the spine starts at its output
        if not exact:insts[sbn] = mk(sbn, rt.BUF, *sxy)
        rec['cell_tree'][sbn] = 'spine'
        insts[sbn].findITerm('A').connect(src_net)
        spine_net = odb.dbNet.create(blk, 'n_dc_spine_src')
        spine_net.setSigType('CLOCK')
        insts[sbn].findITerm('Y').connect(spine_net)
        rec['parent'][sbn] = src
        orphan = []
        for t, rb in members:
            ai = insts[rb].findITerm('A')
            old = ai.getNet()
            ai.disconnect()
            if old and old.getName() != src_net.getName() and not old.getITerms():
                odb.dbNet.destroy(old)
            spine_roots.add(t['root'])
            gn = blk.findITerm(t['root'])
            if t['root'] != src and gn and gn.getNet() and not [x for x in gn.getNet().getITerms() if x.getIoType() == 'INPUT']:
                orphan.append(t['root'])
        for n, drv, loads in sb.nets:
            if drv[0] == 'pin':
                net = spine_net
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
        for k_, v_ in sb.parent.items():
            rec['parent'][k_[:-2] if k_.endswith('/A') and k_[:-2] in mrb else k_] = sbn if v_ == src else v_
        lv = {}
        for c_ in [b_[0] for b_ in sb.bufs]:
            d_, x_ = 1, c_
            while sb.parent.get(x_) not in (None, src):
                x_ = sb.parent[x_]; d_ += 1
            lv[c_] = d_ + 1      # + the spine source buffer
        rec['spine'] = dict(source=src, topology=topology, period=float(sp_.get('period', 833.333333)), members=[t['name'] for t, _ in members],
                            cells=len(sb.bufs) + 1, levels=max(lv.values(), default=0), model=smodel,
                            generator_pins_without_loads=orphan)
        if exact:
            # Measure actual placed pin coordinates; legal origins alone do not
            # account for library pin offsets and must not waive reach.
            for edge in sb.edges:
                def endpoint(ref,output):
                    kind,name=ref
                    pin=(sbn+'/Y' if name==src else name) if kind=='pin' else name+('/Y' if output else '/A')
                    it=blk.findITerm(pin)
                    if not it:raise ValueError('exact corridor pin missing: '+pin)
                    bb=it.getBBox();return ((bb.xMin()+bb.xMax())/2/u,(bb.yMin()+bb.yMax())/2/u)
                edge['placed_pin_routed_bound_um']=check_reach(edge['route_cells'],endpoint(edge['driver'],True),endpoint(edge['load'],False),eg)
            rec['spine']['exact_bay_edges']=sb.edges
            rec['spine']['source_input_routed_bound_um']=source_reach
            if region_exact:g=eg
        log('SPINE', src, 'members', len(members), 'cells', len(sb.bufs) + 1, 'levels', rec['spine']['levels'],
            'model', json.dumps(smodel), 'generator pins left without loads', len(orphan), ' '.join(orphan[:20]))
    log('instantiated', len(rec['cells']), 'cells')
    if region_exact:
        # Actual output pin coordinates, not model/grid centres. Preserve the
        # failing ODB before rejecting any inherited native wire over405um.
        long=[];max_native_direct=0.0
        for name,_,_,_ in rec['cells']:
            output=insts[name].findITerm('Y')
            if not output or not output.getNet():continue
            bb=output.getBBox();p=((bb.xMin()+bb.xMax())/2/u,(bb.yMin()+bb.yMax())/2/u)
            for sink in output.getNet().getITerms():
                if sink.getIoType()!='INPUT':continue
                bb=sink.getBBox();q=((bb.xMin()+bb.xMax())/2/u,(bb.yMin()+bb.yMax())/2/u)
                distance=abs(p[0]-q[0])+abs(p[1]-q[1]);max_native_direct=max(max_native_direct,distance)
                if distance>405+1e-7:long.append([name+'/Y',sink.getInst().getName()+'/'+sink.getMTerm().getName(),distance])
        rec['native_geometry']=dict(exact_region_bays=True,max_actual_direct_um=max_native_direct,
                                    direct_reach_violations=long,routed_native_qualified=False)
        if long:
            D.design.writeDb(str(out/'native_reach_fail.odb'))
            (out/'native_reach_fail.json').write_text(json.dumps(rec)+'\n')
            raise ValueError(f'actual native clock wires >405um: {len(long)}; worst {max(x[2] for x in long):.3f}')
        if not getattr(a,'geometry_only',False):
            raise ValueError('exact regional candidate requires actual physical-row/PDN audit before timing; use geometry-only')
    if getattr(a,'geometry_only',False):
        rec['geometry_only']=True;rec['timing_qualified']=False
        (out/'geometry_manifest.json').write_text(json.dumps(rec)+'\n')
        if a.write_odb:D.design.writeDb(str(out/'geometry.odb'))
        log('DIE_CLOCK_GEOMETRY_DONE',len(rec['cells']),'cells; no STA/admission')
        return
    clocks_orig = list(clocks)
    if spec.get('clock_at_root_buffer'):
        # the PLL model has no output drive / timing arc (Qwen KV qkd_pllm: STA slew 114 ns at the root buffer input);
        # the clock is defined at the root buffer input beside the PLL pin, so the delivered tree is what is measured
        clocks = [(n, rec.get('root_buffer', {}).get(p) + '/A' if rec.get('root_buffer', {}).get(p) else p, per)
                  for n, p, per in clocks]
        rec['clock_source'] = 'root buffer input (spec clock_at_root_buffer)'
    if spine_roots:
        per_ = rec['spine']['period']
        clocks = [c_ for c_, o_ in zip(clocks, clocks_orig) if o_[1] not in spine_roots] + [('spine', rec['spine']['source'], per_)]
        rec['clock_source'] = (rec.get('clock_source', '') + '; spine trees: clock at the spine source').lstrip('; ')
    D.setup_sta(clocks, spec.get('rc_layer', 'M8'))
    # measured trim.  Two delay elements: PAD (BUFx12f stacked on one site: gate delay, FF/TT ~0.77) and WPAD (BUFx24
    # local/far buffer PAIRS WPAD_UM apart: buffered wire like the tree's own repeater stages, FF/TT ~0.84).  One corner: PAD only.
    # Two corners: each leaf's (TT, FF) deficit is solved as nP PADs + nW WPADs, so the trim matches the tree at BOTH
    # sign-off corners (HBM t4: PAD-only group offsets of up to 8.5 ns balanced TT to 75 ps but left FF at 685 ps).
    two = D.two
    # W seed from native_wire_units.py TT/FF placed-cell measurement; contextual calibration follows.
    el = dict(P=[rt.PAD_PS, rt.PAD_PS * 0.77], W=[250.0, 212.0])     # seeds [tt, ff] ps per element; measured below
    cellof = dict(P=rt.PAD, W=rt.BUF)
    leaf_pads = defaultdict(int)
    pad_n = defaultdict(int)
    chains = []
    WPAD_UM = 180.0
    RAISE_CAP_PS = 300.0
    DAMP = 0.9     # approach the target from below: an overshooting leaf would raise the whole group's target
    gtarget = {}
    for it_ in range(a.iters + 1):
        arr = D.measure(sorted(sink_pins), out / f'arr_iter{it_}.tsv')
        flop, flopf = {}, {}
        for p, s in sink_pins.items():
            if arr.get(p, (None,))[0] is not None:
                flop[p] = arr[p][0] + s['R'][2]
                if two and arr[p][1] is not None:
                    flopf[p] = arr[p][1] + s['R'][1]
        by_tree, by_treef = defaultdict(dict), defaultdict(dict)
        for lb, L in rec['leaves'].items():
            v = [flop[p] for p in L['pins'] if p in flop]
            if v:
                by_tree[L['tree']][lb] = statistics.mean(v)
            v = [flopf[p] for p in L['pins'] if p in flopf]
            if v:
                by_treef[L['tree']][lb] = statistics.mean(v)
        # balance groups: trees whose seams are timed synchronously (S81 stream 833.3 / serial 1111.1 ps, fixed 3:4
        # schedule on the common 3.333 ns epoch; HBM serial:stream) share ONE flop-arrival target per corner
        stats, gstats = {}, {}
        for tn in by_tree:
            pv = [flop[p] for p in flop if sink_pins[p]['tree'] == tn]
            pa = [arr[p][0] for p in flop if sink_pins[p]['tree'] == tn]
            stats[tn] = dict(flop_spread=round(max(pv) - min(pv), 1), pin_min=round(min(pa), 1), pin_max=round(max(pa), 1),
                             flop_max=round(max(pv), 1))
            if two:
                fv = [flopf[p] for p in flopf if sink_pins[p]['tree'] == tn]
                stats[tn].update(ff_spread=round(max(fv) - min(fv), 1), ff_max=round(max(fv), 1))
            k = tree_group.get(tn)
            if k:
                g_ = gstats.setdefault(k, dict(flop_min=1e18, flop_max=-1e18, ff_min=1e18, ff_max=-1e18))
                g_['flop_min'] = min(g_['flop_min'], min(pv)); g_['flop_max'] = max(g_['flop_max'], max(pv))
                if two:
                    g_['ff_min'] = min(g_['ff_min'], min(fv)); g_['ff_max'] = max(g_['ff_max'], max(fv))
        for g_ in gstats.values():
            g_['flop_spread'] = round(g_['flop_max'] - g_['flop_min'], 1)
            g_['ff_spread'] = round(g_['ff_max'] - g_['ff_min'], 1) if two else None
        # neighbour pairs: worst flop-arrival difference between any sink of one region and any of the other
        nstats = {}
        for x, y in spec.get('neighbours', []):
            ex = [s_ for t_, s_ in stats.items() if tree_group.get(t_, t_) == tree_group.get(x, x)]
            ey = [s_ for t_, s_ in stats.items() if tree_group.get(t_, t_) == tree_group.get(y, y)]
            if not ex or not ey:
                continue
            mx = lambda e, k: max(v[k] for v in e)
            mn = lambda e, k, sk: min(v[k] - v[sk] for v in e)
            d_ = dict(tt=round(max(mx(ex, 'flop_max') - mn(ey, 'flop_max', 'flop_spread'),
                                   mx(ey, 'flop_max') - mn(ex, 'flop_max', 'flop_spread')), 1))
            if two:
                d_['ff'] = round(max(mx(ex, 'ff_max') - mn(ey, 'ff_max', 'ff_spread'),
                                     mx(ey, 'ff_max') - mn(ex, 'ff_max', 'ff_spread')), 1)
            nstats[f'{x}|{y}'] = d_
        rec['iterations'].append(dict(iter=it_, elements=json.loads(json.dumps(el)), pads=dict(pad_n), trees=stats, groups=gstats,
                                      neighbours=nstats))
        sp = [s_['flop_spread'] for s_ in stats.values()] + [g_['flop_spread'] for g_ in gstats.values()]
        sp += [v['tt'] - spec.get('neighbour_budget_ps', 60.0) + a.tol for v in nstats.values()]
        if two:
            sp += [s_['ff_spread'] for s_ in stats.values()] + [g_['ff_spread'] for g_ in gstats.values()]
            sp += [v['ff'] - spec.get('neighbour_budget_ps', 60.0) + a.tol for v in nstats.values()]
        if nstats:
            log('iter', it_, 'neighbours', json.dumps(nstats))
        worst = max(sp, default=0)
        cols = [v['flop_spread'] for k, v in stats.items() if k.startswith('col_')]
        log('iter', it_, 'elements', json.dumps(el), 'pads', dict(pad_n), 'worst spread', worst, 'groups', json.dumps(gstats),
            json.dumps({k: v for k, v in stats.items() if not k.startswith('col_')}),
            'col trees', len(cols), 'col flop spread max', max(cols, default=None))
        if it_ == a.iters or worst <= a.tol:
            break
        # element delays measured IN CONTEXT on the nodes trimmed last iteration: (node output now - before) minus
        # (its upstream driver output now - before), divided by the elements added.  This includes the wire the
        # elements add in front of the node, and a common-path shift of the whole tree cancels.
        key = lambda d_: f'{d_}/Y' if d_ in insts else d_
        if chains:
            pm = sorted({q for c in chains for q in (f'{c[0]}/Y', key(c[1]))})
            ca = D.measure(pm, out / f'pads_iter{it_}.tsv')
            for ty in el:
                cs = [c for c in chains if c[3] == ty]
                kmin = 3 if sum(1 for c in cs if c[2] >= 3) >= 20 else 1
                for ci in ((0, 1) if two else (0,)):
                    r_ = []
                    for nd, dv, k, _, bn, bd in cs:
                        an, ad = ca.get(f'{nd}/Y', (None, None))[ci], ca.get(key(dv), (None, None))[ci]
                        if k >= kmin and None not in (an, ad, bn[ci], bd[ci]):
                            r_.append(((an - bn[ci]) - (ad - bd[ci])) / k)
                    if len(r_) >= 3:
                        el[ty][ci] = max(3.0, statistics.median(r_))
                if not two:
                    el[ty][1] = el[ty][0] * 0.77
            log('elements measured in context on', len(chains), 'nodes:', json.dumps(el))
        chains = []
        calib = {}

        def pad_before(bname, k, tree, ty):
            ai = insts[bname].findITerm('A')
            drv_net = ai.getNet()
            ai.disconnect()
            x, y = cell_xy[bname]
            off = (0.0, 0.0)
            if ty == 'W':     # stages alternate between the node and a free spot WPAD_UM away (wire like a tree stage)
                for dx, dy in ((WPAD_UM, 0), (-WPAD_UM, 0), (0, WPAD_UM), (0, -WPAD_UM)):
                    ix, iy = round((x + dx) / XPITCH), round((y + dy) / YPITCH)
                    if 0 <= x + dx < D.W and 0 <= y + dy < D.H and sites.legal(ix, iy):
                        off = (dx, dy)
                        break
                else:
                    off = (WPAD_UM, 0.0)
            orig = rec['parent'][bname]
            first = None
            for j in range(k * (2 if ty == 'W' else 1)):
                leaf_pads[bname] += 1
                pn = f'{bname}_{ty.lower()}p{leaf_pads[bname]}'
                # Each W unit is a local/far PAIR, including k=1: every unit adds one complete round trip.
                # An odd single stage at the node has no added wire and is a different delay element (t8).
                # The first stage stays at the node's spot, so the upstream driver's net
                # (shared with the node's siblings) keeps its load and wire (t7: a far first stage slowed the siblings,
                # the group maximum rose ~250 ps per iteration and the trim never converged)
                far = ty == 'W' and j % 2 == 1
                pi = mk(pn, cellof[ty], x + (off[0] if far else 0), y + (off[1] if far else 0))
                insts[pn] = pi
                rec['cell_tree'][pn] = tree
                pi.findITerm('A').connect(drv_net)
                nn = odb.dbNet.create(blk, f'n_{pn}')
                nn.setSigType('CLOCK')
                pi.findITerm('Y').connect(nn)
                rec['parent'][pn] = rec['parent'][bname]
                rec['parent'][bname] = pn
                drv_net = nn
                first = first or pn
            ai.connect(drv_net)
            if bname in calib:
                chains.append((bname, orig, k, ty) + calib[bname])

        # per-leaf element counts.  One corner: nP = round(D_tt / P).  Two corners: the group targets (Ttt, Tff) are
        # the smallest for which EVERY leaf's deficit lies in the cone of the two elements (FF/TT ratio between PAD's
        # and WPAD's), then each leaf solves nP * P + nW * W = (D_tt, D_ff).
        need = {}
        groups_L, tg = {}, {}
        (p1, p2), (w1, w2) = el['P'], el['W']
        rlo, rhi = sorted((p2 / p1, w2 / w1))
        for gk in set(tree_group.get(t, t) for t in by_tree):
            tl = [t for t in by_tree if tree_group.get(t, t) == gk]
            L = [(lb, by_tree[t][lb], by_treef[t].get(lb, by_tree[t][lb])) for t in tl for lb in by_tree[t]]
            groups_L[gk] = L
            Ttt = max(v[1] for v in L)
            if not two:
                tg[gk] = (Ttt, None, Ttt, None)
                continue
            # closed form: Tf(Tt) = rlo*Tt + A is the least FF target with every leaf's FF deficit >= rlo x its TT
            # deficit; Tt is raised (capped at RAISE_CAP_PS) until no leaf's FF deficit exceeds rhi x its TT deficit.
            # Leaves still outside the cone are solved by clamped least squares (their residual is reported).
            A = max(ff_ - rlo * ft for _, ft, ff_ in L)
            base_ff_max = max(ff_ for _, _, ff_ in L)
            need_t = max((A - ff_ + rhi * ft) / (rhi - rlo) for _, ft, ff_ in L) if rhi - rlo > 1e-3 else Ttt
            Tt = Ttt + min(max(0.0, need_t - Ttt), RAISE_CAP_PS)
            Tf = rlo * Tt + A
            # the group targets are set ONCE (first trim) and then held: later iterations only correct residuals
            # against them (re-deriving them each iteration walked the target up by the raise every time); they move
            # only if a leaf overshoots
            if gk in gtarget and gtarget[gk][0] > Ttt + RAISE_CAP_PS:
                # stale hold: the group's arrivals FELL (Qwen KV kv_rt1: iter-0 c tree 22.7 ns with an over-loaded
                # trunk net, 10.2 ns after the first trim re-buffered it); a held 22.9 ns target then asked for 12 ns of
                # pads everywhere and the neighbour gaps never closed.  Re-derive from the current arrivals.
                del gtarget[gk]
            if gk in gtarget:
                # a leaf that overshoots the held target by less than tol/2 does NOT raise it (t9: raising the target
                # to every new maximum walked the group up ~70 ps/iteration and left the slowest-trimmed leaves ~100 ps
                # behind for ten iterations)
                Tt = max(gtarget[gk][0], Ttt - 0.5 * a.tol)
                Tf = max(gtarget[gk][1], base_ff_max - 0.5 * a.tol)
            tg[gk] = (Tt, Tf, Ttt, base_ff_max)
        # NEIGHBOUR-RELATIVE targets (owner 2026-10-16): no die-wide target; each communicating neighbour pair of
        # regions (spec "neighbours", tree or group names) must be within neighbour_budget_ps at TT and FF.  Targets
        # only rise (delay can only be added): difference-constraint relaxation to the least fixpoint; a raise keeps
        # its FF/TT ratio inside the element cone [rlo, rhi].
        nb_pairs = [(tree_group.get(x, x), tree_group.get(y, y)) for x, y in spec.get('neighbours', [])]
        nbB = float(spec.get('neighbour_budget_ps', 60.0))
        nb_pairs = [(x, y) for x, y in nb_pairs if x in tg and y in tg and x != y]
        for _ in range(10 * max(1, len(tg))):
            moved = False
            for x, y in nb_pairs + [(y, x) for x, y in nb_pairs]:
                Tt, Tf, b1, b2 = tg[x]
                dt = max(0.0, tg[y][0] - nbB - Tt)
                df = max(0.0, tg[y][1] - nbB - Tf) if two else 0.0
                if dt <= 1e-6 and df <= 1e-6:
                    continue
                # TT and FF are relaxed independently (coupling them through the element cone ran away on Qwen KV
                # kv_nb2: every FF raise forced dt = df / rhi, which re-raised the neighbours, +6..17 ns per iteration);
                # the per-leaf P/W solve absorbs the residual cone mismatch
                tg[x] = (Tt + dt, (Tf + df) if two else None, b1, b2)
                moved = True
            if not moved:
                break
        if nb_pairs:
            rec.setdefault('neighbour_targets', []).append({k: [round(v[0], 1), round(v[1], 1) if v[1] is not None else None]
                                                            for k, v in tg.items()})
        for gk, L in groups_L.items():
            Tt, Tf, Ttt, _ = tg[gk]
            if not two:
                for lb, ft, _ in L:
                    need[lb] = (int((Tt - ft) / el['P'][0] + 0.5), 0)
                continue
            gtarget[gk] = (Tt, Tf)
            det = p1 * w2 - w1 * p2
            for lb, ft, ff_ in L:
                dt, df = Tt - ft, Tf - ff_
                nP = (dt * w2 - w1 * df) / det
                nW = (p1 * df - p2 * dt) / det
                if nP < 0:
                    nP, nW = 0.0, (dt * w1 + df * w2) / (w1 * w1 + w2 * w2)
                elif nW < 0:
                    nW, nP = 0.0, (dt * p1 + df * p2) / (p1 * p1 + p2 * p2)
                # W (a ~100 ps wire round trip) is coarse: take whole W units only below the damped need (floor), then
                # trim the remainder with P (~15 ps) so W rounding never overshoots the target
                kW = max(0, int(DAMP * nW))
                rt_, rf_ = dt - kW * w1, df - kW * w2
                kP = max(0, int(DAMP * max(0.0, (rt_ * p1 + rf_ * p2) / (p1 * p1 + p2 * p2)) + 0.5))
                need[lb] = (kP, kW)
            log('group', gk, 'targets tt', round(Tt, 1), 'ff', round(Tf, 1), '(raised tt by', round(Tt - Ttt, 1), ')')
        # HIERARCHICAL TRIM: the part of a type that every leaf below a node needs goes ONCE at that node's input
        # (min over its leaves minus what its parent already carries): group offsets land on the common path at the
        # root, subtree offsets at their branch point, only the residual at the leaves
        plan = []
        src_bufs = {b_ for r_, b_ in rec.get('root_buffer', {}).items() if r_ not in spine_roots} if spec.get('clock_at_root_buffer') else set()
        if spine_roots:
            src_bufs.add('dc_spine_src')     # the clock is defined at the generator pin: nothing above the spine source buffer
        for ty in ('W', 'P'):   # W first: wire stages above, gate pads nearer the node
            units, par_of = {}, {}
            for lb, nn_ in need.items():
                u_ = nn_[1] if ty == 'W' else nn_[0]
                x, prev = lb, None
                while True:
                    if x not in units or u_ < units[x]:
                        units[x] = u_
                    if prev is not None:
                        par_of[prev] = x
                    px = rec['parent'].get(x)
                    # with clock_at_root_buffer the clock is DEFINED at the root buffer input: an element placed before
                    # the root buffer is upstream of the clock source and adds nothing (Qwen KV kv_rt2: WN/EN 4 ns
                    # offsets requested at dc_root_* every iteration, arrivals moved ~120 ps); stop below it
                    if px not in insts or px in src_bufs:
                        par_of.setdefault(x, None)
                        break
                    prev, x = x, px
            for x, u_ in units.items():
                k = u_ - (units[par_of[x]] if par_of.get(x) else 0)
                if k > 0:
                    plan.append((x, ty, k))
        # calibration sample: nodes that get ONE element type this iteration, up to 300 per type
        one = defaultdict(set)
        for x, ty, k in plan:
            one[x].add(ty)
        samp, cnt = [], defaultdict(int)
        for x, ty, k in sorted(plan, key=lambda t: -t[2]):
            if len(one[x]) == 1 and cnt[ty] < 300:
                samp.append(x); cnt[ty] += 1
        if samp:
            pm = sorted({q for x in samp for q in (f'{x}/Y', key(rec['parent'][x]))})
            cb = D.measure(pm, out / f'pads_before_iter{it_}.tsv')
            for x in samp:
                calib[x] = (cb.get(f'{x}/Y', (None, None))[:2], cb.get(key(rec['parent'][x]), (None, None))[:2])
        added = defaultdict(int)
        nodes = 0
        for x, ty, k in plan:
            pad_before(x, k, rec['cell_tree'].get(x, ''), ty)
            added[ty] += k
            nodes += 1
        for ty, k in added.items():
            pad_n[ty] += k
        log('iter', it_, 'hierarchical trim inserted', dict(added), 'elements at', nodes, 'nodes')
    rec['trim_element_cells'] = dict(P=1, W=2)
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
    ap.add_argument('--libs-ff', help='two-corner trim: also balance FF early arrivals (TT late + FF early in one STA)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--spec')
    ap.add_argument('--targets')
    ap.add_argument('--iters', type=int, default=3)
    ap.add_argument('--tol', type=float, default=20.0, help='stop trimming when every tree flop spread <= tol ps')
    ap.add_argument('--corner', default='tt')
    ap.add_argument('--only', default='')
    ap.add_argument('--write-odb', action='store_true')
    ap.add_argument('--geometry-only', action='store_true',help='replay complete occupied topology; no timing/admission')
    ap.add_argument('--measure')
    a = ap.parse_args()
    if a.measure:
        measure_only(a)
    else:
        build(a)


if __name__ == '__main__':
    main()
