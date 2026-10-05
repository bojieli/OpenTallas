#!/usr/bin/env python3
"""Allocate the connected two-row W2 result seats after installed W2 planes.

Calls the existing Program.put without constructing a checkpoint/model or
rewriting any original image. The emitted include is allocation, not a lease,
installation acknowledgement, source permit, or completion.
"""
import argparse
import ast
import csv
import json
from pathlib import Path
from types import SimpleNamespace


def emit(recipe, spans, allocator, out):
    book = json.loads(Path(recipe).read_text())
    if (book['schema'] != 'opentallas.ds20.installed_workspace.v1'
            or book['memory_bytes'] != 2 * 2097152 * 32):
        raise ValueError('actual NS2/MEM_WORDS2097152 recipe required')
    successor = book['recipe_successor']
    cursor = successor['emitted_image_bytes']
    layout = {a['name']: a['base'] for a in book['allocation_envelopes']}
    layout.update({a['name']: a['base'] for a in successor['allocations']})
    if cursor < max(a['end'] for a in successor['allocations']):
        raise ValueError('recipe cursor overlaps installed reservations')
    with Path(spans).open() as stream:
        rows = [{k: int(v) for k, v in row.items()}
                for row in csv.DictReader(stream)]
    # Existing installer emits six literal 136-line, 128-byte expert planes.
    # Each CSV extent is contiguous within its actual plane; no guessed padding.
    for slot in range(6):
        plane = sorted((r for r in rows if r['slot'] == slot), key=lambda r: r['base'])
        if not plane or plane[0]['base'] != cursor:
            raise ValueError('installed W2 planes must start at the actual recipe cursor')
        end = cursor
        for row in plane:
            if row['base'] != end or row['end'] <= end:
                raise ValueError('installed W2 span gap or overlap')
            end = row['end']
        if end - cursor != 136 * 128:
            raise ValueError('actual released W2 plane geometry required')
        layout[f'W2_COMPACT_SLOT{slot}'] = cursor
        cursor = end
    if len(rows) != sum(1 for r in rows if 0 <= r['slot'] < 6):
        raise ValueError('unexpected installed W2 slot')
    tree = ast.parse(Path(allocator).read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Program')
    put = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'put')
    namespace = {}
    exec(compile(ast.Module(body=[put], type_ignores=[]), str(allocator), 'exec'), namespace)
    state = SimpleNamespace(cur=cursor, a=dict(layout))
    extents = []
    for name in ('HBM_W2_CONNECTED_RESULT_A', 'HBM_W2_CONNECTED_RESULT_B'):
        if name in state.a:
            raise ValueError('output seats already allocated')
        base = namespace['put'](state, name, 64, align=64)
        if base % 64 or base < cursor or base + 64 > book['memory_bytes']:
            raise ValueError('actual installed capacity/alignment exhausted')
        extents.append((base, base + 64))
    if any(state.a[k] != v for k, v in layout.items()):
        raise ValueError('original allocator layout changed')
    target = Path(out)
    if target.exists():
        raise ValueError('preserve existing fixture include; use fresh output')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('// Actual Program.put output reservations; no installed/grant/done signal.\n'
                      f'localparam integer RAM_BYTES={book["memory_bytes"]};\n'
                      + ''.join(f'localparam [31:0] BASE_{label}=32\'d{base}, '
                                f'LIMIT_{label}=32\'d{end};\n'
                                for label, (base, end) in zip(('A', 'B'), extents)))
    return extents


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('recipe', 'spans', 'allocator', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(emit(args.recipe, args.spans, args.allocator, args.out))
