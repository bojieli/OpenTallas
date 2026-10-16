#!/usr/bin/env python3
"""Instantiate a physical S81 die-clock candidate in a copy of an actual ODB.

Run with OpenROAD -python. Input clock-check dump supplies the observed entry
pins and communication pairs, never synthetic tile centres. Macro clock outputs
remain the sources; the original ODB and data connectivity are preserved.
This is a physical topology pilot, not a clock or die qualification. Forwarded
clocks and per-child insertion compensation must be separately supplied/proven.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hbm_die_v15'))
import die_clock_tree as dct
import clock_sites


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load_dump(path):
    roots, entries, pairs = {}, defaultdict(list), set()
    for line in Path(path).read_text().splitlines():
        s = line.split('\t')
        if s[0] == 'R':
            roots[s[1]] = (float(s[2]), float(s[3]))
        elif s[0] == 'T':
            entries[s[5]].append((s[1], s[2], float(s[3]), float(s[4])))
        elif s[0] == 'P':
            pairs.add(tuple(sorted(s[1:3])))
    return roots, entries, pairs


def graph_pairs(entries, tile_pairs):
    """Preserve distinct actual child clock pins, even on one parent macro.

    Dataflow graph identifies communicating macro pairs. Connect their closest
    placed clock entries; connect entries inside each macro by adjacent physical
    position. These choices define a candidate topology, not timing equivalence
    or proof of a data pin's related clock. Every child retains its own leaf.
    """
    by = defaultdict(list)
    for key, _, x, y in entries:
        by[key.rsplit('/', 1)[0]].append((key, x, y))
    out = set()
    for pins in by.values():
        pins.sort(key=lambda p: (p[1], p[2], p[0]))
        out.update((a[0], b[0]) for a, b in zip(pins, pins[1:]))
    for a, b in sorted(tile_pairs):
        if a not in by or b not in by:
            continue
        p, q = min(((p, q) for p in by[a] for q in by[b]),
                   key=lambda pq: abs(pq[0][1]-pq[1][1])+abs(pq[0][2]-pq[1][2]))
        out.add((p[0], q[0]))
    return sorted(out)


def verify_topology(tree, expected):
    drivers, loads, edges = {}, {}, defaultdict(list)
    for name, driver, sinks in tree['nets']:
        if driver in drivers:
            raise ValueError(f'multiple nets from {driver}')
        drivers[driver] = name
        for load in sinks:
            if load in loads:
                raise ValueError(f'double-driven clock load {load}')
            loads[load] = name
            edges[driver].append(load)
    visited, stack = set(), [('port', 'clk_hbm')]
    while stack:
        node = stack.pop()
        if node in visited:
            raise ValueError(f'cycle or reconvergence at {node}')
        visited.add(node)
        stack.extend(edges.get(node, []))
    actual = {x[1] for x in visited if x[0] == 'pin'}
    if actual != set(expected):
        raise ValueError(f'clock coverage mismatch: missing {set(expected)-actual}, extra {actual-set(expected)}')
    if {x[1] for x in visited if x[0] == 'buf'} != {b[0] for b in tree['buffers']}:
        raise ValueError('orphan clock buffer')
    return dict(covered_entries=len(actual), buffers=len(tree['buffers']), cycles=0, multiple_drivers=0)


def main():
    import odb
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input-odb', required=True, type=Path)
    ap.add_argument('--dump', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--domains', default='serial', help='comma-separated PLL domains; empty string selects only extra roots')
    ap.add_argument('--extra-root', action='append', default=[], metavar='NAME=INST/PIN',
                    help='actual forwarded clock output; preserve that native driver and all its actual input loads')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if (a.out / 'physical_clock.odb').exists():
        raise ValueError('refusing to overwrite an existing physical candidate')
    roots, entries, pairs = load_dump(a.dump)
    db = odb.dbDatabase.create()
    odb.read_db(db, str(a.input_odb))
    block = db.getChip().getBlock()
    dbu = block.getDbUnitsPerMicron()
    die = block.getDieArea()
    if die.xMin() or die.yMin():
        raise ValueError('nonzero die origin needs explicit site-origin handling')
    width, height = die.xMax()/dbu, die.yMax()/dbu
    obstacles, instances = [], {}
    for inst in block.getInsts():
        instances[inst.getName()] = inst
        if inst.getMaster().isBlock():
            box = inst.getBBox()
            obstacles.append(tuple(v/dbu for v in (box.xMin(), box.yMin(), box.xMax(), box.yMax())))
    # Snapshot a complete clock-like input inventory. This is a deliberately
    # conservative discovery list; it is NOT a substitute for per-pin Liberty
    # and RTL clock-source/forwarded-clock binding.
    clocklike = re.compile(r'^(?:(?:ck|clk|sk)|(?:fi0?|xf|cr|wclk|rclk|io_clk)(?:_|\[|$))')
    root_names={d:f'sp_collective/pll_{d}[0]' for d in a.domains.split(',') if d}
    noncanonical_entries=[]
    for spec in a.extra_root:
        name,root=spec.split('=',1)
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',name) or name in root_names:
            raise ValueError(f'invalid or duplicate extra clock root name: {name}')
        driver=block.findITerm(root)
        if not driver or driver.getIoType()!='OUTPUT' or not driver.getNet():
            raise ValueError(f'extra root must be an actual connected macro clock output: {root}')
        box=driver.getBBox()
        roots[root]=((box.xMin()+box.xMax())/2/dbu,(box.yMin()+box.yMax())/2/dbu)
        entries[root]=[]
        for pin in driver.getNet().getITerms():
            if pin.getIoType()!='INPUT':continue
            inst=pin.getInst();port=pin.getMTerm().getName();box=pin.getBBox()
            if not clocklike.match(port) and pin.getMTerm().getSigType()!='CLOCK':
                noncanonical_entries.append(inst.getName()+'/'+port)
            entries[root].append((inst.getName()+'/'+port,inst.getMaster().getName(),
                (box.xMin()+box.xMax())/2/dbu,(box.yMin()+box.yMax())/2/dbu))
        if not entries[root]:raise ValueError(f'extra root has no real input loads: {root}')
        root_names[name]=root
    observed = {row[0] for vals in entries.values() for row in vals}
    discovery = []
    master_pins = {}
    for inst in instances.values():
        master = inst.getMaster()
        if not master.isBlock():
            continue
        names = master_pins.setdefault(master.getName(), [p.getName() for p in master.getMTerms()
            if p.getIoType() == 'INPUT' and (p.getSigType() == 'CLOCK' or clocklike.match(p.getName()))])
        for name in names:
            pin = inst.findITerm(name)
            key = inst.getName()+'/'+name
            net = pin.getNet()
            if key not in observed:
                discovery.append(dict(pin=key, net=net.getName() if net else None,
                                      reason='not reached by supplied PLL clock check'))
    (a.out / 'uncovered_clock_inventory.json').write_text(json.dumps(discovery, indent=1)+'\n')
    trees, selected, checks = {}, {}, {}
    for domain,root in root_names.items():
        if root not in roots or root not in entries:
            raise ValueError(f'no actual placed root/entries for {root}')
        rpin = block.findITerm(root)
        if not rpin or not rpin.getNet():
            raise ValueError(f'root missing in actual ODB: {root}')
        net = rpin.getNet()
        sinks = []
        for key, master, x, y in entries[root]:
            pin = block.findITerm(key)
            if not pin or pin.getNet() != net or pin.getIoType() != 'INPUT':
                raise ValueError(f'dump/ODB clock connection mismatch: {key}')
            bbox = pin.getBBox()
            xy = ((bbox.xMin()+bbox.xMax())/2/dbu, (bbox.yMin()+bbox.yMax())/2/dbu)
            if abs(xy[0]-x)+abs(xy[1]-y) > .002:
                raise ValueError(f'dump/ODB placed pin mismatch: {key} {xy} vs {(x,y)}')
            sinks.append((key, 'entry', *xy))
        local_pairs = graph_pairs(entries[root], pairs)
        print(f'CLOCK_BUILD {domain}: {len(sinks)} actual pins, {len(local_pairs)} graph edges', flush=True)
        tree = dct.build(width, height, obstacles, roots[root], sinks,
                         lambda n: 'SW', mode='graph', pairs=local_pairs)
        checks[domain] = verify_topology(tree, [s[0] for s in sinks])
        # A removed leaf must be rejected; this guards the actual coverage gate.
        broken = dict(tree, nets=[n for n in tree['nets'] if not any(p[0]=='pin' for p in n[2])])
        try:
            verify_topology(broken, [s[0] for s in sinks])
        except ValueError:
            checks[domain]['missing_leaf_mutant_rejected'] = True
        else:
            raise ValueError('missing-leaf mutant incorrectly passed')
        trees[domain] = tree
        selected[domain] = (root, net, sinks)
    clock_sites.allocate(trees, width, height, obstacles)
    all_buffers, leaf_map = [], []
    for domain, tree in sorted(trees.items()):
        root, root_net, sinks = selected[domain]
        buf_instances = {}
        for name, cell, x, y in tree['buffers']:
            master = db.findMaster(cell)
            if not master:
                raise ValueError(f'ASAP7 buffer master absent from actual DB: {cell}')
            if abs(master.getWidth()/dbu-clock_sites.SIZES[cell][0]) > 1e-6 or abs(master.getHeight()/dbu-.270) > 1e-6:
                raise ValueError(f'actual clock cell dimensions differ: {cell}')
            full = f's81clk_{domain}_{name}'
            if block.findInst(full):
                raise ValueError(f'clock name already exists: {full}')
            inst = odb.dbInst.create(block, master, full)
            inst.setOrient(clock_sites.orientation(y))
            inst.setLocation(round(x*dbu), round(y*dbu))
            inst.setPlacementStatus('PLACED')
            buf_instances[name] = inst
            all_buffers.append(dict(name=full, cell=cell, x=x, y=y, orient=clock_sites.orientation(y)))
        for key, _, _, _ in sinks:
            block.findITerm(key).disconnect()
        for name, driver, loads in tree['nets']:
            if driver[0] == 'port':
                net = root_net
            else:
                net = odb.dbNet.create(block, f's81clk_{domain}_{name}')
                buf_instances[driver[1]].findITerm('Y').connect(net)
            for load in loads:
                if load[0] == 'buf':
                    buf_instances[load[1]].findITerm('A').connect(net)
                else:
                    pin = block.findITerm(load[1])
                    pin.connect(net)
                    leaf_map.append(dict(pin=load[1], root=root, leaf_driver=driver[1], net=net.getName()))
        print(f'CLOCK_INSTANTIATED {domain}: {len(buf_instances)} actual buffers', flush=True)
    manifest = dict(schema='opentallas.s81.physical_clock_candidate.v1',
        scope='PHYSICAL_TOPOLOGY_PILOT_NOT_NATIVE_CLOCK_OR_DIE_QUALIFICATION',
        input_odb=dict(path=str(a.input_odb), sha256=digest(a.input_odb)),
        input_dump=dict(path=str(a.dump), sha256=digest(a.dump)),
        source_sha256={str(p.relative_to(Path(__file__).resolve().parents[2])): digest(p)
            for p in [Path(__file__).resolve(), Path(dct.__file__), Path(clock_sites.__file__)]},
        dimensions_um=[width,height], hard_obstacles=len(obstacles),
        domains={d:dict(root=selected[d][0], clock_kind='pll' if selected[d][0].startswith('sp_collective/pll_') else 'native_macro_forwarded_output', actual_entries=len(selected[d][2]), checks=checks[d], model=t['model'])
                 for d,t in trees.items()},
        actual_clock_buffers=len(all_buffers), buffers=all_buffers, entries=leaf_map,
        unwalked_clocklike_pins=len(discovery),noncanonical_explicit_root_entries=noncanonical_entries,
        open_obligations=['propagated TT/FF arrival with actual pin capacitance and physical RC',
            'per-child corner insertion R compensation: physical positive delays only',
            'all PLL and forwarded/ratio clock coverage against RTL/Liberty',
            'post-route uncertainty and setup/hold/DRC; topology model gives no credit'])
    odb.write_db(db, str(a.out/'physical_clock.odb'))
    (a.out/'physical_clock.json').write_text(json.dumps(manifest,indent=1)+'\n')
    print('PHYSICAL_CLOCK_PILOT_COMPLETE', len(all_buffers), 'cells;', len(discovery), 'unwalked clocklike pins', flush=True)


if __name__ == '__main__':
    main()
