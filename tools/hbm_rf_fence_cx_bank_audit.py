#!/usr/bin/env python3
"""Audit mapped OpenDB connectivity, not RTL attributes or control protection.
Input TSV is emitted using actual library MTerm directions by the companion hook.
Fail closed if naming or topology cannot establish all 130 physical banks.
"""
import argparse, collections, json, re
from pathlib import Path

BANK = re.compile(r'(?:^|[./])(?P<skid>u_cap|u_hw)[./]banked[./]bank\[(?P<n>\d+)\][./]local_slice[./](?P<leaf>.*)')

def audit(rows):
    cells = {}
    for name, master, pin, direction, net in rows:
        c = cells.setdefault(name, {'master': master, 'inputs': {}, 'outputs': {}})
        if direction not in ('INPUT', 'OUTPUT', 'INOUT'):
            raise ValueError('unknown library pin direction ' + direction)
        if direction == 'INOUT':
            raise ValueError('inout cell pin cannot establish directed topology')
        c['inputs' if direction == 'INPUT' else 'outputs'][pin] = net
    drivers = collections.defaultdict(list)
    for name, c in cells.items():
        for net in c['outputs'].values():
            if net: drivers[net].append(name)
    groups = collections.defaultdict(dict)
    controls = {}
    payload = collections.defaultdict(lambda: collections.defaultdict(list))
    for name, c in cells.items():
        m = BANK.search(name)
        if not m: continue
        group = (m['skid'], int(m['n']))
        groups[group][name] = c
        if not c['master'].upper().startswith('DFF'): continue
        leaf = m['leaf']
        for role in ('s_v', 'out_v', 'in_ready'):
            if re.match(re.escape(role) + r'(?:\$|\[0\]|$)', leaf):
                if (group, role) in controls:
                    raise ValueError('duplicate control flop ' + str((group, role)))
                controls[group, role] = name
        for role in ('s_d', 'out_d'):
            if re.match(re.escape(role) + r'\[\d+\]', leaf):
                payload[group][role].append(name)
    expected = {(s, b) for s in ('u_cap', 'u_hw') for b in range(65)}
    if set(groups) != expected:
        raise ValueError('bank inventory mismatch: missing=' + str(sorted(expected-set(groups))) + ' extra=' + str(sorted(set(groups)-expected)))
    if len(controls) != 390:
        raise ValueError('expected 390 local control flops, found ' + str(len(controls)))
    control_by_cell = {v: k for k, v in controls.items()}
    if len(control_by_cell) != 390:
        raise ValueError('local capture-control driver groups collapsed')
    output_nets = []
    for name in control_by_cell:
        nets = [n for n in cells[name]['outputs'].values() if n]
        if not nets: raise ValueError('control flop without connected output ' + name)
        output_nets.extend(nets)
        for n in nets:
            if drivers[n] != [name]: raise ValueError('shared or ambiguous control driver ' + n)
    if len(set(output_nets)) != len(output_nets):
        raise ValueError('control output net reused between banks')
    cache = {}
    def roots(net, visiting):
        if not net: return frozenset()
        if net in cache: return cache[net]
        if net in visiting: raise ValueError('combinational loop at ' + net)
        result = set()
        for name in drivers.get(net, []):
            if len(drivers[net]) != 1: raise ValueError('multiple drivers at ' + net)
            c = cells[name]
            if c['master'].upper().startswith('DFF'):
                if name in control_by_cell: result.add(control_by_cell[name])
            else:
                for n in c['inputs'].values(): result.update(roots(n, visiting | {net}))
        cache[net] = frozenset(result)
        return cache[net]
    counts = {}
    for group in sorted(expected):
        width = 64 if group[1] < 64 else (18 if group[0] == 'u_cap' else 9)
        counts['%s.bank[%d]' % group] = {}
        for role in ('s_d', 'out_d'):
            names = payload[group][role]
            if len(names) != width:
                raise ValueError('payload inventory mismatch ' + str(group) + ' ' + role + ': ' + str(len(names)))
            for name in names:
                d = cells[name]['inputs'].get('D')
                if not d: raise ValueError('missing actual mapped D pin ' + name)
                r = roots(d, set())
                required = {(group, 's_v')}
                if role == 'out_d': required.add((group, 'out_v'))
                if not required <= r:
                    raise ValueError('missing local capture controls ' + name + ' roots=' + str(sorted(r)))
                # Other skids may supply data. Other banks within this skid may
                # not supply its capture/hold control. Stop at every data FF.
                foreign = {x for x in r if x[0][0] == group[0] and x[0] != group}
                if foreign: raise ValueError('foreign bank capture controls ' + name + ': ' + str(sorted(foreign)))
            counts['%s.bank[%d]' % group][role] = len(names)
    return {'status': 'PASS', 'banks': {'u_cap': 65, 'u_hw': 65}, 'control_flops': len(controls),
            'payload_flops': sum(sum(x.values()) for x in counts.values()), 'bank_inventory': counts,
            'scope': 'actual mapped ordinary performance bank capture-control connectivity; no protection claim'}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('graph'); p.add_argument('record')
    a = p.parse_args()
    try:
        rows = [line.rstrip('\n').split('\t') for line in Path(a.graph).read_text().splitlines() if line]
        # mtp-lead 2026-10-09: OpenDB names carry escaped brackets (bank\[0\]); the first mapped run failed the
        # inventory on the escape alone (all 130 banks present).  Unescape names and nets before the audit.
        rows = [[f.replace('\\', '') for f in r] for r in rows]
        result = audit(rows)
    except Exception as e:
        result = {'status': 'FAIL', 'reason': str(e)}
    Path(a.record).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'bank_inventory'}))
    return 0 if result['status'] == 'PASS' else 1
if __name__ == '__main__': raise SystemExit(main())
