#!/usr/bin/env python3
"""Full H3 finite SOFTWARE calendar; explicit provisional cycles, never an RTL oracle.

An interval with repeats is a lossless run-length schedule: repeat i owns the
listed credits on [start+i*stride,start+(i+1)*stride). Conservative batches
retain their ports through retirement. No traffic, admission, or ACK is free.
"""
import argparse
import ast
import math
import re
from collections import Counter, defaultdict
import gzip
import hashlib
import heapq
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = 'results/uarch/h3_complete_native_calendar_20261002'
LOWERING = 'results/uarch/h3_versioned_lowering_20261002'
DISTRIBUTED = 'results/uarch/h3_distributed_norm_endpoint_20261002'
PINS = [f'{folder}/{target}.json.gz' for folder in (LOWERING, DISTRIBUTED)
        for target in ('Qwen', 'DeepSeek')] + [
    DISTRIBUTED + '/model.json', LOWERING + '/manifest.json',
    'results/uarch/qwen_hbm_connected_20261001/common_HBM_backend_provider_binding_r2.json',
    'results/uarch/qwen_hbm_resource_schedule_20261002/required_phase_provider_r7.json',
    'results/uarch/qwen_hbm_downstream_contract_20261002/provider_ports_r8.json',
    'rtl/gpu/ot_gpu_rf_service.sv', 'rtl/gpu/ot_gpu_full_sm_service.sv',
    'tools/deepseek_hbm_complete_memory.py',
    'tools/qwen_hbm_complete_service_provider.py',
    'tools/deepseek_hbm_complete_packed_index_provider.py',
    'tools/h3_complete_native_calendar.py']


def positive(n, label):
    if type(n) is not int or n < 1:
        raise ValueError('positive explicit integer required: ' + label)
    return n


def ceil(n, d):
    return (n + d - 1) // d


