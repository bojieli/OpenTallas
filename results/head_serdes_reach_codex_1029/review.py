"""Read-only typed INTERNAL_CORE reach review; no generic face-register exemption.

Usage: review.py geom.tsv endpoint_census.json freeze.json io.tcl resize_liberty.json report.json
Every actual placed cell box is bounded, so this is stronger than bounding only
first/last FFs. Semantic cones still must be nonempty, direction typed, and fully
mapped to real placed instance/master pairs. Clocks/resets come from freeze.
"""
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

geom, semantic, freeze, io, liberty, out = map(Path, sys.argv[1:])
models = json.loads(liberty.read_text())["models"]
census = json.loads(semantic.read_text())
fz = json.loads(freeze.read_text())
contract = fz['source_profile']['endpoint_contract']
assert contract == census['contract']
assert contract['kind'] == 'INTERNAL_CORE'
assert contract['partition_rule'] == 'R2_INTERNAL_TIMED_IN_PARTITION'
assert fz['face_shell'] is None and fz['module'] == census['top']
assert census['verdict'] == 'PASS' and not census['fails']

def normal(name):
    return name.replace('\\[', '[').replace('\\]', ']')

cells, ports, kinds = {}, {}, collections.Counter()
for line in geom.open():
    row = line.rstrip('\n').split('\t')
    if row[0] == 'C':
        name = normal(row[8])
        assert name not in cells
        cells[name] = dict(master=row[3], box=list(map(float, row[4:8])))
        kinds[row[2]] += 1
    elif row[0] == 'P' and row[4] == 'SIGNAL':
        assert row[2] not in ports
        ports[row[2]] = dict(direction=row[3].lower(), xy=list(map(float, row[6:8])))

shapes = {}
pattern = r'place_pin -pin_name \{([^}]+)\} -layer (\S+) -location \{([^}]+)\} -pin_size \{([^}]+)\}'
for name, layer, location, size in re.findall(pattern, io.read_text()):
    shapes[name] = dict(layer=layer, xy=list(map(float, location.split())), size=list(map(float, size.split())))
control_ports = set(fz['clocks']) | set(fz['resets'])
assert set(ports) == set(census['ports']) | control_ports
assert set(ports) <= set(shapes)
for name, p in ports.items():
    assert max(abs(a-b) for a,b in zip(p['xy'], shapes[name]['xy'])) <= .001

# Exact extrema of all vertices, sufficient for all possible cell-pin positions.
extrema = []
for sx in (-1, 1):
    for sy in (-1, 1):
        best = max((sx*x+sy*y, name, x, y)
                   for name, cell in cells.items()
                   for x in (cell['box'][0], cell['box'][2])
                   for y in (cell['box'][1], cell['box'][3]))
        extrema.append((sx, sy, *best))

def box_reach(p, box):
    x,y = p
    return max(abs(x-a)+abs(y-b) for a in (box[0], box[2]) for b in (box[1], box[3]))

resized = []
for e in census['endpoints']:
    cell = cells[normal(e['instance'])]
    if cell['master'] != e['master']:
        old, new = models[e['master']], models[cell['master']]
        assert old == new and new['sequential_kind'] == 'ff'
        pin = new['pins'][e['pin']]
        assert pin['direction'] == ('input' if e['kind'] == 'REGISTER_D' else 'output')
        assert set(pin['related_clocks']) <= {p for p,v in new['pins'].items() if v['clock']}
        resized.append(dict(instance=e['instance'], source_master=e['master'], physical_master=cell['master'], pin=e['pin']))

rows = {}
for name, p in census['ports'].items():
    actual = ports[name]
    assert p['direction'] == actual['direction']
    assert p['endpoints']
    expected_kind = {'input': 'REGISTER_D', 'output': 'REGISTER_Q'}[p['direction']]
    endpoints = [census['endpoints'][i] for i in p['endpoints']]
    assert all(e['kind'] == expected_kind for e in endpoints)
    margin = sum(shapes[name]['size'])/2
    bound = max((box_reach(actual['xy'], cells[normal(e['instance'])]['box']), e['instance']) for e in endpoints)
    x,y = actual['xy']
    global_bound = max((value-sx*x-sy*y, cell, cx, cy) for sx,sy,value,cell,cx,cy in extrema)
    rows[name] = dict(direction=p['direction'], kind=expected_kind, endpoint_count=len(endpoints),
        endpoint_master_instance_coverage='PASS_TYPED_LIBERTY_RESIZE_CHECKED', pin_xy=actual['xy'], pin_half_manhattan_um=margin,
        first_last_ff_box_bound_um=round(bound[0]+margin, 6), first_last_witness=bound[1],
        all_placed_cells_box_bound_um=round(global_bound[0]+margin, 6), all_cells_witness=global_bound[1:])

worst = max((r['all_placed_cells_box_bound_um'], n) for n,r in rows.items())
assert worst[0] <= 405, worst
report = dict(verdict='PASS', scope='TYPED_INTERNAL_CORE_ACTUAL_IO_REACH_ONLY', contract=contract,
    master=fz['module'], typed_ports=len(rows), directions=dict(collections.Counter(r['direction'] for r in rows.values())),
    physical_signal_ports=len(ports), declared_clock_reset_ports=sorted(control_ports),
    all_placed_cells=len(cells), physical_cell_flags=dict(kinds), semantic_endpoint_records=len(census['endpoints']),
    mapped_endpoint_records=len(census['endpoints']), typed_port_endpoint_relations=sum(r['endpoint_count'] for r in rows.values()),
    missing_ports=0, missing_endpoints=0, empty_cones=0, direction_or_unclassified_master_mismatches=0,
    typed_liberty_resized_endpoint_records=len(resized), resized_instances=len({r['instance'] for r in resized}), resized_endpoints=resized,
    method='All actual cell-box vertices bound every possible register pin; actual full pin-shape half-Manhattan size added. Each typed semantic first/last register endpoint also mapped by instance AND master.',
    limit_um=405, worst_all_cell_box_bound_um=worst[0], worst_port=worst[1],
    max_first_last_ff_box_bound_um=max(r['first_last_ff_box_bound_um'] for r in rows.values()),
    inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (geom,semantic,freeze,io,liberty)},
    semantic_netlist_sha256=census['netlist_sha256'], ports=rows,
    not_qualified=['actual TT setup833ps/60ps', 'actual FF hold25ps', 'related pair CPPR/skew', 'LEC', 'partition composed signoff'],
    generic_auto_geom='Original pin_unreg320 failure retained; no rule waiver or generic gate edit')
out.write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps({k:report[k] for k in ('verdict','typed_ports','semantic_endpoint_records','typed_port_endpoint_relations','worst_all_cell_box_bound_um','worst_port','max_first_last_ff_box_bound_um')}))
