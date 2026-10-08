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
  * Hold: HOLD_SKEW (50 ps hold IO uncertainty, owner clarification
    2026-10-06: hold is closed by hold repair under FF-corner constraints,
    FF insertion + 50 ps) is budgeted on the receiving side only (input min
    = Lff_min-HOLD_SKEW+CLKQ_MIN); output min asks nothing beyond the
    block's own launch (output min = -Lff_min), so it is never double counted.
  * IO_REF_PERIOD: the IO budgets are a die contract at the sign-off period.
    When the block is routed over-constrained (770 ps) the input/output
    delays are shifted by (period - IO_REF_PERIOD) so the pin windows equal
    the sign-off windows; only reg2reg is over-constrained. Hold-repair
    buffers on the input pins then see the true setup window.
"""
import argparse
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--period-ps', type=float, required=True)
p.add_argument('--l-max', type=float, required=True, help='SS clk_sm insertion, latest flop (setup: input side)')
p.add_argument('--l-min', type=float, required=True, help='SS clk_sm insertion, earliest flop (setup: output side)')
p.add_argument('--l-ff-min', type=float, required=True, help='FF clk_sm insertion, earliest flop (hold side)')
p.add_argument('--l-ff-max', type=float, default=None, help='FF clk_sm insertion, latest flop: approved IO hold model (inputs launched at FF max insertion + clk->Q FF + wire credit, hold uncertainty 50)')
p.add_argument('--wire-credit-ps', type=float, default=0.0, help='0.112 ps/um x minimum die wire to the neighbour pin (stn_io_min.py)')
p.add_argument('--hold-relax', action='store_true', help='calibration run: IO hold constraints relaxed (insertion measurement only)')
p.add_argument('--half', action='store_true', help='half-rate shell: forwarded inverters are w_clk*, core clock is a divide-by-2 generated clock at the ICG AND')
p.add_argument('--route-ss-hold', action='store_true', help='route SDC: hold windows referenced to the SS insertion (the flow repairs hold at the SS corner; sign-off uses the FF model)')
p.add_argument('--skew-ps', type=float, default=150.0)
p.add_argument('--hold-skew-ps', type=float, default=50.0)
p.add_argument('--io-ref-period-ps', type=float, default=None, help='sign-off period the IO windows refer to (default: --period-ps)')
p.add_argument('--wire-ps', type=float, default=200.0)
p.add_argument('--int-ps', type=float, default=60.0)
p.add_argument('--clkq-ps', type=float, default=100.0)
p.add_argument('--clkq-min-ps', type=float, default=30.0)
p.add_argument('--setup-ps', type=float, default=25.0)
p.add_argument('--link-ps', type=float, default=None,
               help='MEASURED die link delay between this pin and the neighbour pin (wire + pin station), ps; default '
                    '--link-um x 1.135 ps/um (SS buffered wire, memory ss-wire-reach-504um)')
p.add_argument('--link-um', type=float, default=100.0, help='die link length when --link-ps is not given (pin-station '
               'rule: last segment <= ~100 um)')
p.add_argument('--sender-frac', type=float, default=0.5, help='share of the link budget given to the sender side')
p.add_argument('--legacy-split', action='store_true', help='the pre-2026-10-07 per-side budgets (they overlap: invalid '
               'evidence, kept only to reproduce old routes)')
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
# Each budget takes the insertion that is pessimistic for it: inputs are
# captured by our latest flop at SS (setup) and earliest flop at FF (hold);
# outputs are captured externally up to SKEW before our earliest SS flop.
shift = a.period_ps - (a.io_ref_period_ps if a.io_ref_period_ps else a.period_ps)
# CONSISTENT link split (setup-triage 2026-10-07, owner-delegated decision): one registered die link is
#   S (sender clk->Q + reg->pin) + LINK (measured wire + pin station) + R (receiver pin->flop + setup) + SKEW <= T - 60
# and BOTH sides' SDCs must take their window from the same split S + R = T - 60 - SKEW - LINK.  The legacy budgets
# gave the receiver T-60-(SKEW+CLKQ+INT+WIRE) = 263 ps and the sender T-60-(WIRE+INT+SETUP+SKEW) = 338 ps: 601 ps of
# windows for a 423 ps link (WIRE 200), so neither SDC proved the link.
T_ref = a.io_ref_period_ps if a.io_ref_period_ps else a.period_ps
link = a.link_ps if a.link_ps is not None else 1.135 * a.link_um
B = T_ref - 60.0 - a.skew_ps - link
S = a.sender_frac * B
R = B - S
assert abs(S + R + link + a.skew_ps - (T_ref - 60.0)) < 1e-6
if a.legacy_split:
    in_max = a.l_max + a.skew_ps + a.clkq_ps + a.int_ps + a.wire_ps + shift
else:
    in_max = a.l_max + a.skew_ps + link + S + shift   # receiver window = T - 60 - (in_max - L) = R
in_min = (a.l_ff_max + 32.2 + a.wire_credit_ps) if a.l_ff_max else a.l_ff_min - a.hold_skew_ps + a.clkq_min_ps
hold_unc = a.hold_skew_ps if a.l_ff_max else 25
if a.hold_relax:
    in_min = 0.0
    hold_unc = 0
if a.legacy_split:
    out_max = a.wire_ps + a.int_ps + a.setup_ps + a.skew_ps - a.l_min + shift
else:
    out_max = link + R + a.skew_ps - a.l_min + shift   # sender window = T - 60 - out_max - L = S
out_min = -(a.l_ff_min - 60.0)  # launch-only promise; 60 ps below our earliest FF flop
if a.route_ss_hold and not a.hold_relax:
    in_min = a.l_min - a.hold_skew_ps + a.clkq_min_ps
    out_min = -(a.l_min - a.hold_skew_ps)
    hold_unc = 25
L = a.l_max
lines = [
    f'# W2 rb station receiver clock-root contract ({"LEGACY overlapping split" if a.legacy_split else f"consistent link split S {S:.1f} / R {R:.1f} / link {link:.1f}"}): period {a.period_ps} ps, L SS {a.l_min}..{a.l_max} FFmin {a.l_ff_min} ps, setup skew {a.skew_ps} ps, hold skew {a.hold_skew_ps} ps, IO windows at {a.io_ref_period_ps or a.period_ps} ps',
    f'create_clock -name clk_sm -period {a.period_ps:.3f} [get_ports clk_sm]',
    'set prev [get_ports clk_sm]', 'set master clk_sm',
    'for {set i 0} {$i<4} {incr i} {',
    ' set roots {}',
    ' foreach p [get_pins -hierarchical *] {',
    f'  if {{[regexp "{"w_clk" if a.half else "u_clk"}${{i}}.*/Y$" [get_full_name $p]]}} {{lappend roots $p}}',
    ' }',
    ' if {[llength $roots]!=1} {error "missing kept station forwarding inverter $i"}',
    ' create_generated_clock -name forwarded$i -source $prev -master_clock $master -divide_by 1 -invert [lindex $roots 0]',
    ' set prev [lindex $roots 0];set master forwarded$i',
    '}',
    'create_generated_clock -name forwarded_port -source $prev -master_clock $master -divide_by 1 [get_ports fclk_o]',
    'set_clock_uncertainty -setup 60 [all_clocks]',
    f'set_clock_uncertainty -hold {hold_unc:g} [all_clocks]',
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
if a.half:
    lines += ['set ot_g {}', 'foreach p [get_pins -hierarchical *] {', ' set n [get_full_name $p]', ' if {[regexp {u_icg.*/Y$} $n]} {', '  set c [get_cells -of_objects $p]', '  if {[regexp {AND} [get_property $c ref_name]]} {lappend ot_g $p}', ' }', '}', 'if {[llength $ot_g]!=1} {error "expected one ICG AND output, found [llength $ot_g]"}', 'create_generated_clock -name gclk -source [get_ports clk_sm] -divide_by 2 [lindex $ot_g 0]']
a.out.write_text('\n'.join(lines)+'\n')
print(a.out, dict(in_max=in_max, in_min=in_min, out_max=out_max, out_min=out_min, link=link, S=S, R=R, legacy=a.legacy_split))
