#!/usr/bin/env python3
"""Regroup a die pdn.tcl (write_pdn_r5) onto an M8 lattice that is a multiple of the macro-origin lattice
(compute-die lead r3, 2026-10-14).

WHY: r5 puts every instance whose M8 stripe phase ((-y) mod pitch) is equal into one macro grid.  The core pitch is
bump-aligned (63.64 / 7 = 9.091 um) and every instance origin sits on the 2.16-um lattice, so the phases are spread
uniformly: the split compute C3 case had 13,509 instances in 2,365 macro grids and pdngen ran > 5 h single-threaded
(merged-die r18/r19 PDN 0.96-1.3 h).  Only the M9 stripes (the bump layer, `-pins {M9}`) need the bump pitch; the
horizontal M8 stripes connect the elements' M7 straps to M9 and may take any pitch.  r6 = M8 (core AND macro grids)
at P8 = k x 2.16 um (default 8.64 = 4 x 2.16: M8 PG coverage 11.1 % vs 10.56 % at 9.091, more metal, never less),
M9 unchanged: every instance phase is one of P8 / 2.16 values, so the macro grids collapse to <= 4 (+ the PHY M5
grids, kept as they are).  Same stripes per instance (one M8 lattice everywhere: macro stripes land on core stripes),
same connects.

MEASURED (C3 case, 13,509 instances): pdngen inserts ~32 instance grids a minute whatever the grouping (r5 2,365
grids and r6 4 grids alike), so the r5 case PDN is ~7 h single-threaded.  r7 = r6 + `--skip-prefix rly_`: the die
relays get no macro grid.  The core M8 / M9 lattice runs over them either way (the macro M8 stripes of r6 lie on the
core stripes), so GRT resources are unchanged; only the relays' M7 -> M8 vias are missing: check_power_grid reports
the relays as islands (a recorded PDN scope item, not a timing input).

    python3 tools/qwen_split/pdn_regroup.py CASE_DIR [--p8 8.64] [--out pdn_r6.tcl] [--skip-prefix rly_]
reads CASE_DIR/pdn.tcl + CASE_DIR/floorplan_placed.def, writes CASE_DIR/<out> and prints a JSON summary.
"""
import argparse, json, re
from pathlib import Path

GY = 2.16


def placed(def_path):
    pos, unit = {}, 1000.0
    f = False
    for line in open(def_path):
        if line.startswith('UNITS DISTANCE MICRONS'):
            unit = float(line.split()[3])
        elif line.startswith('COMPONENTS'):
            f = True
        elif line.startswith('END COMPONENTS'):
            break
        elif f and ('PLACED' in line or 'FIXED' in line):
            t = line.split()
            i = t.index('(')
            pos[t[1]] = (float(t[i + 1]) / unit, float(t[i + 2]) / unit)
    return pos


def regroup(case, p8, out, skip_prefix=(), pos_json=None):
    case = Path(case)
    src = (case / 'pdn.tcl').read_text().split('\n')
    if pos_json:      # before the real case has placed the die: the build's own instance origins (rom_tp8b.json)
        pos = {i['n']: (i['x'], i['y']) for i in json.loads(Path(pos_json).read_text())['insts']}
    else:
        pos = placed(case / 'floorplan_placed.def')
    if abs(p8 / GY - round(p8 / GY)) > 1e-9:
        raise SystemExit(f'--p8 {p8} is not a multiple of the {GY}-um macro lattice')
    head, m8, m5 = [], [], []
    cur = None
    for line in src:
        if line.startswith('define_pdn_grid -macro'):
            pats = re.search(r'-instances \{([^}]*)\}', line).group(1).split()
            names = [p.strip('^$') for p in pats]
            cur = dict(names=names, lines=[line])
            (m5 if re.search(r'-name pg_m5_', line) else m8).append(cur)
        elif cur is not None and line.startswith(('add_pdn_stripe -grid pg_', 'add_pdn_connect -grid pg_')):
            cur['lines'].append(line)
        elif line.strip():
            cur = None
            head.append(line)
    core_m8 = [i for i, l in enumerate(head) if l.startswith('add_pdn_stripe -grid core -layer M8')]
    if len(core_m8) != 1:
        raise SystemExit('expected one core M8 stripe line')
    head[core_m8[0]] = re.sub(r'-pitch [0-9.]+', f'-pitch {p8:.3f}', head[core_m8[0]])
    head[0] = '# r6 full-die PDN (tools/qwen_split/pdn_regroup.py): M8 core + macro stripes at %.3f um = %d x %.2f-um macro lattice (one phase per lattice row class), M9 bump pitch unchanged' % (p8, round(p8 / GY), GY)
    groups, missing = {}, []
    skipped = 0
    for g in m8:
        for n in g['names']:
            if skip_prefix and n.startswith(tuple(skip_prefix)):
                skipped += 1
                continue
            if n not in pos:
                missing.append(n)
                continue
            groups.setdefault(round((-pos[n][1]) % p8, 3) % round(p8, 3), []).append(n)
    if missing:
        raise SystemExit(f'{len(missing)} grid instances not in the placed DEF, e.g. {missing[:3]}')
    L = list(head)
    for j, (off, names) in enumerate(sorted(groups.items())):
        g = f'pg_m8_{j}'
        L.append(f'define_pdn_grid -macro -instances {{{" ".join("^" + n + "$" for n in sorted(names))}}} -voltage_domains CORE '
                 f'-name {g} -starts_with GROUND -grid_over_boundary')
        L += [f'add_pdn_stripe -grid {g} -layer M8 -width .48 -pitch {p8:.3f} -offset {off:.3f}',
              f'add_pdn_connect -grid {g} -layers {{M7 M8}}', f'add_pdn_connect -grid {g} -layers {{M8 M9}}']
    for g in m5:
        L += g['lines']
    (case / out).write_text('\n'.join(L) + '\n')
    return dict(case=str(case), out=out, p8=p8, m8_grids_before=len(m8), m8_grids_after=len(groups),
                m5_grids=len(m5), instances=sum(len(v) for v in groups.values()), skipped_no_macro_grid=skipped,
                skip_prefix=list(skip_prefix),
                phases={str(k): len(v) for k, v in sorted(groups.items())})


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('case')
    ap.add_argument('--p8', type=float, default=8.64)
    ap.add_argument('--out', default='pdn_r6.tcl')
    ap.add_argument('--skip-prefix', action='append', default=[],
                    help='instances (name prefix) that get NO macro grid (r7: rly_ -- see the module note)')
    ap.add_argument('--pos', help='instance origins from the build (OUT/rom_tp8b.json) instead of the placed DEF')
    a = ap.parse_args()
    print(json.dumps(regroup(a.case, a.p8, a.out, a.skip_prefix, a.pos)))
