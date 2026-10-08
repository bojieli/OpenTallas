"""Read-only OpenDB analysis of the retained R2 failure; never calls a router."""
import collections
import hashlib
import json
from pathlib import Path
import re
import statistics

import odb

INPUT = Path('/input/5_1_grt-failed.odb')
REPORT = Path('/reports/congestion.rpt')
OUT = Path('/output')
db = odb.dbDatabase.create()
odb.read_db(db, str(INPUT))
block = db.getChip().getBlock()
dbu = block.getDbUnitsPerMicron()
core = block.getCoreArea()
die = block.getDieArea()
grid = block.getGCellGrid()
xs, ys = grid.getGridX(), grid.getGridY()
normalize = lambda n: n.replace('\\', '')


def box(inst):
    r = inst.getBBox()
    return [r.xMin()/dbu, r.yMin()/dbu, r.xMax()/dbu, r.yMax()/dbu]


def union(a, b):
    if a is None:
        return list(b)
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def passthrough(master):
    return master.startswith(('BUF', 'INV'))


def instance_class(name, master):
    if master.startswith('TIE'):
        return 'tie'
    if master.startswith('DFF'):
        return 'DFF'
    for prefix in ['hold', 'input', 'output', 'place', 'wire', 'clkbuf']:
        if name.startswith(prefix):
            return prefix
    return 'mapped_buffer_or_inverter' if passthrough(master) else 'mapped_logic'


cells = collections.Counter()
areas = collections.Counter()
for inst in block.getInsts():
    m = inst.getMaster()
    c = instance_class(inst.getName(), m.getName())
    cells[c] += 1
    areas[c] += m.getWidth()*m.getHeight()/dbu**2

parents = {}
netinfo = {}
fanout_histogram = collections.Counter()
pins = []
for net in block.getNets():
    name = normalize(net.getName())
    terms = list(net.getITerms())
    outs = [t for t in terms if t.getIoType() == 'OUTPUT']
    sinks = [t for t in terms if t.getIoType() == 'INPUT']
    ports = list(net.getBTerms())
    fanout_histogram[len(sinks)] += 1
    d = outs[0].getInst() if len(outs) == 1 else None
    master = d.getMaster().getName() if d else None
    if d and passthrough(master):
        inputs = [t for t in d.getITerms() if t.getIoType() == 'INPUT' and t.getNet()]
        if len(inputs) == 1:
            parents[name] = normalize(inputs[0].getNet().getName())
    bounds = None
    for t in sinks + outs:
        bounds = union(bounds, box(t.getInst()))
    for bt in ports:
        for bp in bt.getBPins():
            for r in bp.getBoxes():
                pb = [r.xMin()/dbu, r.yMin()/dbu, r.xMax()/dbu, r.yMax()/dbu]
                bounds = union(bounds, pb)
                pins.append({'name': normalize(bt.getName()), 'direction': bt.getIoType(),
                             'layer': r.getTechLayer().getName(), 'bbox_um': pb})
    leaves = sum(not passthrough(t.getInst().getMaster().getName()) for t in sinks)
    leaves += sum(bt.getIoType() == 'OUTPUT' for bt in ports)
    netinfo[name] = {'driver': d.getName() if d else None, 'master': master,
                     'ports': [normalize(t.getName()) for t in ports],
                     'signal_type': net.getSigType(), 'sinks': len(sinks),
                     'terminal_sinks': leaves, 'bbox_um': bounds}

root_cache = {}


def root(name):
    path, seen = [], set()
    while name in parents and name not in root_cache and name not in seen:
        seen.add(name)
        path.append(name)
        name = parents[name]
    result = root_cache.get(name, name)
    for n in path:
        root_cache[n] = result
    return result


def root_class(name):
    n = netinfo[name]
    if n['signal_type'] == 'CLOCK' or name.startswith('clk'):
        return 'clock'
    for p in n['ports']:
        if p == 'por_n':
            return 'cold_POR'
        for prefix in ['in_data', 'in_owner', 'in_frame', 'release_', 'ACK_', 'out_']:
            if p.startswith(prefix):
                return prefix
        return 'other_boundary'
    if (n['master'] or '').startswith('TIE'):
        return 'tie'
    if (n['master'] or '').startswith('DFF'):
        return 'register_output'
    return 'internal_logic'


