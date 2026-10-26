#!/usr/bin/env python3
"""Check genuine Engram H through the native entry row codec and NX partials."""
import argparse
import json
from pathlib import Path
import numpy as np
import entry_engram
import entry_inputs
import norm_nx


def unpack_h(record):
    h = np.zeros((4, 5120), dtype=np.uint16)
    halves = {}
    for w in record['writes']:
        if w['region'] != 'H':
            continue
        e = w['elements']
        key = (w['sid'], w['leaf'], e['subbeat'], e['half'])
        halves.setdefault(key, {})[e['halfrow_bank']] = w
    if len(halves) != 1280:
        raise ValueError('native H codec needs all 1280 half-row pairs')
    for banks in halves.values():
        if set(banks) != {0, 1}:
            raise ValueError('missing native H half-row bank')
        packed = int(banks[0]['data128'], 16) | int(banks[1]['data128'], 16) << 128
        start = banks[0]['elements']['global_start']
        for c in range(4):
            for lane in range(4):
                h[c, start + lane] = (packed >> (16 * (4*c + lane))) & 65535
    return h


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tree', required=True, type=Path)
    p.add_argument('--fixtures', required=True, type=Path)
    p.add_argument('--inputs', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    die = entry_inputs.D.Die(a.tree)
    rows = entry_inputs.compile_inputs(die, a.fixtures, a.inputs)
    h = entry_engram.entry_h(a.fixtures, a.inputs)
    expected = (h.view(np.uint32) >> 16).astype(np.uint16)
    errors = int(np.count_nonzero(unpack_h(rows) != expected))
    partials = norm_nx.partials(a.fixtures, h_override=h)
    # This is the actual old producer mistake, rather than an arbitrary codec mutant.
    raw = entry_inputs.compile_inputs(die, a.fixtures)
    bypass = int(np.count_nonzero(unpack_h(raw) != expected))
    rec = dict(verdict='PASS' if errors == 0 and bypass > 0 else 'FAIL', h_words=expected.size,
               h_mismatches=errors, native_rows=rows['row_count'], nx_partials=len(partials),
               bypass_engram_control_mismatches=bypass, input_sources=rows['input_sources'],
               scope='entry row codec and golden NX partials; transport/schedule not qualified')
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec))
    return rec['verdict'] != 'PASS'


if __name__ == '__main__':
    raise SystemExit(main())
