# Add after the existing core clock is defined. No clock groups, false paths,
# disabled timing arcs or relaxed gating checks are permitted here.
set rp0 [get_pins -quiet {g_half.g_root.u_inv0.u_inv/Y}]
set rp1 [get_pins -quiet {g_half.g_root.u_inv1.u_inv/Y}]
if {[llength $rp0]!=1 || [llength $rp1]!=1} {
  error "BF_ROOT_PHASE real kept phase clock branch is missing"
}
create_generated_clock -name bf_phase_inv -source [get_ports clk] -divide_by 1 -invert $rp0
create_generated_clock -name bf_phase_local -source $rp0 -master_clock bf_phase_inv -divide_by 1 -invert $rp1
set_clock_uncertainty -setup 60 [get_clocks {bf_phase_inv bf_phase_local}]
set_clock_uncertainty -hold 25 [get_clocks {bf_phase_inv bf_phase_local}]
set_propagated_clock [get_clocks {bf_phase_inv bf_phase_local}]