trees = {}
for name, info in netinfo.items():
    r = root(name)
    t = trees.setdefault(r, {'root': r, 'class': root_class(r),
                             'root_driver': netinfo[r]['driver'],
                             'root_master': netinfo[r]['master'], 'buffer_nets': 0,
                             'terminal_sinks': 0, 'bbox_um': None,
                             'buffers_by_class': collections.Counter(),
                             'overflow_region_memberships': 0})
    t['terminal_sinks'] += info['terminal_sinks']
    t['bbox_um'] = union(t['bbox_um'], info['bbox_um']) if info['bbox_um'] else t['bbox_um']
    if name in parents:
        t['buffer_nets'] += 1
        t['buffers_by_class'][instance_class(info['driver'], info['master'])] += 1

regions = []
membership = collections.Counter()
edge_overflow = collections.Counter()
for chunk in REPORT.read_text().split('violation type: ')[1:]:
    direction = chunk.split(' congestion', 1)[0]
    m = re.search(r'capacity:(\d+) usage:(\d+) congestion:(\d+)', chunk)
    coords = re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\)', chunk)
    if not m or not coords:
        raise ValueError('Unparsed original congestion report region')
    bbox = [float(x) for x in coords.groups()]
    nets = [normalize(n) for n in re.findall(r'net:(\S+)', chunk)]
    classes = collections.Counter()
    roots = set()
    for n in nets:
        if n not in netinfo:
            classes['unmatched'] += 1
            continue
        rr = root(n)
        classes[root_class(rr)] += 1
        roots.add(rr)
    for rr in roots:
        trees[rr]['overflow_region_memberships'] += 1
    membership.update(classes)
    v = int(m.group(3))
    # Near-boundary uses real physical core coordinates, not a pin-side guess.
    distance = min(bbox[0]-core.xMin()/dbu, core.xMax()/dbu-bbox[2],
                   bbox[1]-core.yMin()/dbu, core.yMax()/dbu-bbox[3])
    edge_overflow['within_5um_of_core_edge' if distance <= 5 else 'interior'] += v
    regions.append({'direction': direction, 'bbox_um': bbox, 'capacity': int(m.group(1)),
                    'usage': int(m.group(2)), 'overflow': v, 'classes': dict(classes),
                    'roots': sorted(roots), 'net_count': len(nets)})

layer_stats = {}
layer_bins = []
for layername in ['M2', 'M3', 'M4', 'M5', 'M6', 'M7']:
    layer = db.getTech().findLayer(layername)
    over = []
    for ix in range(len(xs)):
        for iy in range(len(ys)):
            cap, usage = grid.getCapacity(layer, ix, iy), grid.getUsage(layer, ix, iy)
            if usage > cap:
                over.append({'layer': layername, 'bbox_um': [xs[ix]/dbu, ys[iy]/dbu,
                     (xs[ix+1] if ix+1<len(xs) else xs[ix]+xs[-1]-xs[-2])/dbu, (ys[iy+1] if iy+1<len(ys) else ys[iy]+ys[-1]-ys[-2])/dbu], 'capacity': cap, 'usage': usage,
                     'overflow': usage-cap})
    layer_stats[layername] = {'overflow': sum(x['overflow'] for x in over),
                              'overflow_bins': len(over),
                              'max_overflow': max((x['overflow'] for x in over), default=0)}
    layer_bins.extend(over)

pin_counts = collections.Counter()
pin_positions = collections.defaultdict(list)
for p in pins:
    x, y = (p['bbox_um'][0]+p['bbox_um'][2])/2, (p['bbox_um'][1]+p['bbox_um'][3])/2
    sides = {'bottom': abs(y-die.yMin()/dbu), 'top': abs(y-die.yMax()/dbu),
             'left': abs(x-die.xMin()/dbu), 'right': abs(x-die.xMax()/dbu)}
    side = min(sides, key=sides.get)
    pin_counts[side+':'+p['layer']+':'+p['direction']] += 1
    pin_positions[side+':'+p['layer']].append(x if side in ['top', 'bottom'] else y)

