#!/usr/bin/env python3
"""Extract whole station instances; certify the unchanged elaborated net graph.

This emits a preparation artifact, not a physical plan or a routing approval.
The physical consumer must fit complete stage footprints, clock/reset ports,
registered faces and parent access before using the two child modules.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def state_bits(modules, name, active=(), sequential=()):
    if name in active:
        raise ValueError('recursive module hierarchy')
    m = modules[name]
    count = sum(v['width'] * v['size'] for v in m.get('memories', {}).values())
    for c in m['cells'].values():
        t = c['type']
        if t in sequential:
            outputs = modules[t]['ports']
            width = sum(len(v['bits']) for n, v in outputs.items() if n in ('Q', 'QN'))
            if width != 1:
                raise ValueError('native sequential state width requires explicit support: ' + t)
            count += 1
        elif t in modules:
            count += state_bits(modules, t, active + (name,), sequential)
        elif re.search(r'\$(?:[a-z]*dff|ff|[a-z]*latch)', t):
            count += len(c['connections'].get('Q', []))
    return count


def prepare(source, groups, module, cut, prefix, mapped=False, sequential=()):
    m = source['modules'][module]
    chosen = {'w': [], 'e': []}
    crossing = []
    whole_groups = {'w': set(), 'e': set()}
    for n in sorted(m['cells']):
        if mapped:
            match = re.match(r'u_bound\.(u_ft_ft\d+_o_\d+|u_cland_ft\d+_i)(?:[/.]|$)', n)
            if not match:
                continue
            group = match[1]
        else:
            if not (re.fullmatch(r'u_ft_ft\d+_o_\d+', n) or re.fullmatch(r'u_cland_ft\d+_i', n)):
                continue
            group = n
        key = 'u_bound.' + group
        if key not in groups:
            raise ValueError('missing actual stage footprint: ' + key)
        z = groups[key]
        side = 'w' if (z[1] + z[3]) / 2 < cut else 'e'
        chosen[side].append(n)
        if group not in whole_groups[side] and z[1] < cut < z[3]:
            crossing.append(dict(cell=group, bounds_um=z[1:], target_child=side))
        whole_groups[side].add(group)
    if not all(chosen.values()):
        raise ValueError('both children must own whole station cells')
    ys = ['read_json /work/annotated.json'] if mapped else ['read_json /work/captured.json']
    for side, names in chosen.items():
        if mapped:
            for n in names:
                m['cells'][n].setdefault('attributes', {})['submod'] = prefix + '_' + side
        else:
            ys += ['select -clear',
                   'select ' + ' '.join(module + '/' + n for n in names),
                   'submod -name ' + prefix + '_' + side]
    if mapped:
        ys += ['submod']
    writer = 'write_verilog ' + ('' if mapped else '-noattr ')
    ys += ['select -clear', 'check -assert', 'write_json /work/split.json',
           writer + '/work/split.sv', 'design -reset',
           'read_json /work/captured.json', writer + '/work/captured.sv']
    event = dict(schema='opentallas.station_hierarchy_split.v1', module=module,
                 cut_um=cut, mapped=mapped, sequential_masters=list(sequential),
                 child_modules={prefix+'_'+s: (module+'_'+prefix+'_'+s if mapped else prefix+'_'+s) for s in chosen},
                 child_instances={prefix+'_'+s: (module+'_'+prefix+'_'+s if mapped else prefix+'_'+s) for s in chosen},
                 whole_groups={s: sorted(v) for s,v in whole_groups.items()}, children={prefix + '_' + s: ns for s, ns in chosen.items()},
                 crossing_whole_stage_groups=crossing, cycles_added=0,
                 status='SOURCE_EXTRACTION_ONLY; complete footprint/clock/reset/parent-access refit owed')
    return event, '\n'.join(ys) + '\n'


def _name(n):
    return n.removeprefix('$submod\\')


def _bits_to_original(new, old):
    result = {x: x for x in ('0', '1', 'x', 'z')}
    for n, wire in new['netnames'].items():
        n = _name(n)
        if n not in old['netnames']:
            continue
        target = old['netnames'][n]['bits']
        if len(wire['bits']) != len(target):
            raise ValueError('wire width changed: ' + n)
        for a, b in zip(wire['bits'], target):
            if a in result and result[a] != b:
                raise ValueError('conflicting wire identity: ' + n)
            result[a] = b
    return result


def _mapped(bits, mapping):
    try:
        return [mapping[b] for b in bits]
    except KeyError as e:
        raise ValueError('unidentified source bit: ' + str(e)) from e


def _same_cell(name, new, old, mapping):
    for key in ('type', 'parameters', 'port_directions', 'attributes'):
        if new.get(key, {}) != old.get(key, {}):
            raise ValueError('cell ' + key + ' changed: ' + name)
    if set(new['connections']) != set(old['connections']):
        raise ValueError('cell port inventory changed: ' + name)
    for port, bits in new['connections'].items():
        if _mapped(bits, mapping) != old['connections'][port]:
            raise ValueError('cell connection changed: ' + name + '.' + port)


def _inits(module, mapping):
    result = {}
    for wire in module['netnames'].values():
        initial = wire.get('attributes', {}).get('init')
        if initial is None:
            continue
        if len(initial) != len(wire['bits']):
            raise ValueError('initial state width mismatch')
        for bit, value in zip(_mapped(wire['bits'], mapping), reversed(initial)):
            if value in 'xz':
                continue
            if bit in result and result[bit] != value:
                raise ValueError('conflicting initial state')
            result[bit] = value
    return result


def _identity(module):
    return {bit: bit for wire in module['netnames'].values() for bit in wire['bits']}


def check(source, transformed, event):
    name = event['module']
    sm, tm = source['modules'], transformed['modules']
    old, new = sm[name], tm[name]
    children = event['children']
    child_modules = event.get('child_modules', {n: n for n in children})
    child_instances = event.get('child_instances', {n: n for n in children})
    selected = [n for ns in children.values() for n in ns]
    if len(selected) != len(set(selected)):
        raise ValueError('a whole instance belongs to multiple children')
    if set(tm) != set(sm) | set(child_modules.values()):
        raise ValueError('module inventory changed beyond declared children')
    pmap = _bits_to_original(new, old)
    if set(new['ports']) != set(old['ports']):
        raise ValueError('parent interface inventory changed')
    for p, v in new['ports'].items():
        if v['direction'] != old['ports'][p]['direction'] or _mapped(v['bits'], pmap) != old['ports'][p]['bits']:
            raise ValueError('parent port changed: ' + p)
    if new.get('attributes', {}) != old.get('attributes', {}):
        raise ValueError('parent module attributes changed')
    initial = _inits(new, pmap)
    parent_cells = set(old['cells']) - set(selected)
    expected_parent = parent_cells | set(child_instances.values())
    if set(new['cells']) != expected_parent:
        missing = sorted(expected_parent - set(new['cells']))
        extra = sorted(set(new['cells']) - expected_parent)
        raise ValueError('parent cell inventory changed: missing=' + str(missing[:5]) + ' extra=' + str(extra[:5]))
    for n in parent_cells:
        _same_cell(n, new['cells'][n], old['cells'][n], pmap)
    drivers = collections.defaultdict(set)
    for n, c in old['cells'].items():
        for p, bits in c['connections'].items():
            if c['port_directions'][p] in ('output', 'inout'):
                for b in bits:
                    drivers[b].add(n)
    for child, names in children.items():
        cm, inst = tm[child_modules[child]], new['cells'][child_instances[child]]
        if inst['type'] != child_modules[child] or inst.get('parameters'):
            raise ValueError('child instance type/parameters changed')
        if set(cm['cells']) != set(names):
            raise ValueError('whole child instance inventory changed: ' + child)
        cmap = _bits_to_original(cm, old)
        for bit, value in _inits(cm, cmap).items():
            if bit in initial and initial[bit] != value:
                raise ValueError('conflicting child initial state')
            initial[bit] = value
        if set(cm['ports']) != set(inst['connections']):
            raise ValueError('child boundary port inventory changed')
        owned = set(names)
        for p, v in cm['ports'].items():
            child_bits = _mapped(v['bits'], cmap)
            if child_bits != _mapped(inst['connections'][p], pmap):
                raise ValueError('child boundary connection changed: ' + child + '.' + p)
            expected = {'output' if drivers[b] & owned else 'input' for b in child_bits}
            if expected != {v['direction']} or inst['port_directions'][p] != v['direction']:
                raise ValueError('child boundary direction changed: ' + child + '.' + p)
        for n, c in cm['cells'].items():
            _same_cell(n, c, old['cells'][n], cmap)
    if initial != _inits(old, _identity(old)):
        raise ValueError('parent/child initial state changed')
    for n in set(sm) - {name}:
        a, z = sm[n], tm[n]
        mapping = _bits_to_original(z, a)
        if a.get('attributes', {}) != z.get('attributes', {}) or _inits(a, _identity(a)) != _inits(z, mapping):
            raise ValueError('source leaf attributes/initial state changed: ' + n)
        if set(a['ports']) != set(z['ports']) or a.get('parameter_default_values', {}) != z.get('parameter_default_values', {}):
            raise ValueError('source leaf interface/parameters changed: ' + n)
        for pn, pv in z['ports'].items():
            if pv['direction'] != a['ports'][pn]['direction'] or _mapped(pv['bits'], mapping) != a['ports'][pn]['bits']:
                raise ValueError('source leaf port changed: ' + n + '/' + pn)
        if set(a['cells']) != set(z['cells']) or a.get('memories', {}) != z.get('memories', {}):
            raise ValueError('source leaf state/inventory changed: ' + n)
        for cn, c in z['cells'].items():
            _same_cell(n + '/' + cn, c, a['cells'][cn], mapping)
    seq = event.get('sequential_masters', [])
    before, after = state_bits(sm, name, sequential=seq), state_bits(tm, name, sequential=seq)
    if before != after:
        raise ValueError('state bit count changed')
    return dict(schema='opentallas.station_split_conservation.v1', verdict='PASS',
                checked_cells=len(old['cells']), selected_whole_cells=len(selected),
                state_bits_before=before, state_bits_after=after, cycles_added=0,
                children={n: dict(instances=len(v), state_bits=state_bits(tm, child_modules[n], sequential=seq),
                                   module=child_modules[n], ports=len(tm[child_modules[n]]['ports'])) for n, v in children.items()},
                physical_qualified=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('source'); p.add_argument('groups'); p.add_argument('--module', required=True)
    p.add_argument('--prefix', required=True); p.add_argument('--cut', type=float, required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--mapped', action='store_true')
    p.add_argument('--clock-receipt')
    p = sub.add_parser('check')
    p.add_argument('source'); p.add_argument('transformed'); p.add_argument('event')
    p.add_argument('--out', required=True)
    args = ap.parse_args()
    read = lambda p: json.loads(Path(p).read_text())
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    if args.command == 'prepare':
        source = read(args.source)
        event, ys = prepare(source, read(args.groups), args.module, args.cut, args.prefix, args.mapped,
                            read(args.clock_receipt)['sequential_masters'] if args.clock_receipt else ())
        if args.mapped:
            (out / 'annotated.json').write_text(json.dumps(source) + '\n')
        event['captured_sha256'] = digest(args.source)
        (out / 'selection.json').write_text(json.dumps(event, indent=2) + '\n')
        (out / 'split.ys').write_text(ys)
    else:
        event = read(args.event)
        if digest(args.source) != event['captured_sha256']:
            raise ValueError('captured source identity changed')
        receipt = check(read(args.source), read(args.transformed), event)
        receipt['source_sha256'] = digest(args.source)
        receipt['transformed_sha256'] = digest(args.transformed)
        (out / 'conservation.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(receipt))


if __name__ == '__main__':
    main()
