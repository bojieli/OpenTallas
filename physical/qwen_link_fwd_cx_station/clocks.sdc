# Centre-aligned forwarded-clock station (redesign-2). ASAP7/OpenSTA units ps/fF.
# Forwarded-clock station model: every port is timed against ITS forwarded clock, never a core clock.
# Capture on the falling edge of the received clock; the upstream launched on our rising edge (its falling edge,
# its forward is inverted), so input->capture and launch->output are half-cycle paths both ways (setup AND hold).
# The forwarded outputs are generated clocks on the fclk_*_o PORTS (-invert): a CTS rewrite of the kept inverter cannot
# unbind them. No false paths, multicycles or clock groups.
set T 833.333333333
create_clock -name fclk_ab -period $T [get_ports fclk_ab_i]
create_clock -name fclk_ba -period $T -waveform {133.333333333 550} [get_ports fclk_ba_i]
create_generated_clock -name fclk_ab_fwd -source [get_ports fclk_ab_i] -master_clock fclk_ab -divide_by 1 -invert [get_ports fclk_ab_o]
create_generated_clock -name fclk_ba_fwd -source [get_ports fclk_ba_i] -master_clock fclk_ba -divide_by 1 -invert [get_ports fclk_ba_o]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_clock_transition 50 [get_clocks {fclk_ab fclk_ba}]
# Station link budget (fixture 0.2T each side, as the full-cycle vehicle): data valid window centred on the capture edge.
# Inputs: launched on the RISING edge of the received clock (+- 166.667 ps incl. data/clock wire mismatch).
set B 166.667
set_input_delay -max $B -clock fclk_ab [get_ports {ab_i*}]
set_input_delay -min -$B -clock fclk_ab [get_ports {ab_i*}]
set_input_delay -max $B -clock fclk_ba [get_ports {ba_i*}]
set_input_delay -min -$B -clock fclk_ba [get_ports {ba_i*}]
# Outputs: the downstream captures on the FALLING edge of the forwarded (inverted) clock.
set_output_delay -max $B -clock fclk_ab_fwd -clock_fall [get_ports {ab_o*}]
set_output_delay -min -$B -clock fclk_ab_fwd -clock_fall [get_ports {ab_o*}]
set_output_delay -max $B -clock fclk_ba_fwd -clock_fall [get_ports {ba_o*}]
set_output_delay -min -$B -clock fclk_ba_fwd -clock_fall [get_ports {ba_o*}]
# Cold POR: ordinary recovery/removal against both received clocks (released on their capture edge).
foreach c {fclk_ab fclk_ba} {
 set_input_delay -add_delay -max $B -clock $c [get_ports rst_n]
 set_input_delay -add_delay -min 50 -clock $c [get_ports rst_n]
}
set_input_transition 150 [get_ports {ab_i* ba_i* rst_n}]
set_load 20 [get_ports {ab_o* ba_o* fclk_ab_o fclk_ba_o}]
set_max_fanout 32 [current_design]
set_max_transition 260 [current_design]
set_propagated_clock [all_clocks]
if {[llength [all_clocks]] != 4} {error "two received plus two forwarded port clocks required"}
