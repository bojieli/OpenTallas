# Clear only the pre-CTS LOCAL network estimate; preserve early core source latencies.
unset_clock_latency -clock clk [get_ports {clk}]
source /work/clock_taps.tcl

set rt_postplace 1
set rt_leaf_reach_um 405
source /work/reset_taps.tcl
unset rt_postplace
# DIE-HEAD-14 DIAGNOSTIC (kit-local, not a shared fix): TritonCTS stops with CTS-0114 "Clock fclk_out_o overlaps a previous
# clock" because landing_exports.tcl ties the forwarded-clock output fclk_out_o onto the clk root net and the SDC declares a
# divide_by 1 generated clock on that port. The generated clock is removed for clock_tree_synthesis only and re-created
# unchanged at the start of POST_CTS (cts_post.tcl), so 4_cts.sdc keeps it.
if {[llength [get_clocks -quiet fclk_out_o]]} { delete_generated_clock [get_clocks fclk_out_o]; set ::dh14_fclk_out 1; puts "DH14 fclk_out_o generated clock removed for CTS" }
# DIE-HEAD-14 DIAGNOSTIC (kit-local): cts_post OT_CLOCK_FAMILY stopped on "missing unique active clock edge
# u_core.u_b.g_cv.u_eA0/ft_ck0_i ()": the one-entry kit ties the hard cores island feed-through clock input ft_ck0_i to clk
# (no sequential arc in the core Liberty; the core clock pin is ft_mstrap_i). For this diagnostic CTS/GRT run only, the
# ft_ck0_i/ft_ck1_i/ft_mesh_i pins are disconnected from clk (island pass-through, no tile sink behind it).
set dh14_n 0
foreach dh14_i [[ord::get_db_block] getInsts] {
  if {![[$dh14_i getMaster] isBlock]} continue
  foreach dh14_p {ft_ck0_i ft_ck1_i ft_mesh_i} { set dh14_t [$dh14_i findITerm $dh14_p]
  if {$dh14_t ne "NULL" && [$dh14_t getNet] ne "NULL"} { $dh14_t disconnect; incr dh14_n } }
}
puts "DH14 disconnected $dh14_n island ft clock pins (ft_ck0_i ft_ck1_i ft_mesh_i) on hard cores"
uplevel #0 {source /work/h16_coretaps.tcl}
uplevel #0 {source /work/h16_spine.tcl}