pin_spacing = {}
for key, values in pin_positions.items():
    positions = sorted(values)
    gaps = [b-a for a, b in zip(positions, positions[1:])]
    pin_spacing[key] = {'shape_count': len(positions), 'coordinate_min_um': positions[0],
                        'coordinate_max_um': positions[-1],
                        'min_center_spacing_um': min(gaps) if gaps else None,
                        'median_center_spacing_um': statistics.median(gaps) if gaps else None}

tile_overflow = collections.Counter()
for r in regions:
    x, y = (r['bbox_um'][0]+r['bbox_um'][2])/2, (r['bbox_um'][1]+r['bbox_um'][3])/2
    tile_overflow[(int(x//25), int(y//25))] += r['overflow']
root_class_totals = {}
for t in trees.values():
    a = root_class_totals.setdefault(t['class'], {'trees': 0, 'buffer_nets': 0,
                                                 'terminal_sinks': 0,
                                                 'buffers_by_class': collections.Counter()})
    a['trees'] += 1
    a['buffer_nets'] += t['buffer_nets']
    a['terminal_sinks'] += t['terminal_sinks']
    a['buffers_by_class'].update(t['buffers_by_class'])

critical = ['_002818_', '_036106_', '_043426_', '_049997_', '_052484_', '_021358_', '_016590_']
summary = {
    'basis': 'Read-only failed global-route OpenDB; no reroute, placement or functional gate',
    'odb_sha256': hashlib.sha256(INPUT.read_bytes()).hexdigest(),
    'report_sha256': hashlib.sha256(REPORT.read_bytes()).hexdigest(),
    'cell_classes': dict(cells), 'cell_class_area_um2': dict(areas),
    'core_bbox_um': [core.xMin()/dbu, core.yMin()/dbu, core.xMax()/dbu, core.yMax()/dbu],
    'die_bbox_um': [die.xMin()/dbu, die.yMin()/dbu, die.xMax()/dbu, die.yMax()/dbu],
    'boundary_terminal_count': len(list(block.getBTerms())),
    'root_class_totals': root_class_totals,
    'post_buffer_direct_fanout_histogram': dict(sorted(fanout_histogram.items())),
    'root_buffer_tree_top_by_terminal_sinks': sorted(trees.values(), key=lambda x:x['terminal_sinks'], reverse=True)[:30],
    'root_buffer_tree_top_by_overflow_membership': sorted(trees.values(), key=lambda x:x['overflow_region_memberships'], reverse=True)[:30],
    'critical_path_root_trees': [trees[root(n)] for n in critical if n in netinfo],
    'congestion_report_region_count': len(regions),
    'congestion_report_overflow_sum': sum(r['overflow'] for r in regions),
    'congestion_report_direction_overflow': dict(collections.Counter({d:sum(r['overflow'] for r in regions if r['direction']==d) for d in ['Horizontal','Vertical']})),
    'congestion_report_net_membership_classes': dict(membership),
    'congestion_report_edge_overflow': dict(edge_overflow),
    'ODB_layer_overflow': layer_stats,
    'ODB_reader_overflow_sum': sum(x['overflow'] for x in layer_stats.values()),
    'ODB_reader_limit': 'getUsage/getCapacity layer scan totals 11163 versus original GRT/report 11199. Preserve this discrepancy; original GRT layer totals are authoritative. Do not infer missing per-direction capacity from these getters.',
    'highest_overflow_25um_tiles': [{'bbox_um': [x*25, y*25, (x+1)*25, (y+1)*25],
                                    'overflow': n} for (x, y), n in tile_overflow.most_common(12)],
    'boundary_pin_shape_counts': dict(pin_counts),
    'boundary_pin_center_spacing': pin_spacing,
    'attribution_limit': 'Membership is participation in an overflowing channel, not causal allocation of overflow. BUF/INV trees are traced to their original driver; no traversal through multi-input logic. CTS hold/setup remains checkpoint-only.'
}
OUT.mkdir(exist_ok=True)
for name, data in [('diagnosis.json', summary), ('overflow_regions.json', regions),
                   ('layer_overflow_bins.json', layer_bins), ('root_buffer_trees.json', trees),
                   ('boundary_pins.json', pins)]:
    (OUT/name).write_text(json.dumps(data, indent=2)+'\n')
print(json.dumps(summary, indent=2))
