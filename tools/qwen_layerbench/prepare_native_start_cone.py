#!/usr/bin/env python3
"""Extract genuine retained START RTL for a selected frozen ancestor cone.

All clock inputs retain their actual typed source names. This emits source only;
clock driver/polarity binding and physical phase remain external obligations.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def prepare(source, stages, cone):
    if stages['schema'] != 'ot_start_stages/1':
        raise ValueError('unsupported retained provider ABI')
    selected = {s['region']: s for s in stages['stages'] if s['region'] in cone['provider_nodes']}
    if set(selected) != set(cone['provider_nodes']):
        raise ValueError('incomplete virtual ancestor closure')
    for region, s in selected.items():
        d = cone['regions'][region]
        for k in ('parent', 'pad', 'edge_fall'):
            if s[k] != d[k]:
                raise ValueError(f'changed selected START graph: {region}/{k}')
        for k in ('id', 'parent', 'clock_port', 'module', 'flops'):
            if s[k] != cone['provider_nodes'][region][k]:
                raise ValueError(f'changed selected provider ABI: {region}/{k}')
        if s['parent'] is not None and s['parent'] not in selected:
            raise ValueError('missing ancestor '+s['parent'])
    outputs = [o for o in stages['die_outputs'] if o['dst_region'] in cone['regions']]
    clocks = [s['clock_port'] for s in selected.values()]
    if len(set(clocks)) != len(clocks):
        raise ValueError('clock port collision')
    ids = {s['id'] for s in selected.values()}
    ports = ['input wire rst_raw_n'] + ['input wire '+c for c in clocks]
    ports += ['output wire '+o['net'] for o in outputs]
    lines = ['// Extracted actual retained provider ancestor cone. SOURCE_ONLY.',
             '// Clock inputs require selected actual source/polarity binding; no dummy aliases.',
             'module ot_die_start_stages_native_cone (', ',\n'.join('    '+p for p in ports), ');']
    counts = {i: [0, 0] for i in ids}
    for line in source.splitlines():
        m = re.search(r'\bu_(st|rst)_(\w+)\s*\(', line)
        if m and m[2] in ids:
            lines.append(line)
            counts[m[2]][m[1] == 'rst'] += 1
        elif re.match(r'\s*wire st_(\w+)_(?:start|start_d|rraw)\b', line):
            if re.match(r'\s*wire st_(\w+)_(?:start|start_d|rraw)\b', line)[1] in ids:
                lines.append(line)
        elif any(re.match(r'\s*assign '+re.escape(o['net'])+r'\s*=', line) for o in outputs):
            lines.append(line)
    for s in selected.values():
        if counts[s['id']] != [1, int(not s['root'])]:
            raise ValueError('not the actual expected root/origin/reset source '+s['id'])
    lines.append('endmodule')
    helper = re.search(r'(?ms)^(?:\(\*[^\n]*?\*\) )?module ot_die_start_reset_relay\b.*?^endmodule', source)
    if not helper:
        raise ValueError('actual bounded reset relay source missing')
    lines.append(helper[0])
    metadata = dict(schema='native_start_cone/1', source_only=True, selected_phase_qualified=False,
                    physical_qualified=False, virtual_stage_count=len(selected),
                    native_outputs=outputs, stages=list(selected.values()),
                    source_commit=cone['source_commit'], root_reset_source=cone['reset_source'],
                    holds=['selected actual stage clock driver and polarity binding',
                           'native producer command/operand/write source cone',
                           'full current physical provider composition and timing'],
                    excluded='unrelated provider branches pruned; no alternate origin or added cycle',
                    retained_source_sha256=hashlib.sha256(source.encode()).hexdigest())
    return '\n'.join(lines)+'\n', metadata


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True); p.add_argument('--stages', required=True)
    p.add_argument('--cone', required=True); p.add_argument('--out', required=True)
    a = p.parse_args()
    sv, meta = prepare(Path(a.source).read_text(), json.loads(Path(a.stages).read_text()), json.loads(Path(a.cone).read_text()))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out/'start_cone.sv').write_text(sv)
    (out/'start_cone.json').write_text(json.dumps(meta, indent=2)+'\n')
    print(json.dumps(dict(virtual_stages=meta['virtual_stage_count'], native_outputs=len(meta['native_outputs']), source_only=True)))


if __name__ == '__main__':
    main()
