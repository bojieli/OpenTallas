# CLK-LEAF-BAL-1 11-11: measure clk_leaf_repeat sibling balance and the FF hold paths it touches, on one DB.
# openroad -no_init -exit clk_leaf_sibling_report.tcl, env:
#   OT_SR_HOOK  clk_leaf_repeat.tcl (sourced with OT_CLK_LEAF_REPEAT=0: procs only, no flow action)
#   OT_SR_LIBS  liberty files (space separated, one corner)   OT_SR_ODB odb   OT_SR_SDC sdc
#   OT_SR_SPEF  SPEF (routed RCX), else OT_SR_GUIDE (route.guide: estimate_parasitics -global_routing), else placement
#   OT_SR_RC    the kit's RC tcl (set_layer_rc / set_wire_rc, e.g. /work/setRC_rcx.tcl); required for the estimates
#   OT_SR_MODE  report (default) | balance (clr_balance on the DB's own families, then report again; writes the
#               chosen masters to OT_SR_OUT.masters.tsv) | apply (OT_SR_APPLY = a masters.tsv: swap those masters, report)
#   OT_SR_OUT   output prefix (.fam.tsv per-repeater rows, .hold.tsv hold paths, .masters.tsv)
#   OT_SR_HOLD_PS hold slack threshold of the path census (default 20)
# Groups: clr_bal_groups of the hook (clkleafrep repeaters under one grandparent net: cousins + siblings).  Member
# delay = mean propagated rising-edge clock arrival at the repeater's leaf loads (through nested repeaters).
set ::env(OT_CLK_LEAF_REPEAT) 0
source $::env(OT_SR_HOOK)
foreach l $::env(OT_SR_LIBS) { read_liberty $l }
read_db $::env(OT_SR_ODB)
read_sdc $::env(OT_SR_SDC)
if {[info exists ::env(OT_SR_RC)] && $::env(OT_SR_RC) ne ""} { source $::env(OT_SR_RC) }
set_propagated_clock [all_clocks]
if {[info exists ::env(OT_SR_SPEF)] && $::env(OT_SR_SPEF) ne ""} { read_spef $::env(OT_SR_SPEF); set par spef
} elseif {[info exists ::env(OT_SR_GUIDE)] && $::env(OT_SR_GUIDE) ne ""} { read_guides $::env(OT_SR_GUIDE); estimate_parasitics -global_routing; set par grt
} else { estimate_parasitics -placement; set par placement }
# clr_balance re-estimates after its swaps (swapMaster drops estimated parasitics; SPEF ones survive)
set ::clr_bal_reest_cmd [dict get {spef {} grt {estimate_parasitics -global_routing} placement {estimate_parasitics -placement}} $par]
clr_sta_refresh
set out $::env(OT_SR_OUT)
set mode [expr {[info exists ::env(OT_SR_MODE)] ? $::env(OT_SR_MODE) : "report"}]
set thr [expr {[info exists ::env(OT_SR_HOLD_PS)] ? double($::env(OT_SR_HOLD_PS)) : 20.0}]
set blk [ord::get_db_block]

