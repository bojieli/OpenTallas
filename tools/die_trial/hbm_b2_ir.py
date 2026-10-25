#!/usr/bin/env python3
"""PDNSim (OpenROAD analyze_power_grid) on the B2r2 die PG plan with the ESTIMATED power map (TRIAL-HBM step 4b).

    python3 tools/die_trial/hbm_b2_ir.py generate --plan PLAN.json --power power_map.json --out DIR
            [--window X0 Y0 X1 Y1] [--tile 43.2] [--scale 1] [--no-bumps X0 Y0 X1 Y1 ...]
    (docker) openroad -threads N -exit DIR/run.tcl > DIR/run.log
    python3 tools/die_trial/hbm_b2_ir.py record --out DIR

Method (the tile-current method of tools/hbm_die_ir_window.py, results/physical/die_iter_1012/r25gq/ir_1012):
- die PG = the plan's die.pg.grid: M8 (H) / M9 (V), width 0.48, pitch 8.64, offset 4.32, VDD + VSS (VSS half a pitch
  after VDD), M8-M9 vias at every same-net crossing.  --scale k (coarse full-die case) multiplies width AND pitch by k:
  the per-um-of-die conductance of each layer (width / pitch) is unchanged, so the sheet resistance of the grid is
  preserved; the grid only loses the fine spatial detail.
- partition PG is abstracted as the mock-LEF M7 stripes (gen_phys.mock_lef: VDD x = 4.128, VSS x = 4.512 mod 8.64,
  0.288 wide), on load tiles of <= --tile um (default 43.2 = 5 x 8.64, global die phase), M7-M8 vias where same-net
  stripes cross.  Each tile carries the power-map current over its area (PSM's single-node-per-instance injection
  makes big blocks unusable as loads).  The partitions' internal M5/M6/M7 grids and their IR are NOT modelled.
- C4 bumps: 45 um array, checkerboard per net (63.64 um per-rail pitch), 20 um, 0.7 V (the ir_1012 assumption), in
  die coordinates; --no-bumps rects remove the bumps there (signal-bump fields, sensitivity).
- a window is solved with a guard of two per-rail bump pitches; only nodes inside the inner window count.
"""
import argparse
import json
import math
import sys
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
VDD, ARRAY, BUMP, BUDGET_MV = 0.7, 45.0, 20.0, 35.0
VP = ARRAY / math.sqrt(0.5)
G = 8.64


def rects_power(pm):
    """[(x0, y0, x1, y1, W/um2)] with IO regions replacing the partition density (negative + positive overlay)."""
    out = []
    for p in pm["partitions"]:
        x0, y0, x1, y1 = p["rect_um"]
        out.append((x0, y0, x1, y1, p["w_per_mm2"] / 1e6))
    for s in pm["regions"]:
        x0, y0, x1, y1 = s["rect_um"]
        base = next(p["w_per_mm2"] for p in pm["partitions"] if p["name"] == s["part"]) / 1e6
        out.append((x0, y0, x1, y1, s["w_per_mm2"] / 1e6 - base))
    return out


