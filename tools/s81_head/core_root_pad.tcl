# HEAD-CORE-LAT 10-26: core clock-latency target pad (POST_CTS hook, before any repair).
# Owner: common per-die clock-latency target at the core clk pin.  The faster core type gets a delay chain between its
# clk port and the CTS root, i.e. on the path COMMON to every sink of the core (intra-core skew unchanged), placed next
# to the clk pin on the infra-island edge.  N stages are chosen from the measured intrinsic insertion of the trial
# (T - measured) / stage delay; the gate on 5_1_grt (GRT RC, TT and FF) then confirms |mean - T| <= tol.
#   OT_ROOT_PAD_N       number of stages (0 = no-op)
#   OT_ROOT_PAD_MASTER  default BUFx4f_ASAP7_75t_R (TT/FF ratio of a cell chain ~ the core tree's 0.80)
set ot_rp_n [expr {[info exists ::env(OT_ROOT_PAD_N)] ? $::env(OT_ROOT_PAD_N) : 0}]
if {$ot_rp_n > 0} {
  set ot_rp_m [expr {[info exists ::env(OT_ROOT_PAD_MASTER)] ? $::env(OT_ROOT_PAD_MASTER) : "BUFx4f_ASAP7_75t_R"}]
  set blk [ord::get_db_block]
  set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set master [[ord::get_db] findMaster $ot_rp_m]
  if {$master eq "NULL"} { error "core_root_pad: no master $ot_rp_m" }
  set bt [$blk findBTerm clk]
  set cnet [$bt getNet]
  # loads of the port net move to the end of the chain
  set loads {}
  foreach it [$cnet getITerms] { if {[$it isInputSignal]} { lappend loads $it } }
  set bp [lindex [$bt getBPins] 0]
  set bb [$bp getBBox]
  set px [expr {([$bb xMin] + [$bb xMax]) / 2}]
  set py [expr {([$bb yMin] + [$bb yMax]) / 2}]
  set prev $cnet
  for {set k 0} {$k < $ot_rp_n} {incr k} {
    set inst [odb::dbInst_create $blk $master "ot_rootpad_$k"]
    set out [odb::dbNet_create $blk "ot_rootpad_net_$k"]
    $out setSigType CLOCK
    foreach it [$inst getITerms] {
      set mt [$it getMTerm]
      if {[$mt getSigType] eq "POWER" || [$mt getSigType] eq "GROUND"} continue
      if {[$mt getIoType] eq "INPUT"} { $it connect $prev } elseif {[$mt getIoType] eq "OUTPUT"} { $it connect $out }
    }
    # pin sits on the hole N edge: put the chain just above it (outside the core keep-out), legalised below
    $inst setLocation [expr {$px - 2 * $dbu + $k * round(0.54 * $dbu)}] [expr {$py + round(1.62 * $dbu)}]
    $inst setPlacementStatus PLACED
    set prev $out
  }
  foreach it $loads { $it disconnect; $it connect $prev }
  global_connect
  detailed_placement
  puts "OT_ROOT_PAD $ot_rp_n x $ot_rp_m on clk -> [llength $loads] root load(s)"
}
