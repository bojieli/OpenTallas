#!/usr/bin/env python3
"""Compare settled RTL diagnostic snapshots to unchanged ISA instruction states.

Full-vector differences include asynchronous receive buffers; the first differing
snapshot is a locator, not by itself proof of the first numerical fault.
"""
import argparse
import json
from pathlib import Path
import re
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('root', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
manifest = json.loads((args.root / 'golden_diagnostic_manifest.json').read_text())
files = []
for path in (args.root / 'snapshots').glob('rtl_n*_j*_pc*.hex'):
    node, job, pc = map(int, re.fullmatch(r'rtl_n(\d+)_j(\d+)_pc(\d+)\.hex', path.name).groups())
    files.append((job, pc, node, path))
rows = []
for job, pc, node, path in sorted(files):
    gold = args.root / 'golden_snapshots' / f'gold_n{node}_j{job}_pc{pc}.bin'
    if not gold.exists():
        continue
    values = [int(s, 16) for s in path.read_text().splitlines() if s and not s.startswith('//')]
    rtl = np.asarray(values, dtype=np.uint32)
    expected = np.fromfile(gold, dtype='<u4')
    assert rtl.shape == expected.shape, (path, rtl.shape, expected.shape)
    indices = np.flatnonzero(rtl != expected)
    instruction = manifest['programs'][node + 1][pc]
    rows.append(dict(node=node, job=job, pc=pc, tag=instruction.get('_tag'),
                     different_words=len(indices), first_words=[dict(address=int(i), rtl=f'{int(rtl[i]):08x}',
                     golden=f'{int(expected[i]):08x}') for i in indices[:12]], instruction=instruction))
record = dict(scope='original reduced campaign14 first-divergence locator; receive-buffer differences need attribution',
              snapshots_compared=len(rows), rows=rows)
args.output.write_text(json.dumps(record, indent=2) + '\n')
print('snapshots_compared', len(rows))
for row in rows:
    if row['different_words']:
        print('DIFF', row['node'], row['job'], row['pc'], row['tag'], row['different_words'], row['first_words'][:3])
