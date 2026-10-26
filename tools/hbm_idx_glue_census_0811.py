#!/usr/bin/env python3
"""Count actual mapped scorer glue per input clock, excluding declared hard leaves."""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mapped-json', type=Path, required=True)
    ap.add_argument('--stat', type=Path, required=True)
    ap.add_argument('--source-manifest', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    modules = json.loads(args.mapped_json.read_text())['modules']
    top = 'ot_hbm_idx_score_static'
    roots, boxes = collections.Counter(), collections.Counter()
    hard = {'ot_hbm_idx_hslice_ready_native', 'hidx_meta_w25_d123_r0'}
    env = {
        bit: name + (f'[{i}]' if len(port['bits']) > 1 else '')
        for name, port in modules[top]['ports'].items()
        if port['direction'] == 'input'
        for i, bit in enumerate(port['bits'])
    }

    def count(module, mapping, path):
        for name, cell in modules[module]['cells'].items():
            kind, ports = cell['type'], cell['connections']
            if kind.startswith('DFF'):
                clock = mapping.get(ports['CLK'][0])
                assert clock and clock.startswith('clk_'), (path, name, clock)
                roots[clock] += 1
            elif kind in hard:
                boxes[kind] += 1
            elif kind in modules and modules[kind].get('cells'):
                child = {
                    bit: mapping.get(ports[p][i], f'{path}/wire_{ports[p][i]}')
                    for p, port in modules[kind]['ports'].items() if p in ports
                    for i, bit in enumerate(port['bits']) if i < len(ports[p])
                }
                count(kind, child, path + '/' + name)

    count(top, env, top)
    assert boxes == {'ot_hbm_idx_hslice_ready_native': 512, 'hidx_meta_w25_d123_r0': 4}, boxes
    text = args.stat.read_text()
    local_area = {}
    for section in re.split(r'(?m)^=== ', text)[1:]:
        name = section.splitlines()[0].removesuffix(' ===')
        area = re.search(r'Chip area for module .*?: ([\d.]+)', section)
        if area:
            local_area[name] = float(area.group(1))

    def area(module):
        return local_area.get(module.lstrip('\\'), 0) + sum(
            area(c['type']) for c in modules[module].get('cells', {}).values()
            if c['type'] in modules and modules[c['type']].get('cells')
        )

    measured = float(re.search(r'Chip area for top module .*?: ([\d.]+)', text).group(1))
    assert abs(area(top) - measured) < 0.001
    # Independently reconcile mapped FF total against the final hierarchy stat.
    final = text.split('=== design hierarchy ===')[-1]
    stat_ff = sum(int(n) for n in re.findall(r'^\s+(\d+)\s+\S+\s+DFF\w+\s*$', final, re.M))
    assert sum(roots.values()) == stat_ff, (roots, stat_ff)
    report = {
        'schema': 'opentallas.idx_actual_glue_clock_count.v1',
        'scope': 'Actual mapped scorer glue. The 512 exact hslice and four metadata cells are blackboxes; their area and FF are excluded. No CTS, native port or parent closure claim.',
        'flops': stat_ff, 'roots': len(roots), 'root_ff_counts': dict(roots),
        'max_root_ff': max(roots.values()), 'blackbox_counts': dict(boxes),
        'mapped_std_area_um2': measured, 'area_at_55_percent_um2': measured / .55,
        'actual_transitive_std_area_um2': {
            m: area(m) for m in ['ot_hbm_idx_tail_native', 'ot_hbm_idx_chunk_owned_native', top]
        },
        'source_files': json.loads(args.source_manifest.read_text()),
        'mapped_json_sha256': hashlib.sha256(args.mapped_json.read_bytes()).hexdigest(),
        'stat_sha256': hashlib.sha256(args.stat.read_bytes()).hexdigest(),
        'limits': 'All25 soft-logic roots have <=15000 mapped FF. Actual clock insertion/spread, hardened control/tail slots and parent wire reaches remain unmeasured.',
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'FF': stat_ff, 'roots': len(roots), 'max_root': max(roots.values()), 'std_um2': measured}))


if __name__ == '__main__':
    main()
