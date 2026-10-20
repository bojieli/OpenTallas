"""Private source-pinned placed sequential-cone audit; run inside exact ORFS image."""
import collections
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

import odb
sys.path.insert(0, '/audit_tools')
import native_census as NC

OUT = Path('/out')
OUT.mkdir(exist_ok=True)
errors = []
EXCLUDED_PORTS = {'ck', 'hck'}
MEMORIES = {'ot_sram_1r1w_4x32_m1_p192_grp_rsp',
            'ot_sram_1r1w_128x256_m1_r2c2_p192_mir'}
odb_path = next(Path('/gate/routes/gate/work/orfs/results/asap7').glob('*/base/4_1_cts.odb'))
log = Path('/gate/cts.log').read_text()
libs = sorted(set(re.findall(r'^read_liberty (\S+)', log, re.M)))
roles, receipts = NC.liberty_roles(libs)
memory_receipts = []
for master in sorted(MEMORIES):
    p = Path('/src/physical/asap7_memory_macros') / master / (master + '.v')
    text = p.read_text()
    if not re.search(r'always\s*@\(posedge clk\)', text) or not re.search(r'if\s*\(r_ce_in\)\s*rd_out\s*<=', text):
        errors.append('synchronous SRAM read not established:' + master)
    memory_receipts.append({'master': master, 'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                            'boundary': 'posedge clk registered rd_out, verified in exact behavioural source'})
db = odb.dbDatabase.create()
odb.read_db(db, str(odb_path))
block = db.getChip().getBlock()
dbu = block.getDbUnitsPerMicron()
nets = {n.getId(): n for n in block.getNets()}
roots, endpoints = {}, collections.defaultdict(list)
back, forward = {}, collections.defaultdict(list)
constant_nets = set()
ring_inputs, ring_outputs, rings = {}, {}, {}
counts = collections.Counter()

def coordinate(t):
    if hasattr(t, 'getInst'):
        inst = t.getInst()
        if inst.getMaster().isBlock():
            ok, x, y = t.getAvgXY()
            if not ok:
                raise RuntimeError('missing actual macro pin geometry:' + inst.getName() + '/' + t.getMTerm().getName())
            return [x / dbu, y / dbu]
        z = inst.getBBox()
        return [(z.xMin() + z.xMax()) / (2 * dbu), (z.yMin() + z.yMax()) / (2 * dbu)]
    boxes = [z for pin in t.getBPins() for z in pin.getBoxes()]
    if not boxes:
        raise RuntimeError('missing port geometry:' + t.getName())
    z = boxes[0]
    return [(z.xMin() + z.xMax()) / (2 * dbu), (z.yMin() + z.yMax()) / (2 * dbu)]

def descriptor(t, kind):
    p = coordinate(t)
    if not hasattr(t, 'getInst'):
        return {'name': 'port:' + t.getName(), 'pin': t.getName(), 'kind': kind, 'xy_um': p}
    i = t.getInst()
    r = {'name': i.getName() + '/' + t.getMTerm().getName(), 'instance': i.getName(),
         'master': i.getMaster().getName(), 'pin': t.getMTerm().getName(), 'kind': kind, 'xy_um': p}
    if i.getMaster().isBlock():
        x, y = i.getOrigin()
        r.update(macro_origin_um=[x / dbu, y / dbu], orientation=str(i.getOrient()),
                 pin_offset_from_origin_um=[p[0] - x / dbu, p[1] - y / dbu])
    return r

def role_pin(role, master, name):
    p = role['pins'].get(name)
    if p is None:
        m = re.fullmatch(r'(.*)\[(-?\d+)\]', name)
        if m and int(m[2]) in role['bus_order'].get(m[1], []):
            p = role['pins'].get(m[1])
    if p is None:
        errors.append('missing Liberty pin:' + master + '/' + name)
    return p

for inst in block.getInsts():
    master = inst.getMaster().getName()
    role = roles.get(master)
    if role is None:
        errors.append('missing Liberty cell:' + master)
        continue
    seq = role['sequential'] or master in MEMORIES
    if inst.getMaster().isBlock() and master not in MEMORIES:
        errors.append('unclassified macro:' + master)
    ins, outs = {}, []
    for t in inst.getITerms():
        if t.getSigType() in ('POWER', 'GROUND'):
            continue
        pr = role_pin(role, master, t.getMTerm().getName())
        if not pr:
            continue
        if pr['clock']:
            counts['actual_liberty_clock_pins_excluded'] += 1
            continue
        if t.getNet() is None:
            # Unused outputs are legal; an unconnected data/control input is not.
            if pr['direction'] == 'input':
                errors.append('unconnected input:' + inst.getName() + '/' + t.getMTerm().getName())
            continue
        if pr['direction'] == 'input':
            ins[t.getMTerm().getName()] = t
        elif pr['direction'] == 'output':
            outs.append((t, pr))
        elif pr['direction'] != 'internal':
            errors.append('unsupported direction:' + master + '/' + t.getMTerm().getName())
    if seq:
        kind = 'synchronous_sram' if master in MEMORIES else 'sequential'
        for t in ins.values():
            endpoints[t.getNet().getId()].append(descriptor(t, kind + '_input'))
        for t, pr in outs:
            n = t.getNet().getId()
            if n in roots or n in back:
                errors.append('multiple drivers:' + nets[n].getName())
            roots[n] = descriptor(t, kind + '_output')
        counts[kind + '_instances'] += 1
    else:
        for t, pr in outs:
            n = t.getNet().getId()
            f = re.sub(r'[\s()]', '', pr['function'] or '')
            if f in ('0', '1', "1'b0", "1'b1"):
                constant_nets.add(n)
                continue
            if not f:
                errors.append('missing combinational function:' + master + '/' + t.getMTerm().getName())
                continue
            tokens = set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*(?:\[-?\d+\])?', f))
            unknown = tokens - set(ins)
            if unknown:
                errors.append('unknown function inputs:' + master + '/' + str(sorted(unknown)))
                continue
            deps = sorted({ins[x].getNet().getId() for x in tokens})
            if not deps:
                errors.append('empty nonconstant cone:' + inst.getName())
            if n in back or n in roots:
                errors.append('multiple drivers:' + nets[n].getName())
            cell = inst.getName() + '/' + t.getMTerm().getName()
            back[n] = (deps, cell)
            for dep in deps:
                forward[dep].append((n, cell))
        counts['combinational_instances'] += 1
    if master == 'ot_sram_1r1w_4x32_m1_p192_grp_rsp':
        name = inst.getName()
        x, y = inst.getOrigin()
        rings[name] = {'instance': name, 'master': master, 'origin_um': [x / dbu, y / dbu],
                       'orientation': str(inst.getOrient()),
                       'master_size_um': [inst.getMaster().getWidth() / dbu, inst.getMaster().getHeight() / dbu],
                       'input_pin_count': len(ins), 'output_pin_count': len(outs)}
        ring_inputs[name] = list(ins.values())
        ring_outputs[name] = [t for t, _ in outs]

for t in block.getBTerms():
    if not t.getNet() or t.getSigType() in ('POWER', 'GROUND'):
        continue
    if t.getName() in EXCLUDED_PORTS:
        counts['declared_clock_ports_excluded'] += 1
        continue
    n = t.getNet().getId()
    if t.getIoType() == 'INPUT':
        if n in roots or n in back:
            errors.append('multiple drivers:' + nets[n].getName())
        roots[n] = descriptor(t, 'input_port')
    elif t.getIoType() == 'OUTPUT':
        endpoints[n].append(descriptor(t, 'output_port'))
    else:
        errors.append('unsupported port direction:' + t.getName())

# Memoized complete graph traversal: stop only on sequential/SRAM/port boundaries.
root_cache, end_cache = {}, {}
def cone(n, direction, active=None):
    cache = root_cache if direction == 'backward' else end_cache
    if n in cache:
        return cache[n]
    active = set() if active is None else active
    if n in active:
        errors.append('combinational cycle:' + nets[n].getName())
        return {}
    if direction == 'backward' and n in roots:
        cache[n] = {roots[n]['name']: roots[n]}
        return cache[n]
    active.add(n)
    result = {} if direction == 'backward' else {e['name']: e for e in endpoints.get(n, [])}
    if direction == 'backward':
        if n in back:
            for dep in back[n][0]:
                result.update(cone(dep, direction, active))
        elif n not in constant_nets:
            # A declared clock port feeding DATA is excluded only by the explicit task instruction.
            ports = [t.getName() for t in nets[n].getBTerms()]
            if not (ports and set(ports) <= EXCLUDED_PORTS):
                errors.append('undriven cone net:' + nets[n].getName())
    else:
        for dep, cell in forward.get(n, []):
            result.update(cone(dep, direction, active))
    active.remove(n)
    cache[n] = result
    return result

def reach(a, b):
    return abs(a['xy_um'][0] - b['xy_um'][0]) + abs(a['xy_um'][1] - b['xy_um'][1])

rows, all_edges = [], []
for name in sorted(rings):
    edges = []
    for t in ring_inputs[name]:
        end = descriptor(t, 'synchronous_sram_input')
        n = t.getNet().getId()
        for root in cone(n, 'backward').values():
            edges.append({'direction': 'to_ring', 'root': root, 'endpoint': end,
                          'endpoint_manhattan_um': round(reach(root, end), 6)})
    for t in ring_outputs[name]:
        root = descriptor(t, 'synchronous_sram_output')
        for end in cone(t.getNet().getId(), 'forward').values():
            edges.append({'direction': 'from_ring', 'root': root, 'endpoint': end,
                          'endpoint_manhattan_um': round(reach(root, end), 6)})
    edges.sort(key=lambda x: (-x['endpoint_manhattan_um'], x['root']['name'], x['endpoint']['name']))
    rec = dict(rings[name], edge_count=len(edges), over405_count=sum(e['endpoint_manhattan_um'] > 405 for e in edges),
               max_endpoint_manhattan_um=edges[0]['endpoint_manhattan_um'] if edges else None, edges=edges)
    rows.append(rec)
    all_edges.extend(dict(e, ring=name) for e in edges)

all_edges.sort(key=lambda e: -e['endpoint_manhattan_um'])
if len(rings) != 32:
    errors.append('expected32 tiny SRAM macros, got' + str(len(rings)))
if not all_edges:
    errors.append('no complete sequential-cone edges')
die = block.getDieArea()
result = {'schema': 'opentallas.grp_full_sequential_cones.v1',
          'method': 'Full Liberty-function combinational fanin/fanout traversal to sequential ff/latch, synchronous SRAM, or port boundaries. All tiny SRAM data/control inputs and all rd_out bits. No data exemptions. Endpoint Manhattan distance, NOT routed wirelength or combinational path wirelength sum.',
          'coordinate_policy': 'Actual getAvgXY for every macro ITerm; standard-cell centre and first BPin box centre as explicit proxies.',
          'clock_exclusion': 'Only actual Liberty clock input pins and declared ck/hck input ports; no net-label/ODB-signal-type clock exemption.',
          'odb_path': str(odb_path), 'odb_sha256': hashlib.sha256(odb_path.read_bytes()).hexdigest(),
          'cts_log_sha256': hashlib.sha256(Path('/gate/cts.log').read_bytes()).hexdigest(),
          'audit_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'die_um': [die.xMin()/dbu, die.yMin()/dbu, die.xMax()/dbu, die.yMax()/dbu],
          'liberty': receipts, 'synchronous_memory_proof': memory_receipts, 'counts': dict(counts),
          'role_errors': sorted(set(errors)), 'tiny_macro_count': len(rings), 'edge_count': len(all_edges),
          'max_endpoint_manhattan_um': all_edges[0]['endpoint_manhattan_um'] if all_edges else None,
          'over405_count': sum(e['endpoint_manhattan_um'] > 405 for e in all_edges),
          'top30': all_edges[:30], 'rings': rows}
result['status'] = 'ERROR' if errors else ('FAIL' if result['over405_count'] else 'PASS')
with gzip.open(OUT/'full_sequential_cones.json.gz', 'wt') as f:
    json.dump(result, f, separators=(',', ':'))
summary = {k:v for k,v in result.items() if k not in ('rings', 'liberty')}
(OUT/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print({k:v for k,v in summary.items() if k not in ('top30', 'synchronous_memory_proof')})
if errors:
    raise SystemExit(2)
if result['over405_count']:
    raise SystemExit(1)
