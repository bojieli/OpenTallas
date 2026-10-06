#!/usr/bin/env python3
"""Reserve TP96 sources using the retained allocator; never publish payloads.

This extends the actual DS20 saved installer recipe. Runtime source readbacks,
all-rank producer enrollment and a linked consumer remain separate requirements.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from hbm_opt_integrated_20261005_gather import (
    ALLOCATOR_SHA256, extend_saved_installer_recipe,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reserve(book_path, allocator_path):
    original = json.loads(book_path.read_text())
    book = extend_saved_installer_recipe(book_path, allocator_path)
    tree = ast.parse(allocator_path.read_bytes())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Program')
    node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'put')
    scope = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(allocator_path), 'exec'), scope)
    allocations = book['recipe_successor']['allocations']
    state = SimpleNamespace(cur=max(a['end'] for a in allocations),
                            a={a['name']: a['base'] for a in original['allocation_envelopes']})
    state.a.update({a['name']: a['base'] for a in allocations})
    producer = 'tools/hbm_index_tp96_producer.py'
    spans = {}
    for name, size in (('LOCAL_SCORES', 2048), ('LOCAL_IDS', 2048),
                       ('FULL_SCORES', 196608), ('FULL_IDS', 196608)):
        base = scope['put'](state, 'HBM_INDEX_' + name, size, align=64)
        span = dict(name='HBM_INDEX_' + name, kind='source', base=base,
                    end=base + size, producer=producer, allocator='Program.put')
        allocations.append(span)
        spans[name] = span
    if state.cur > book['memory_bytes']:
        raise ValueError('Full sources exceed actual installed backing capacity')
    ranges = [(a['base'], a['end']) for a in allocations]
    if any(lo < original['original_image_bytes'] or lo % 64 or hi <= lo
           for lo, hi in ranges):
        raise ValueError('Successor altered protected prefix or alignment')
    if any(max(a[0], b[0]) < min(a[1], b[1])
           for i, a in enumerate(ranges) for b in ranges[i+1:]):
        raise ValueError('Successor spans overlap')
    book['index_local_sources'] = dict(scores=spans['LOCAL_SCORES'], ids=spans['LOCAL_IDS'])
    book['index_full_sources'] = dict(scores=spans['FULL_SCORES'], ids=spans['FULL_IDS'])
    # Local source buffers are separate occupied spans; full source ownership is
    # represented by the 192 accepted rank records in the hardware installer.
    book['occupied'].extend([spans['LOCAL_SCORES'], spans['LOCAL_IDS']])
    book['full_source_rank_records'] = [
        dict(kind=kind, rank=rank, base=spans[name]['base'] + rank * 2048,
             end=spans[name]['base'] + (rank + 1) * 2048)
        for kind, name in ((1, 'FULL_SCORES'), (2, 'FULL_IDS')) for rank in range(96)
    ]
    book['recipe_successor']['emitted_image_bytes'] = (state.cur + 4095) // 4096 * 4096
    book['unassigned_padding']['base'] = state.cur
    book['workspace_producer'] = 'tools/hbm_formatter_fullplane_install_recipe.py'
    book['workspace_producer_sha256'] = sha(Path(__file__))
    book['recipe_successor']['fullplane_reservation_only'] = True
    book['source_phase_required'] = 'L20.op14.index_scores.pre_candidate_mask.local_top512'
    book['missing_bindings'] = [
        '96 actual runtime producer publications and payload pins',
        'actual provider source installation and 6144 checked publication ACKs',
        'linked numerical consumer entry and private CMD descriptor bank',
        'parameterized preinstall/helper geometry matching this recipe',
    ]
    book['production_installation_complete'] = False
    book['source_pins'][str(book_path)] = sha(book_path)
    book['source_pins'][str(allocator_path)] = ALLOCATOR_SHA256
    return book


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--book', type=Path, required=True)
    parser.add_argument('--allocator', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    book = reserve(args.book, args.allocator)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'workspace.json').write_text(json.dumps(book, indent=2) + '\n')


if __name__ == '__main__':
    main()
