#!/usr/bin/env python3
"""Die IR-drop check with M8 die signals present (ROOT14 10-20; owner 21:27: M8 open for die signals, keep regular PG
straps on M8, run the die IR-drop/power check and REPORT any problem to the owner -- never work around it silently).

Method (generalises tools/hbm_die_ir_window.py, the HBM B2 die-grid experiment, to every die):
  1. dump      in the die's OpenROAD session (post-GRT odb): every instance box -> insts.tsv  (Tcl from `dump-tcl`)
  2. generate  assumed peak power density per instance (default 1.2 W/mm2, --density {glob: W/mm2}, first match wins,
               0 = excluded e.g. off-die PHY), projected on 43.2-um load tiles; the K hottest windows (inner 1296 um +
               2-bump guard) each become an OpenROAD PDN case: M8 + M9 straps (width 0.48, per-net coverage
               --coverage, default 0.0878 = the HBM die grid), 45-um bump array, loads tie to the grid through M7.
               M8 SIGNALS: the GRT M8 usage (--grt-log table or --m8-usage) plus the two nets' strap coverage must fit
               M8 (<= 1.0) -- an over-subscribed M8 is a FAIL (signals would displace the regular straps).
  3. run       openroad -exit run.tcl per window (pdngen, check_power_grid, analyze_power_grid VDD + VSS)
  4. record    worst VDD drop + VSS bounce in each inner window; rail-to-rail bound <= --limit-mv (default 35 mV =
               5% of 0.7 V) -> PASS.  FAIL prints an OWNER_REPORT line (the coordinator tells the owner).
Assumptions are recorded (peak density assumed, not SAIF; child-internal IR and package not modelled): the result is
die-grid evidence, never a sign-off.

  ir_drop.py dump-tcl --out /work/ir/insts.tsv                 -> Tcl text (source it after read_db)
  ir_drop.py generate --insts insts.tsv --out DIR [--grt-log grt.log | --m8-usage 0.31] [--density d.json]
                      [--windows 3] [--window-um 1296] [--coverage 0.0878] [--limit-mv 35] [--design s81]
  ir_drop.py record --out DIR                                   -> DIR/ir_drop.json, one status line, exit 1 on FAIL
  tools/die_safety/ir_step.sh ODB OUTDIR [GRT_LOG]              -> all four steps (docker openroad/orfs:asap7lock)
"""
import argparse
import collections
import fnmatch
import json
import math
import re
import sys
from pathlib import Path

PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'
VDD, BUMP_ARRAY, BUMP_SIZE, TILE = 0.7, 45.0, 20.0, 43.2
DEFAULT_DENSITY = 1.2          # W/mm2 assumed peak (HBM DENS sm 1.20)
STRAP_W = 0.48
GRT_ROW = re.compile(r'^\s*(M\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s*%')


def dump_tcl(out):
    return f'''# ROOT14 die IR-drop step 1 (tools/die_safety/ir_drop.py): instance boxes of the die
proc ot_ir_dump {{path}} {{
  set blk [ord::get_db_block]; set u [$blk getDbUnitsPerMicron]; set f [open $path w]
  set d [$blk getDieArea]
  puts $f "#die\\t[expr {{[$d xMin]*1.0/$u}}]\\t[expr {{[$d yMin]*1.0/$u}}]\\t[expr {{[$d xMax]*1.0/$u}}]\\t[expr {{[$d yMax]*1.0/$u}}]"
  set n 0
  foreach i [$blk getInsts] {{
    set b [$i getBBox]
    puts $f "[$i getName]\\t[[$i getMaster] getName]\\t[expr {{[$b xMin]*1.0/$u}}]\\t[expr {{[$b yMin]*1.0/$u}}]\\t[expr {{[$b xMax]*1.0/$u}}]\\t[expr {{[$b yMax]*1.0/$u}}]"
    incr n
  }}
  close $f; puts "OT_IR_DUMP insts=$n"; flush stdout
}}
file mkdir [file dirname {out}]
ot_ir_dump {out}
'''


