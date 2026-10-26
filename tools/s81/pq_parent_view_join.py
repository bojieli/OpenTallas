#!/usr/bin/env python3
"""Join an actual elaborated PQ hierarchy to immutable routed view candidates.

The packet is a conservation inventory. A name match is never a source,
parameter, native-pin, orientation, clock or parent-placement qualification.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--hierarchy', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--commit', default='HEAD')
    a = p.parse_args()
    commit = git('rev-parse', a.commit).decode().strip()
    h = json.loads(a.hierarchy.read_text())
    paths = git('ls-tree', '-r', '--name-only', commit, 'physical').decode().splitlines()
    names = {c['original_master'] for c in h['actual_cells']}
    candidates = {n: [] for n in names}
    for path in paths:
        if not path.endswith('/abstract.json') or '/views/' not in path:
            continue
        master = path.split('/')[-2]
        if master not in candidates:
            continue
        raw = git('show', commit + ':' + path)
        abstract = json.loads(raw)
        spec_path = path.split('/views/')[0] + '/spec.json'
        try:
            spec = json.loads(git('show', commit + ':' + spec_path))
        except subprocess.CalledProcessError:
            spec = {}
        checks = abstract.get('verdict', {}).get('check', {})
        candidates[master].append(dict(
            view=str(Path(path).parent), abstract_sha256=hashlib.sha256(raw).hexdigest(),
            replayed_verdict=bool(checks) and all(v.get('ok') for v in checks.values()),
            route_source=abstract.get('orfs_dir'), outline=spec.get('outline'),
            params=spec.get('params', {}), defines=spec.get('defines', []),
            source_paths=spec.get('sources', []), qualified_for_this_instance=False))
    # The two mapped memories are hard IP with their actual functional models.
    memories = {'ot_rom_4096x72_m8', 'ot_sram_1r1w_128x256_m1_r2c2'}
    frontier, expanded, uncovered = [], [], []
    cells = h['actual_cells']
    for c in sorted(cells, key=lambda c: (c['hier'].count('.'), c['hier'])):
        hierarchy = c['hier']
        if any(hierarchy.startswith(x['hier'] + '.') for x in frontier):
            continue
        master = c['original_master']
        item = dict(hier=hierarchy, original_master=master, elaborated_master=c['submodname'])
        if candidates[master] or master in memories:
            item.update(kind='mapped_memory' if master in memories else 'routed_view_candidates',
                        candidates=candidates[master], qualified_for_this_instance=False)
            frontier.append(item)
        elif any(x['hier'].startswith(hierarchy + '.') for x in cells):
            expanded.append(item)
        else:
            uncovered.append(item)
    record = dict(schema='opentallas.s81.pq-parent-conservation.v1',
                  hierarchy_sha256=hashlib.sha256(a.hierarchy.read_bytes()).hexdigest(),
                  view_commit=commit, manifest=h.get('manifest'), defines=h['defines'],
                  frontier=frontier, expanded_parents=expanded, uncovered_terminal_cells=uncovered,
                  frontier_counts=dict(Counter(x['original_master'] for x in frontier)),
                  uncovered_counts=dict(Counter(x['original_master'] for x in uncovered)),
                  source_module_census=h.get('module_census'),
                  qualification=dict(native_parent=False, source_parameter_match=False,
                                     actual_pin_clock_join=False, placement=False,
                                     complete_normal_token_calendar=False))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(dict(frontier=record['frontier_counts'], uncovered=record['uncovered_counts'])))


if __name__ == '__main__':
    main()
