# Add after the existing core clock is defined. No clock groups, false paths,
# disabled timing arcs or relaxed gating checks are permitted here.
# Yosys may flatten hierarchy with '.', while OpenROAD links kept modules
# with '/'. Match one semantic identity, not a guessed literal separator.
set rp0 {}; set rp1 {}
foreach pin [get_pins -hierarchical *] {
  set semantic [string map {/ .} [get_full_name $pin]]
  if {[string match {*g_half.g_root.u_inv0.u_inv.Y} $semantic]} {lappend rp0 $pin}
  if {[string match {*g_half.g_root.u_inv1.u_inv.Y} $semantic]} {lappend rp1 $pin}
}
if {[llength $rp0]!=1 || [llength $rp1]!=1} {
  error "BF_ROOT_PHASE real kept phase clock branch is missing or ambiguous"
}
foreach pin [concat $rp0 $rp1] {
  if {[get_property [get_cells -of_objects $pin] ref_name] ne "INVx1_ASAP7_75t_R"} {
    error "BF_ROOT_PHASE branch is not the modeled real inverter cell"
  }
}
create_generated_clock -name bf_phase_inv -source [get_ports clk] -divide_by 1 -invert $rp0
create_generated_clock -name bf_phase_local -source $rp0 -master_clock bf_phase_inv -divide_by 1 -invert $rp1
set_clock_uncertainty -setup 60 [get_clocks {bf_phase_inv bf_phase_local}]
set_clock_uncertainty -hold 25 [get_clocks {bf_phase_inv bf_phase_local}]
set_propagated_clock [get_clocks {bf_phase_inv bf_phase_local}]