def generate(a):
    pm = json.loads(Path(a.power).read_text())
    plan = json.loads(Path(a.plan).read_text())
    DW, DH = plan["die"]["outline_um"]
    g = plan["die"]["pg"]["grid"]
    assert [x["layer"] for x in g] == ["M8", "M9"], g
    wid, pitch, off = g[0]["width_um"] * a.scale, g[0]["pitch_um"] * a.scale, g[0]["offset_um"] * a.scale
    offx = g[1]["offset_um"] * a.scale
    x0, y0, x1, y1 = a.window or (0.0, 0.0, DW, DH)
    guard = 0 if not a.window else 2 * VP
    T = a.tile
    bx = max(0.0, math.floor((x0 - guard) / T) * T)
    by = max(0.0, math.floor((y0 - guard) / T) * T)
    ex, ey = min(DW, math.ceil((x1 + guard) / T) * T), min(DH, math.ceil((y1 + guard) / T) * T)
    w, h = ex - bx, ey - by
    nx, ny = math.ceil(w / T - 1e-6), math.ceil(h / T - 1e-6)
    # tile loads (die-phase tiles; the last row/column may be partial at the die edge)
    loads = {}
    for rx0, ry0, rx1, ry1, d in rects_power(pm):
        if rx1 <= bx or ry1 <= by or rx0 >= ex or ry0 >= ey:
            continue
        for j in range(max(0, int((ry0 - by) // T)), min(ny, int((ry1 - by) // T) + 1)):
            for i in range(max(0, int((rx0 - bx) // T)), min(nx, int((rx1 - bx) // T) + 1)):
                tx0, ty0 = bx + i * T, by + j * T
                ov = max(0, min(rx1, tx0 + T, ex) - max(rx0, tx0)) * max(0, min(ry1, ty0 + T, ey) - max(ry0, ty0))
                if ov > 0:
                    loads[(i, j)] = loads.get((i, j), 0.0) + d * ov
    loads = {k: v for k, v in loads.items() if v > 1e-12}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    # load masters: full tile + edge tiles (the die edge is not a multiple of T)
    sizes = {}
    for (i, j) in loads:
        tw = min(T, ex - (bx + i * T))
        th = min(T, ey - (by + j * T))
        sizes.setdefault((round(tw, 4), round(th, 4)), f"L{len(sizes)}")
    lef = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;']
    for (tw, th), name in sizes.items():
        lef += [f'MACRO {name}', ' CLASS BLOCK ;', ' ORIGIN 0 0 ;', f' SIZE {tw:.4f} BY {th:.4f} ;']
        for net, o in (("VDD", 4.128), ("VSS", 4.512)):
            lef += [f' PIN {net}', ' DIRECTION INOUT ;', f' USE {"POWER" if net == "VDD" else "GROUND"} ;', ' PORT', ' LAYER M7 ;']
            c = o
            while c + 0.144 < tw:
                lef.append(f'  RECT {c - 0.144:.4f} 0 {c + 0.144:.4f} {th:.4f} ;')
                c += G
            lef += [' END', f' END {net}']
        lef += [f'END {name}']
    lef += ['END LIBRARY']
    (out / 'loads.lef').write_text('\n'.join(lef) + '\n')
    d = ['VERSION 5.8 ;', 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', 'DESIGN hbm_b2_ir ;', 'UNITS DISTANCE MICRONS 1000 ;',
         f'DIEAREA ( 0 0 ) ( {round(w * 1000)} {round(h * 1000)} ) ;', f'COMPONENTS {len(loads)} ;']
    for (i, j) in loads:
        tw = round(min(T, ex - (bx + i * T)), 4)
        th = round(min(T, ey - (by + j * T)), 4)
        d.append(f'- T_{i}_{j} {sizes[(tw, th)]} + FIXED ( {round(i * T * 1000)} {round(j * T * 1000)} ) N ;')
    d += ['END COMPONENTS', 'END DESIGN']
    (out / 'case.def').write_text('\n'.join(d) + '\n')
    # bumps in die coordinates, shifted into the case frame
    nob = [a.no_bumps[k:k + 4] for k in range(0, len(a.no_bumps or []), 4)]
    nb = {}
    for net, ph in (("VDD", VP / 2), ("VSS", 0.0)):
        rows = []
        jy = math.ceil((by - ph) / VP)
        while ph + jy * VP <= ey:
            yy = ph + jy * VP
            ix = math.ceil((bx - ph) / VP)
            while ph + ix * VP <= ex:
                xx = ph + ix * VP
                if bx + 1 <= xx <= ex - 1 and by + 1 <= yy <= ey - 1 and \
                        not any(r[0] <= xx <= r[2] and r[1] <= yy <= r[3] for r in nob):
                    rows.append(f'{xx - bx:.4f}, {yy - by:.4f}, {BUMP:g}, {VDD if net == "VDD" else 0}\n')
                ix += 1
            jy += 1
        (out / f'vsrc_{net}.loc').write_text(''.join(rows))
        nb[net] = len(rows)
    # die-phase stripe offsets in the case frame (pdngen offset = from the core edge to the first stripe's edge?
    # we place the stripe CENTRE phase explicitly: centre = off + k * pitch in die coordinates)
    def ofs(base, phase):
        return (phase - base) % pitch          # pdngen 26Q3: -offset = the first stripe's CENTRE (checked: OT_STRIPE)
    sp = pitch / 2 - wid
    t = f'''read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/loads.lef
read_def /work/case.def
add_global_connection -net VDD -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net VSS -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name top -voltage_domains CORE
add_pdn_stripe -grid top -layer M8 -width {wid:.4f} -pitch {pitch:.4f} -spacing {sp:.4f} -offset {ofs(by, off):.4f} -starts_with POWER
add_pdn_stripe -grid top -layer M9 -width {wid:.4f} -pitch {pitch:.4f} -spacing {sp:.4f} -offset {ofs(bx, offx):.4f} -starts_with POWER
add_pdn_connect -grid top -layers {{M8 M9}}
define_pdn_grid -macro -name load -cells {{{" ".join(sizes.values())}}} -halo {{0 0 0 0}} -voltage_domains CORE
add_pdn_connect -grid load -layers {{M7 M8}}
set t0 [clock seconds]
pdngen -failed_via_report /work/failed_vias.rpt
puts "OT_PDN PASS [expr {{[clock seconds]-$t0}}] s"
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
source {PLAT}/setRC.tcl
set_cmd_units -power W
source /work/power.tcl
foreach net {{VDD VSS}} {{
  if {{[catch {{check_power_grid -net $net -error_file /work/pg_err_$net.rpt}} e]}} {{ puts "OT_PG net=$net FAIL $e" }} else {{ puts "OT_PG net=$net PASS" }}
  set_pdnsim_net_voltage -net $net -voltage [expr {{$net eq "VDD" ? {VDD} : 0}}]
  set t1 [clock seconds]
  analyze_power_grid -net $net -vsrc /work/vsrc_$net.loc -voltage_file /work/ir_$net.rpt -error_file /work/ir_err_$net.rpt
  puts "OT_IR net=$net PASS [expr {{[clock seconds]-$t1}}] s"
}}
set b [ord::get_db_block]
foreach n {{VDD VSS}} {{ set k 0; foreach sw [[$b findNet $n] getSWires] {{ foreach w [$sw getWires] {{ if {{$k < 3 && ![$w isVia] && [[$w getTechLayer] getName] in {{M8 M9}}}} {{ puts "OT_STRIPE $n [[$w getTechLayer] getName] [$w xMin] [$w yMin] [$w xMax] [$w yMax]"; incr k }} }} }} }}
puts OT_DONE
'''
    (out / 'run.tcl').write_text(t)
    (out / 'power.tcl').write_text(''.join(f'set_pdnsim_inst_power -inst T_{i}_{j} -power {p:.9g}\n' for (i, j), p in loads.items()))
    man = dict(schema='opentallas.die_trial.ir_case.v1', plan=a.plan, power=a.power, power_total_w=pm['total_w'],
               inner_um=[x0, y0, x1, y1], solved_um=[bx, by, ex, ey], guard_um=guard, tile_um=T,
               loads=len(loads), load_w=round(sum(loads.values()), 4),
               grid=dict(layers=['M8', 'M9'], width_um=wid, pitch_um=pitch, offset_um=off, offset_xy_um=[offx, off], scale=a.scale,
                         per_net_coverage=wid / pitch, plan_exact=a.scale == 1),
               partition_pg='mock-LEF M7 stripes (VDD 4.128 / VSS 4.512 mod 8.64, 0.288 um) on <= tile loads',
               bumps=dict(array_um=ARRAY, per_net_pitch_um=VP, size_um=BUMP, n=nb, removed_in=nob),
               voltage_v=VDD, budget_mv=BUDGET_MV)
    (out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print(json.dumps(man))


def record(a):
    out = Path(a.out)
    m = json.loads((out / 'manifest.json').read_text())
    log = (out / 'run.log').read_text(errors='replace') if (out / 'run.log').exists() else ''
    bx, by = m['solved_um'][:2]
    x0, y0, x1, y1 = m['inner_um']
    rails = {}
    for net in ('VDD', 'VSS'):
        f = out / f'ir_{net}.rpt'
        best, n, bi = None, 0, None
        DW, DH = m.get('die_um', [25194.24, 18316.8])
        if f.exists():
            with f.open() as fh:
                for line in fh:
                    c = line.split(',')
                    if len(c) < 6:
                        continue
                    try:
                        x, y, v = float(c[3]), float(c[4]), float(c[5])
                    except ValueError:
                        continue
                    X, Y = x + bx, y + by
                    if not (x0 <= X <= x1 and y0 <= Y <= y1):
                        continue
                    n += 1
                    dv = (VDD - v) if net == 'VDD' else v
                    if best is None or dv > best[0]:
                        best = (dv, X, Y, c[0].strip())
                    T = m['tile_um']
                    if min(X, Y, DW - X - T, DH - Y - T) >= VP and (bi is None or dv > bi[0]):
                        bi = (dv, X, Y, c[0].strip())
        rails[net] = dict(nodes=n, worst_mv=round(best[0] * 1000, 3) if best else None,
                          worst_at_um=[round(best[1], 2), round(best[2], 2)] if best else None,
                          worst_inst=best[3] if best else None,
                          interior_worst_mv=round(bi[0] * 1000, 3) if bi else None,
                          interior_worst_at_um=[round(bi[1], 2), round(bi[2], 2)] if bi else None)
    ok = all(r['worst_mv'] is not None for r in rails.values())
    s = sum(r['worst_mv'] for r in rails.values()) if ok else None
    si = sum(r['interior_worst_mv'] for r in rails.values()) if ok and all(r['interior_worst_mv'] is not None for r in rails.values()) else None
    r = dict(interior_rail_sum_mv=si, interior_note='tiles >= one per-rail bump pitch (63.64 um) from the die edge: '
             'the checkerboard bump lattice (VSS at k x 63.64, VDD at 31.82 + k x 63.64) loses its die-edge VSS row/column '
             '(x = 0 / y = 0), so edge tiles see one-sided bump support (edge artefact of the assumed bump map)',
             manifest=m, pdn_pass='OT_PDN PASS' in log,
             pg_connected={n: f'OT_PG net={n} PASS' in log for n in ('VDD', 'VSS')},
             done='OT_DONE' in log, rails=rails, rail_sum_mv=s,
             verdict=('NOT RUN' if not ok else ('PASS' if s <= BUDGET_MV else 'FAIL')),
             budget_mv=BUDGET_MV)
    (out / 'result.json').write_text(json.dumps(r, indent=1) + '\n')
    print(json.dumps({k: r[k] for k in ('pdn_pass', 'pg_connected', 'done', 'rails', 'rail_sum_mv', 'interior_rail_sum_mv', 'verdict')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('mode', choices=['generate', 'record'])
    p.add_argument('--plan')
    p.add_argument('--power')
    p.add_argument('--window', type=float, nargs=4)
    p.add_argument('--tile', type=float, default=43.2)
    p.add_argument('--scale', type=float, default=1.0)
    p.add_argument('--no-bumps', type=float, nargs='*', default=[])
    p.add_argument('--out', required=True)
    a = p.parse_args()
    (generate if a.mode == 'generate' else record)(a)
