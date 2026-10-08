#!/usr/bin/env python3
"""IO SDC of the pin-registered norm engine view (clock port clk). Same contract as the W2 station / spine views:
inputs arrive L_ss_max + 150 ps die-clock term + clk->Q + int + wire after the clock edge; outputs leave with the
same budget against the earliest flop; hold: inputs launched at the FF MAX insertion + FF clk->Q, outputs against
the FF MIN insertion, 50 ps IO hold uncertainty (approved FF hold model). Routed at --period-ps (770) with the IO
windows referred to the 833.333 sign-off period."""
import argparse
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--period-ps', type=float, default=770.0)
p.add_argument('--io-ref-period-ps', type=float, default=833.333)
p.add_argument('--l-ss-max', type=float, default=350.0)
p.add_argument('--l-ss-min', type=float, default=300.0)
p.add_argument('--l-ff-min', type=float, default=180.0)
p.add_argument('--l-ff-max', type=float, default=220.0)
p.add_argument('--skew-ps', type=float, default=150.0)
p.add_argument('--wire-ps', type=float, default=200.0)
p.add_argument('--int-ps', type=float, default=60.0)
p.add_argument('--clkq-ps', type=float, default=100.0)
p.add_argument('--setup-ps', type=float, default=25.0)
p.add_argument('--signoff', action='store_true', help='833.333 ps / 60 ps sign-off flavour')
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
per = a.io_ref_period_ps if a.signoff else a.period_ps
shift = per - a.io_ref_period_ps
in_max = a.l_ss_max + a.skew_ps + a.clkq_ps + a.int_ps + a.wire_ps + shift
out_max = a.wire_ps + a.int_ps + a.setup_ps + a.skew_ps - a.l_ss_min + shift
in_min = a.l_ff_max + 32.2
out_min = -(a.l_ff_min - 60.0)
L = [f'# norm engine view IO SDC: period {per} ps, SS insertion {a.l_ss_min}..{a.l_ss_max}, FF {a.l_ff_min}..{a.l_ff_max}',
     f'create_clock -name clk -period {per:.3f} [get_ports clk]',
     'set_clock_uncertainty -setup 60 [all_clocks]', 'set_clock_uncertainty -hold 50 [all_clocks]',
     'set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y [delete_from_list [all_inputs] [get_ports clk]]',
     'foreach p [all_inputs] {', ' if {[get_full_name $p] eq "clk"} {continue}',
     f' set_input_delay -max {in_max:.3f} -clock clk $p', f' set_input_delay -min {in_min:.3f} -clock clk $p', '}',
     'foreach p [all_outputs] {', f' set_output_delay -max {out_max:.3f} -clock clk $p',
     f' set_output_delay -min {out_min:.3f} -clock clk $p', ' set_load 4.0 $p', '}',
     'set_max_fanout 32 [current_design]']
a.out.write_text('\n'.join(L) + '\n'); print(a.out, in_max, in_min, out_max, out_min)
