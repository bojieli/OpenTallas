# The actual engine's generated clock and ping-pong contracts are unchanged.
source /src/physical/dsrom_qx10_parent_context/boundary.sdc
set cfg_clock [get_pins -quiet g_cfg_provider.u_provider.g_hard_cfg.u_cfg/clk]
if {[llength $cfg_clock]!=1} {error "actual configuration macro clock missing"}
# cfg macro is on core_clk, one read per free edge; its own SS/FF Liberty
# clkQ/address/CE/CLK caps drive the real loader's48 payload capture pins.
# No multicycle/false path or fake clock is added for this ROM.
set cfg_captures [get_cells -hierarchical -quiet *u_provider.u_ld.c_d*]
if {[llength $cfg_captures]!=48} {error "actual48 cfg payload receiver registers missing"}
puts "OT_QX10_CFG_CLOCK_CAPTURE root=core_clk macro=[get_full_name $cfg_clock] captures=[llength $cfg_captures] missing_full_field_input_clocks=1"
