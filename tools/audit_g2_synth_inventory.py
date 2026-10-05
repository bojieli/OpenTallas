#!/usr/bin/env python3
"""Check flattened G2 synthesis inventory; this is not timing/area closure."""
import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path


def audit(netlist, config):
    modules = netlist['modules']
    if 'ot_a3_g2_cluster' not in modules:
        raise ValueError('G2 top missing')
    top = modules['ot_a3_g2_cluster']
    argv = config['argv']
    expected = dict(argv[i+1].split('=', 1) for i, v in enumerate(argv) if v == '--param')
    parameters = {k: int(v, 2) for k, v in top['parameter_default_values'].items()}
    issues = [f'parameter {k}: expected {v}, got {parameters.get(k)}'
              for k, v in expected.items() if parameters.get(k) != int(v)]
    macros = []
    roms = []
    unknown = Counter()
    for name, cell in top['cells'].items():
        kind = cell['type']
        if kind.startswith('fakeram'):
            macros.append({'instance': name, 'type': kind})
        elif kind == '$mem_v2':
            p = cell['parameters']
            item = {'instance': name, **{k: int(p[k], 2) for k in ['WIDTH', 'SIZE', 'RD_PORTS', 'WR_PORTS']}}
            roms.append(item)
            if item['WR_PORTS']:
                issues.append('unmapped writable memory: '+name)
        elif not kind.startswith('$'):
            unknown[kind] += 1
    counts = dict(Counter(m['type'] for m in macros))
    macro_bits = 0
    capacity_known = True
    for kind, count in counts.items():
        geometry = re.fullmatch(r'fakeram_(\d+)x(\d+)', kind)
        if geometry is None:
            capacity_known = False
            issues.append('unknown macro capacity: '+kind)
        else:
            depth, width = map(int, geometry.groups())
            if depth == 0 or width == 0:
                capacity_known = False
                issues.append('invalid macro capacity: '+kind)
            macro_bits += count * depth * width
    if capacity_known and macro_bits != config['expected_memory_bits']:
        issues.append('macro bit capacity differs from configuration')
    if counts != config['expected_memory_instances']:
        issues.append('macro inventory differs from configuration')
    if unknown:
        issues.append('unresolved nonprimitive hierarchy')
    return {'status': 'pass' if not issues else 'fail', 'issues': issues,
            'scope': 'Intermediate flattened synthesis inventory only; not final placed macros, routed area, timing or deployment coverage.',
            'parameters': parameters, 'macro_instances': macros, 'macro_counts': counts,
            'expected_macro_bits': config['expected_memory_bits'],
            'observed_macro_bits': macro_bits if capacity_known else None,
            'inferred_memories': roms, 'inferred_rom_bits': sum(r['WIDTH']*r['SIZE'] for r in roms if not r['WR_PORTS']),
            'unresolved_types': dict(unknown), 'cell_types': dict(Counter(c['type'] for c in top['cells'].values()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--netlist', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(json.loads(args.netlist.read_text()), json.loads(args.config.read_text()))
    result['inputs'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [args.netlist, args.config]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'], result['macro_counts'], 'ROM bits', result['inferred_rom_bits'])
    raise SystemExit(result['status'] != 'pass')


if __name__ == '__main__':
    main()
