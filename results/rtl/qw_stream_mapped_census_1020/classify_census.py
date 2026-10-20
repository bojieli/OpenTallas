#!/usr/bin/env python3
"""Attach mapped master/instance evidence to existing census findings, no waivers."""
import collections
import json
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / 'tools/ref_tile'))
import native_census as NC

for job in json.loads((root / 'manifest.json').read_text())['jobs']:
    path = root / job['job']
    report = json.loads((path / 'native_census.json').read_text())
    roles, _ = NC.liberty_roles([item['snapshot'] for item in job['libraries']])
    mods = NC.TL.parse_verilog(Path(job['netlist']).read_text())
    mods = {k:v for k,v in mods.items() if k == 'qfd_dv_stream_tile' or k not in roles}
    g, _ = NC.TL.flatten(mods, 'qfd_dv_stream_tile')
    drivers = {}
    for ci, (master, name, pins) in enumerate(g.cells):
        for pin, nets in pins.items():
            role = roles[master]['pins'].get(pin, {})
            if role.get('direction') == 'output':
                for net in nets:
                    drivers[net] = ci
    def cone(net, depth=0, visited=None):
        visited = set() if visited is None else visited
        if net in visited:
            return []
        visited.add(net)
        if net not in drivers:
            return ['INPUT_OR_LITERAL:' + g.net_name[net]]
        ci = drivers[net]
        master, name, pins = g.cells[ci]
        if roles[master]['sequential'] or depth >= 12:
            return [name]
        sources = []
        for pin, nets in pins.items():
            if roles[master]['pins'].get(pin, {}).get('direction') == 'input':
                for n in nets:
                    sources += cone(n, depth + 1, visited)
        return sorted(set(sources))
    violations = []
    for v in report['violations']:
        endpoints = []
        for ci, pin, bit in v['endpoints']:
            if isinstance(ci, int):
                master, name, _ = g.cells[ci]
                endpoints.append({'master':master, 'instance':name, 'pin':pin, 'bit':bit})
            else:
                endpoints.append({'port':ci, 'pin':pin, 'bit':bit})
        item = dict(v)
        item['sample_endpoints_resolved'] = endpoints
        item['samples_truncated_at_40_by_native_tool'] = v['loads'] > 40
        item['upstream_sequential_or_input_cone'] = cone(g.net_id[v['net']])
        violations.append(item)
    masters = collections.Counter(c[0] for c in g.cells)
    seq = collections.Counter()
    for master, name, pins in g.cells:
        if roles[master]['sequential']:
            seq[re.sub(r'\[\d+\].*', '', name)] += 1
    (path / 'classification.json').write_text(json.dumps({'job':job['job'], 'masters':dict(masters),
            'sequential_groups':dict(seq), 'violations':violations}, indent=2) + '\n')
    print(job['job'], 'classified', len(violations), flush=True)
