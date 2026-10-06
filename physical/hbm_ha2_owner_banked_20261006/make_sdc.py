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
p.add_argument('--skew-ps',type=float,default=150.0);p.add_argument('--hold-io-ps',type=float,default=50.0)
p.add_argument('--wire-ps',type=float,default=200.0);p.add_argument('--clkq-ps',type=float,default=100.0)
p.add_argument('--clkq-min-ps',type=float,default=30.0);p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
in_max=a.l_max+a.skew_ps+a.clkq_ps+a.wire_ps
in_min=a.l_ff_min-a.hold_io_ps+a.clkq_min_ps
out_max=a.wire_ps+25+a.skew_ps-a.l_min
out_min=-(a.l_ff_min-a.hold_io_ps)
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
