source $::env(SCRIPTS_DIR)/load.tcl
load_design 4_1_diag.odb 3_place.sdc
estimate_parasitics -placement
catch {ot_mm_sync}
puts "=== HOLD internal worst (BC)"
report_checks -path_delay min -scenes BC -to [get_pins {u_g.u_tile.u_tile.u_logic.u_me.g_hier.g_sl[1].g_hd.g_tx.g_r[0].u_tx/q[244]$_DFF_P_/D}] -format full_clock_expanded -digits 2
puts "=== SETUP ENA worst"
report_checks -path_delay max -to [get_pins g_icg.g_hop.u_hop_ck/u_icg/ENA] -format full_clock_expanded -digits 2
puts "=== CLOCK LATENCY"
catch {report_clock_latency -clock clk} m; puts $m
