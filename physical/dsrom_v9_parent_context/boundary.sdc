# Conditional terminal budgets inherited from actual QX timing vehicle,
# not measured parent/child arrivals or a whole-field qualification.
set gp [get_pins -quiet g_qx.g_cg.u_cg.u_icg/GCLK]
set cp [get_pins -quiet g_qx.g_cg.u_cg.u_icg/CLK]
if {[llength $gp]!=1 || [llength $cp]!=1} {error "literal source ICG pins missing"}
create_generated_clock -name q_gated -master_clock core_clk -source $cp -combinational $gp
set_clock_uncertainty -setup 60 [get_clocks {core_clk q_gated}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk q_gated}]
set_clock_gating_check -setup 60 -hold 25 [get_cells g_qx.g_cg.u_cg.u_icg]
# Replace default domain on actual gated-engine source cuts.
set gi [get_ports {tree_valid* tree_idle* tree_payload* busy_source frontend_fault_source bank_fault_source* walk_busy}]
remove_input_delay $gi
set_input_delay -min 360 -clock q_gated $gi
set_input_delay -max 727 -clock q_gated $gi
set go [get_ports {engine_xs*}]
remove_output_delay $go
set_output_delay -min 360 -clock q_gated $go
set_output_delay -max 727 -clock q_gated $go
# A clock terminal is propagated clock topology, rather than a data output.
remove_output_delay [get_ports engine_clk]
source /src/physical/dsrom_v9_parent_context/loaded_ports.sdc
