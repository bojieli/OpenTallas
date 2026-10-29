# Opt-in A0 parent hook; wrapper replaces ONLY the outer CTS call in this kit.
if {[llength [info commands ot_parent_native_cts]]} {error "parent hook sourced twice"}
rename clock_tree_synthesis ot_parent_native_cts
proc clock_tree_synthesis {args} {
 set b [ord::get_db_block];set db [ord::get_db];set dbu [$b getDbUnitsPerMicron]
 set ck [$b findNet ck]
 if {$ck eq "NULL"} {error "parent hook no ck net"}
 set icgs {}
 foreach i [$b getInsts] {if {[[$i getMaster] getName] eq "ICGx8DC_ASAP7_75t_R"} {lappend icgs $i}}
 if {[llength $icgs]!=1} {error "parent hook needs exactly one RTL ICG, got [llength $icgs]"}
 set icg [lindex $icgs 0];set gated [[$icg findITerm GCLK] getNet]
 set f [open /work/parent_sinks.txt w];set die [$b getDieArea]
 puts $f "DIE [$die xMax] [$die yMax] $dbu"
 foreach i [$b getInsts] {if {[[$i getMaster] isBlock]} {set bb [$i getBBox];puts $f "MACRO [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]"}}
 foreach {n ung} [list $gated 0 $ck 1] {
  foreach it [$n getITerms] {
   set i [$it getInst]
   if {$i eq $icg || ![$it isInputSignal]} {continue}
   set pn [[$it getMTerm] getName]
   if {$pn ni {CLK clk ck}} {error "parent clock net reaches unexpected [$i getName]/$pn"}
   set bb [$it getBBox];set m [$i getMaster]
   puts $f "SINK [$i getName] [$m getName] $pn [expr {([$bb xMin]+[$bb xMax])/2.0}] [expr {([$bb yMin]+[$bb yMax])/2.0}] $ung [$m isBlock]"
  }
 }
 close $f
 puts [exec python3 -I /work/parent_trunk_prepare.py /work/parent_sinks.txt /work/parent_clusters.json]
 source /work/parent_clusters.tcl
 set nets {};set master [$db findMaster CKINVDCx16_ASAP7_75t_R]
 foreach c $CL {
  lassign $c name x y ung regs
  set net [odb::dbNet_create $b $name];$net setSigType CLOCK
  set i [odb::dbInst_create $b $master ${name}_root]
  $i setLocation [expr {int($x*$dbu)}] [expr {int($y*$dbu)}];$i setPlacementStatus PLACED
  [$i findITerm A] connect [expr {$ung ? $ck : $gated}];[$i findITerm Y] connect $net
  foreach r $regs {set it [[$b findInst $r] findITerm CLK];$it disconnect;$it connect $net}
  lappend nets $name
 }
 detailed_placement
 ot_parent_native_cts -clk_nets $nets -sink_clustering_enable -repair_clock_nets
 detailed_placement
 check_placement
 estimate_parasitics -placement
 # DPL can snap or move cluster roots; the planner must use the built locations.
 set sf [open /work/parent_cluster_sites.txt w]
 foreach c $CL {
  set name [lindex $c 0];set i [$b findInst ${name}_root]
  lassign [$i getLocation] x y
  puts $sf "$name [expr {$x/double($dbu)}] [expr {$y/double($dbu)}]"
 }
 close $sf
 write_db /work/parent_clusters.odb
 write_sdc /work/parent_clusters.sdc
 foreach {corner var} {TT TC_LIB_FILES FF BC_LIB_FILES} {
  if {![info exists ::env($var)]} {error "parent hook missing exact $var"}
  puts [exec env PT_CORNER=$corner PT_LIBS=$::env($var) openroad -exit /work/parent_trunk_measure.tcl 2>@1]
 }
 puts [exec python3 -I /work/parent_trunk_plan.py 2>@1]
 if {[info exists ::env(OT_PT_PLAN_ONLY)] && $::env(OT_PT_PLAN_ONLY) eq "1"} {
  puts "PARENT_TRUNK_PLAN_ONLY: local CTS and proposed trunk saved; inspect rendered tree before inserting trunk or GRT"
  return
 }
 set ::env(TTCL) /work/parent_trunk_plan.tcl
 set ::env(ICG_INST) [$icg getName]
 set ::env(OT_PT_NO_IO) 1
 source /work/parent_trunk_insert.tcl
 foreach i [$b getInsts] {
  if {[string match a0t_* [$i getName]] || [string match a0cl*_root [$i getName]] || $i eq $icg} {$i setDoNotTouch 1}
 }
 puts "PARENT_TRUNK_CTS installed [llength $nets] clusters, RTL ICG [$icg getName], plan /work/parent_trunk_plan.json"
}
