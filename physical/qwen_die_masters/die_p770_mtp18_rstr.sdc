# Qwen die master margin route (die-context IO, template station_die_p770.sdc of the die-top a9bf510a0): 770 ps over-constrained (sign-off 833.333 = slack + 63.333),
# 60 / 25 ps uncertainty, boundary 0.2 x 833.333; after CTS the hooks switch to io_ref_skew.sdc.
create_clock -name core_clk -period 770 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay 166.667 -clock core_clk [all_inputs -no_clocks]
set_output_delay 166.667 -clock core_clk [all_outputs]
set_max_fanout 32 [current_design]
# die-wire context (r21 die STA): an output drives one die hop of <= 430.56 um on M8/M9 (~0.17 fF/um) plus the
# receiving pin: 80 fF; an input arrives through that wire: 150 ps transition
set_load 80 [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
set_max_transition 260 [current_design]

# GX7 / SC-19 (hgi-takeover 2026-10-09): ot_hgi_mtp_core18 RSTR=1.  The core's synchronised reset flop u_core.rst_s[1]
# fans out to every async reset pin of the core; its release is a 4-cycle path (setup 4 / hold 3, hold stays at the
# launch edge).  Only that flop's fan-out; every datapath stays single-cycle.  Validity: no input is used within 4
# cycles of release (bench HELD_RELEASE_CHECK; die config settle >> 4 cycles).
set ot_rs [get_cells -hierarchical -quiet {*u_core*rst_s?1??_DFF*}]
if {[llength $ot_rs] == 0} { error "mtp18_rstr_mc: rst_s[1] not found" }
set_multicycle_path -setup 4 -from $ot_rs
set_multicycle_path -hold 3 -from $ot_rs
puts "mtp18_rstr_mc: [llength $ot_rs] rst_s[1] cell(s): 4-cycle reset tree"