def read_json(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt') as f:
            return json.load(f)
    return json.loads(Path(path).read_text())


class Calendar:
    """Deterministic earliest-ready DAG scheduler, atomic all-resource admission.

    Slots are concrete finite credit identities. Each reservation holds them
    through final consumption/reverse-credit. Atomic admission removes circular
    hold-and-wait; DAG cycles and impossible requests are rejected, not timed out.
    """
    def __init__(self, capacities):
        self.capacities = {k: positive(v, k) for k, v in capacities.items()}
        self.slots = {k: [0] * v for k, v in self.capacities.items()}
        self.events = []
        self.ends = {}

    def add(self, name, deps, duration, resources, *, ready=0, **attrs):
        if name in self.ends:
            raise ValueError('duplicate event identity ' + name)
        positive(duration, name)
        if type(ready) is not int or ready < 0:
            raise ValueError('invalid ready cycle')
        if len(deps) != len(set(deps)) or any(d not in self.ends for d in deps):
            raise ValueError('unresolved dependency/deadlock ' + name)
        start = max([ready] + [self.ends[d] for d in deps])
        selected = {}
        for key, count in sorted(resources.items()):
            positive(count, key)
            if key not in self.slots or count > self.capacities[key]:
                raise ValueError('finite capacity exhausted: ' + key)
            choices = sorted(range(len(self.slots[key])), key=lambda i: (self.slots[key][i], i))[:count]
            selected[key] = choices
            start = max(start, *(self.slots[key][i] for i in choices))
        end = start + duration
        for key, slots in selected.items():
            for slot in slots:
                self.slots[key][slot] = end
        event = dict(id=name, deps=list(deps), start=start, end=end,
                     resources=selected, **attrs)
        self.events.append(event)
        self.ends[name] = end
        return name

    def dag(self, tasks):
        tasks = list(tasks)
        byid = {t['id']: t for t in tasks}
        if len(byid) != len(tasks):
            raise ValueError('duplicate task')
        indegree = {}; successors = defaultdict(list)
        for t in tasks:
            if len(t['deps']) != len(set(t['deps'])):
                raise ValueError('duplicate dependency')
            indegree[t['id']] = len(t['deps'])
            for dep in t['deps']:
                if dep not in byid:
                    raise ValueError('unknown dependency')
                successors[dep].append(t['id'])
        queue = [k for k, v in indegree.items() if not v]
        heapq.heapify(queue)
        while queue:
            key = heapq.heappop(queue); t = byid[key]
            self.add(key, t['deps'], t['duration'], t['resources'])
            for nxt in successors[key]:
                indegree[nxt] -= 1
                if not indegree[nxt]:
                    heapq.heappush(queue, nxt)
        if len(self.ends) != len(tasks):
            raise ValueError('dependency cycle/deadlock')
        return self.events


def verify_calendar(events, capacities):
    """Independent interval/credit and dependency proof; handles parallel events."""
    seen = {}; owners = defaultdict(list)
    for e in events:
        if e['id'] in seen or type(e['start']) is not int or e['start'] < 0 or e['end'] <= e['start']:
            raise ValueError('event identity/time')
        for dep in e['deps']:
            if dep not in seen or seen[dep]['end'] > e['start']:
                raise ValueError('premature consume/dependency')
        for key, slots in e['resources'].items():
            if key not in capacities or len(slots) != len(set(slots)):
                raise ValueError('unknown/duplicate resource')
            for slot in slots:
                if type(slot) is not int or not 0 <= slot < capacities[key]:
                    raise ValueError('finite capacity exhausted')
                owners[key, slot].append((e['start'], e['end'], e['id']))
        if 'repeats' in e:
            if positive(e['repeats'], 'repeats') * positive(e['stride'], 'stride') != e['end'] - e['start']:
                raise ValueError('batch interval inconsistent')
        if 'native_program' in e:
            verify_native_program(e['native_program'])
            if e['end'] - e['start'] != e['native_program']['duration']:
                raise ValueError('native enclosing reservation mismatch')
        seen[e['id']] = e
    for intervals in owners.values():
        ordered = sorted(intervals)
        if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
            raise ValueError('overlapping credit/port ownership')
    return {'events': len(events), 'resource_slots_used': len(owners),
            'dependency_edges': sum(len(e['deps']) for e in events),
            'status': 'PASS_FINITE_INTERVAL_PROOF'}


def verify_native_program(program):
    """Replay compressed primitive timing and finite scratch, independently."""
    def walk(nodes):
        offset = 0; counts = Counter()
        for node in nodes:
            if node['offset'] != offset:
                raise ValueError('native primitive ordering/offset')
            if node['kind'] == 'primitive':
                for name, value in node['stage_cycles'].items():
                    positive(value, name)
                if node['duration'] != sum(node['stage_cycles'].values()):
                    raise ValueError('native stage composition')
                credit = node['storage_credit']
                if credit['sector_credit'] != 1 or credit['read_ports'] > 2 or credit['write_ports'] != 1:
                    raise ValueError('native primitive finite capacity')
                if not node['rounding'] or not node['source_instruction'].get('op'):
                    raise ValueError('native arithmetic provenance')
                counts[node['op']] += node['batches128']
            elif node['kind'] == 'loop':
                if node['count'] < 0:
                    raise ValueError('negative loop trip count')
                duration, body_counts = walk(node['body'])
                expected = duration * node['count'] + node.get('control_cycles', node.get('explicit_empty_loop_control_cycles', 0))
                if node['duration'] != expected:
                    raise ValueError('native loop repetition/stride')
                counts.update({op: n * node['count'] for op, n in body_counts.items()})
            else:
                raise ValueError('native calendar node kind')
            positive(node['duration'], 'native duration'); offset += node['duration']
        return offset, counts
    duration, counts = walk(program['primitive_tree'])
    duration += program.get('empty_owned_extent_control_cycles', 0)
    if duration != program['duration']:
        raise ValueError('native recipe duration')
    live = []
    for home in program['scratch_homes'].values():
        lo = home['byte_offset']; size = home['buffer_bytes'] * home['buffers']
        if lo < 0 or lo % 512 or size % 512 or lo + size > program['finite_scratch_bytes']:
            raise ValueError('native scratch capacity')
        live.append((lo, lo + size))
    live.sort()
    if any(a[1] > b[0] for a, b in zip(live, live[1:])):
        raise ValueError('native scratch alias')
    return dict(counts)


def cycle_table(graphs, layouts):
    endpoints = {'admit', 'RF_read', 'RF_write_ACK', 'consume', 'retire',
                 'visibility_fence', 'HBM_read_sector', 'HBM_write_sector',
                 'forward_CDC', 'reverse_CDC', 'collective_sector', 'PACK_BF16',
                 'root_delivery', 'scalar_broadcast', 'matrix_stage', 'matrix_weight_sector',
                 'norm_collector_tail', 'norm_output_scale', 'external_stage', 'native:STAGE_OPERAND', 'owner_lookup', 'owner_held_accept', 'validated_reverse_grant'}
    for g in graphs.values():
        for o in g['operations']:
            endpoints.add('operator:' + o['opcode'])
            endpoints.update('provider:' + p for p in o['missing_native_endpoints'])
    for layout in layouts.values():
        for template in layout['selected_command_bindings']['command_templates'].values():
            endpoints.update('native:' + c['op'] for c in template)
    # These are deliberately explicit SOFTWARE estimates in abstract scheduler ticks.
    # Users may replace every value with calibrated endpoint inputs via --cycles.
    estimates = {'admit': 2, 'RF_read': 3, 'RF_write_ACK': 3, 'consume': 2,
                 'retire': 2, 'visibility_fence': 4, 'HBM_read_sector': 64,
                 'HBM_write_sector': 80, 'forward_CDC': 4, 'reverse_CDC': 4,
                 'collective_sector': 32, 'PACK_BF16': 8, 'root_delivery': 12,
                 'scalar_broadcast': 12, 'matrix_stage': 8, 'matrix_weight_sector': 64,
                 'owner_lookup': 12, 'owner_held_accept': 1, 'validated_reverse_grant': 4,
                 'norm_collector_tail': 512, 'norm_output_scale': 32, 'external_stage': 16}
    return {'schema': 'H3_EXPLICIT_ENDPOINT_CYCLES_V1', 'unit': 'abstract_software_tick',
            'calibration': 'PROVISIONAL_UNCALIBRATED', 'hardware_clock_claim': False,
            'values': {key: estimates.get(key, 32) for key in sorted(endpoints)},
            'basis': 'Explicit conservative software service estimates; provider/operator cost per 128-word tile; memory/collective per sector32; native per command; no CPU numerical oracle.'}


def validate_cycles(table, required):
    if table.get('unit') != 'abstract_software_tick' or table.get('hardware_clock_claim') is not False:
        raise ValueError('software cycle unit/clock scope')
    if table.get('calibration') not in ('PROVISIONAL_UNCALIBRATED', 'MEASURED_ENDPOINT_INPUTS'):
        raise ValueError('latency provenance missing')
    if table['calibration'] == 'MEASURED_ENDPOINT_INPUTS' and not table.get('measurement_pins'):
        raise ValueError('measured inputs require separate source pins')
    for key in required:
        positive(table.get('values', {}).get(key), key)


def version_homes(graph, layout, ranks):
    """Expand real rank groups; add finite persistent object/opaque homes explicitly."""
    homes = defaultdict(list)
    for h in layout['homes']:
        for rank in h['rank_group']:
            homes[h['version'], rank].append({k: v for k, v in h.items() if k != 'rank_group'})
    for v in graph['operands']:
        for rank in range(ranks):
            n = v['elements_per_rank'][rank]
            if not n or homes[v['id'], rank]:
                continue
            if v['bits_per_element'] == 0:
                home = {'class': 'publication', 'object': v['id'], 'bytes': 1}
            elif v['name'].startswith(('window.', 'compressed.', 'index_keys.', 'selected.')):
                home = {'class': 'persistent', 'object': v['name'],
                        'bytes': ceil(n * v['bits_per_element'], 8), 'byte_offset': 0}
            else:
                raise ValueError('unmapped version ' + v['id'])
            homes[v['id'], rank].append({'version': v['id'], 'name': v['name'], 'SM': 0,
                'birth_pc': v['birth_pc'], 'retire_pc': v['retire_pc'], 'home': home})
    return homes


def bind_provider_homes(provider, graph, fallback):
    if provider.get('schema') != 'opentallas.Qwen.provider-binding.v1':
        raise ValueError('provider binding schema')
    coverage = provider['coverage']
    if coverage['PCs'] != len(graph['operations']) or coverage['versions'] != len(graph['operands']) or coverage['unbound_versions']:
        raise ValueError('provider coverage')
    homes = defaultdict(list); refs = {}; release_at = defaultdict(list)
    versions = {v['id']: v for v in graph['operands']}
    for h in provider['version_homes']:
        if h['version'] not in versions or h['provider_ref'] in refs:
            raise ValueError('provider home/version identity')
        if h['birth_pc'] != versions[h['version']]['birth_pc'] or h['retire_pc'] != versions[h['version']]['retire_pc']:
            raise ValueError('provider lifetime mismatch')
        record = dict(h); record['name'] = versions[h['version']]['name']
        homes[h['version'], h['rank']].append(record); refs[h['provider_ref']] = h
        release_at[h['retire_pc']].append(h)
    for h in provider['control_homes']:
        if h['version'] not in versions or h['provider_ref'] in refs:
            raise ValueError('control provider identity')
        record = {'version': h['version'], 'name': versions[h['version']]['name'],
            'SM': 0, 'home': {'class': 'publication', 'object': h['version'], 'bytes': 1,
                'provider_extent': h['state_extent']}, 'provider_ref': h['provider_ref']}
        homes[h['version'], h['rank']].append(record); refs[h['provider_ref']] = h
    for key, entries in fallback.items():
        if entries and not homes[key]:
            raise ValueError('unbound provider version/rank')
    reuse = defaultdict(list); release_refs = {h['release_event']: h for h in provider['version_homes']}
    for edge in provider['reuse_dependencies']:
        if edge['new_home'] not in refs or edge['wait_release'] not in release_refs:
            raise ValueError('provider reuse dependency identity')
        new, old = refs[edge['new_home']], release_refs[edge['wait_release']]
        if old['retire_pc'] >= new['birth_pc']:
            raise ValueError('provider premature reuse')
        reuse[edge['new_home']].append(edge['wait_release'])
    operations = {}
    for p, op in zip(provider['operations'], graph['operations']):
        if p['pc'] != op['pc'] or p['opcode'] != op['opcode'] or p['source_dependencies'] != op['dependencies']:
            raise ValueError('provider PC/dependency mismatch')
        if set(p['inputs']) != set(op['reads']) or set(p['outputs']) != set(op['writes']):
            raise ValueError('provider PC operand mismatch')
        if any(ref not in refs for group in (p['inputs'], p['outputs']) for ids in group.values() for ref in ids):
            raise ValueError('unknown concrete provider reference')
        operations[p['pc']] = p
    if len(operations) != len(graph['operations']):
        raise ValueError('provider operation coverage')
    return homes, reuse, release_at, operations


def check_homes(homes, graph):
    values = {v['id']: v for v in graph['operands']}
    groups = defaultdict(list); persistent = defaultdict(list)
    for (vid, rank), entries in homes.items():
        if vid not in values:
            raise ValueError('unknown version home')
        for h in entries:
            p = h['home']; cls = p['class']
            if cls not in ('RF', 'spill', 'persistent', 'publication'):
                raise ValueError('home class')
            if cls == 'RF':
                lo, size = p['slot_first'], positive(p['vectors'], 'vectors')
                if lo < 32 or lo + size > 512:
                    raise ValueError('RF aperture/workspace capacity')
            elif cls == 'spill':
                lo, size = p['byte_offset'], positive(p['bytes'], 'spill bytes')
                if lo < 0 or lo % 512 or size % 512:
                    raise ValueError('spill alignment')
            elif cls == 'persistent':
                persistent[rank, p['object']].append((values[vid]['birth_pc'], values[vid]['retire_pc'], vid))
                continue
            else:
                continue
            groups[rank, h['SM'], cls].append((values[vid]['birth_pc'], values[vid]['retire_pc'], lo, lo + size, vid))
    for entries in groups.values():
        live = []
        for birth, retire, lo, hi, vid in sorted(entries):
            live = [x for x in live if x[0] >= birth]
            if any(lo < x[2] and x[1] < hi for x in live):
                raise ValueError('live home alias/premature write reuse ' + vid)
            live.append((retire, lo, hi, vid))
    for entries in persistent.values():
        ordered = sorted(entries)
        if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
            raise ValueError('persistent generation reused with future readers')
    return True


def extent_demands(layout):
    demands = []
    for binding in layout['spill_resident_bindings']:
        if not binding.get('fits', True):
            extent = binding['source_extent']; required = binding['required_bytes']
            demands.append({'rank_group': binding['rank_group'], 'class': 'activation_spill',
                'source_extent': extent, 'required_bytes': required,
                'additional_bytes': required - extent['bytes'], 'alignment_bytes': 512,
                'AW': binding['provider_ABI']['AW'],
                'status': 'CONSTRAINED_SUCCESSOR_EXTENT_REQUIRED',
                'constraints': ['nonalias with all checkpoint/KV/source extents',
                    'fulladdress end <= 2**AW', 'one distinct arena per rank; explicit SM subranges',
                    'all readers retired and reverse credit returned before address reuse'],
                'calendar_binding': 'logical successor arena; NOT an allocated source address'})
    return demands


class Shape:
    """Shape-only expressions. Never stores or evaluates numerical tensor data."""
    def __init__(self, shape=()):
        self.shape = tuple(int(n) for n in shape)
        if any(n < 0 for n in self.shape):
            raise ValueError('negative tensor extent')
    def __getitem__(self, key):
        keys = key if isinstance(key, tuple) else (key,)
        if Ellipsis in keys:
            missing = len(self.shape) - sum(k is not None and k is not Ellipsis for k in keys)
            keys = tuple(x for k in keys for x in ([slice(None)] * missing if k is Ellipsis else [k]))
        out = []; axis = 0
        for item in keys:
            if item is None:
                out.append(1); continue
            n = self.shape[axis]; axis += 1
            if isinstance(item, slice):
                out.append(len(range(*item.indices(n))))
            elif isinstance(item, Shape):
                out.extend(item.shape)
            elif not -n <= int(item) < n:
                raise ValueError('shape index aperture')
        return Shape(out + list(self.shape[axis:]))
    def binary(self, other):
        return Shape(broadcast(self.shape, other.shape if isinstance(other, Shape) else ()))
    __add__ = __radd__ = __sub__ = __rsub__ = __mul__ = __rmul__ = binary
    __truediv__ = __rtruediv__ = __floordiv__ = __rfloordiv__ = __mod__ = __rmod__ = binary


def broadcast(*shapes):
    result = []
    for axis in range(1, max(map(len, shapes), default=0) + 1):
        sizes = {s[-axis] for s in shapes if len(s) >= axis} - {1}
        if len(sizes) > 1:
            raise ValueError('incompatible broadcast extents')
        result.append(next(iter(sizes), 1))
    return tuple(reversed(result))


def shape_reshape(value, shape):
    shape = list(shape); size = math.prod(value.shape)
    if shape.count(-1) > 1:
        raise ValueError('reshape inferred dimension')
    if -1 in shape:
        known = math.prod(n for n in shape if n != -1)
        if not known or size % known:
            raise ValueError('reshape extent')
        shape[shape.index(-1)] = size // known
    if math.prod(shape) != size:
        raise ValueError('reshape element count')
    return Shape(shape)


def shape_concat(values, axis=0):
    shapes = [as_shape(v).shape for v in values]; out = list(shapes[0]); axis %= len(out)
    for shape in shapes[1:]:
        if len(shape) != len(out) or any(a != b for i, (a, b) in enumerate(zip(out, shape)) if i != axis):
            raise ValueError('concat extent')
        out[axis] += shape[axis]
    return Shape(out)


def as_shape(value):
    if isinstance(value, Shape):
        return value
    if isinstance(value, (tuple, list)):
        return Shape((len(value),))
    return Shape()


def shape_expression(expr, env):
    expr = re.sub(r'np\.float64\(([-+0-9.eE]+)\)', r'\1', str(expr))
    tree = ast.parse(expr, mode='eval')
    allowed = (ast.Expression, ast.Name, ast.Load, ast.Constant, ast.Tuple, ast.List,
        ast.Subscript, ast.Slice, ast.Attribute, ast.Call, ast.BinOp, ast.UnaryOp,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.USub)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError('non-shape expression ' + expr)
        if isinstance(node, ast.Attribute) and node.attr != 'shape':
            raise ValueError('shape expression attribute')
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in
                ('reshape', 'transpose', 'concat', 'zeros', 'arange', 'f32', 'int', 'min', 'max')):
            raise ValueError('non-shape call: ' + expr)
    helpers = {'reshape': shape_reshape,
        'transpose': lambda v: Shape(tuple(reversed(v.shape))), 'concat': shape_concat,
        'zeros': lambda s: Shape(s), 'arange': lambda n: Shape((n,)),
        'f32': lambda n: Shape(), 'int': lambda n: n if isinstance(n, int) else Shape(),
        'min': min, 'max': max}
    return eval(compile(tree, '<shape-only-native-index>', 'eval'), {'__builtins__': {}, **helpers}, env)


