# HBM-CORES-REBAL-10: lanes__canon TT setup on STAGE (3_place: ideal clock; 4_cts: propagated) with the kit RCX RC and the
# vclk TT bound: WNS/TNS, negative-endpoint classes (REBAL-9 sta_cls.tcl classes), and the three write hops this lane
# restructures: pins -> relay (wd_pin/wa_pin/w_pin), relay -> column copy (g_wcopy.*_q), copy -> SRAM (wd_in/w_addr/w_ce),
# plus reset recovery and multiplier stage-1 (REBAL-9 sta_cts.tcl).  Env: STAGE, PROP (1 = set_propagated_clock).
foreach f {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib} { read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$f }
read_liberty /work/macros/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
read_db [glob /work/run/results/asap7/*/base/$::env(STAGE).odb]
read_sdc [glob /work/run/results/asap7/*/base/$::env(STAGE).sdc]
if {$::env(PROP) eq "1"} { set_propagated_clock [get_clocks clk] }
if {[info exists ::env(OT_VCLK_TT)] && $::env(OT_VCLK_TT) ne ""} { source /work/vclk_corner.tcl; ot_vclk_bind tt }
source /work/setRC_rcx.tcl
estimate_parasitics -placement
puts "STAGE $::env(STAGE) PROP $::env(PROP)"
puts "WNS_ALL [sta::worst_slack_cmd max]"
report_tns
array set n {}; array set w {}
set nneg 0
foreach p [find_timing_paths -path_delay max -group_path_count 100000 -endpoint_path_count 1 -slack_max 0] {
  incr nneg
  set e [get_full_name [get_property $p endpoint]]; set s [get_full_name [get_property $p startpoint]]
  if {[regexp {u_m/(\w+)} $e -> pin]} { set k "SRAM_$pin<-[expr {[string match *wcopy* $s] ? {wcopy} : {other}}]" } \
  elseif {[string match *g_wcopy* $e]} { set k "COPY_D<-[expr {[string match *_pin* $s] ? {relay} : {other}}]" } \
  elseif {[regexp {u_bank\d\.(wd_pin|wa_pin|w_pin)} $e -> r]} { set k "RELAY_$r" } \
  elseif {[regexp {u_lane\.(u_\w+)} $e -> b]} { set k "lane.$b" } \
  elseif {[regexp {(u_bank\d|u_lane\d)} $e -> b]} { set k "[string range $b 0 5]" } else { set k other }
  if {![info exists n($k)]} { set n($k) 0; set w($k) 0 }
  incr n($k); set sl [get_property $p slack]; if {$sl < $w($k)} { set w($k) $sl }
}
puts "NEG_ENDPOINTS $nneg"
foreach k [lsort [array names n]] { puts "CLS $k $n($k) [format %.1f [expr {$w($k)*1e12}]]" }
proc hop {tag pins} {
  if {[llength $pins] == 0} { puts "HOP $tag none"; return }
  set p [lindex [find_timing_paths -path_delay max -to $pins -group_path_count 1] 0]
  if {$p eq ""} { puts "HOP $tag unconstrained"; return }
  puts [format "HOP %s n %d slack %.1f from %s to %s" $tag [llength $pins] [expr {[get_property $p slack]*1e12}] \
        [get_full_name [get_property $p startpoint]] [get_full_name [get_property $p endpoint]]]
}
hop relay_D [get_pins -quiet -hierarchical {*u_bank?.wd_pin*/D *u_bank?.wa_pin*/D *u_bank?.w_pin*/D}]
hop copy_D [get_pins -quiet -hierarchical *g_wcopy*/D]
hop sram_wd [get_pins -quiet -hierarchical *u_m/wd_in*]
hop sram_waddr [get_pins -quiet -hierarchical *u_m/w_addr_in*]
hop sram_wce [get_pins -quiet -hierarchical *u_m/w_ce_in]
hop sram_wmask [get_pins -quiet -hierarchical *u_m/w_mask_in*]
hop sram_raddr [get_pins -quiet -hierarchical *u_m/r_addr_in*]
foreach u {u_m1 u_m2 u_q u_e1m u_me2} {
  set ps [get_pins -hierarchical -quiet *u_lane.${u}.*/D]
  if {[llength $ps]} { set p [lindex [find_timing_paths -path_delay max -to $ps -group_path_count 1] 0]
    puts "MULALL $u [llength $ps] [format %.1f [expr {[get_property $p slack]*1e12}]]" }
}
puts "RESET_PATHS"; report_checks -path_delay max -from [get_ports {rst_lane_n* rst_n}] -format end -group_path_count 3
puts "WORST_FULL"; report_checks -path_delay max -group_path_count 1 -fields {fanout cap slew} -digits 1
