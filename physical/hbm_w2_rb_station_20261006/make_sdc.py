#!/usr/bin/env python3
"""Receiver clock-root contract SDC for the REGISTERED_BOUNDARY W2 station.

Contract (decided for die integration):
  * Every station flop is a leaf of the die clk_sm tree entering at the clk_sm
    pin. fclk_o (four kept inversions) is exported for observation only; no
    receiver is clocked from it, so it is not a timing root of any die path.
  * Every boundary is register-to-register (flop at the pin), so a die path is
    flop -> pin -> die wire -> pin -> flop. Both ends see clk_sm with a die
    clock-arrival difference of up to SKEW (150 ps) around the block's own
    measured insertion L (the clock latency of the block's flops).
  * Setup: the die wire between two stations' pins gets WIRE ps (one die
    station hop); each block keeps INT ps for its own pin<->flop wire, clk->Q
    budgeted CLKQ. Input max = L+SKEW+CLKQ+INT+WIRE; output max =
    WIRE+INT+SETUP+SKEW-L (external capture up to SKEW early).
  * Hold: the whole SKEW is budgeted on the receiving side only (input min =
    L-SKEW+CLKQ_MIN); output min assumes nothing beyond the block's own launch
    (output min = -L), so the skew is never double counted.
"""
import argparse
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--period-ps', type=float, required=True)
p.add_argument('--insertion-ps', type=float, required=True, help='block clock insertion L (measured after CTS)')
p.add_argument('--skew-ps', type=float, default=150.0)
p.add_argument('--wire-ps', type=float, default=200.0)
p.add_argument('--int-ps', type=float, default=60.0)
p.add_argument('--clkq-ps', type=float, default=100.0)
p.add_argument('--clkq-min-ps', type=float, default=30.0)
p.add_argument('--setup-ps', type=float, default=25.0)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
L = a.insertion_ps
in_max = L + a.skew_ps + a.clkq_ps + a.int_ps + a.wire_ps
in_min = L - a.skew_ps + a.clkq_min_ps
out_max = a.wire_ps + a.int_ps + a.setup_ps + a.skew_ps - L
out_min = -L
lines = [
    f'# W2 rb station receiver clock-root contract: period {a.period_ps} ps, L {L} ps, skew +-{a.skew_ps} ps',
    f'create_clock -name clk_sm -period {a.period_ps:.3f} [get_ports clk_sm]',
    'set prev [get_ports clk_sm]', 'set master clk_sm',
    'for {set i 0} {$i<4} {incr i} {',
    ' set roots {}',
    ' foreach p [get_pins -hierarchical *] {',
    '  if {[regexp "u_clk${i}.*/Y$" [get_full_name $p]]} {lappend roots $p}',
    ' }',
    ' if {[llength $roots]!=1} {error "missing kept station forwarding inverter $i"}',
    ' create_generated_clock -name forwarded$i -source $prev -master_clock $master -divide_by 1 -invert [lindex $roots 0]',
    ' set prev [lindex $roots 0];set master forwarded$i',
    '}',
    'create_generated_clock -name forwarded_port -source $prev -master_clock $master -divide_by 1 [get_ports fclk_o]',
    'set_clock_uncertainty -setup 60 [all_clocks]',
    'set_clock_uncertainty -hold 25 [all_clocks]',
    'set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y [delete_from_list [all_inputs] [get_ports clk_sm]]',
    'foreach p [all_inputs] {',
    ' if {[get_full_name $p] eq "clk_sm"} {continue}',
    f' set_input_delay -max {in_max:.3f} -clock clk_sm $p',
    f' set_input_delay -min {in_min:.3f} -clock clk_sm $p',
    '}',
    'foreach p [all_outputs] {',
    ' if {[get_full_name $p] eq "fclk_o"} {continue}',
    f' set_output_delay -max {out_max:.3f} -clock clk_sm $p',
    f' set_output_delay -min {out_min:.3f} -clock clk_sm $p',
    ' set_load 4.0 $p',
    '}',
    'set_max_fanout 32 [current_design]',
]
a.out.write_text('\n'.join(lines)+'\n')
print(a.out, dict(in_max=in_max, in_min=in_min, out_max=out_max, out_min=out_min))
