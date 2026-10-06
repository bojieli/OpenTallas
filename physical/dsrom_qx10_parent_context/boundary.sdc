# Actual selected ICG; the XS boundary is internal and uses this generated clock.
set cp [get_pins -quiet u_qx.u_e.g_cg.u_cg.u_icg/CLK]
set gp [get_pins -quiet u_qx.u_e.g_cg.u_cg.u_icg/GCLK]
if {[llength $cp]!=1 || [llength $gp]!=1} {error "full QX10 literal ICG missing"}
create_generated_clock -name q_gated -master_clock core_clk -source $cp -combinational $gp
set_clock_uncertainty -setup 60 [get_clocks {core_clk q_gated}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk q_gated}]
set_clock_gating_check -setup 60 -hold 25 [get_cells u_qx.u_e.g_cg.u_cg.u_icg]
# The real inherited ping-pong capture contract, unchanged from Z18.
set roms [get_cells -hierarchical *u_rom?]
if {[llength $roms]!=4} {error "full NB2/PP1 requires FOUR actual ROMs"}
set_multicycle_path -setup 2 -from $roms
set_multicycle_path -hold 1 -from $roms
# Remaining observation cuts inherit Copernicus's measured family envelope.
# This is not qualified downstream S81 loading. Internal engine cuts have
# actual connected receivers and therefore receive no external load substitute.
set_load 0.577042 [get_ports {f_bus* node_v node_e node_t* node_d* busy fault captured_root* cfg_rom_a*}]
