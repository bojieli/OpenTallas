#!/usr/bin/env python3
"""HBM-R16/ISL: build the standalone plan delta (isl_delta.json) from the chosen isl_plan.py results.

  build_delta.py OUT.json NAME=PLAN.json[:set_entry] ... [--kit-note MODULE=text]

Per type: in_core_islands + core_tree go into clock_entries (apply_isl_delta.py), core_islands_record is the
master_plan.py --core-islands form.  All insertion numbers are PLAN MODEL, UNCHECKED.
"""
import json, sys
from pathlib import Path


def main(argv):
    out = Path(argv[0]); types = {}; notes = {}
    for a in argv[1:]:
        if a.startswith('--kit-note='):
            m, t = a[len('--kit-note='):].split('=', 1); notes[m] = t; continue
        name, rest = a.split('=', 1)
        path, _, flag = rest.partition(':')
        R = json.loads(Path(path).read_text())
        isl = [dict(name=q['name'], centre_um=q['centre_lattice_um'], rect_um=q['rect_um'], load=q['load'],
                    load_frac=q['load_frac'], entry_maze_um=q['entry_maze_um'], reach_um=q['reach_um'],
                    clear_of_macros=q['clear_of_macros'],
                    island_rooted_pred=R['island_rooted_pred'].get(q['name'], {}).get('pred'))
               for q in R['islands']]
        em = [q['entry_maze_um'] for q in isl]
        rec = dict(method='HBM-R16/ISL isl_plan.py (core_infra_htree equal-structure tree; islands = level-%d node sites, '
                          'equal-count groups)' % R['island_level'],
                   k=len(isl), max_entry_um=max(em), entry_um=R['entry_um'], sinks=R['n_sinks'],
                   islands=[dict(centre_um=q['centre_um'], rect_um=q['rect_um'], load_frac=q['load_frac'],
                                 entry_maze_um=q['entry_maze_um'], reach_um=q['reach_um']) for q in isl],
                   entry_maze_um=dict(min=min(em), max=max(em)),
                   leaf_reach_um=max(q['reach_um']['p95'] for q in isl),
                   equal_path_um=R['path_wire_um'],
                   floor_entry_to_sink_maze_um=R['entry_to_farthest_sink_maze_um'],
                   verdict='PASS' if all(q['clear_of_macros'] for q in isl) and R['entry_island_clear'] else 'FAIL')
        tree = dict(rule='12.8a-c centre entry + structured tree; 12.8d1 plan-computed sizing; 12.2a1 pushdown islands',
                    splits=R['splits'], leaves=R['leaves'], leaf_load=R['leaf_load'], level_len_um=R['level_len_um'],
                    repeaters_per_edge=R['repeaters_per_edge'], stages_per_path=R['stages_per_path'],
                    path_wire_um=R['path_wire_um'], leaf_radius_um=R['leaf_radius_um'], trunk=R['trunk'],
                    drivers=R['drivers'],
                    pred_entry_rooted=dict(TT=R['pred']['TT'], FF=R['pred']['FF']),
                    pred_island_rooted={k: v for k, v in R['island_rooted_pred'].items() if k.startswith('_')},
                    in_band=R['in_band'], label='PLAN MODEL, UNCHECKED', plan_json=Path(path).name)
        types[R['module']] = dict(name=name, core_um=R['core_um'], entry_um=R['entry_um'],
                                  entry_island_um=R['entry_island_um'], macros=R['macros'], set_entry=(flag == 'set_entry'),
                                  in_core_islands=dict(source=rec['method'], islands=isl, leaf_reach_um=rec['leaf_reach_um'],
                                                       entry_maze_um=rec['entry_maze_um']),
                                  core_tree=tree, core_islands_record=rec,
                                  kit_note=notes.get(R['module'], ''),
                                  source_note='in-core islands/structured tree %s (plan model UNCHECKED)' % name)
    D = dict(schema='hbm_r16_isl_delta/1', lane='HBM-R16/ISL', types=types,
             apply='apply_isl_delta.py isl_delta.json PLAN_DIR (writes clock_entries.json in_core_islands/core_tree + core_islands.json)')
    out.write_text(json.dumps(D, indent=1) + '\n')
    for m, t in types.items():
        print(m, [q['centre_um'] for q in t['in_core_islands']['islands']], t['core_tree']['pred_entry_rooted']['TT']['grt_basis_mean'],
              t['core_tree']['pred_entry_rooted']['FF']['grt_basis_mean'], t['core_islands_record']['verdict'])


if __name__ == '__main__':
    main(sys.argv[1:])
