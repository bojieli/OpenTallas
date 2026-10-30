set ::env(OT_VCLK_FF) 253.555495
set ::env(OT_HOLD_MARGIN) 10
set E /eco
set B /work/run/results/asap7/kq_qfd_dv_s8x_vmr_f4a_m1/base
set fh [open $E/libs_tt.txt]; foreach f [split [string trim [read $fh]] "\n"] { read_liberty $f }; close $fh
read_db $B/5_2_route.odb
read_spef $B/6_final.spef
read_sdc $E/golden.sdc
set_propagated_clock [all_clocks]
set_clock_latency -source 253.555495 [get_clocks vclk]
set din {}; foreach p [all_inputs] { set n [get_full_name $p]; if {$n ni {ck ft_ck_i ft_rst_i}} { lappend din $p } }
set dout [lmap p [all_outputs] {if {[get_full_name $p] in {ft_ck_o ft_rst_o}} continue; set p}]
set_input_delay -min -40 -clock vclk $din
set_output_delay -min 0 -clock vclk $dout
set_dont_use {*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*}
proc hp {v} { return [format %.2f [sta::time_sta_ui $v]] }
proc ckfp {} {
  set n 0; set h 0
  foreach c [get_cells -quiet -hierarchical ot_ms_*] { incr n; set h [expr {($h * 31 + [string length [get_full_name $c]] + [string length [get_property $c ref_name]]) % 1000000007}] }
  return "$n $h"
}
proc isclk {n} { set nm [$n getName]; return [expr {[$n getSigType] eq "CLOCK" || [string match ot_ms_* $nm] || [string match clknet* $nm]}] }
set blk [ord::get_db_block]
proc netsig {n} { set s {}; foreach t [$n getITerms] { lappend s "[[$t getInst] getName]/[[$t getMTerm] getName]" }; foreach t [$n getBTerms] { lappend s "P:[$t getName]" }; return [lsort $s] }
set sig0 [dict create]; foreach n [$blk getNets] { if {[$n isSpecial]} continue; dict set sig0 [$n getName] [netsig $n] }
set st0 [dict create]; foreach i [$blk getInsts] { dict set st0 [$i getName] [$i getPlacementStatus] }
set m0 [dict create]; foreach i [$blk getInsts] {dict set m0 [$i getName] [[$i getMaster] getName]}
set fp0 [ckfp]
set h0 [hp [sta::worst_slack_cmd min]]; set e0 [sta::endpoint_violation_count min]; set s0 [hp [sta::worst_slack_cmd max]]
puts "ECO_BEFORE hold $h0 ep $e0 setup_ff $s0 vclk_ff $::env(OT_VCLK_FF) clock_cells $fp0"
# Data-only TT routed-RC slew repair. Existing flops and clock cells remain fixed masters.
set_dont_touch [all_registers -cells]
set_dont_touch [get_cells -hierarchical ot_ms_*]
set_dont_touch [get_nets -hierarchical ot_ms_*]
report_check_types -max_slew -violators -max_count 100
repair_design -slew_margin 10 -cap_margin 0 -verbose
report_check_types -max_slew -violators -max_count 100
set fp1 [ckfp]
set h1 [hp [sta::worst_slack_cmd min]]; set e1 [sta::endpoint_violation_count min]; set s1 [hp [sta::worst_slack_cmd max]]
puts "ECO_AFTER_REPAIR hold $h1 ep $e1 setup_ff $s1 clock_cells $fp1"
if {$fp0 ne $fp1} { error "ECO: clock cell fingerprint changed $fp0 -> $fp1" }
# ---- (3) legalize only new cells ----
set new {}
foreach i [$blk getInsts] { set nm [$i getName]; if {[dict exists $st0 $nm]} { if {[dict get $st0 $nm] eq "PLACED" && [dict get $m0 $nm] eq [[$i getMaster] getName]} { $i setPlacementStatus FIRM } } else { lappend new $nm } }
puts "ECO_NEW_INSTS [llength $new]"
detailed_placement
check_placement -verbose
foreach i [$blk getInsts] { set nm [$i getName]; if {[dict exists $st0 $nm]} { $i setPlacementStatus [dict get $st0 $nm] } }
global_connect
# ---- dirty nets ----
set resized {}; foreach i [$blk getInsts] {set nm [$i getName]; if {[dict exists $m0 $nm] && [dict get $m0 $nm] ne [[$i getMaster] getName]} {lappend resized $nm}}
puts "ECO_RESIZED $resized"
set dirty {}
foreach n [$blk getNets] {
  if {[$n isSpecial]} continue
  set nm [$n getName]
  set touched 0; foreach t [$n getITerms] {if {[[$t getInst] getName] in $resized} {set touched 1}}
  if {$touched || ![dict exists $sig0 $nm] || [dict get $sig0 $nm] ne [netsig $n]} { lappend dirty $n }
}
set dn {}
foreach n $dirty { if {[isclk $n]} { error "ECO: clock net [$n getName] is dirty" }; lappend dn [$n getName]; set w [$n getWire]; if {$w ne "NULL" && $w ne ""} { odb::dbWire_destroy $w } }
set f [open $E/dirty_nets.txt w]; puts $f [join [lsort $dn] "\n"]; close $f
puts "ECO_DIRTY nets [llength $dn]"
set_routing_layers -clock M4-M5
set_routing_layers -signal M2-M5
global_route -congestion_iterations 30 -allow_congestion
set ng 0; set nc 0
foreach n [$blk getNets] { if {[$n isSpecial]} continue; if {[$n getName] in $dn} { incr ng; continue }; $n clearGuides; incr nc }
puts "ECO_GUIDES kept_on_dirty $ng cleared $nc"
set f [open $E/eco_repair.txt w]
puts $f "ECO_REPAIR hold_before $h0 ep $e0 hold_after_est $h1 ep $e1 setup_ff $s0 -> $s1 vclk_tt 253.555495 slew_margin 10 new_insts [llength $new] dirty_nets [llength $dn] clock_cells $fp0 -> $fp1 | [clock format [clock seconds]]"
close $f
write_db $B/5_1_grt.odb
puts ECO_DONE