def normalize_bundle(data):
    if data.get('schema') == 'opentallas.H3.qwen-complete-native-software.v1':
        return {**data, 'target': 'Qwen'}
    if data.get('schema') == 'H3_DEEPSEEK_COMPLETE_NATIVE_V1':
        operations = []
        for op in data['instructions']:
            groups = defaultdict(list)
            for binding in op['rank_bindings']:
                if not binding.get('empty_owned_extent'):
                    groups[binding['template']].append(binding['rank'])
            programs = [{'rank_group': ranks, 'instructions': data['templates'][key]['code'],
                'providers': op['provider_bindings'][key], 'outputs': data['templates'][key]['outputs'],
                'source_template': key, 'resources': data['templates'][key]['resources']}
                for key, ranks in groups.items()]
            operations.append({**op, 'opcode': op['family'], 'programs': programs,
                'reads': [v['version'] for v in op['reads']], 'writes': [v['version'] for v in op['writes']]})
        return {**data, 'target': 'DeepSeek', 'operations': operations}
    return data


def bundle_primitives(data):
    if data.get('schema') == 'H3_ORDERED_NATIVE_LOWERING_V1':
        return {step['op'] for op in data['operations'] for step in op['steps']}
    result = set()
    def walk(nodes):
        for node in nodes:
            result.add(node['op'])
            walk(node.get('body', [])); walk(node.get('exact_template', []))
    for op in data['operations']:
        if 'recipe' in op:
            walk(op['recipe'])
        else:
            for program in op.get('programs', []):
                walk(program['instructions'])
    return result


def validate_bundle(native, graph):
    if len(native['operations']) != len(graph['operations']):
        raise ValueError('native bundle PC coverage')
    for plan, op in zip(native['operations'], graph['operations']):
        if plan['pc'] != op['pc'] or plan.get('opcode', plan.get('family')) != op['opcode']:
            raise ValueError('native bundle PC identity')
        if plan['reads'] != op['reads'] or plan['writes'] != op['writes']:
            raise ValueError('native bundle version mismatch')
        if 'recipe' not in plan and 'programs' not in plan:
            raise ValueError('native bundle instructions missing')


