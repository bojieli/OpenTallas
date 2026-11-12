# GENERATED-INTO-KIT by face_hold_pad.py stage(): port-scope hold pad for forwarded-clock capture flops (S81-CORES-1).
# PRE_CTS, once, on the placed 3_place DB.  Sizes come from face_hold_pad_n.tcl (per endpoint, measured FF hold):
#   ::ot_fp_match glob of the capture flop instance names, ::ot_fp_by inst|port, ::ot_fp_per {key n}, ::ot_fp_default n for unlisted flops.
# Each selected DFF gets a chain of n HB4xp67 cells on its D net, placed at the flop (DPL legalises later).
# Fail closed: a sized instance that is not in the DB (stale sizing) stops the kit unless OT_FACE_PAD_ALLOW_MISSING=1.
source /work/face_hold_pad_n.tcl
proc ::ot_fp_master {nm} { foreach l [[ord::get_db] getLibs] { set m [$l findMaster $nm]; if {$m ne "NULL"} { return $m } }; return "NULL" }
proc ::ot_fp_io {m} {
  set i ""; set o ""
  foreach t [$m getMTerms] {
    if {[$t getSigType] ne "SIGNAL"} continue
    if {[$t getIoType] eq "INPUT"} {set i [$t getName]} elseif {[$t getIoType] eq "OUTPUT"} {set o [$t getName]}
  }
  return [list $i $o]
}
set ot_fp_blk [ord::get_db_block]
set ot_fp_hb4 [::ot_fp_master HB4xp67_ASAP7_75t_R]
if {$ot_fp_hb4 eq "NULL"} { puts "OT_FACE_PAD ERROR HB4xp67 master missing"; error "OT_FACE_PAD master" }
lassign [::ot_fp_io $ot_fp_hb4] ot_fp_in ot_fp_out
# by=port: the key is the input port feeding the D pin (traced back through BUF/INV/HB cells); stage DBs rename the flops.
proc ::ot_fp_port {dt} {
  set net [$dt getNet]
  for {set hop 0} {$hop < 64} {incr hop} {
    if {[llength [$net getBTerms]]} { return [[lindex [$net getBTerms] 0] getName] }
    set drv ""
    foreach it [$net getITerms] { if {[$it isOutputSignal]} { set drv $it } }
    if {$drv eq ""} { return "" }
    if {![regexp {^(BUF|INV|HB)} [[[$drv getInst] getMaster] getName]]} { return "" }
    set in ""
    foreach it [[$drv getInst] getITerms] { if {[$it isInputSignal]} { set in $it } }
    if {$in eq ""} { return "" }
    set net [$in getNet]
  }
  return ""
}
set ot_fp_cnt 0; set ot_fp_seq 0; set ot_fp_seen {}
foreach ot_fp_inst [$ot_fp_blk getInsts] {
  set ot_fp_nm [$ot_fp_inst getName]
  if {![string match $::ot_fp_match $ot_fp_nm]} continue
  if {![string match DFF* [[$ot_fp_inst getMaster] getName]]} continue
  set ot_fp_dt [$ot_fp_inst findITerm D]
  if {$ot_fp_dt eq "NULL" || $ot_fp_dt eq ""} continue
  set ot_fp_key $ot_fp_nm
  if {$::ot_fp_by eq "port"} { set ot_fp_key [::ot_fp_port $ot_fp_dt] }
  set ot_fp_n [expr {[dict exists $::ot_fp_per $ot_fp_key] ? [dict get $::ot_fp_per $ot_fp_key] : $::ot_fp_default}]
  if {[dict exists $::ot_fp_per $ot_fp_key]} { lappend ot_fp_seen $ot_fp_key }
  if {$ot_fp_n <= 0} continue
  set ot_fp_net [$ot_fp_dt getNet]
  if {$ot_fp_net eq "NULL" || $ot_fp_net eq ""} continue
  set ot_fp_bb [$ot_fp_inst getBBox]
  set ot_fp_x [$ot_fp_bb xMin]; set ot_fp_y [$ot_fp_bb yMin]
  $ot_fp_dt disconnect
  set ot_fp_prev $ot_fp_net
  for {set ot_fp_k 0} {$ot_fp_k < $ot_fp_n} {incr ot_fp_k} {
    incr ot_fp_seq
    set ot_fp_b [odb::dbInst_create $ot_fp_blk $ot_fp_hb4 "ot_fpad_$ot_fp_seq"]
    $ot_fp_b setOrigin $ot_fp_x $ot_fp_y
    $ot_fp_b setPlacementStatus PLACED
    set ot_fp_nn [odb::dbNet_create $ot_fp_blk "ot_fpad_n$ot_fp_seq"]
    [$ot_fp_b findITerm $ot_fp_in] connect $ot_fp_prev
    [$ot_fp_b findITerm $ot_fp_out] connect $ot_fp_nn
    set ot_fp_prev $ot_fp_nn
  }
  $ot_fp_dt connect $ot_fp_prev
  incr ot_fp_cnt
}
set ot_fp_missing 0
dict for {ot_fp_k ot_fp_v} $::ot_fp_per { if {[lsearch -exact -sorted [lsort $ot_fp_seen] $ot_fp_k] < 0} { incr ot_fp_missing } }
puts "OT_FACE_PAD flops padded $ot_fp_cnt hb4 cells $ot_fp_seq sized_endpoints [dict size $::ot_fp_per] missing $ot_fp_missing"
if {$ot_fp_missing > 0 && !([info exists ::env(OT_FACE_PAD_ALLOW_MISSING)] && $::env(OT_FACE_PAD_ALLOW_MISSING) eq "1")} {
  error "OT_FACE_PAD: $ot_fp_missing sized endpoints not in the DB (stale sizing)"
}
