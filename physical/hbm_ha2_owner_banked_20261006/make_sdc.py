#!/usr/bin/env python3
"""Margin-rule SDC for the banked HA2 owner reducer (every pin flop-direct).
Setup: die clock-arrival difference SKEW (150 ps) + clk->Q + die wire around the
block's measured insertion L; hold: FF insertion with a 50 ps IO uncertainty
(same clock region as the TU caller), closed by hold repair, never RTL."""
import argparse
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--period-ps',type=float,required=True)
p.add_argument('--l-max',type=float,required=True);p.add_argument('--l-min',type=float,required=True)
p.add_argument('--l-ff-min',type=float,required=True)
p.add_argument('--io-ref-period-ps',type=float,default=833.333)
p.add_argument('--route-ss-hold',action='store_true',help='route SDC: hold windows referenced to the SS insertion (the flow repairs hold at the SS corner; FF hold is signed off by signoff.py with the FF numbers)')
p.add_argument('--half',action='store_true',help='half-rate core: generated clock gclk (divide by 2) at the ICG AND gate')
p.add_argument('--h1',action='store_true',help='rule H1 (flow-hold 2026-10-07): input min = L_FF + clk->Q min, the die-link hold term is carried once by the sender output min')
p.add_argument('--skew-ps',type=float,default=150.0);p.add_argument('--hold-io-ps',type=float,default=50.0)
p.add_argument('--wire-ps',type=float,default=200.0);p.add_argument('--clkq-ps',type=float,default=100.0)
p.add_argument('--clkq-min-ps',type=float,default=30.0);p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
shift=a.period_ps-a.io_ref_period_ps
in_max=a.l_max+a.skew_ps+a.clkq_ps+a.wire_ps+shift
in_min=a.l_ff_min-(0.0 if a.h1 else a.hold_io_ps)+a.clkq_min_ps  # rule H1: the receiver input min carries no hold term
out_max=a.wire_ps+25+a.skew_ps-a.l_min+shift
out_min=-(a.l_ff_min-a.hold_io_ps)
if a.route_ss_hold:
    in_min=a.l_min-a.hold_io_ps+a.clkq_min_ps
    out_min=-(a.l_min-a.hold_io_ps)
a.out.write_text('\n'.join([
 f'# HA2 banked: period {a.period_ps} ps, L SS {a.l_min}..{a.l_max}, FF min {a.l_ff_min}',
 f'create_clock -name clk -period {a.period_ps:.3f} [get_ports clk]',
 'set_clock_uncertainty -setup 60 [all_clocks]','set_clock_uncertainty -hold 25 [all_clocks]',
 'set ins [delete_from_list [all_inputs] [get_ports clk]]',
 'set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $ins',
 f'set_input_delay -max {in_max:.3f} -clock clk $ins',f'set_input_delay -min {in_min:.3f} -clock clk $ins',
 f'set_output_delay -max {out_max:.3f} -clock clk [all_outputs]',f'set_output_delay -min {out_min:.3f} -clock clk [all_outputs]',
 'set_load 4.0 [all_outputs]','set_false_path -from [get_ports rst_n]','set_max_fanout 32 [current_design]',''])+'\n')
print(a.out,dict(in_max=in_max,in_min=in_min,out_max=out_max,out_min=out_min))
if a.half:
    with open(a.out,'a') as f:
        f.write('''# half-rate core clock: the ICG AND output is a divide-by-2 generated clock of clk
set ot_g {}
foreach p [get_pins -hierarchical *] {
 set n [get_full_name $p]
 if {[regexp {u_icg.*/Y$} $n]} {
  set c [get_cells -of_objects $p]
  if {[regexp {AND} [get_property $c ref_name]]} {lappend ot_g $p}
 }
}
if {![llength $ot_g]} {error "expected at least one ICG AND output"}
# cg_pushdown (PRE_CTS) clones the gate per sink cluster: gclk is generated at every clone output
create_generated_clock -name gclk -source [get_ports clk] -divide_by 2 $ot_g
# the gclk edge comes from the AND's clock input; en_l changes only while clk is low: no clock through en_l
set ot_q {}
foreach p [get_pins -hierarchical *] { if {[regexp {u_icg.*en_l.*/QN?$} [get_full_name $p]]} {lappend ot_q $p} }
if {[llength $ot_q] && [catch {set_sense -type clock -stop_propagation -clocks [get_clocks clk] $ot_q} ot_e]} {puts "set_sense: $ot_e"}
''')
