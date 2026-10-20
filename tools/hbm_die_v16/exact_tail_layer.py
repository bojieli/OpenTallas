#!/usr/bin/env python3
"""Materialize real narrow tail cores for an existing, immutable relay layer.

Only unused high positions in the final tile of each bus disappear. All real
driver/load bit maps, stations, clocks, epochs, reset landings and ages remain.
New masters are source variants: they require their own synthesis/native views.
"""
import argparse
import collections
import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def transform(layer, source_rel):
    instances = {x['name']: x for x in layer['instances']}
    variants = {}
    removed = collections.Counter()
    for bus in layer['relay_splice_v2']:
        width, count, bits = bus['width'], bus['tiles'], bus['bits']
        assert count == (bits + width - 1) // width
        widths = [min(width, bits - t * width) for t in range(count)]
        bus['lane_widths'] = widths
        narrow = widths[-1]
        if narrow == width:
            continue
        names = {node['names'][-1] for node in bus['nodes']}
        names.update(stage[-1] for sink in bus['sinks'].values() for stage in sink['chain'])
        for name in sorted(names):
            inst = instances[name]
            master, source = inst['master'], inst['source']
            key = (master, source, width, narrow)
            if key not in variants:
                text = (ROOT / source).read_text()
                match = re.search(r'\bmodule\s+' + re.escape(master) + r'\b.*?\bendmodule\b', text, re.S)
                if not match:
                    raise ValueError(f'no literal source module {master}')
                body = match.group()
                new = master + f'_tail{narrow}'
                body = re.sub(r'\b' + re.escape(master) + r'\b', new, body)
                # Resize actual core W and each packed data branch. Control
                # widths stay untouched; no spare tie or full-width hidden core.
                body, replacements = re.subn(r'\.W\(' + str(width) + r'\)', f'.W({narrow})', body)
                if width > 256 and re.search(r'\bot_hbm_rly(?:_fc|_fcf)?\s*#', body) and '.RS_RELAY(' not in body:
                    body = body.replace(f'.W({narrow})', f'.W({narrow}), .RS_RELAY(1)')
                if replacements != 1:
                    raise ValueError(f'{master}: expected one literal real-core W')
                body = re.sub(r'\[(\d+):0\]', lambda m: f'[{(int(m[1])+1)//width*narrow-1}:0]'
                              if (int(m[1])+1) % width == 0 else m[0], body)
                variants[key] = (new, body)
            inst['master'] = variants[key][0]
            inst['rtl_deps'] = sorted(set(inst.get('rtl_deps', [])) | {source})
            inst['source'] = source_rel
            inst['note'] += f'; exact real-core tail {narrow}/{width}, own native view required'
            removed['data_positions'] += width - narrow
            removed['instances'] += 1
    source = '`timescale 1ns/1ps\n`default_nettype none\n' + '\n'.join(v[1] for _, v in sorted(variants.items())) + '\n`default_nettype wire\n'
    return layer, source, dict(removed, variants=len(variants), buses=len(layer['relay_splice_v2']))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('layer')
    ap.add_argument('--out', required=True)
    ap.add_argument('--source', required=True, help='repository-relative generated RTL path')
    ap.add_argument('--report', required=True)
    args = ap.parse_args()
    path = Path(args.source)
    if path.is_absolute() or '..' in path.parts or not str(path).startswith('rtl/hbm_accel/die_glue/'):
        ap.error('source must be a repository-owned die_glue RTL path')
    layer = json.loads(gzip.open(args.layer, 'rt').read() if args.layer.endswith('.gz') else Path(args.layer).read_text())
    result, source, report = transform(layer, args.source)
    (ROOT / path).write_text(source)
    with gzip.open(args.out, 'wt') as stream:
        json.dump(result, stream)
    Path(args.report).write_text(json.dumps(report, indent=2) + '\n')
    print('EXACT_TAIL_MODEL', json.dumps(report))


if __name__ == '__main__':
    main()
