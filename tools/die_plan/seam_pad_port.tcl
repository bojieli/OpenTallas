# GENERATED-INTO-KIT by seam_pad_per_pin.py stage() (SEAM-PAD-R3, class C-PARENT-SEAM-HOLD): per-pin PORT-INGRESS hold pad.
# A chain of n HB4xp67 between the input port net and EVERY load of that net (one chain per port, however many capture
# flops it feeds), n from seam_pad_port_n.tcl (::ot_sp_per {port n}).  Function-preserving (buffers only).  Run once on a
# placed DB (hold_budget.tcl PRE_CTS) or in memory by seam_pad_measure.tcl (the proof sources this same file).
# Fail closed: a sized port that is not a port of the DB, has no net, or shares its net with another port stops the run
# (stale sizing) unless OT_SEAM_PAD_ALLOW_MISSING=1.
if {[info exists ::env(OT_SP_N_FILE)]} { source $::env(OT_SP_N_FILE) } else { source /work/seam_pad_port_n.tcl }
proc ::ot_sp_master {nm} { foreach l [[ord::get_db] getLibs] { set m [$l findMaster $nm]; if {$m ne "NULL"} { return $m } }; return "NULL" }
set ot_sp_blk [ord::get_db_block]
set ot_sp_hb4 [::ot_sp_master HB4xp67_ASAP7_75t_R]
if {$ot_sp_hb4 eq "NULL"} { puts "OT_SEAM_PAD ERROR HB4xp67 master missing"; error "OT_SEAM_PAD master" }
set ot_sp_in ""; set ot_sp_out ""
foreach t [$ot_sp_hb4 getMTerms] {
  if {[$t getSigType] ne "SIGNAL"} continue
  if {[$t getIoType] eq "INPUT"} {set ot_sp_in [$t getName]} elseif {[$t getIoType] eq "OUTPUT"} {set ot_sp_out [$t getName]}
}
set ot_sp_seq 0; set ot_sp_ports 0; set ot_sp_missing 0
dict for {ot_sp_port ot_sp_n} $::ot_sp_per {
  set ot_sp_bt [$ot_sp_blk findBTerm $ot_sp_port]
  if {$ot_sp_bt eq "NULL" || $ot_sp_bt eq ""} { incr ot_sp_missing; puts "OT_SEAM_PAD missing port $ot_sp_port"; continue }
  set ot_sp_net [$ot_sp_bt getNet]
  if {$ot_sp_net eq "NULL" || $ot_sp_net eq "" || [llength [$ot_sp_net getBTerms]] != 1} { incr ot_sp_missing; puts "OT_SEAM_PAD port $ot_sp_port: no net or shared net"; continue }
  set ot_sp_loads [$ot_sp_net getITerms]
  if {![llength $ot_sp_loads]} { incr ot_sp_missing; puts "OT_SEAM_PAD port $ot_sp_port: no loads"; continue }
  set ot_sp_bb [$ot_sp_bt getBBox]
  set ot_sp_x [expr {([$ot_sp_bb xMin] + [$ot_sp_bb xMax]) / 2}]; set ot_sp_y [expr {([$ot_sp_bb yMin] + [$ot_sp_bb yMax]) / 2}]
  foreach ot_sp_it $ot_sp_loads { $ot_sp_it disconnect }
  set ot_sp_prev $ot_sp_net
  for {set ot_sp_k 0} {$ot_sp_k < $ot_sp_n} {incr ot_sp_k} {
    incr ot_sp_seq
    set ot_sp_b [odb::dbInst_create $ot_sp_blk $ot_sp_hb4 "ot_seampad_$ot_sp_seq"]
    $ot_sp_b setOrigin $ot_sp_x $ot_sp_y
    $ot_sp_b setPlacementStatus PLACED
    set ot_sp_nn [odb::dbNet_create $ot_sp_blk "ot_seampad_n$ot_sp_seq"]
    [$ot_sp_b findITerm $ot_sp_in] connect $ot_sp_prev
    [$ot_sp_b findITerm $ot_sp_out] connect $ot_sp_nn
    set ot_sp_prev $ot_sp_nn
  }
  foreach ot_sp_it $ot_sp_loads { $ot_sp_it connect $ot_sp_prev }
  incr ot_sp_ports
}
puts "OT_SEAM_PAD ports padded $ot_sp_ports hb4 cells $ot_sp_seq sized [dict size $::ot_sp_per] missing $ot_sp_missing"
if {$ot_sp_missing > 0 && !([info exists ::env(OT_SEAM_PAD_ALLOW_MISSING)] && $::env(OT_SEAM_PAD_ALLOW_MISSING) eq "1")} {
  error "OT_SEAM_PAD: $ot_sp_missing sized ports not usable in the DB (stale sizing)"
}