def read_insts(p):
    die, insts = None, []
    for ln in Path(p).read_text().splitlines():
        f = ln.split('\t')
        if f[0] == '#die':
            die = tuple(map(float, f[1:5]))
        elif len(f) >= 6 and not ln.startswith('#'):
            insts.append((f[0], f[1], *map(float, f[2:6])))
    if die is None:
        raise SystemExit(f'ir_drop: no #die line in {p}')
    return die, insts


def m8_usage_from_log(text):
    """GRT final usage table: 'M8  resource demand usage%' -> usage fraction (last table in the log wins)"""
    u = None
    for ln in text.splitlines():
        m = GRT_ROW.match(ln)
        if m and m.group(1) == 'M8':
            u = float(m.group(4)) / 100.0
    return u


def density_of(master, name, table):
    for g, v in table.items():
        if fnmatch.fnmatch(master, g) or fnmatch.fnmatch(name, g):
            return float(v)
    return float(table.get('default', DEFAULT_DENSITY))


def power_map(die, insts, table):
    dx0, dy0, dx1, dy1 = die
    nx, ny = max(1, math.ceil((dx1 - dx0) / TILE)), max(1, math.ceil((dy1 - dy0) / TILE))
    grid = collections.defaultdict(float)
    total = 0.0
    for n, m, x0, y0, x1, y1 in insts:
        dens = density_of(m, n, table) * 1e-6        # W/um2
        if dens <= 0 or x1 <= x0 or y1 <= y0:
            continue
        total += dens * (x1 - x0) * (y1 - y0)
        for j in range(max(0, int((y0 - dy0) // TILE)), min(ny, int((y1 - dy0) // TILE) + 1)):
            for i in range(max(0, int((x0 - dx0) // TILE)), min(nx, int((x1 - dx0) // TILE) + 1)):
                ov = (max(0.0, min(x1, dx0 + (i + 1) * TILE) - max(x0, dx0 + i * TILE)) *
                      max(0.0, min(y1, dy0 + (j + 1) * TILE) - max(y0, dy0 + j * TILE)))
                if ov:
                    grid[(i, j)] += dens * ov
    return grid, (nx, ny), total


def hot_windows(grid, nxy, die, k, win_um):
    """greedy K non-overlapping windows (win_um square) with the highest power, on a TILE grid"""
    nx, ny = nxy
    s = max(1, int(round(win_um / TILE)))
    pre = [[0.0] * (ny + 1) for _ in range(nx + 1)]
    for i in range(nx):
        for j in range(ny):
            pre[i + 1][j + 1] = grid.get((i, j), 0.0) + pre[i][j + 1] + pre[i + 1][j] - pre[i][j]
    cands = []
    step = max(1, s // 2)
    for i in range(0, max(1, nx - s + 1), step):
        for j in range(0, max(1, ny - s + 1), step):
            i1, j1 = min(nx, i + s), min(ny, j + s)
            cands.append((pre[i1][j1] - pre[i][j1] - pre[i1][j] + pre[i][j], i, j, i1, j1))
    cands.sort(reverse=True)
    out = []
    for p, i, j, i1, j1 in cands:
        if p <= 0 or len(out) >= k:
            break
        if any(not (i1 <= a or i >= c or j1 <= b or j >= d) for _, a, b, c, d in out):
            continue
        out.append((p, i, j, i1, j1))
    dx0, dy0 = die[0], die[1]
    return [dict(power_w=p, inner_um=[dx0 + i * TILE, dy0 + j * TILE, dx0 + i1 * TILE, dy0 + j1 * TILE]) for p, i, j, i1, j1 in out]


def window_case(wdir, die, grid, inner, coverage):
    """one OpenROAD PDN case (as tools/hbm_die_ir_window.py): loads.lef, window.def, vsrc_{VDD,VSS}.loc, run.tcl"""
    vp = BUMP_ARRAY / math.sqrt(0.5)
    guard = 2 * vp
    x0, y0, x1, y1 = inner
    dx0, dy0, dx1, dy1 = die
    bx = max(dx0, math.floor((x0 - guard) / vp) * vp)
    by = max(dy0, math.floor((y0 - guard) / vp) * vp)
    ex, ey = min(dx1, x1 + guard), min(dy1, y1 + guard)
    w, h = ex - bx, ey - by
    nx, ny = max(1, math.ceil(w / TILE)), max(1, math.ceil(h / TILE))
    tw, th = w / nx, h / ny
    loads = {}
    for j in range(ny):
        for i in range(nx):
            gx, gy = int((bx - dx0 + (i + 0.5) * tw) // TILE), int((by - dy0 + (j + 0.5) * th) // TILE)
            p = grid.get((gx, gy), 0.0) * (tw * th) / (TILE * TILE)
            if p > 0:
                loads[(i, j)] = p
    wdir.mkdir(parents=True, exist_ok=True)
    lef = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', 'MACRO ot_ir_load', ' CLASS BLOCK ;',
           ' SYMMETRY X Y ;', f' SIZE {tw:.6f} BY {th:.6f} ;']
    for net, off in (('VDD', 1.35), ('VSS', 4.05)):
        lef += [f' PIN {net}', ' DIRECTION INOUT ;', f' USE {"POWER" if net == "VDD" else "GROUND"} ;', ' PORT', ' LAYER M7 ;']
        xx = off
        while xx + .288 < tw:
            lef.append(f' RECT {xx:.6f} 0.1 {xx + .288:.6f} {th - .1:.6f} ;')
            xx += 5.4
        lef += [' END', f' END {net}']
    lef += ['END ot_ir_load', 'END LIBRARY']
    (wdir / 'loads.lef').write_text('\n'.join(lef) + '\n')
    d = ['VERSION 5.8 ;', 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', 'DESIGN ot_die_ir ;', 'UNITS DISTANCE MICRONS 1000 ;',
         f'DIEAREA ( 0 0 ) ( {round(w * 1000)} {round(h * 1000)} ) ;', f'COMPONENTS {len(loads)} ;']
    d += [f'- L_{i}_{j} ot_ir_load + FIXED ( {round(i * tw * 1000)} {round(j * th * 1000)} ) N ;' for i, j in loads]
    d += ['END COMPONENTS', 'END DESIGN']
    (wdir / 'window.def').write_text('\n'.join(d) + '\n')
    raw = math.floor((STRAP_W / coverage) / .16) * .16
    div = math.ceil(vp / raw)
    div += (div % 2 == 0)
    pitch = round(vp / div / .004) * .004
    offset = round(((vp / 2) % pitch) / .004) * .004
    for net, phase in (('VDD', vp / 2), ('VSS', 0)):
        sites = []
        yy = phase if phase else vp
        while yy < h - 1:
            xx = phase if phase else vp
            while xx < w - 1:
                sites.append(f'{xx:.6f}, {yy:.6f}, {BUMP_SIZE}, {VDD if net == "VDD" else 0}\n')
                xx += vp
            yy += vp
        (wdir / f'vsrc_{net}.loc').write_text(''.join(sites))
    t = f'''# ROOT14 die IR-drop window (tools/die_safety/ir_drop.py)
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/loads.lef
read_def /work/window.def
add_global_connection -net VDD -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net VSS -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name top -voltage_domains CORE
add_pdn_stripe -grid top -layer M8 -width {STRAP_W} -pitch {pitch:.6f} -spacing {pitch / 2 - STRAP_W:.6f} -offset {offset:.6f}
add_pdn_stripe -grid top -layer M9 -width {STRAP_W} -pitch {pitch:.6f} -spacing {pitch / 2 - STRAP_W:.6f} -offset {offset:.6f}
add_pdn_connect -grid top -layers {{M8 M9}}
define_pdn_grid -macro -name load -cells {{^ot_ir_load$}} -halo {{0 0 0 0}} -voltage_domains CORE
add_pdn_connect -grid load -layers {{M7 M8}}
pdngen -failed_via_report /work/failed_vias.rpt
puts {{OT_PDN PASS}}
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
set_cmd_units -power W
source {PLAT}/setRC.tcl
'''
    t += '\n'.join(f'set_pdnsim_inst_power -inst L_{i}_{j} -power {p:.12f}' for (i, j), p in loads.items())
    t += f'''
foreach net {{VDD VSS}} {{
check_power_grid -net $net -error_file /work/pg_err_$net.rpt
puts "OT_PG net=$net PASS"
set_pdnsim_net_voltage -net $net -voltage [expr {{$net eq "VDD" ? {VDD} : 0}}]
analyze_power_grid -net $net -vsrc /work/vsrc_$net.loc -voltage_file /work/ir_$net.rpt -error_file /work/ir_err_$net.rpt
puts "OT_IR net=$net PASS"
}}
puts OT_DONE
'''
    (wdir / 'run.tcl').write_text(t)
    return dict(inner_um=list(inner), solved_um=[bx, by, ex, ey], loads=len(loads), peak_w=sum(loads.values()),
                strap_pitch_um=pitch, coverage_per_net=STRAP_W / pitch)


def generate(a):
    die, insts = read_insts(a.insts)
    table = json.loads(Path(a.density).read_text()) if a.density else {}
    m8u = a.m8_usage
    if m8u is None and a.grt_log:
        m8u = m8_usage_from_log(Path(a.grt_log).read_text(errors='replace'))
    grid, nxy, total = power_map(die, insts, table)
    wins = hot_windows(grid, nxy, die, a.windows, a.window_um)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cases = []
    for k, w in enumerate(wins):
        c = window_case(out / f'w{k}', die, grid, w['inner_um'], a.coverage)
        c.update(name=f'w{k}', window_power_w=round(w['power_w'], 4))
        cases.append(c)
    m8 = dict(signal_usage=m8u, strap_coverage_both_nets=round(2 * STRAP_W / cases[0]['strap_pitch_um'], 4) if cases else None)
    m8['total'] = round(m8u + m8['strap_coverage_both_nets'], 4) if (m8u is not None and cases) else None
    m8['verdict'] = ('UNKNOWN (no GRT M8 usage given)' if m8['total'] is None else 'PASS' if m8['total'] <= 1.0 else 'FAIL')
    man = dict(schema='opentallas.die_ir_drop.v1', design=a.design, die_um=list(die), instances=len(insts),
               die_peak_w=round(total, 3), density_table=table or {'default': DEFAULT_DENSITY}, limit_mv=a.limit_mv,
               voltage_v=VDD, coverage=a.coverage, windows=cases, m8=m8,
               limitations=['Peak power density is assumed, not SAIF measured.',
                            'Die-grid loads tie in through M7; child-internal IR / leaf PG access not modelled.',
                            'M8 signal demand enters as a capacity check (GRT usage + strap coverage <= 1), not as via blockage.',
                            'Package / bump impedance not modelled.'],
               final_signoff_eligible=False)
    (out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f"DIE_IR_GEN windows={len(cases)} die_peak_w={man['die_peak_w']} m8={m8['verdict']}")
    return 0 if cases else 1


def _worst(rpt, inner, solved, net):
    x0, y0, x1, y1 = inner
    bx, by = solved[0], solved[1]
    worst, n = None, 0
    for ln in Path(rpt).read_text().splitlines()[1:]:
        c = ln.split(',')
        if len(c) < 6:
            continue
        try:
            x, y, v = map(float, c[3:6])
        except ValueError:
            continue
        if x0 <= x + bx <= x1 and y0 <= y + by <= y1:
            d = (VDD - v) if net == 'VDD' else v
            worst = d if worst is None else max(worst, d)
            n += 1
    return worst, n


def record(a):
    out = Path(a.out)
    man = json.loads((out / 'manifest.json').read_text())
    rows, problems = [], []
    for c in man['windows']:
        wd = out / c['name']
        log = (wd / 'run.log').read_text(errors='replace') if (wd / 'run.log').exists() else ''
        rc = (wd / 'run.exit').read_text().strip() if (wd / 'run.exit').exists() else None
        r = dict(name=c['name'], inner_um=c['inner_um'], exit=rc, done='OT_DONE' in log, pdn='OT_PDN PASS' in log,
                 grid_connected=all(f'OT_PG net={n} PASS' in log for n in ('VDD', 'VSS')))
        tot = 0.0
        for net in ('VDD', 'VSS'):
            p = wd / f'ir_{net}.rpt'
            wv, n = _worst(p, c['inner_um'], c['solved_um'], net) if p.exists() else (None, 0)
            r[f'{net}_worst_mv'] = None if wv is None else round(wv * 1000, 2)
            r[f'{net}_nodes'] = n
            tot = None if (tot is None or wv is None) else tot + wv * 1000
        r['rail_to_rail_mv'] = None if tot is None else round(tot, 2)
        if not (rc == '0' and r['done'] and r['rail_to_rail_mv'] is not None):
            problems.append(f"{c['name']}: solver not complete (exit {rc}, done {r['done']}, pdn {r['pdn']}, grid {r['grid_connected']})")
        elif r['rail_to_rail_mv'] > man['limit_mv']:
            problems.append(f"{c['name']}: IR drop {r['rail_to_rail_mv']} mV > limit {man['limit_mv']} mV at {c['inner_um']}")
        rows.append(r)
    if man['m8']['verdict'] == 'FAIL':
        problems.append(f"M8 over-subscribed: GRT signal usage {man['m8']['signal_usage']} + strap coverage "
                        f"{man['m8']['strap_coverage_both_nets']} = {man['m8']['total']} > 1.0")
    worst = max((r['rail_to_rail_mv'] for r in rows if r['rail_to_rail_mv'] is not None), default=None)
    incomplete = any('solver not complete' in p for p in problems)
    verdict = 'NOT_RUN' if not rows else ('FAIL' if problems else 'PASS')
    res = dict(schema='opentallas.die_ir_drop.result.v1', design=man.get('design'), verdict=verdict, worst_mv=worst,
               limit_mv=man['limit_mv'], m8=man['m8'], windows=rows, problems=problems, incomplete=incomplete,
               owner_report=(verdict != 'PASS'), final_signoff_eligible=False, limitations=man['limitations'])
    (out / 'ir_drop.json').write_text(json.dumps(res, indent=1) + '\n')
    line = (f"DIE_IR_DROP {verdict} design={man.get('design')} worst={worst} mV limit={man['limit_mv']} mV "
            f"windows={len(rows)} m8={man['m8']['verdict']}")
    print(line + ('' if verdict == 'PASS' else ' | ' + ' | '.join(problems)))
    if verdict != 'PASS':
        print(f"OWNER_REPORT die IR-drop {verdict} ({man.get('design')}): " + ('; '.join(problems) or 'no window solved')
              + f" -- {out / 'ir_drop.json'} (coordinator: tell the owner; do not work around it)")
    return 0 if verdict == 'PASS' else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('dump-tcl'); d.add_argument('--out', required=True)
    g = sub.add_parser('generate')
    g.add_argument('--insts', required=True); g.add_argument('--out', required=True)
    g.add_argument('--grt-log'); g.add_argument('--m8-usage', type=float)
    g.add_argument('--density', help='JSON {glob: W/mm2}; "default" key = the rest (1.2)')
    g.add_argument('--windows', type=int, default=3); g.add_argument('--window-um', type=float, default=1296.0)
    g.add_argument('--coverage', type=float, default=.0878); g.add_argument('--limit-mv', type=float, default=35.0)
    g.add_argument('--design')
    r = sub.add_parser('record'); r.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'dump-tcl':
        sys.stdout.write(dump_tcl(a.out))
        return 0
    return generate(a) if a.cmd == 'generate' else record(a)


if __name__ == '__main__':
    sys.exit(main())