def bind_recipe(native, plan, macro, rank, table):
    """Instruction-dependent ordered nested calendar; loops remain lossless RLE.

    Every primitive serially consumes at most two RF read ports, one write port,
    one finite sector credit and one of 32 lane engines. Source temporaries use
    a finite double-buffered logical scratch arena, sized by this binding. It is
    a constrained successor allocation if the existing scratch extent is short.
    """
    costs = table['values']; env = {}; buffers = {}; stats = Counter(); serial = [0]
    source = native.get('source_program', {})
    version_shapes = {v['version']: v['shape'] for v in native.get('operands', []) if 'version' in v and 'shape' in v}
    version_names = {v['version']: v.get('name', '') for v in native.get('operands', []) if 'version' in v}
    context = source.get('context_capacity', 8192)
    env['position'] = context - 1
    for i, vid in enumerate(macro['reads']):
        shape = version_shapes.get(vid)
        if shape is not None:
            env[f'input{i}'] = Shape([context if n == 'position+1' else n for n in shape])
            if version_names.get(vid) == 'position':
                env[f'input{i}'] = context - 1
            if macro['opcode'] == 'ARGMAX_REDUCE':
                env[f'input{i}'] = Shape((2,))
    def register(name, shape):
        if name:
            name = name.split('[')[0]
            size = max(8, 8 * math.prod(shape))
            buffers[name] = max(buffers.get(name, 0), ceil(size, 512) * 512)
    for key, val in env.items():
        if isinstance(val, Shape):
            register(key, val.shape)
    def primitive(node, local_env, path):
        op = node['op']; src = node.get('src', []); dst = node.get('dst')
        rounding = node.get('round_point', node.get('rounding'))
        if not rounding:
            rounding = 'FP32_RNE_then_positive_zero' if op in ('FADD', 'FMUL') else 'explicit native instruction contract'
        if any(k in node for k in ('callback', 'handler', 'golden_callback')):
            raise ValueError('native callback forbidden')
        args = [shape_expression(x, local_env) for x in src]
        if 'shape' in node:
            result = Shape(node['shape'])
        elif op == 'LOAD_WEIGHT':
            d = source['weight_descriptors'][node['key']]; result = Shape((d['rows'], d['K']))
        elif op == 'LOAD_EMBED_CODES':
            result = Shape((source['config']['hidden_size'],))
        elif op == 'LOAD_EMBED_SCALE':
            result = Shape()
        elif op == 'LOAD_GAMMA':
            result = Shape((source['config']['head_dim'] if node.get('kind') != 'final' else source['config']['hidden_size'],))
        elif op in ('LOAD_ROPE_COS', 'LOAD_ROPE_SIN'):
            result = Shape((source['config']['head_dim'] // 2,))
        elif op == 'LOAD_SCALE':
            d = source['weight_descriptors'][node['key']]; result = Shape((d['rows'],))
        elif op == 'READ_BYTES':
            result = as_shape(args[-1])
        elif op in ('BEGIN_WRITE', 'ACQUIRE', 'BIND_LEASE', 'COMMIT_PUBLISH', 'CONSUMER_DONE'):
            result = Shape()
        else:
            result = Shape(broadcast(*(as_shape(a).shape for a in args))) if args else Shape()
        if op == 'MOV' and args:
            result = as_shape(args[0])
        name = dst.split('[')[0] if dst else None
        if name:
            if '[' in dst:
                # Destination scatter is a costed materialization under its full lease.
                if name not in local_env:
                    raise ValueError('scatter destination uninitialized')
                register(name, as_shape(local_env[name]).shape)
            else:
                if op != 'STAGE_OPERAND' or not isinstance(local_env.get(name), int):
                    local_env[name] = result
                register(name, result.shape)
        batches = max(1, ceil(math.prod(result.shape), 128))
        read_batches = sum(max(1, ceil(math.prod(as_shape(a).shape) * 8, 512)) for a in args)
        write_batches = max(1, ceil(math.prod(result.shape) * 8, 512)) if dst else 1
        # A source recipe may have three-input SELECT or CONCAT. Decompose RF
        # operand reads into serial pairs, retaining values in the finite arena.
        operand_pairs = max(1, ceil(len(args), 2))
        stages = {'admit': costs['admit'], 'RF_read': costs['RF_read'] * max(read_batches, operand_pairs),
            'execute': costs['native:' + op] * batches,
            'RF_write_ACK': costs['RF_write_ACK'] * write_batches,
            'consume': costs['consume'], 'retire': costs['retire']}
        # All temporaries are explicitly scratch-backed. No invisible limitless RF.
        sectors = 16 * (read_batches + write_batches)
        ownership = 2 * (costs['owner_lookup'] + costs['owner_held_accept'])
        read_sectors, write_sectors = 16 * read_batches, 16 * write_batches
        stages['scratch_read'] = max(1, read_sectors) * (costs['HBM_read_sector'] + ownership +
            costs['forward_CDC'] + costs['consume'] + costs['reverse_CDC'] + costs['validated_reverse_grant'] + costs['retire'])
        stages['scratch_write'] = write_sectors * (costs['HBM_write_sector'] + ownership +
            costs['visibility_fence'] + costs['forward_CDC'] + costs['consume'] + costs['reverse_CDC'] +
            costs['validated_reverse_grant'] + costs['retire'])
        if op.startswith('LOAD') or op in ('WRITE_BYTES', 'READ_BYTES', 'PACKET_COMMIT'):
            stages['provider_visibility'] = max(1, ceil(math.prod(result.shape) * 8, 32)) * (
                costs['HBM_write_sector' if op in ('WRITE_BYTES', 'PACKET_COMMIT') else 'HBM_read_sector'] +
                costs['visibility_fence'] + ownership + costs['validated_reverse_grant'])
        index = serial[0]; serial[0] += 1; stats[op] += batches
        return {'kind': 'primitive', 'index': index, 'op': op, 'source_instruction': node,
            'rounding': rounding, 'shape': list(result.shape), 'batches128': batches, 'scratch_element_bytes': 8,
            'RF_read_batches': read_batches, 'RF_write_batches': write_batches,
            'operand_pair_reads': operand_pairs, 'storage_sectors32': sectors, 'scratch_read_sectors32': read_sectors, 'scratch_write_sectors32': write_sectors,
            'owner_lookup_edges_per_sector': 2 * costs['owner_lookup'],
            'owner_accept_edges_per_sector': 2 * costs['owner_held_accept'],
            'validated_reverse_grant_cycles': costs['validated_reverse_grant'],
            'stage_cycles': stages, 'duration': sum(stages.values()),
            'version_identity': ['event.target', 'event.pc', 'event.rank', path, index, 'loop_iteration_tuple'],
            'read_symbols': src, 'write_symbol': dst,
            'storage_credit': {'sector_credit': 1, 'read_ports': 2, 'write_ports': 1,
                               'lanes': 128, 'double_buffer_versions': 2}}
    def walk(nodes, local_env, path=()):
        out = []; offset = 0
        for i, node in enumerate(nodes):
            if node['op'] in ('FOR', 'SUM_TEMPLATE'):
                if node['op'] == 'FOR':
                    start = shape_expression(node['start'], local_env); stop = shape_expression(node['stop'], local_env)
                    step = shape_expression(node['step'], local_env); count = len(range(start, stop, step))
                    local_env[node['var']] = start; body = node['body']
                else:
                    start = 0; step = 1; count = 1; body = node['exact_template']
                if count == 0:
                    record = {'kind': 'loop', 'count': 0, 'body': [], 'duration': costs['admit'],
                              'explicit_empty_loop_control_cycles': costs['admit']}
                else:
                    children, duration = walk(body, local_env, path + (i,))
                    record = {'kind': 'loop', 'count': count, 'iteration_start': start, 'iteration_step': step,
                        'iteration_stride': duration, 'body': children, 'duration': duration * count + costs['admit'],
                        'control_cycles': costs['admit'], 'ordering': 'iteration-major exact body order'}
                    if node['op'] == 'FOR':
                        local_env[node['var']] = start + step * (count - 1)
            else:
                record = primitive(node, local_env, path + (i,))
            record['offset'] = offset; offset += record['duration']; out.append(record)
        return out, offset
    if 'recipe' in plan:
        nodes = plan['recipe']
    else:
        programs = plan['programs']; program = next((p for p in programs if rank in p['rank_group']), None)
        if program is None:
            return {'schema': 'H3_ORDERED_PRIMITIVE_CALENDAR_V1', 'duration': costs['admit'],
                'primitive_tree': [], 'finite_scratch_bytes': 0, 'scratch_homes': {},
                'empty_owned_extent_control_cycles': costs['admit'], 'no_tensor_value_evaluation': True}
        nodes = program['instructions']
        definitions = set()
        for node in nodes:
            if any(v not in definitions for v in node['src']):
                raise ValueError('Peirce SSA premature consume')
            if node['dst'] in definitions:
                raise ValueError('Peirce SSA duplicate write')
            definitions.add(node['dst'])
        for node in nodes:
            # DS instructions use SSA symbol references, not expression callbacks.
            if node['op'] == 'LOAD':
                env[node['dst']] = Shape(node['shape'])
    prefix = [{'op': 'STAGE_OPERAND', 'dst': name, 'src': [name],
        'round_point': 'bit-exact source version movement; no arithmetic',
        'version': macro['reads'][int(name[5:])], 'source': 'macro RF/persistent read landing'}
        for name in list(env) if name.startswith('input') and name[5:].isdigit()]
    tree, duration = walk(prefix + nodes, env)
    arena = {}; cursor = 0
    for name, size in sorted(buffers.items()):
        arena[name] = {'byte_offset': cursor, 'buffer_bytes': size, 'buffers': 2,
                       'version_buffer': 'iteration-local producer parity; read old parity before mirrored ACK switch'}
        cursor += 2 * size
    return {'schema': 'H3_ORDERED_PRIMITIVE_CALENDAR_V1', 'duration': duration,
        'primitive_tree': tree, 'finite_scratch_bytes': cursor, 'scratch_homes': arena,
        'source_arithmetic': macro['golden_contract'], 'source_recipe_sha256': hashlib.sha256(encode(nodes)).hexdigest(),
        'provider_refs': native.get('provider_requirements', 'Peirce LOAD/provider program descriptors'),
        'storage_scope': 'finite logical successor arena per rank; does not alias source scratch',
        'scratch_layout': '8 bytes per logical element: F32/U32 lowword plus explicit padded highword; I64 retains both32bit words. Two RF staging vectors per128 logical values; no I64 truncation.',
        'no_tensor_value_evaluation': True}


def validate_native_lowering(native, graph, homes, ranks):
    """Worker interchange: every PC and concrete ordered two-source native steps.

    Each step has rank, SM, op, repeats, reads=[{version,slot}],
    writes=[{version,slot}], rounding, provider_refs, and source_arithmetic.
    Macro inputs initialize their concrete slots. Constants need explicit
    provider descriptors, which create costed staging steps. Local versions may
    reuse a slot only after their last listed read. No callback is executable.
    """
    if native.get('schema') != 'H3_ORDERED_NATIVE_LOWERING_V1':
        raise ValueError('native lowering schema')
    operations = native.get('operations', [])
    if len(operations) != len(graph['operations']):
        raise ValueError('native lowering must cover every PC')
    plans = {}
    for plan, macro in zip(operations, graph['operations']):
        if plan.get('pc') != macro['pc'] or plan.get('opcode') != macro['opcode']:
            raise ValueError('native PC identity/order')
        if plan.get('operand_versions') != {'reads': macro['reads'], 'writes': macro['writes']}:
            raise ValueError('native operand version mismatch')
        if not plan.get('source_arithmetic') or not plan.get('rounding') or not plan.get('provider_refs'):
            raise ValueError('native arithmetic/provider contract missing')
        steps = plan.get('steps', [])
        if not steps:
            raise ValueError('native steps missing')
        state = {}; last = {}; definitions = set()
        for i, step in enumerate(steps):
            for ref in step.get('reads', []):
                last[step['rank'], step['SM'], ref['version']] = i
        for rank in macro['participants']:
            for vid in macro['reads']:
                for h in homes[vid, rank]:
                    if h['home']['class'] == 'RF':
                        p = h['home']
                        for slot in range(p['slot_first'], p['slot_first'] + p['vectors']):
                            state[rank, h['SM'], slot] = vid
        for i, step in enumerate(steps):
            rank, sm = step['rank'], step['SM']
            if rank not in macro['participants'] or not 0 <= sm < 32:
                raise ValueError('native step owner')
            if not step.get('op') or any(k in step for k in ('callback', 'golden', 'handler')):
                raise ValueError('native callback/opcode forbidden')
            positive(step['repeats'], 'native repeats')
            if not step.get('rounding') or not step.get('provider_refs') or not step.get('source_arithmetic'):
                raise ValueError('native step provenance')
            if len(step['reads']) > 2 or len(step['writes']) > 1:
                raise ValueError('native two-source port capacity')
            for ref in step['reads'] + step['writes']:
                if type(ref['slot']) is not int or not 0 <= ref['slot'] < 512:
                    raise ValueError('native slot aperture')
            for ref in step['reads']:
                key = rank, sm, ref['slot']
                if state.get(key) != ref['version']:
                    raise ValueError('native stale/unpublished input')
            for ref in step['writes']:
                key = rank, sm, ref['slot']; old = state.get(key)
                if old is not None and last.get((rank, sm, old), -1) > i:
                    raise ValueError('native premature write reuse')
                ident = rank, sm, ref['version']
                if ident in definitions:
                    raise ValueError('native duplicate version')
                definitions.add(ident); state[key] = ref['version']
        plans[plan['pc']] = plan
    return plans


def compile_target(target, graph, layout, table, native=None, providers=None):
    ranks = 2 if target == 'Qwen' else 96
    homes = version_homes(graph, layout, ranks); check_homes(homes, graph)
    values = {v['id']: v for v in graph['operands']}
    reuse = defaultdict(list); release_at = defaultdict(list); provider_ops = {}
    if providers:
        homes, reuse, release_at, provider_ops = bind_provider_homes(providers, graph, homes)
        check_homes(homes, graph)
    bundled = native and native.get('schema') != 'H3_ORDERED_NATIVE_LOWERING_V1'
    native_plans = ({o['pc']: o for o in native['operations']} if bundled else
                    validate_native_lowering(native, graph, homes, ranks) if native else {})
    if bundled:
        validate_bundle(native, graph)
    selected = {b['pc']: b for b in layout['selected_command_bindings']['bindings']}
    caps = {'global.collective': 1}
    for r in range(ranks):
        caps.update({f'r{r}.{k}': n for k, n in [('issue', 1), ('collective', 1), ('HBM', 1),
            ('sector_credit', 4), ('ACK_capture', 4), ('forward_CDC', 4), ('reverse_CDC', 4),
            ('RMW_lock', 4), ('opcode_context', 4), ('owner_lookup', 1), ('owner_context', 4)]})
        for sm in range(32):
            caps.update({f'r{r}.s{sm}.{k}': n for k, n in [('RF', 1), ('read_port', 2),
                ('write_port', 1), ('execute', 1), ('packing_queue', 2), ('root_FIFO', 2),
                ('shared_workspace', 1)]})
    scratch_peaks = Counter(); primitive_counts = Counter(); programs = {}; recipe_cache = {}
    cal = Calendar(caps); cost = table['values']; pcs = []; visible = {}; last_reader = {}; terminal = {}; last_pc = None
    persistent_owner = {}

    def stage(name, deps, endpoint, resources, units=1, **attrs):
        units = positive(units, name + '.units')
        return cal.add(name, list(dict.fromkeys(deps)), cost[endpoint] * units, resources,
                       endpoint=endpoint, repeats=units, stride=cost[endpoint], **attrs)

    def transfer(name, deps, h, rank, write):
        p = h['home']; sm = h['SM']; rr = f'r{rank}'; ss = rr + f'.s{sm}'
        if write and providers:
            deps = list(deps) + reuse.get(h.get('provider_ref'), [])
            if any(d not in cal.ends for d in deps):
                raise ValueError('provider home reuse before release')
        if p['class'] == 'RF':
            resources = {ss + '.RF': 1, ss + ('.write_port' if write else '.read_port'): 1}
            endpoint = 'RF_write_ACK' if write else 'RF_read'; units = p['vectors']
        elif p['class'] in ('spill', 'persistent'):
            resources = {rr + '.HBM': 1, rr + '.sector_credit': 1, rr + '.forward_CDC': 1,
                         rr + '.ACK_capture': 1, rr + '.RMW_lock': 1, rr + '.reverse_CDC': 1,
                         rr + '.owner_lookup': 1, rr + '.owner_context': 1}
            endpoint = 'HBM_write_sector' if write else 'HBM_read_sector'; units = ceil(p['bytes'], 32)
        else:
            resources = {rr + '.opcode_context': 1}; endpoint = 'consume'; units = 1
        event = stage(name, deps, endpoint, resources, units, version=h['version'], rank=rank,
                      SM=sm, home=p, provider_ref=h.get('provider_ref'),
                      request_identity={'version': h['version'], 'rank': rank, 'SM': sm, 'serial': name,
                          'repeat_sector_ordinal': 'repeat_index', 'epoch': 'token_session',
                          'quarantine': 'compound consumer+reverse+validated grant retirement'},
                      direction='write' if write else 'read')
        # HBM transport slots above stay owned across the full compound sequence.
        # Repeat stride explicitly includes backing visibility, consumer completion
        # and reverse CDC. It never purports to be an actual DUT completion event.
        if p['class'] in ('spill', 'persistent'):
            e = cal.events[-1]
            owner_cycles = 2 * (cost['owner_lookup'] + cost['owner_held_accept'])
            extra = owner_cycles + sum(cost[k] for k in ('forward_CDC', 'consume', 'reverse_CDC', 'validated_reverse_grant', 'retire'))
            if write:
                extra += cost['visibility_fence']
            e['stride'] += extra; e['end'] += extra * units
            e['phases_per_repeat'] = {'service': cost[endpoint], 'forward_CDC': cost['forward_CDC'],
                'consume': cost['consume'], 'reverse_CDC': cost['reverse_CDC'], 'retire': cost['retire'],
                'owner_lookup': 2 * cost['owner_lookup'], 'owner_held_accept': 2 * cost['owner_held_accept'],
                'validated_reverse_grant': cost['validated_reverse_grant']}
            if write:
                e['phases_per_repeat']['backing_visibility_fence'] = cost['visibility_fence']
            cal.ends[event] = e['end']
            for key, slots in e['resources'].items():
                for slot in slots:
                    cal.slots[key][slot] = e['end']
        return event

    # External values are scheduled provider inputs, never magically visible.
    for v in graph['operands']:
        if not v['external_source']:
            continue
        for rank in range(ranks):
            entries = homes[v['id'], rank]
            if not entries:
                continue
            prev = stage(f'input.{v["id"]}.r{rank}', [], 'external_stage', {f'r{rank}.issue': 1}, version=v['id'])
            ends = [transfer(f'{prev}.h{i}', [prev], h, rank, True) for i, h in enumerate(entries)]
            visible[v['id'], rank] = stage(prev + '.visible', ends, 'visibility_fence', {f'r{rank}.issue': 1})
            for h in entries:
                if h['home']['class'] == 'persistent':
                    persistent_owner[rank, h['home']['object']] = visible[v['id'], rank]

    # Source ordering is retained: macro dependencies include previous-PC retire.
    # Independent SM chains inside each macro overlap only on disjoint resources.
    for op in graph['operations']:
        pc = op['pc']; prefix = f'pc{pc}'; participants = op['participants']
        if not participants or len(participants) != len(set(participants)) or any(r not in range(ranks) for r in participants):
            raise ValueError('participant/rendezvous identity')
        deps = []
        for dep in op['dependencies']:
            if dep not in terminal:
                raise ValueError('PC dependency deadlock')
            deps.append(terminal[dep])
        if last_pc:
            deps.append(last_pc)
        admitted = stage(prefix + '.admit', deps, 'admit', {f'r{r}.issue': 1 for r in participants}, pc=pc)
        reads = []; read_by_rank = defaultdict(list)
        for vid in op['reads']:
            if vid not in values:
                raise ValueError('unknown read version')
            for rank in participants:
                for i, h in enumerate(homes[vid, rank]):
                    if (vid, rank) not in visible:
                        raise ValueError('unpublished/premature read ' + vid)
                    e = transfer(f'{prefix}.read.{vid}.r{rank}.h{i}', [admitted, visible[vid, rank]], h, rank, False)
                    reads.append(e); read_by_rank[rank].append(e); last_reader[vid, rank] = e
        collective = op['opcode'] in ('ALL_REDUCE', 'ARGMAX_REDUCE', 'all_gather', 'all_reduce', 'topk_merge', 'kv_gather')
        executions = []; collective_ready = admitted
        if collective and pc in native_plans:
            resources = {'global.collective': 1, **{f'r{r}.collective': 1 for r in participants}}
            collective_ready = stage(prefix + '.collective_admit', reads + [admitted], 'collective_sector',
                resources, max(1, ceil(sum(ceil(values[v]['elements_per_rank'][r] * values[v]['bits_per_element'], 8)
                    for v in op['reads'] for r in participants), 32)),
                atomic_rendezvous=True, participants=participants, phase='ordered source delivery before native consumption',
                golden_contract=op['golden_contract'])
        if pc in native_plans and bundled:
            for rank in participants:
                plan = native_plans[pc]
                if 'programs' in plan:
                    template = next((p for p in plan['programs'] if rank in p['rank_group']), None)
                    cache_key = template['source_template'] if template else 'empty_extent'
                else:
                    cache_key = f'Qwen.pc{pc}'
                if cache_key not in recipe_cache:
                    recipe = bind_recipe(native, plan, op, rank, table)
                    counts = verify_native_program(recipe)
                    key = hashlib.sha256(cache_key.encode()).hexdigest()[:24]
                    programs[key] = recipe
                    recipe_cache[cache_key] = key, counts
                key, counts = recipe_cache[cache_key]; recipe = programs[key]
                primitive_counts.update(counts)
                scratch_peaks[rank] = max(scratch_peaks[rank], recipe['finite_scratch_bytes'])
                rr = f'r{rank}'
                resources = {rr + '.HBM': 1, rr + '.sector_credit': 1, rr + '.ACK_capture': 1,
                    rr + '.forward_CDC': 1, rr + '.reverse_CDC': 1, rr + '.opcode_context': 1,
                    rr + '.owner_lookup': 1, rr + '.owner_context': 1}
                for sm in range(32):
                    resources.update({rr + f'.s{sm}.RF': 1, rr + f'.s{sm}.execute': 1,
                        rr + f'.s{sm}.read_port': 2, rr + f'.s{sm}.write_port': 1,
                        rr + f'.s{sm}.shared_workspace': 1})
                executions.append(cal.add(f'{prefix}.r{rank}.native_recipe',
                    list(dict.fromkeys(read_by_rank[rank] + [collective_ready])), recipe['duration'], resources,
                    native_program_ref=key, native_source_PC=pc, pc=pc, rank=rank,
                    operand_versions={'reads': op['reads'], 'writes': op['writes']},
                    concrete_provider_operation=provider_ops.get(pc),
                    policy='exclusive finite rank lease; ordered primitive calendar below; no internal ideal overlap'))
        elif pc in native_plans:
            plan = native_plans[pc]; chains = {}
            for index, step in enumerate(plan['steps']):
                rank, sm = step['rank'], step['SM']; ss = f'r{rank}.s{sm}'
                previous = [chains[rank, sm]] if (rank, sm) in chains else read_by_rank[rank] + [collective_ready]
                stem = f'{prefix}.native{index}'
                issued = stage(stem + '.issue', previous, 'admit', {ss + '.execute': 1}, native_step=step)
                read = stage(stem + '.consume', [issued], 'RF_read', {ss + '.RF': 1, ss + '.read_port': max(1, len(step['reads']))}, step['repeats'])
                execute = stage(stem + '.execute', [read], 'native:' + step['op'], {ss + '.execute': 1}, step['repeats'])
                write = stage(stem + '.commit', [execute], 'RF_write_ACK', {ss + '.RF': 1, ss + '.write_port': 1}, step['repeats'])
                chains[rank, sm] = stage(stem + '.retire', [write], 'retire', {ss + '.execute': 1})
            executions.extend(chains.values())
        elif pc in selected:
            b = selected[pc]; templates = layout['selected_command_bindings']['command_templates']; roots = defaultdict(list)
            for binding in b['participant_commands']:
                for rank in binding['rank_group']:
                    if rank not in participants:
                        raise ValueError('native participant outside macro')
                    sm = binding['SM']; ss = f'r{rank}.s{sm}'; previous = list(read_by_rank[rank]) + [admitted]
                    previous = [stage(f'{prefix}.r{rank}.s{sm}.constants', previous, 'external_stage',
                        {ss + '.RF': 1, ss + '.write_port': 1},
                        max(1, len(binding['coefficient_constant_provider_preconditions'])),
                        provider_preconditions=binding['coefficient_constant_provider_preconditions'])]
                    template = templates[binding['command_template']]
                    for command in template:
                        ci = command['command_index']; stem = f'{prefix}.r{rank}.s{sm}.cmd{ci}'
                        issued = stage(stem + '.issue', previous, 'admit', {ss + '.execute': 1}, command=command)
                        consumed = stage(stem + '.consume', [issued], 'RF_read', {ss + '.RF': 1, ss + '.read_port': 2})
                        ran = stage(stem + '.execute', [consumed], 'native:' + command['op'], {ss + '.execute': 1})
                        committed = stage(stem + '.commit', [ran], 'RF_write_ACK', {ss + '.RF': 1, ss + '.write_port': 1})
                        previous = [stage(stem + '.retire', [committed], 'retire', {ss + '.execute': 1})]
                    roots[rank].append(stage(f'{prefix}.r{rank}.s{sm}.root', previous, 'root_delivery',
                        {ss + '.root_FIFO': 1, f'r{rank}.s0.RF': 1, f'r{rank}.s0.write_port': 1},
                        source_RF_slot=binding['root_RF_slot'], root_version=binding['root_version'],
                        collector_lane=sm, closed_delivery_fence=True))
            for rank in participants:
                if not roots[rank]:
                    raise ValueError('missing root participant')
                tail = stage(f'{prefix}.r{rank}.collector', roots[rank], 'norm_collector_tail',
                    {f'r{rank}.s0.RF': 1, f'r{rank}.s0.execute': 1},
                    golden_contract=op['golden_contract'], root_order=sorted(x['SM'] for x in b['participant_commands'] if rank in x['rank_group']))
                for sm in sorted({h['SM'] for vid in op['writes'] for h in homes[vid, rank]}):
                    delivered = stage(f'{prefix}.r{rank}.s{sm}.scalar', [tail], 'scalar_broadcast',
                        {f'r{rank}.s{sm}.root_FIFO': 1, f'r{rank}.s{sm}.RF': 1})
                    executions.append(stage(f'{prefix}.r{rank}.s{sm}.scale', [delivered], 'norm_output_scale',
                        {f'r{rank}.s{sm}.execute': 1}))
        elif collective:
            resources = {'global.collective': 1}
            resources.update({f'r{r}.collective': 1 for r in participants})
            bytes_ = sum(ceil(values[v]['elements_per_rank'][r] * values[v]['bits_per_element'], 8)
                         for v in op['reads'] for r in participants)
            executions.append(stage(prefix + '.rendezvous', reads + [admitted], 'collective_sector',
                resources, max(1, ceil(bytes_, 32)), participants=participants,
                atomic_rendezvous=True, golden_contract=op['golden_contract'],
                ordered_source_ranks=participants, payload_bytes=bytes_))
        else:
            for rank in participants:
                previous = list(read_by_rank[rank]) + [admitted]
                units = max(1, ceil(max(sum(values[v]['elements_per_rank'][rank] for v in op['reads']),
                                       sum(values[v]['elements_per_rank'][rank] for v in op['writes'])), 128))
                for index, endpoint in enumerate(op['missing_native_endpoints']):
                    is_memory = any(s in endpoint.lower() for s in ('hbm', 'provider', 'packed', 'fetch', 'visible'))
                    resources = {f'r{rank}.opcode_context': 1,
                                 f'r{rank}.HBM' if is_memory else f'r{rank}.s0.execute': 1}
                    previous = [stage(f'{prefix}.r{rank}.provider{index}', previous, 'provider:' + endpoint,
                        resources, units, golden_contract=op['golden_contract'],
                        source_binding=op.get('external_bindings', op['source']))]
                executions.append(stage(f'{prefix}.r{rank}.execute', previous, 'operator:' + op['opcode'],
                    {f'r{rank}.s0.execute': 1, f'r{rank}.opcode_context': 1}, units,
                    source_operation=op['source'], golden_contract=op['golden_contract'],
                    implementation='parameterized software endpoint; numerical execution separate'))
        if collective and pc in native_plans:
            resources = {'global.collective': 1, **{f'r{r}.collective': 1 for r in participants}}
            executions = [stage(prefix + '.rendezvous', executions + reads + [admitted],
                'collective_sector', resources, max(1, ceil(sum(
                    ceil(values[v]['elements_per_rank'][r] * values[v]['bits_per_element'], 8)
                    for v in op['reads'] for r in participants), 32)),
                atomic_rendezvous=True, participants=participants, golden_contract=op['golden_contract'])]
        consumed = stage(prefix + '.consume', executions + reads + [admitted], 'consume',
                         {f'r{r}.issue': 1 for r in participants}, pc=pc)
        commits = []
        for vid in op['writes']:
            if vid not in values or values[vid]['birth_pc'] != pc:
                raise ValueError('wrong write version producer')
            for rank in range(ranks):
                entries = homes[vid, rank]
                destination_admit = consumed
                if entries and rank not in participants:
                    destination_admit = stage(f'{prefix}.delivery.r{rank}.{vid}', [consumed], 'admit', {f'r{rank}.issue': 1},
                        source_ranks=participants, destination_rank=rank)
                for i, h in enumerate(entries):
                    p = h['home']; extra = []
                    if p['class'] == 'persistent' and (rank, p['object']) in persistent_owner:
                        extra.append(persistent_owner[rank, p['object']])
                    # RF/spill reuse obeys inclusive static lifetime check and previous
                    # macro retirement; old consumer and reverse credits have drained.
                    event = transfer(f'{prefix}.write.{vid}.r{rank}.h{i}', [destination_admit] + extra, h, rank, True)
                    commits.append(event)
                if entries:
                    fence = stage(f'{prefix}.visible.{vid}.r{rank}', commits[-len(entries):],
                        'visibility_fence', {f'r{rank}.issue': 1}, version=vid, rank=rank)
                    visible[vid, rank] = fence; commits.append(fence)
                    for h in entries:
                        if h['home']['class'] == 'persistent':
                            persistent_owner[rank, h['home']['object']] = fence
        last_pc = stage(prefix + '.retire', commits + [consumed], 'retire',
                        {f'r{r}.issue': 1 for r in participants}, pc=pc)
        terminal[pc] = last_pc
        for h in release_at.get(pc, []):
            stage(h['release_event'], [last_pc, visible[h['version'], h['rank']]], 'validated_reverse_grant',
                {f'r{h["rank"]}.issue': 1}, provider_ref=h['provider_ref'],
                requires=h['release_requires'], source_consumers=h['consumers'])
        pcs.append({'pc': pc, 'opcode': op['opcode'], 'participants': participants,
                    'admit': admitted, 'consume': consumed, 'commit_fences':
                    [e for e in commits if '.visible.' in e], 'retire': last_pc,
                    'read_versions': op['reads'], 'write_versions': op['writes'],
                    'native_commands': pc in selected or pc in native_plans, 'atomic_collective': collective})
    proof = verify_calendar(cal.events, caps)
    for e in cal.events:
        if 'native_program_ref' in e and e['end'] - e['start'] != programs[e['native_program_ref']]['duration']:
            raise ValueError('native enclosing reservation duration')
    demands = [] if providers else extent_demands(layout)
    for rank, size in sorted(scratch_peaks.items()):
        if size:
            demands.append({'rank_group': [rank], 'class': 'native_temporary_scratch',
                'required_bytes': size, 'alignment_bytes': 512, 'additional_bytes': size,
                'required_minimum_AW': max(1, (size - 1).bit_length()),
                'source_provider_AW': 34 if target == 'Qwen' else 27,
                'source_provider_address_width_fits': size <= 2**(34 if target == 'Qwen' else 27),
                'status': 'CONSTRAINED_SUCCESSOR_EXTENT_REQUIRED',
                'constraints': ['distinct from all version spill, checkpoint and persistent extents',
                    'capacity >= maximum bound recipe arena; no modulo alias',
                    'primitive consumes old double buffer before ACK switches generation'],
                'calendar_binding': 'finite logical arena; resident physical base needs provider binding'})
    persistent_caps = {}
    for (vid, rank), entries in homes.items():
        for h in entries:
            if h['home']['class'] == 'persistent':
                key = f'r{rank}:' + h['home']['object']
                persistent_caps[key] = max(persistent_caps.get(key, 0), h['home']['bytes'])
    return {'schema': 'H3_COMPLETE_NATIVE_SOFTWARE_CALENDAR_V1', 'target': target,
        'status': ('PASS_COMPLETE_NATIVE_SOFTWARE_CALENDAR' if len(native_plans) == len(pcs) else
                   'PASS_MACRO_RESERVATION_INTERMEDIATE'), 'PC_count': len(pcs), 'PCs': pcs,
        'native_lowering_PC_count': len(native_plans),
        'native_operator_lowering_complete': len(native_plans) == len(pcs),
        'ordinary_native_lowering_gap_PCs': [p['pc'] for p in pcs if p['pc'] not in native_plans and not p['native_commands']],
        'events': cal.events, 'resources': caps, 'proof': proof,
        'native_primitive_batch_counts': dict(sorted(primitive_counts.items())),
        'native_programs': programs,
        'version_home_archive': ('Qwen_provider_binding.json.gz' if providers else DISTRIBUTED + '/' + target + '.json.gz'),
        'provider_binding_coverage': providers['coverage'] if providers else None,
        'provider_resource_contract': providers['resource_contract'] if providers else None,
        'cycles': cal.ends[last_pc], 'cycle_unit': table['unit'],
        'latency_calibration': table['calibration'], 'hardware_clock_claim': False,
        'RTL_or_physical_admission': False, 'CPU_numerical_oracle_cycles': False,
        'source_backed_extent_admission': not bool(demands), 'constrained_extent_successors': demands,
        'home_binding': 'actual provider lookup when supplied; otherwise exact distributed RF/spill homes; persistent finite logical objects, physical bases separate gate',
        'persistent_object_capacities': persistent_caps,
        'provisional_endpoint_scope': 'All macro providers and ordinary operators have explicit tile service reservations. Selected native templates expand command-by-command. Generic endpoints are parameterized software providers, not hardware implementation claims.'}


def load_inputs():
    manifest = read_json(ROOT / LOWERING / 'manifest.json')
    for path, digest in manifest['outputs'].items():
        if hashlib.sha256((ROOT / LOWERING / path).read_bytes()).hexdigest() != digest:
            raise ValueError('lowering input pin mismatch: ' + path)
    graphs = {t: read_json(ROOT / LOWERING / (t + '.json.gz')) for t in ('Qwen', 'DeepSeek')}
    layouts = {t: read_json(ROOT / DISTRIBUTED / (t + '.json.gz')) for t in graphs}
    return graphs, layouts


def encode(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=ROOT / OUT)
    ap.add_argument('--cycles', type=Path)
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--native-lowering', type=Path, action='append', default=[])
    ap.add_argument('--qwen-providers', type=Path)
    args = ap.parse_args()
    providers = read_json(args.qwen_providers) if args.qwen_providers else None
    native = {}
    for path in args.native_lowering:
        data = normalize_bundle(read_json(path))
        if data['target'] in native:
            raise ValueError('duplicate target lowering')
        native[data['target']] = data
    graphs, layouts = load_inputs(); default = cycle_table(graphs, layouts)
    table = read_json(args.cycles) if args.cycles else default
    required = set(default['values'])
    for data in native.values():
        for primitive in bundle_primitives(data):
            key = 'native:' + primitive
            if not args.cycles:
                table['values'][key] = 32
            required.add(key)
    validate_cycles(table, required)
    sources = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in PINS}
    if args.qwen_providers:
        sources[str(args.qwen_providers.resolve())] = hashlib.sha256(args.qwen_providers.read_bytes()).hexdigest()
    for path in args.native_lowering:
        sources[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in args.native_lowering:
        for snapshot in sorted(path.parent.glob('*.source')):
            sources[str(snapshot.resolve())] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        for name in ('h3_exact_scalar_contract.py', 'compile_deepseek_snapshot.py', 'producer_pins.json'):
            snapshot = path.parent / name
            if snapshot.exists():
                sources[str(snapshot.resolve())] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    if args.cycles:
        sources[str(args.cycles.resolve())] = hashlib.sha256(args.cycles.read_bytes()).hexdigest()
    if not args.verify:
        args.out.mkdir(parents=True, exist_ok=False)
    digests = {}; summaries = {}
    for target in graphs:
        result = compile_target(target, graphs[target], layouts[target], table, native.get(target), providers if target == 'Qwen' else None)
        raw = encode(result); path = args.out / (target + '.json.gz')
        if args.verify:
            if gzip.decompress(path.read_bytes()) != raw:
                raise ValueError('calendar replay mismatch ' + target)
        else:
            path.write_bytes(gzip.compress(raw, mtime=0))
        digests[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        summaries[target] = {k: result[k] for k in ('status', 'PC_count', 'proof', 'cycles',
            'source_backed_extent_admission', 'constrained_extent_successors',
            'native_lowering_PC_count', 'native_operator_lowering_complete')}
    sources = {str(Path(k).relative_to(ROOT)) if Path(k).is_absolute() and Path(k).is_relative_to(ROOT) else k: v
               for k, v in sources.items()}
    manifest = {'schema': 'H3_COMPLETE_CALENDAR_REPLAY_V1', 'source_sha256': sources,
        'output_sha256': digests, 'endpoint_cycles': table, 'targets': summaries,
        'calibration_gate': 'Separate measured provider composition and numerical operator gates required; software ticks do not transfer to hardware clocks.',
        'replay': 'python tools/h3_complete_native_calendar.py --verify --out ' + str(args.out) +
            ''.join(' --native-lowering ' + str(p) for p in args.native_lowering) +
            (' --cycles ' + str(args.cycles) if args.cycles else '') +
            (' --qwen-providers ' + str(args.qwen_providers) if args.qwen_providers else '')}
    path = args.out / 'manifest.json'
    if args.verify:
        if read_json(path) != manifest:
            raise ValueError('source-pin manifest replay mismatch')
        print('PASS_SOURCE_PINNED_COMPLETE_CALENDAR_REPLAY')
    else:
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main()
