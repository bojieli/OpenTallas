#!/usr/bin/env python3
"""Install retained compact W2 bytes into a successor of the current DS20 recipe.

Produces sparse, addressed $readmemh overlays for the EXISTING NS2 partitions.
No checkpoint, inference, repacking, permission/grant or executable compilation.
Load overlays AFTER original images and BEFORE requests in the isolated gate.
"""
import argparse
import ast
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from gpu_sys.mem_image import placement

ROOT = Path(__file__).resolve().parents[1]


def install(book_path, source, out):
    book = json.loads(Path(book_path).read_text())
    source, out = Path(source), Path(out)
    if (book['schema'] != 'opentallas.ds20.installed_workspace.v1'
            or book['memory_bytes'] != 2*2097152*32):
        raise ValueError('current NS2/MEM_WORDS2097152 installer recipe required')
    recipe = book['recipe_successor']
    cursor = recipe['emitted_image_bytes']
    allocations = recipe['allocations']
    if (type(cursor) is not int or cursor % 4096
            or cursor < max(a['end'] for a in allocations)
            or cursor >= book['memory_bytes']):
        raise ValueError('invalid current allocated image boundary')
    counts = [int(w, 16) for w in (source/'cfg_lines.hex').read_text().split()]
    lut = [int(w, 16) for w in (source/'cfg_lut.hex').read_text().split()]
    words = [int(w, 16) for w in (source/'w2.hex').read_text().split()]
    if counts != [10, 10, 0, 0, 29, 29, 29, 29]:
        raise ValueError('released die2/stack0 complete W2 layout required')
    expected_lut = [(sm << 8) | line for sm, n in enumerate(counts) for line in range(n)]
    if lut != expected_lut or len(words) != 6*136 or any(w >> 1024 for w in words):
        raise ValueError('literal cfg ownership or released W2 payload extent differs')
    # Execute the existing allocator and byte emitter, rather than a new arena.
    path = ROOT/'tools/gpu_sys/v41_hbm.py'
    cls = next(n for n in ast.parse(path.read_text()).body
               if isinstance(n, ast.ClassDef) and n.name == 'Program')
    nodes = [next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
             for name in ('put', 'wr')]
    ns = {'np': np}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), ns)
    layout = {r['name']: r['base'] for r in book['allocation_envelopes']}
    layout.update({a['name']: a['base'] for a in allocations})
    state = SimpleNamespace(cur=cursor, a=layout, mem=[{}])
    blobs = []
    for slot in range(6):
        raw = b''.join(w.to_bytes(128, 'little') for w in words[slot*136:(slot+1)*136])
        base = ns['put'](state, f'W2_COMPACT_SLOT{slot}', len(raw), align=128)
        if base+len(raw) > book['memory_bytes'] or base+len(raw) > 1 << 32:
            raise ValueError('real installed backing/address aperture exhausted')
        ns['wr'](state, 0, base, np.frombuffer(raw, dtype=np.uint8))
        blobs.append((slot, base, raw))
    # CSV is literal existing-provider address data, not a lease or hardware map.
    rows = ['slot,sm,rows,base,end']
    sectors = ['slot,sm,local_line,quarter,provider_byte_address']
    partition_lines = [[], []]
    for slot, base, raw in blobs:
        emitted = state.mem[0][base].tobytes()
        if emitted != raw:
            raise ValueError('original Program.wr changed retained source bytes')
        prefix = 0
        for sm, count in enumerate(counts):
            if count:
                rows.append(f'{slot},{sm},{count*128//1224},{base+prefix*128},{base+(prefix+count)*128}')
            for line in range(count):
                for q in range(4):
                    addr = base+128*(prefix+line)+32*q
                    part, sector, _, lane = placement(addr, 2, 2097152)
                    if lane or sector >= 2097152:
                        raise ValueError('sector would alias actual partition storage')
                    word = emitted[128*(prefix+line)+32*q:128*(prefix+line)+32*(q+1)]
                    partition_lines[part].append(f'@{sector:x}\n{word[::-1].hex()}\n')
                    sectors.append(f'{slot},{sm},{line},{q},{addr}')
            prefix += count
    out.mkdir(parents=True, exist_ok=False)
    for part in range(2):
        (out/f'w2_p{part}.hex').write_text(''.join(partition_lines[part]))
    (out/'spans.csv').write_text('\n'.join(rows)+'\n')
    (out/'sectors.csv').write_text('\n'.join(sectors)+'\n')
    print(f'W2 source overlay emitted: {cursor}..{state.cur}; '
          '3264 addressed sectors; load before permit; no grant generated')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--recipe', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    install(a.recipe, a.source, a.out)
