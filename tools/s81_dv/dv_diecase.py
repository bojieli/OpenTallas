#!/usr/bin/env python3
"""S81-DV die case (p4 and later): plan -> OpenROAD die-top case for a GRT (+ die STA) trial.

Emits in --out:
  views/<master>.lef   one ABSTRACT per block instance (pins at the plan's link end points, bits spread along the face
                       at 2-track pitch; OBS M1-M6 over the body, so die nets may cross blocks only on M7+)
  die.v                the die top: every block as a cell, every planned relay stage as one DFF per bit
                       (DFFHQNx1_ASAP7_75t_R), chained driver pin -> stages -> receiver pin; one clock net per die
                       region (marked special: GRT routes data only; clocks are DIE-CLOCK's neighbour-relative roots)
  place.tcl            FIRM block placement from the plan + relay flops at their planned hop points (rows/site snapped)
  run.tcl / run.sh     floorplan, place, snap-legalise, [DIE-FLOW repeater step], GRT, gcell usage, census
  case.json            census (real / stand-in per block kind), nets, bits, flops, region, honest memory estimate
Labels: NOT_A_DIE_RESULT until every block binds to a real view (the census says which are stand-ins).
"""
import argparse
import collections
import gzip
import json
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from die_cluster import boundary as CB   # noqa: E402

PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'
DFF = 'DFFHQNx1_ASAP7_75t_R'
ROW, SITE = 0.27, 0.054
PIN_PITCH = 0.096            # 2 tracks of M4 (y) / M5 (x)
# what each plan block kind is today (DV p4): a real closed view exists for none of the DV-specific blocks yet
CENSUS = {'frame': 'stand-in (frame cluster wrappers from GEN not hardened; in-frame tiles bind native-PASS views)',
          'slice': 'stand-in (S81-SLICE 5-leaf cluster in progress; xfin leaf in closure)',
          'unit': 'stand-in (G-unit / seq / coll edge / bk / mix: re-parented units, not hardened)',
          'svc': 'stand-in (HBM service halves)', 'phy': 'stand-in abstract (vendor PHY)', 'ctrl': 'stand-in',
          'link': 'stand-in abstract (SerDes / UCIe PHY)'}


def load(p):
    return json.load(gzip.open(p) if str(p).endswith('.gz') else open(p))


def stand_in_lib(m, ports, c_ps=25.0, u_ps=25.0):
    """STAND-IN liberty (labelled): flop-first block, outputs launch C after clk, inputs set up / hold against clk.
    C = 25 / U = 25 are the recipe-4 leaf numbers DIE-FLOW takes for diagnostic stand-ins."""
    L = [f'library ({m}_standin) {{', '  /* STAND-IN: S81-DV die case diagnostic, not a closed view */',
         '  delay_model : table_lookup ; time_unit : "1ps" ; capacitive_load_unit (1, ff) ; voltage_unit : "1V" ;',
         '  current_unit : "1mA" ; pulling_resistance_unit : "1kohm" ; leakage_power_unit : "1nW" ;',
         '  nom_voltage : 0.7 ; nom_temperature : 25 ; nom_process : 1 ;',
         '  input_threshold_pct_rise : 50 ; input_threshold_pct_fall : 50 ; output_threshold_pct_rise : 50 ;',
         '  output_threshold_pct_fall : 50 ; slew_lower_threshold_pct_rise : 10 ; slew_lower_threshold_pct_fall : 10 ;',
         '  slew_upper_threshold_pct_rise : 90 ; slew_upper_threshold_pct_fall : 90 ;']
    widths = sorted({b for _, _, b, *_ in ports})
    for b in widths:
        L.append(f'  type (b{b}) {{ base_type : array ; data_type : bit ; bit_width : {b} ; bit_from : {b - 1} ; bit_to : 0 ; downto : true ; }}')
    L += [f'  cell ({m}) {{', '    area : 1 ;', '    pin (clk) { direction : input ; clock : true ; capacitance : 1.0 ; }']
    for port, d, b, *_ in ports:
        L.append(f'    bus ({port}) {{ bus_type : b{b} ; direction : {d} ;')
        if d == 'input':
            L += ['      capacitance : 0.6 ;',
                  f'      timing () {{ related_pin : "clk" ; timing_type : setup_rising ; rise_constraint (scalar) {{ values ("{u_ps}") ; }} fall_constraint (scalar) {{ values ("{u_ps}") ; }} }}',
                  '      timing () { related_pin : "clk" ; timing_type : hold_rising ; rise_constraint (scalar) { values ("0") ; } fall_constraint (scalar) { values ("0") ; } }']
        else:
            L += ['      max_capacitance : 40 ;',
                  f'      timing () {{ related_pin : "clk" ; timing_type : rising_edge ; cell_rise (scalar) {{ values ("{c_ps}") ; }} cell_fall (scalar) {{ values ("{c_ps}") ; }} rise_transition (scalar) {{ values ("20") ; }} fall_transition (scalar) {{ values ("20") ; }} }}']
        L.append('    }')
    L += ['  }', '}']
    return '\n'.join(L) + '\n'


