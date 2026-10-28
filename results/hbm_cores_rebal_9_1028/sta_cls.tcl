# HBM-CORES-REBAL-9: classify post-CTS TT negative endpoints (SRAM input pin / flop D by block / port) for lanes__canon m5w1.
foreach f {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib} { read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$f }
read_liberty /work/macros/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
read_db [glob /work/run/results/asap7/*/base/4_cts.odb]
read_sdc [glob /work/run/results/asap7/*/base/4_cts.sdc]
set_propagated_clock [get_clocks clk]
if {[info exists ::env(OT_VCLK_TT)] && $::env(OT_VCLK_TT) ne ""} { source /work/vclk_corner.tcl; ot_vclk_bind tt }
source /work/setRC_rcx.tcl
estimate_parasitics -placement
array set n {}; array set w {}
foreach p [find_timing_paths -path_delay max -group_path_count 100000 -endpoint_path_count 1 -slack_max 0] {
  set e [get_full_name [get_property $p endpoint]]; set s [get_full_name [get_property $p startpoint]]
  if {[regexp {u_m/(\w+)} $e -> pin]} { set k "SRAM_$pin<-[expr {[string match *wcopy* $s] ? {wcopy} : {other}}]" } \
  elseif {[regexp {u_lane\.(u_\w+)} $e -> b]} { set k "lane.$b" } \
  elseif {[regexp {(u_bank\d|u_lane\d)} $e -> b]} { set k "[string range $b 0 5]" } else { set k other }
  if {![info exists n($k)]} { set n($k) 0; set w($k) 0 }
  incr n($k); set sl [get_property $p slack]; if {$sl < $w($k)} { set w($k) $sl }
}
foreach k [lsort [array names n]] { puts "CLS $k $n($k) [format %.1f [expr {$w($k)*1e12}]]" }