proc sr_report {tag famlist out} {
  set blk [ord::get_db_block]
  set fh [open $out.$tag.fam.tsv w]
  puts $fh "group\trepeater\tmaster\tleaf_arr_max_ps\tleaf_arr_min_ps\tload_slew_ps\tn_leaves"
  set sps {}; set spn {}
  foreach f $famlist {
    lassign $f pn names
    set vmax {}; set vmin {}
    foreach nm $names {
      set i [$blk findInst $nm]; set m [clr_rep_meas $i]
      if {$m eq ""} continue
      lassign $m a b s n
      puts $fh [format "%s\t%s\t%s\t%.2f\t%.2f\t%.1f\t%d" $pn $nm [[$i getMaster] getName] $a $b $s $n]
      lappend vmax $a; lappend vmin $b
    }
    if {[llength $vmax] >= 2} {
      set smx [expr {[tcl::mathfunc::max {*}$vmax] - [tcl::mathfunc::min {*}$vmax]}]
      set smn [expr {[tcl::mathfunc::max {*}$vmin] - [tcl::mathfunc::min {*}$vmin]}]
      lappend sps [expr {max($smx, $smn)}]
    }
  }
  close $fh
  set sps [lsort -real $sps]; set n [llength $sps]
  if {$n} {
    set tot 0.0; set over 0; foreach v $sps { set tot [expr {$tot + $v}]; if {$v > 10.0} { incr over } }
    puts [format "SR_SPREAD %s families %d worst %.1f median %.1f mean %.1f over10 %d" $tag $n [lindex $sps end] [lindex $sps [expr {$n / 2}]] [expr {$tot / $n}] $over]
  } else { puts "SR_SPREAD $tag families 0" }
}
# clock iterm of a register instance: the input on a clock net
proc sr_ck {inst} {
  foreach it [$inst getITerms] {
    if {[$it isInputSignal] && [$it getNet] ne "NULL" && [clr_is_clock_net [$it getNet]]} { return $it }
  }
  return ""
}
# clock-tree ancestry of a clock iterm: driver instances, nearest first
proc sr_chain {it} {
  set out {}; set guard 0
  while {$it ne "" && [incr guard] < 64} {
    set n [$it getNet]; if {$n eq "NULL"} break
    set d ""
    foreach jt [$n getITerms] { if {[$jt isOutputSignal]} { set d [$jt getInst]; break } }
    if {$d eq ""} break
    lappend out [$d getName]
    set it ""
    foreach jt [$d getITerms] { if {[$jt isInputSignal] && [$jt getNet] ne "NULL"} { set it $jt; break } }
  }
  return $out
}
proc sr_hold {tag thr out} {
  set blk [ord::get_db_block]
  set fh [open $out.$tag.hold.tsv w]
  puts $fh "slack_ps\tskew_ps\tstart\tend\tdiverge_at\tlaunch_child\tcapture_child\trep_in_chain\tsibling_rep_divergence"
  set n 0; set n0 0; set nrep 0; set nsib 0; set nsib0 0; set ws ""
  set nall 0; set nport 0
  foreach pe [find_timing_paths -path_delay min -group_path_count 1000000 -endpoint_path_count 1 -slack_max $thr] {
    incr nall
    set sl [get_property $pe slack]
    set spin [get_property $pe startpoint]; set epin [get_property $pe endpoint]
    set sp [get_full_name $spin]; set ep [get_full_name $epin]
    set si ""; set ei ""
    catch {set si [sta::sta_to_db_inst [get_cells -of_objects $spin]]}
    catch {set ei [sta::sta_to_db_inst [get_cells -of_objects $epin]]}
    if {$si eq "NULL" || $ei eq "NULL" || $si eq "" || $ei eq ""} { incr nport; continue }
    set sck [sr_ck $si]; set eck [sr_ck $ei]
    if {$sck eq "" || $eck eq ""} { incr nport; continue }
    incr n; if {$sl < 0} { incr n0 }
    if {$ws eq "" || $sl < $ws} { set ws $sl }
    set lc [sr_chain $sck]; set cc [sr_chain $eck]
    set lca ""; set li -1; set ci -1
    for {set k 0} {$k < [llength $lc]} {incr k} { set j [lsearch -exact $cc [lindex $lc $k]]; if {$j >= 0} { set lca [lindex $lc $k]; set li $k; set ci $j; break } }
    set lch [expr {$li > 0 ? [lindex $lc [expr {$li - 1}]] : "-"}]
    set cch [expr {$ci > 0 ? [lindex $cc [expr {$ci - 1}]] : "-"}]
    set rep 0; foreach x [concat $lc $cc] { if {[string match "clkleafrep*" $x]} { set rep 1; break } }
    set sib [expr {$lch ne $cch && ([string match "clkleafrep*" $lch] || [string match "clkleafrep*" $cch])}]
    incr nrep $rep; incr nsib $sib; if {$sib && $sl < 0} { incr nsib0 }
    set la [clr_clk_arr [clr_sta_pin $sck] min]
    set ca [clr_clk_arr [clr_sta_pin $eck] max]
    set skew [expr {$la ne "" && $ca ne "" ? $ca - $la : "nan"}]
    puts $fh [format "%.2f\t%s\t%s\t%s\t%s\t%s\t%s\t%d\t%d" $sl [expr {$skew eq "nan" ? "nan" : [format %.1f $skew]}] $sp $ep $lca $lch $cch $rep $sib]
  }
  close $fh
  puts "SR_HOLD_ALL $tag paths slack<$thr: $nall, port / non-register ends: $nport"
  puts [format "SR_HOLD %s reg2reg endpoints slack<%.0f: %d (slack<0: %d), worst %s ps; clkleafrep in clock path: %d; launch/capture diverge at a clkleafrep sibling: %d (slack<0: %d)" \
          $tag $thr $n $n0 [expr {$ws eq "" ? "none" : [format %.2f $ws]}] $nrep $nsib $nsib0]
  puts [format "SR_WNS %s hold_ws %.2f setup_ws %.2f" $tag [worst_slack -min] [worst_slack -max]]
}

set fams [clr_bal_groups]
puts "SR_INFO parasitics $par mode $mode families [llength $fams] repeaters [llength [concat {*}[lmap f $fams {lindex $f 1}]]]"
sr_report before $fams $out
sr_hold before $thr $out
if {$mode eq "balance"} {
  set nsw [clr_balance $fams report]
  set fh [open $out.masters.tsv w]
  foreach f $fams { foreach nm [lindex $f 1] { puts $fh "$nm\t[[[$blk findInst $nm] getMaster] getName]" } }
  close $fh
  sr_report after $fams $out
  sr_hold after $thr $out
} elseif {$mode eq "apply"} {
  set fh [open $::env(OT_SR_APPLY) r]; set na 0
  foreach ln [split [read $fh] "\n"] {
    lassign $ln nm mn; if {$nm eq ""} continue
    set i [$blk findInst $nm]; set m [[ord::get_db] findMaster $mn]
    if {$i eq "NULL" || $m eq "NULL" || $i eq "" || $m eq ""} { puts "SR_APPLY missing $nm $mn"; continue }
    if {[[$i getMaster] getName] ne $mn} { $i swapMaster $m; incr na }
  }
  close $fh
  clr_sta_refresh
  puts "SR_APPLY swapped $na"
  sr_report after $fams $out
  sr_hold after $thr $out
}
puts "SR_DONE"