def face_of(b, x, y):
    d = {'W': abs(x - b['x']), 'E': abs(x - b['x'] - b['w']), 'S': abs(y - b['y']), 'N': abs(y - b['y'] - b['h'])}
    return min(d, key=d.get)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--region', type=float, nargs=4, metavar=('X0', 'Y0', 'X1', 'Y1'),
                    help='pilot: keep blocks whose centre lies inside and links with both ends inside')
    ap.add_argument('--die-repair', action='store_true', help='splice DIE-FLOW step output (die_repeaters_step.tcl)')
    ap.add_argument('--congestion-iterations', type=int, default=30)
    ap.add_argument('--dieflow-ref', default='origin/claude/dieflow-1017')
    a = ap.parse_args()
    plan = load(a.plan)
    out = Path(a.out); (out / 'views').mkdir(parents=True, exist_ok=True); (out / 'out').mkdir(exist_ok=True)
    W, H = plan['facts']['die_um']
    blocks = plan['blocks']
    keep = set(range(len(blocks)))
    ox = oy = 0.0
    if a.region:
        x0, y0, x1, y1 = a.region
        keep = {i for i, b in enumerate(blocks) if x0 <= b['x'] + b['w'] / 2 <= x1 and y0 <= b['y'] + b['h'] / 2 <= y1}
        ox, oy = x0, y0
        W, H = x1 - x0, y1 - y0
    bidx = {blocks[i]['name']: i for i in keep}
    # ------------------------------------------------------------------ links -> ports on blocks + relay chains
    pins = collections.defaultdict(list)          # inst -> [(port, dir, bits, x, y, face)]
    nets, flops, chains = [], [], []
    nbits = 0
    used = collections.Counter()
    for l in plan['links']:
        (bi0, p0, x0_, y0_, _), (bi1, p1, x1_, y1_, _) = l['e']
        n0, n1 = blocks[bi0]['name'], blocks[bi1]['name']
        if n0 not in bidx or n1 not in bidx:
            continue
        b = l['b']
        nm = l['i'].replace('-', '_')
        po = f'o_{nm}'; pi = f'i_{nm}'
        pins[n0].append((po, 'output', b, x0_ - ox, y0_ - oy, face_of(blocks[bi0], x0_, y0_)))
        pins[n1].append((pi, 'input', b, x1_ - ox, y1_ - oy, face_of(blocks[bi1], x1_, y1_)))
        hops = l['h']
        st = len(hops) - 1
        # stage k sits at the end of hop k (k = 0 .. st-1)
        pts = [(h[2] - ox, h[3] - oy) for h in hops[:-1]]
        prev = [f'{n0}/{po}'] * 0
        chains.append(dict(link=l['i'], cls=l['c'], bits=b, stages=st, src=f'{n0}.{po}', dst=f'{n1}.{pi}', hop_um=round(max(abs(h[2] - h[0]) + abs(h[3] - h[1]) for h in hops), 1)))
        for k, (px, py) in enumerate(pts):
            flops.append((nm, k, b, px, py))
        nets.append((nm, n0, po, n1, pi, b, st))
        nbits += b
        used[l['c']] += b
    # ------------------------------------------------------------------ abstracts (one master per kept instance)
    for i in sorted(keep):
        bl = blocks[i]
        m = f"dv_{bl['name']}"
        w, h = bl['w'], bl['h']
        lines = [f'MACRO {m}', '  CLASS BLOCK ;', '  ORIGIN 0 0 ;', f'  SIZE {w:.3f} BY {h:.3f} ;', '  SYMMETRY X Y ;']
        for port, d, bits, px, py, f in pins.get(bl['name'], []):
            lx, ly = px - (bl['x'] - ox), py - (bl['y'] - oy)
            span = bits * PIN_PITCH
            for k in range(bits):
                t = -span / 2 + (k + 0.5) * PIN_PITCH
                if f in 'WE':
                    yy = min(max(ly + t, 0.2), h - 0.2); xx = 0.0 if f == 'W' else w - 0.1
                    rect = f'RECT {xx:.3f} {yy - 0.012:.3f} {xx + 0.1:.3f} {yy + 0.012:.3f}'; layer = 'M4'
                else:
                    xx = min(max(lx + t, 0.2), w - 0.2); yy = 0.0 if f == 'S' else h - 0.1
                    rect = f'RECT {xx - 0.012:.3f} {yy:.3f} {xx + 0.012:.3f} {yy + 0.1:.3f}'; layer = 'M5'
                lines += [f'  PIN {port}[{k}]', f'    DIRECTION {d.upper()} ;', '    USE SIGNAL ;', '    PORT',
                          f'      LAYER {layer} ;', f'        {rect} ;', '    END', f'  END {port}[{k}]']
        lines += ['  PIN clk', '    DIRECTION INPUT ;', '    USE CLOCK ;', '    PORT', '      LAYER M5 ;',
                  f'        RECT {w / 2 - 0.012:.3f} 0.000 {w / 2 + 0.012:.3f} 0.100 ;', '    END', '  END clk']
        lines += ['  OBS', '    LAYER M1 ;', f'      RECT 0.2 0.2 {w - 0.2:.3f} {h - 0.2:.3f} ;']
        for L in ('M2', 'M3', 'M4', 'M5', 'M6'):
            lines += [f'    LAYER {L} ;', f'      RECT 0.2 0.2 {w - 0.2:.3f} {h - 0.2:.3f} ;']
        lines += ['  END', f'END {m}', '']
        (out / 'views' / f'{m}.lib').write_text(stand_in_lib(m, pins.get(bl['name'], [])))
        (out / 'views' / f'{m}.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(lines) + 'END LIBRARY\n')
    # ------------------------------------------------------------------ die netlist
    v = ['module dv_die (input clk);']
    for i in sorted(keep):
        bl = blocks[i]
        conns = []
        for port, d, bits, *_ in pins.get(bl['name'], []):
            conns.append(f'.{port}(w_{bl["name"]}_{port})')
            v.append(f'  wire [{bits - 1}:0] w_{bl["name"]}_{port};')
        v.append(f'  dv_{bl["name"]} u_{bl["name"]} ({", ".join(conns + ["." + "clk(clk)"])});')
    nf = 0
    for nm, n0, po, n1, pi, b, st in nets:
        src = f'w_{n0}_{po}'; dst = f'w_{n1}_{pi}'
        if st == 0:
            v.append(f'  assign {dst} = {src};')
            continue
        prev = src
        for k in range(st):
            wn = f'r_{nm}_{k}'
            v.append(f'  wire [{b - 1}:0] {wn};')
            for j in range(b):
                v.append(f'  {DFF} f_{nm}_{k}_{j} (.CLK(clk), .D({prev}[{j}]), .QN({wn}[{j}]));')
            nf += b
            prev = wn
        v.append(f'  assign {dst} = {prev};')
    v.append('endmodule')
    for i in sorted(keep):
        bl = blocks[i]
        ports = ', '.join(f'{d} [{bits - 1}:0] {port}' for port, d, bits, *_ in pins.get(bl['name'], [])) or ''
        v.append(f'module dv_{bl["name"]} (input clk{", " + ports if ports else ""});\nendmodule')
    (out / 'die.v').write_text('\n'.join(v) + '\n')
    # ------------------------------------------------------------------ placement
    pl = []
    for i in sorted(keep):
        bl = blocks[i]
        pl.append(f'place_inst -name u_{bl["name"]} -location {{{bl["x"] - ox:.3f} {bl["y"] - oy:.3f}}} -orientation R0 -status FIRM')
    # relay flops: a station of `b` flops on a small square of rows / sites at the hop point
    for nm, k, b, px, py in flops:
        side = max(1, int(math.ceil(math.sqrt(b * 0.648 / (ROW * SITE)) / 12)))   # ~12 sites per DFF
        cols = max(1, int(math.ceil(math.sqrt(b))))
        for j in range(b):
            cx = px + (j % cols) * 12 * SITE
            cy = py + (j // cols) * ROW
            cx = round(cx / SITE) * SITE; cy = round(cy / ROW) * ROW + 1.08
            pl.append(f'place_inst -name f_{nm}_{k}_{j} -location {{{cx:.3f} {cy:.3f}}} -orientation R0 -status PLACED')
    (out / 'place.tcl').write_text('\n'.join(pl) + '\n')
    repair = '# no die repair (pure GRT diagnostic)\n'
    if a.die_repair:
        # DIE-FLOW shared step (claude/dieflow-1017, pending ROOT merge): files materialised from that branch
        import subprocess, tempfile
        tmp = Path(tempfile.mkdtemp(prefix='dvrep_'))
        (tmp / 'tools/die_repeaters').mkdir(parents=True)
        for f in ('__init__.py', 'step.py', 'die_repeaters.tcl'):
            (tmp / 'tools/die_repeaters' / f).write_bytes(subprocess.run(['git', '-C', str(ROOT), 'show', f'{a.dieflow_ref}:tools/die_repeaters/{f}'],
                                                                        capture_output=True, check=True).stdout)
        (tmp / 'tools/die_cluster').mkdir(); shutil.copy(ROOT / 'tools/die_cluster/cluster_bounds.tcl', tmp / 'tools/die_cluster/')
        for f in ('die_reach.py',):
            shutil.copy(ROOT / 'tools' / f, tmp / 'tools' / f)
        (tmp / 'results/arch').mkdir(parents=True); shutil.copy(ROOT / 'results/arch/die_reach_1016.json', tmp / 'results/arch/')
        subprocess.run([sys.executable, str(tmp / 'tools/die_repeaters/step.py'), 'copy', str(out)], check=True)
        libs = [f'{PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz', f'{PLAT}/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib']
        t = subprocess.run([sys.executable, str(tmp / 'tools/die_repeaters/step.py'), 'tcl', '--design', 's81', '--report',
                            '/work/die_repeaters.json', '--legalize', 'snap', '--libs', *libs], capture_output=True, text=True, check=True).stdout
        (out / 'die_repeaters_step.tcl').write_text(t)
        repair = f'# DIE-FLOW repeater step ({a.dieflow_ref})\nsource /work/die_repeaters_step.tcl\n'
    tcl = f'''# S81-DV die case (tools/s81_dv/dv_diecase.py) -- NOT_A_DIE_RESULT (stand-in census in case.json)
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob /work/views/*.lef] {{ read_lef $f }}
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
foreach f [glob /work/views/*.lib] {{ read_liberty $f }}
read_verilog /work/die.v
link_design dv_die
{CB.floorplan_tcl(W, H)}
make_tracks M9 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M8 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M7 -x_offset 0.016 -x_pitch 0.064 -y_offset 0.016 -y_pitch 0.064
make_tracks M6 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.016 -y_pitch 0.064
make_tracks M5 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.012 -y_pitch 0.048
make_tracks M4 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.012 -y_pitch 0.048
make_tracks M3 -x_offset 0.009 -x_pitch 0.640 -y_offset 0.009 -y_pitch 0.640
make_tracks M2 -x_offset 0.009 -x_pitch 0.640 -y_offset 0.045 -y_pitch 0.640
make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
set p0 [clock seconds]
source /work/place.tcl
puts "OT_PLACE_S [expr {{[clock seconds]-$p0}}] insts [llength [get_cells *]]"
{CB.legalize_tcl('place', max_dpl_gsites=2.0)}
write_db /work/out/place.odb
source {PLAT}/setRC.tcl
set_wire_rc -signal -layer M6
create_clock -name clk -period 833.333 [get_ports clk]
set ck [[ord::get_db_block] findNet clk]
if {{$ck ne "NULL"}} {{ $ck setSpecial }}
{repair}set_routing_layers -signal M2-M7 -clock M5-M9
set_global_routing_layer_adjustment M2-M3 0.50
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M7 0.20
set t0 [clock seconds]
global_route -congestion_iterations {a.congestion_iterations} -allow_congestion -verbose -congestion_report_file /work/out/grt_congestion.rpt
puts "OT_GRT_S [expr {{[clock seconds]-$t0}}]"
write_db /work/out/grt.odb
puts OT_DONE
'''
    (out / 'run.tcl').write_text(tcl)
    shutil.copy(ROOT / 'tools/die_cluster/cluster_bounds.tcl', out / 'cluster_bounds.tcl')
    (out / 'run.sh').write_text('''#!/bin/bash
D=$(cd $(dirname $0) && pwd); N=dvdie-$$
docker run --rm --name $N --cpus=${CPUS:-8} --memory=${MEMG:-128}g -v $D:/work -w /work openroad/orfs:asap7lock \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads ${CPUS:-8} -no_init -exit /work/run.tcl > /work/out/run.log 2>&1; rc=\\$?; chmod -R a+rwX /work/out; exit \\$rc"
echo $? > $D/out/run.exit
''')
    kinds = collections.Counter(blocks[i]['kind'] for i in keep)
    area = W * H / 1e6
    info = dict(schema='opentallas.s81_dv.die_case.v1', plan=str(a.plan), region=a.region, die_um=[W, H], area_mm2=round(area, 2),
                blocks=dict(kinds), census={k: CENSUS.get(k, 'stand-in') for k in kinds}, real_views=0,
                links=len(nets), bits=nbits, bits_by_class=dict(used), relay_flops=nf,
                die_nets_est=nbits + nf, die_repair=a.die_repair,
                memory_note=('H-REACH measured ~3.5 GB/mm2 for full-die GRT (flat, with block internals); this case is die-top '
                             'only (abstract blocks), so the pilot measures its own GB/mm2 before the full run'),
                label='NOT_A_DIE_RESULT: all DV blocks are stand-in abstracts; GRT diagnostic of the die-top nets')
    (out / 'case.json').write_text(json.dumps(dict(info, chains=chains), indent=1))
    print(json.dumps(info, indent=1))


if __name__ == '__main__':
    main()
