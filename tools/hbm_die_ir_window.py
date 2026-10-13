#!/usr/bin/env python3
"""Pinned HBM B2 current map and independent M8/M9 PDN window experiment.

This measures the die grid with distributed loads, not child internal IR or
signal/PG via access. Missing PG abstracts and assumed power stay explicit.
The input model/LEF are never modified; OpenROAD runs on a new window case.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'
DENS = dict(sm=1.20, svc=3.924, hub=1.05, spine=1.05,
            attn_tile=1.05, waypoint=0.6)
EXCLUDED = ('phy', 'link', 'serdes_slab', 'host_slab')
VDD, BUMP_ARRAY, BUMP_SIZE, TILE = 0.7, 45.0, 20.0, 43.2


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    p = Path(path)
    b = p.read_bytes()
    return json.loads(gzip.decompress(b) if p.suffix == '.gz' else b)


def pg_audit(path):
    """Top PG layers from the actual source abstract, not the load projection."""
    out, master, pin, layer = {}, None, None, None
    for line in Path(path).open():
        s = line.strip()
        if s.startswith('MACRO '):
            master = s.split()[1]
            out[master] = dict(VDD=set(), VSS=set())
        elif s.startswith('PIN '):
            pin = s.split()[1]
        elif s.startswith('LAYER '):
            layer = s.split()[1]
        elif s.startswith('RECT ') and master and pin in ('VDD', 'VSS'):
            out[master][pin].add(layer)
        elif pin and s == 'END ' + pin:
            pin = None
        elif master and s == 'END ' + master:
            master = None
    return {k: {n: sorted(v) for n, v in nets.items()} for k, nets in out.items()}


def generate(a):
    m = read(a.model)
    pg = pg_audit(a.lef)
    if a.pg_lef:
        pg.update(pg_audit(a.pg_lef))
    vp = BUMP_ARRAY / math.sqrt(0.5)
    x0, y0, x1, y1 = a.window
    guard = 2 * vp
    dw, dh = m['outline_um']
    # Keep global bump/strap phase across every independent window.
    bx = max(0, math.floor((x0 - guard) / vp) * vp)
    by = max(0, math.floor((y0 - guard) / vp) * vp)
    ex, ey = min(dw, x1 + guard), min(dh, y1 + guard)
    w, h = ex - bx, ey - by
    power, missing, layers, by_kind = [], [], collections.Counter(), collections.Counter()
    for it in m['insts']:
        n, master, kind, region, domain, x, y, iw, ih, orient = it
        p = 0 if kind in EXCLUDED else (1.25 if n == 'hb_index' else DENS.get(kind, 0)) * (iw + .024) * (ih + .024) / 1e6
        if p:
            entry = dict(instance=n, master=master, kind=kind, domain=domain,
                         rect_um=[x, y, x + iw, y + ih], orientation=orient,
                         peak_w=p, power_grade='assumed peak density on pinned real outline',
                         pg_layers=pg.get(master, dict(VDD=[], VSS=[])))
            power.append(entry)
            by_kind[kind] += p
            if not entry['pg_layers']['VDD'] or not entry['pg_layers']['VSS']:
                missing.append(n)
            else:
                for net in ('VDD', 'VSS'):
                    layers.update(entry['pg_layers'][net])
    nx, ny = math.ceil(w / TILE), math.ceil(h / TILE)
    tw, th = w / nx, h / ny
    loads = collections.defaultdict(float)
    for item in power:
        ax, ay, cx, cy = item['rect_um']
        dens = item['peak_w'] / ((cx - ax) * (cy - ay))
        if cx <= bx or cy <= by or ax >= ex or ay >= ey:
            continue
        for j in range(max(0, int((ay - by) // th)), min(ny, int((cy - by) // th) + 1)):
            for i in range(max(0, int((ax - bx) // tw)), min(nx, int((cx - bx) // tw) + 1)):
                ov = max(0, min(cx, bx + (i + 1) * tw) - max(ax, bx + i * tw)) * max(0, min(cy, by + (j + 1) * th) - max(ay, by + j * th))
                if ov:
                    loads[(i, j)] += dens * ov
    a.out.mkdir(parents=True, exist_ok=True)
    lef = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;',
           'MACRO hbm_ir_load', ' CLASS BLOCK ;', ' SYMMETRY X Y ;',
           f' SIZE {tw:.6f} BY {th:.6f} ;']
    for net, offset in (('VDD', 1.35), ('VSS', 4.05)):
        lef += [f' PIN {net}', ' DIRECTION INOUT ;', f' USE {"POWER" if net == "VDD" else "GROUND"} ;', ' PORT', ' LAYER M7 ;']
        xx = offset
        while xx + .288 < tw:
            lef.append(f' RECT {xx:.6f} 0.1 {xx + .288:.6f} {th - .1:.6f} ;')
            xx += 5.4
        lef += [' END', f' END {net}']
    lef += ['END hbm_ir_load', 'END LIBRARY']
    (a.out / 'loads.lef').write_text('\n'.join(lef) + '\n')
    d = ['VERSION 5.8 ;', 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', 'DESIGN hbm_ir ;', 'UNITS DISTANCE MICRONS 1000 ;',
         f'DIEAREA ( 0 0 ) ( {round(w * 1000)} {round(h * 1000)} ) ;', f'COMPONENTS {len(loads)} ;']
    d += [f'- L_{i}_{j} hbm_ir_load + FIXED ( {round(i * tw * 1000)} {round(j * th * 1000)} ) N ;' for i, j in loads]
    d += ['END COMPONENTS', 'END DESIGN']
    (a.out / 'window.def').write_text('\n'.join(d) + '\n')
    raw = math.floor((.48 / a.coverage) / .16) * .16
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
        (a.out / f'vsrc_{net}.loc').write_text(''.join(sites))
    t = f'''read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/loads.lef
read_def /work/window.def
add_global_connection -net VDD -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net VSS -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name top -voltage_domains CORE
add_pdn_stripe -grid top -layer M8 -width 0.48 -pitch {pitch:.6f} -spacing {pitch / 2 - .48:.6f} -offset {offset:.6f}
add_pdn_stripe -grid top -layer M9 -width 0.48 -pitch {pitch:.6f} -spacing {pitch / 2 - .48:.6f} -offset {offset:.6f}
add_pdn_connect -grid top -layers {{M8 M9}}
define_pdn_grid -macro -name load -cells {{^hbm_ir_load$}} -halo {{0 0 0 0}} -voltage_domains CORE
add_pdn_connect -grid load -layers {{M7 M8}}
pdngen -failed_via_report /work/failed_vias.rpt
puts {{OT_PDN PASS}}
write_db /work/pdn.odb
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
    (a.out / 'run.tcl').write_text(t)
    manifest = dict(schema='opentallas.hbm.ir_window.v1', source_commit=m.get('source_commit'),
                    input_sha256={str(p): sha(p) for p in (a.model, a.lef, a.pg_lef, Path(__file__)) if p},
                    inner_um=a.window, solved_um=[bx, by, ex, ey], guard_um=guard,
                    load_tile_um=[tw, th], peak_w=sum(loads.values()), die_peak_w=sum(by_kind.values()),
                    die_peak_w_by_kind=dict(by_kind), loads=len(loads),
                    grid=dict(layers=['M8', 'M9'], width_um=.48, pitch_um=pitch, coverage_per_net=.48 / pitch),
                    bumps=dict(array_pitch_um=BUMP_ARRAY, per_net_pitch_um=vp, size_um=BUMP_SIZE),
                    voltage_v=VDD, budget_mv=35,
                    real_pg_layer_counts=dict(layers), instances_missing_real_pg=len(missing),
                    limitations=['Peak power density is assumed, not SAIF measured.',
                                 'Die-grid load projections on M7 are not child PG access proof.',
                                 'Leaf M5/M6 to die M8 stacks and exact signal obstructions require a subsequent integrated PDN case.',
                                 'PHY/link/host rails excluded; package/bump impedance not modeled.'],
                    final_signoff_eligible=False)
    (a.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (a.out / 'power_map.json').write_text(json.dumps(dict(instances=power, missing_pg=missing), indent=1) + '\n')
    print(json.dumps(manifest))


def record(a):
    m = read(a.out / 'manifest.json')
    log = (a.out / 'run.log').read_text()
    rc = (a.out / 'run.exit').read_text().strip()
    bx, by, _, _ = m['solved_um']
    x0, y0, x1, y1 = m['inner_um']
    rails = {}
    for net in ('VDD', 'VSS'):
        samples = []
        for line in (a.out / f'ir_{net}.rpt').read_text().splitlines()[1:]:
            c = line.split(',')
            if len(c) < 6:
                continue
            x, y, v = map(float, c[3:6])
            if x0 <= x + bx <= x1 and y0 <= y + by <= y1:
                samples.append((VDD - v) if net == 'VDD' else v)
        rails[net] = dict(nodes=len(samples), worst_mv=max(samples, default=float('inf')) * 1000)
    combined = sum(v['worst_mv'] for v in rails.values())
    r = dict(manifest=m, exit=rc, pdn_pass='OT_PDN PASS' in log,
             grid_connected=all(f'OT_PG net={n} PASS' in log for n in rails),
             done='OT_DONE' in log, inner_rails=rails, rail_to_rail_bound_mv=combined,
             die_grid_window_pass=rc == '0' and 'OT_DONE' in log and combined <= m['budget_mv'],
             final_signoff_eligible=False)
    (a.out / 'result.json').write_text(json.dumps(r, indent=2) + '\n')
    print(json.dumps(r))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['generate', 'record'])
    p.add_argument('--model', type=Path)
    p.add_argument('--lef', type=Path)
    p.add_argument('--pg-lef', type=Path, help='real-view LEF separately loaded by the STA case')
    p.add_argument('--window', type=float, nargs=4)
    p.add_argument('--coverage', type=float, default=.0878)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    (generate if a.mode == 'generate' else record)(a)
