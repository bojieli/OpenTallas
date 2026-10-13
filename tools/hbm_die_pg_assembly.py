#!/usr/bin/env python3
"""Actual leaf PG exports for B2 VM slices and a preserved SM/M9 layer case.

Each current-map tile preserves clipped PG shapes from the original real LEF.
This checks PG access to the child interface; internal child IR remains separate.
The four VM assemblies are die-placed leaves, never opaque hardened parents.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'
TILE = 43.2


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse(path):
    t = Path(path).read_text()
    name = re.search(r'\bMACRO (\S+)', t)[1]
    w, h = map(float, re.search(r'\bSIZE ([\d.]+) BY ([\d.]+)', t).groups())
    nets = {}
    for net in ('VDD', 'VSS'):
        b = re.search(r'\n\s*PIN ' + net + r'\n(.*?)\n\s*END ' + net + r'(?:\s*\n|$)', t, re.S)
        if not b:
            raise ValueError(f'{path}: missing {net}')
        layer, shapes = None, []
        for ln in b[1].splitlines():
            mm = re.search(r'\bLAYER (M\d+) ;', ln)
            if mm:
                layer = mm[1]
            mm = re.search(r'\bRECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s*;', ln)
            if mm and layer:
                shapes.append((layer, tuple(map(float, mm.groups()))))
        top = max(int(s[0][1:]) for s in shapes)
        nets[net] = [(ly, r) for ly, r in shapes if ly == f'M{top}']
    layers = {ly for rs in nets.values() for ly, _ in rs}
    if len(layers) != 1:
        raise ValueError(f'{path}: differing top PG rails {layers}')
    return dict(name=name, w=w, h=h, pg=nets, top=layers.pop(), sha256=sha(path), source=str(path))


def bounds(v):
    n = math.ceil(v / TILE)
    step = math.floor(v / n / .004) * .004
    return [round(i * step, 6) for i in range(n)] + [v]


def pg_macro(name, w, h, pg):
    t = [f'MACRO {name}', ' CLASS BLOCK ;', ' SYMMETRY X Y ;', f' SIZE {w:.6f} BY {h:.6f} ;']
    for net, shapes in pg.items():
        t += [f' PIN {net}', ' DIRECTION INOUT ;', f' USE {"POWER" if net == "VDD" else "GROUND"} ;', ' PORT']
        for ly, r in shapes:
            t += [f' LAYER {ly} ;', ' RECT ' + ' '.join(f'{v:.6f}' for v in r) + ' ;']
        t += [' END', f' END {net}']
    return '\n'.join(t + [f'END {name}'])


def split_leaf(view, origin, prefix):
    """43.2um current-map tiles retaining actual PG, without invented rails."""
    xs, ys = bounds(view['w']), bounds(view['h'])
    out = []
    for j, (y0, y1) in enumerate(zip(ys, ys[1:])):
        for i, (x0, x1) in enumerate(zip(xs, xs[1:])):
            pg = {}
            for net, shapes in view['pg'].items():
                pg[net] = []
                for ly, r in shapes:
                    a, b, c, d = max(x0, r[0]), max(y0, r[1]), min(x1, r[2]), min(y1, r[3])
                    if c > a and d > b:
                        pg[net].append((ly, (a - x0, b - y0, c - x0, d - y0)))
                if not pg[net]:
                    raise ValueError(f'{prefix}[{i},{j}] has no real {net} PG shape')
            n = f'{prefix}_t{i}_{j}'
            out.append(dict(name=n, master=n, w=x1 - x0, h=y1 - y0,
                            x=origin[0] + x0, y=origin[1] + y0,
                            pg=pg, source_master=view['name'], source_rect=[x0, y0, x1, y1], top=view['top']))
    return out


def generate(a):
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    if a.mode == 'vm':
        views = {}
        for k in ('bank', 'hub', 'rstop', 'rcl', 'star'):
            p = a.root / f'physical/ref_tile/vms_{k}/views/ot_vms_{k}/ot_vms_{k}.lef'
            views[k] = parse(p)
        places = []
        for bank in range(8):
            places.append(dict(instance=f'g_bank[{bank}].u_bank', kind='bank',
                               x=21.6 + (bank % 2) * 330.48,
                               y=21.6 + (bank // 2) * 330.48))
        places += [dict(instance='u_hub', kind='hub', x=682.56, y=200.88),
                   dict(instance='u_cw', kind='rstop', x=21.6, y=1343.52),
                   dict(instance='u_ccw', kind='rstop', x=285.12, y=1343.52),
                   dict(instance='u_star', kind='star', x=550.8, y=1343.52),
                   dict(instance='u_rcl', kind='rcl', x=630.72, y=1343.52)]
        w, h = 950.4, 1684.8
    else:
        views = dict(sm=parse(a.sm_lef))
        places = [dict(instance='sm', kind='sm', x=0, y=0)]
        w, h = views['sm']['w'], views['sm']['h']
        if views['sm']['top'] != 'M8':
            raise ValueError('preserved SM exception expects actual M8 PG')
    tiles = []
    pg_export = {}
    for k, v in views.items():
        (out / f'{k}_actual_pg.lef').write_text('VERSION 5.8 ;\n' + pg_macro(v['name'], v['w'], v['h'], v['pg']) + '\nEND LIBRARY\n')
    rects = []
    for n, p in enumerate(places):
        v = views[p['kind']]
        r = [p['x'], p['y'], p['x'] + v['w'], p['y'] + v['h']]
        if r[2] > w or r[3] > h:
            raise ValueError(f'{p["instance"]} exceeds slice outline')
        if any(r[0] < t[2] and r[2] > t[0] and r[1] < t[3] and r[3] > t[1] for t in rects):
            raise ValueError(f'{p["instance"]} overlaps another leaf')
        rects.append(r)
        p.update(rect_um=r, master=v['name'], top_pg=v['top'], source_lef=v['source'], source_sha256=v['sha256'])
        tiles += split_leaf(v, (p['x'], p['y']), f'C{n}')
    (out / 'tiles.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(pg_macro(t['master'], t['w'], t['h'], t['pg']) for t in tiles) + '\nEND LIBRARY\n')
    d = ['VERSION 5.8 ;', 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', 'DESIGN real_pg ;', 'UNITS DISTANCE MICRONS 1000 ;',
         f'DIEAREA ( 0 0 ) ( {round(w * 1000)} {round(h * 1000)} ) ;', f'COMPONENTS {len(tiles)} ;']
    d += [f'- {t["name"]} {t["master"]} + FIXED ( {round(t["x"] * 1000)} {round(t["y"] * 1000)} ) N ;' for t in tiles]
    d += ['END COMPONENTS', 'END DESIGN']
    (out / 'case.def').write_text('\n'.join(d) + '\n')
    tcl = f'''read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/tiles.lef
read_def /work/case.def
add_global_connection -net VDD -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net VSS -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name top -voltage_domains CORE
'''
    for ly in (('M7', 'M8', 'M9') if a.mode == 'vm' else ('M9',)):
        width = .544 if ly == 'M7' else .48
        tcl += f'add_pdn_stripe -grid top -layer {ly} -width {width:.3f} -pitch 4.896 -spacing {4.896 / 2 - width:.3f} -offset 2.16\n'
    if a.mode == 'vm':
        tcl += 'add_pdn_connect -grid top -layers {M7 M8}\nadd_pdn_connect -grid top -layers {M8 M9}\n'
    groups = {}
    for t in tiles:
        groups.setdefault(t['top'], []).append(t['master'])
    for ly, masters in groups.items():
        grid = 'leaf_' + ly
        tcl += f'define_pdn_grid -macro -name {grid} -cells {{{" ".join("^"+s+"$" for s in masters)}}} -halo {{0 0 0 0}} -voltage_domains CORE\n'
        if ly == 'M5':
            tcl += f'add_pdn_stripe -grid {grid} -layer M6 -width 0.288 -pitch 5.4 -spacing 2.412 -offset 1.35\nadd_pdn_connect -grid {grid} -layers {{M5 M6}}\nadd_pdn_connect -grid {grid} -layers {{M6 M7}}\n'
        else:
            tcl += f'add_pdn_connect -grid {grid} -layers {{{ly} M{int(ly[1:])+1}}}\n'
    tcl += f'''pdngen -failed_via_report /work/failed_vias.rpt
puts {{OT_PDN PASS}}
write_db /work/pdn.odb
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
set_cmd_units -power W
source {PLAT}/setRC.tcl
'''
    for t in tiles:
        tcl += f'set_pdnsim_inst_power -inst {t["name"]} -power {a.density * t["w"] * t["h"] / 1e6:.12f}\n'
    vp = 45 / math.sqrt(.5)
    for net, phase in (('VDD', vp/2), ('VSS', vp)):
        sites = []
        yy = phase
        while yy < h - 1:
            xx = phase
            while xx < w - 1:
                sites.append(f'{xx:.6f}, {yy:.6f}, 20, {0.7 if net == "VDD" else 0}\n')
                xx += vp
            yy += vp
        (out / f'vsrc_{net}.loc').write_text(''.join(sites))
    tcl += '''foreach net {VDD VSS} {
check_power_grid -net $net -error_file /work/pg_err_$net.rpt
puts "OT_PG net=$net PASS"
set_pdnsim_net_voltage -net $net -voltage [expr {$net eq "VDD" ? 0.7 : 0}]
analyze_power_grid -net $net -vsrc /work/vsrc_$net.loc -voltage_file /work/ir_$net.rpt -error_file /work/ir_err_$net.rpt
puts "OT_IR net=$net PASS"
}
puts OT_DONE
'''
    (out / 'run.tcl').write_text(tcl)
    m = dict(schema='opentallas.hbm.real_pg_assembly.v1', mode=a.mode, outline_um=[w,h], leaves=places,
             source_sha256={v['source']:v['sha256'] for v in views.values()}, generator_sha256=sha(__file__),
             pg_load_tiles=len(tiles), tile_max_um=TILE, power_w=sum(a.density*t['w']*t['h']/1e6 for t in tiles),
             power_grade='existing assumed peak density', density_w_mm2=a.density,
             actual_pg_preserved=True, child_internal_ir_measured=False,
             signal_obstructions_integrated=False, final_signoff_eligible=False,
             layer_contract=('die-placed VM leaves: M5/M6 real pins -> M6/M7 straps -> M8/M9 die' if a.mode=='vm' else
                             'preserve closed SM M8 PG; parent M9 only over actual SM extent; die M8 excluded'),
             slice_copies=['SW','SE','NW','NE'] if a.mode=='vm' else None,
             hard_parent_created=False)
    (out / 'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    print(json.dumps(m))


def record(a):
    out=a.out
    m=json.loads((out/'manifest.json').read_text())
    log=(out/'run.log').read_text()
    rc=(out/'run.exit').read_text().strip()
    w,h=m['outline_um'];guard=2*45/math.sqrt(.5)
    rails={}
    for net in ('VDD','VSS'):
        inner=[];all_nodes=[]
        for line in (out/f'ir_{net}.rpt').read_text().splitlines()[1:]:
            c=line.split(',')
            if len(c)<6:continue
            x,y,v=map(float,c[3:6]);drop=(.7-v) if net=='VDD' else v
            all_nodes.append(drop)
            if guard<=x<=w-guard and guard<=y<=h-guard:inner.append(drop)
        rails[net]=dict(inner_nodes=len(inner),inner_worst_mv=max(inner,default=float('inf'))*1000,
                        full_worst_mv=max(all_nodes,default=float('inf'))*1000)
    bound=sum(r['inner_worst_mv'] for r in rails.values())
    r=dict(schema='opentallas.hbm.real_pg_result.v1',manifest=m,exit=rc,done='OT_DONE' in log,
           pdn_pass='OT_PDN PASS' in log,grid_connected=all(f'OT_PG net={n} PASS' in log for n in rails),
           rails=rails,inner_guard_um=guard,inner_rail_sum_mv=bound,budget_mv=35,
           interface_window_pass=rc=='0' and 'OT_DONE' in log and bound<=35,
           final_signoff_eligible=False)
    (out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(exit=rc,rails=rails,inner_rail_sum_mv=bound,interface_window_pass=r['interface_window_pass'])))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['vm','sm','record'])
    p.add_argument('--root',type=Path)
    p.add_argument('--sm-lef',type=Path)
    p.add_argument('--density',type=float,default=1.05)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    (record if a.mode=='record' else generate)(a)
