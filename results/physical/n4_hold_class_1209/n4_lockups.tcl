error "PARKED_PROPOSAL_DO_NOT_LAUNCH: broad/incomplete clockload; seePRICE.md"
# New fresh-synthesis physical form: supported transparent-low DLLx1 lockups on measured direct chains only.
# Reads exact source/destination names and original TT setup margin from n4_lockup_targets.tsv.
set lk_blk [ord::get_db_block]
set lk_master [[ord::get_db] findMaster DLLx1_ASAP7_75t_R]
if {$lk_master eq "NULL" || $lk_master eq ""} {error "LOCKUP_FORM DLLx1 master absent"}
set lk_map [dict create]
foreach i [$lk_blk getInsts] {dict set lk_map [string map {\\ {}} [$i getName]] $i}
proc lk_root {pin} {
  set net [$pin getNet];set seen [dict create];set count 0
  while {$net ne "NULL" && $net ne ""} {
    if {[dict exists $seen [$net getName]] || [llength [$net getBTerms]]} {error "LOCKUP_FORM cycle/port in chain"}
    dict set seen [$net getName] 1
    set dr {}
    foreach t [$net getITerms] {if {[[$t getMTerm] getIoType] eq "OUTPUT"} {lappend dr $t}}
    if {[llength $dr] != 1} {error "LOCKUP_FORM nonunique driver"}
    set it [lindex $dr 0];set i [$it getInst];set mn [[$i getMaster] getName]
    if {[regexp {^DFFHQN} $mn] && [[$it getMTerm] getName] eq "QN"} {return $i}
    if {![regexp {^(BUF|INV|HB)} $mn] || [incr count]>8} {error "LOCKUP_FORM arithmetic/non-direct chain: $mn"}
    set ins {}
    foreach t [$i getITerms] {if {[[$t getMTerm] getSigType] eq "SIGNAL" && [[$t getMTerm] getIoType] eq "INPUT"} {lappend ins $t}}
    if {[llength $ins]!=1} {error "LOCKUP_FORM multiinput buffer"}
    set net [[lindex $ins 0] getNet]
  }
  error "LOCKUP_FORM disconnected chain"
}
set lk_f [open /work/n4_lockup_targets.tsv r]
set lk_rows [split [string trim [read $lk_f]] "\n"];close $lk_f
set lk_n 0
foreach row $lk_rows {
  lassign [split $row "\t"] sn dn slack nbuf
  if {$slack<500 || ![string match u_fcore.u_native.* $sn] || ![string match u_fcore.u_native.* $dn]} {error "LOCKUP_FORM unsafe target manifest"}
  if {![dict exists $lk_map $sn] || ![dict exists $lk_map $dn]} {error "LOCKUP_FORM missing source/destination: $sn -> $dn"}
  set si [dict get $lk_map $sn];set di [dict get $lk_map $dn]
  if {![regexp {^DFFHQN} [[$di getMaster] getName]]} {error "LOCKUP_FORM capture is not rising FF"}
  set dp [$di findITerm D];set sc [$si findITerm CLK];set dc [$di findITerm CLK]
  if {$dp eq "NULL" || $sc eq "NULL" || $dc eq "NULL" || [$sc getNet] ne [$dc getNet]} {error "LOCKUP_FORM mismatched clock domain"}
  set root [lk_root $dp]
  if {[string map {\\ {}} [$root getName]] ne $sn} {error "LOCKUP_FORM source identity mismatch"}
  if {![info exists ::env(OT_LOCKUP_DRYRUN)] || !$::env(OT_LOCKUP_DRYRUN)} {
    set old [$dp getNet]
    set ni [odb::dbInst_create $lk_blk $lk_master "codex_n4lk_$lk_n"]
    set nn [odb::dbNet_create $lk_blk "codex_n4lk_${lk_n}_o"]
    $dp disconnect;$dp connect $nn
    [$ni findITerm D] connect $old
    [$ni findITerm Q] connect $nn
    [$ni findITerm CLK] connect [$sc getNet]
    $ni setDoNotTouch 0
  }
  incr lk_n
}
if {$lk_n!=9923} {error "LOCKUP_FORM unexpected target count $lk_n"}
puts "LOCKUP_FORM native_direct_chain_latches $lk_n PIN_CYCLES 0 setup_guard500"
if {![info exists ::env(OT_LOCKUP_DRYRUN)] || !$::env(OT_LOCKUP_DRYRUN)} {global_connect}
