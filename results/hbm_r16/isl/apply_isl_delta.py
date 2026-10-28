#!/usr/bin/env python3
"""HBM-R16/ISL: apply the in-core island / structured-tree delta to an HBM plan directory (clock_entries.json).

  apply_isl_delta.py DELTA.json PLAN_DIR [--dry-run]

For every clock_entries[partition][tap] whose module is in delta.types:
  * the plan entry must equal delta entry_um (|dx|+|dy| <= 1 um) -- else REFUSED (re-site first; a plan whose entry
    moved needs a re-run of isl_plan.py, never a silent re-use); with set_entry=true in the type record the delta's
    entry/island replaces the plan's (calendar: same coordinates as C16r, recorded explicitly);
  * adds in_core_islands (master_plan.py --core-islands form: centre_um/rect_um/load_frac/entry_maze_um) and
    core_tree (splits, fixed trunk, level lengths, repeaters, predicted insertion, UNCHECKED) to the entry.
Also writes PLAN_DIR/core_islands.json ({module: core_islands record}, the master_plan.py --core-islands input) and
PLAN_DIR/isl_delta_report.json.  Geometry checks: every island inside the core outline, island squares do not
overlap each other, the entry island, or any core macro (core_macros.json if present + the delta's macros; halo 0,
the island rect itself is the macro/placement blockage).  Writes nothing on any FAIL.
"""
import argparse, json, sys
from pathlib import Path


def ov(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('delta'); ap.add_argument('plan_dir'); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    D = json.loads(Path(a.delta).read_text())
    pd = Path(a.plan_dir)
    ce_p = pd / 'clock_entries.json'
    ce = json.loads(ce_p.read_text())
    cm = {}
    if (pd / 'core_macros.json').exists():
        cm = json.loads((pd / 'core_macros.json').read_text())
    fails, rows, applied = [], [], {}
    for mod, t in D['types'].items():
        core = t['core_um']
        isl = t['in_core_islands']['islands']
        ent = t['entry_island_um']
        macros = [m['rect_um'] for m in t.get('macros', [])]
        mm = (cm.get('cores') or cm).get(mod) if isinstance(cm, dict) else None
        if isinstance(mm, dict):
            mm = mm.get('macros', mm.get('rects', []))
        for m in (mm or []):
            r = m.get('rect_um') if isinstance(m, dict) else m
            if r and len(r) == 4:
                macros.append(r)
        rects = [q['rect_um'] for q in isl]
        for i, r in enumerate(rects):
            if not (r[0] >= core[0] and r[1] >= core[1] and r[2] <= core[2] and r[3] <= core[3]):
                fails.append((mod, f'island {i} outside core'))
            if ov(r, ent):
                fails.append((mod, f'island {i} overlaps the entry island'))
            for j in range(i + 1, len(rects)):
                if ov(r, rects[j]):
                    fails.append((mod, f'islands {i},{j} overlap'))
            for m in macros:
                if ov(r, m):
                    fails.append((mod, f'island {i} overlaps macro {m}'))
        for m in macros:
            if ov(ent, m):
                fails.append((mod, f'entry island overlaps macro {m}'))
        n = 0
        for part, d in ce.items():
            for tap, e in d.items():
                if e.get('module') != mod:
                    continue
                n += 1
                dx = abs(e['xy_um'][0] - t['entry_um'][0]) + abs(e['xy_um'][1] - t['entry_um'][1])
                if dx > 1.0 and not t.get('set_entry'):
                    fails.append((mod, f'{part}/{tap}: plan entry {e["xy_um"]} != delta entry {t["entry_um"]} (re-site)'))
                    continue
                new = dict(e)
                if t.get('set_entry'):
                    new['xy_um'] = list(t['entry_um']); new['island_um'] = list(ent)
                new['in_core_islands'] = t['in_core_islands']
                new['core_tree'] = t['core_tree']
                new['source'] = e.get('source', '') + ' | HBM-R16/ISL: ' + t['source_note']
                applied.setdefault(part, {})[tap] = new
                rows.append(dict(partition=part, tap=tap, module=mod, entry_moved_um=round(dx, 3)))
        if n == 0:
            fails.append((mod, 'module not in clock_entries.json'))
    rep = dict(delta=str(a.delta), plan_dir=str(pd), applied=len(rows), rows=rows,
               types={m: len([r for r in rows if r['module'] == m]) for m in D['types']},
               fails=[dict(module=m, issue=s) for m, s in fails], verdict='PASS' if not fails else 'FAIL')
    print(json.dumps({k: rep[k] for k in ('applied', 'types', 'fails', 'verdict')}, indent=1))
    if fails or a.dry_run:
        return 1 if fails else 0
    for part, d in applied.items():
        ce[part].update(d)
    ce_p.write_text(json.dumps(ce) + '\n')
    ci_p = pd / 'core_islands.json'
    ci = json.loads(ci_p.read_text()) if ci_p.exists() else {}
    for mod, t in D['types'].items():
        ci[mod] = t['core_islands_record']
    ci_p.write_text(json.dumps(ci, indent=1) + '\n')
    (pd / 'isl_delta_report.json').write_text(json.dumps(rep, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
