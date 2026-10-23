#!/usr/bin/env python3
"""REACH-M89 routed-parasitics check: two placed relay hops (H on M8, V on M9) of L um with BUFx12f every d um,
S81 dsfd_dvrlyh_276_NS relay ETM/LEF at both ends; GRT (signal layers M8-M9, pins lifted from M1/M3/M5 by GRT),
estimate_parasitics -global_routing with setRC.tcl, TT STA (U60+SKEW90 = 150 ps uncertainty)."""
import sys
from pathlib import Path
out = Path(sys.argv[1]); L = float(sys.argv[2]); d = float(sys.argv[3]); buf = sys.argv[4] if len(sys.argv) > 4 else 'BUFx12f_ASAP7_75t_R'
cell, OB, IB, W = 'dsfd_dvrlyh_276_NS', 116, 145, 276
RW, RH = 25.92, 17.28
DIE = L + 400
n = 1 + int((L - 1e-9) // d)
v = ['module top(clk);', 'input clk;']
place = []
for hop, (x0, y0, dx, dy) in {'h': (100.0, DIE / 2, 1, 0), 'v': (DIE / 2 + 300, 100.0, 0, 1)}.items():
    v.append(f'wire [{W-1}:0] {hop}_lo, {hop}_ci;')
    v.append(f'{cell} {hop}_L (.ck(clk), .o({hop}_lo));')
    v.append(f'{cell} {hop}_C (.ck(clk), .i({hop}_ci));')
    # launch relay at (x0,y0); its output edge -> start of the hop; capture relay at start + L
    sx, sy = (x0 + RW, y0) if dx else (x0, y0 + RH)
    place.append((f'{hop}_L', x0, y0, 'FIRM'))
    place.append((f'{hop}_C', sx + dx * L, sy + dy * L, 'FIRM'))
    for k in range(n):
        a = f'{hop}_lo[{OB}]' if k == 0 else f'{hop}_n{k}'
        y = f'{hop}_n{k+1}' if k < n - 1 else f'{hop}_ci[{IB}]'
        if k < n - 1:
            v.append(f'wire {hop}_n{k+1};')
        v.append(f'{buf} {hop}_b{k} (.A({a}), .Y({y}));')
        pos = 2.0 + k * d
        place.append((f'{hop}_b{k}', sx + dx * pos + (0 if dx else 3.0), sy + dy * pos + (3.0 if dx else 0), 'PLACED'))
v.append('endmodule')
out.mkdir(parents=True, exist_ok=True)
(out / 'top.v').write_text('\n'.join(v) + '\n')
pl = '\n'.join(f'set i [$blk findInst {nm}]; $i setOrigin [ord::microns_to_dbu {x:.3f}] [ord::microns_to_dbu {y:.3f}]; $i setPlacementStatus {st}'
               for nm, x, y, st in [(a, round(b / 0.054) * 0.054, round(c / 0.27) * 0.27, e) for a, b, c, e in place])
(out / 'grt.tcl').write_text(f'''
read_lef asap7_tech_1x_201209.lef
read_lef asap7sc7p5t_28_R_1x_220121a.lef
read_lef {cell}.lef
read_liberty asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty {cell}_tt.lib
read_verilog top.v
link_design top
initialize_floorplan -die_area {{0 0 {DIE} {DIE}}} -core_area {{1 1 {DIE-1} {DIE-1}}} -site asap7sc7p5t
source make_tracks.tcl
set blk [ord::get_db_block]
place_pin -pin_name clk -layer M8 -location {{{DIE/2:.3f} 0.5}} -pin_size {{0.08 0.08}}
{pl}
# no DPL: a 2 mm die site grid OOMs it; buffers are set on site/row multiples below

create_clock -name clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 150 [all_clocks]
set_input_transition 20 [get_ports clk]
source setRC.tcl
set_routing_layers -signal M2-M9 -clock M2-M9
set_global_routing_layer_adjustment M2-M7 1.0
global_route -verbose
estimate_parasitics -global_routing
foreach h {{h v}} {{
  report_checks -through [get_pins ${{h}}_b0/A] -fields {{slew cap}} -digits 1 > ${{h}}_dmp.rpt
  puts "SLACK dmp $h [get_property [get_pins ${{h}}_C/i[{IB}]] slack_max]"
}}
set_delay_calculator arnoldi
foreach h {{h v}} {{
  report_checks -through [get_pins ${{h}}_b0/A] -fields {{slew cap}} -digits 1 > ${{h}}_arnoldi.rpt
  puts "SLACK arnoldi $h [get_property [get_pins ${{h}}_C/i[{IB}]] slack_max]"
}}
foreach n [get_nets {{h_n* v_n* h_ci* v_ci* h_lo* v_lo*}}] {{
  set nm [get_full_name $n]
  if {{[llength [get_pins -of_objects $n]] == 2}} {{ report_net -digits 2 $nm }}
}}
report_parasitic_annotation
exit
''')
print(n, 'repeaters per hop')
