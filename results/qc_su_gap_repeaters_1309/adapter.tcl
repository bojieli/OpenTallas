set ot_gap_bands {{4.32 32.56} {304.4 352.24} {624.0799999999999 723.76} {995.5999999999999 1043.44} {1315.28 1334.88}}
set ot_gap_cores {{17.28 34.56 432.0 302.4} {17.28 354.24 432.0 622.0799999999999} {17.28 725.76 432.0 993.5999999999999} {17.28 1045.44 432.0 1313.28}}

# INACTIVE until explicitly sourced by BOTH prototype and production caller.
proc ot_gap_before_repair {} {
  global ot_gap_old ot_gap_moved
  array unset ot_gap_old; array unset ot_gap_moved
  foreach i [[ord::get_db_block] getInsts] { set ot_gap_old([$i getName]) 1 }
}
proc ot_gap_capture_after_repair {outdir} {
  global ot_gap_old
  if {![array exists ot_gap_old]} { error "gap adapter requires before-repair ID capture" }
  file mkdir $outdir
  write_db $outdir/pre_dpl.odb
  write_def $outdir/pre_dpl.def
  set fh [open $outdir/cells.tsv w]
  foreach i [[ord::get_db_block] getInsts] {
    set nm [$i getName]; set b [$i getBBox]
    set fresh [expr {![info exists ot_gap_old($nm)] && [regexp {^(BUF|INV)} [[$i getMaster] getName]]}]
    puts $fh "$nm\t[[$i getMaster] getName]\t[$b xMin]\t[$b yMin]\t[$b xMax]\t[$b yMax]\t$fresh"
  }
  close $fh
  puts "OT_GAP exact post-repair/pre-DPL capture $outdir"
}
# Allocate via this module's allocate_sites using the captured actual cells and
# DEF rows. Source emit_sites_tcl output ONLY after geometry review. There is no
# nearest-gap point-only fallback: all whole cells must fit actual unoccupied sites.
proc ot_gap_validate_after_dpl {{max_dx 4.0}} {
  global ot_gap_moved ot_gap_bands
  set block [ord::get_db_block]; set dbu [$block getDbUnitsPerMicron]
  set failures {}
  foreach nm [array names ot_gap_moved] {
    set i [$block findInst $nm]
    if {$i eq "NULL"} { lappend failures "$nm:missing"; continue }
    set b [$i getBBox]; set x [expr {[$b xMin]/double($dbu)}]; set y [expr {[$b yMin]/double($dbu)}]
    set h [expr {[$b dy]/double($dbu)}]; set oldx [lindex $ot_gap_moved($nm) 0]
    set fit 0
    foreach band $ot_gap_bands { lassign $band lo hi; if {$y>=$lo-1e-6 && $y+$h<=$hi+1e-6} { set fit 1 } }
    if {!$fit || abs($x-$oldx)>$max_dx} { lappend failures "$nm:x=$x,y=$y,oldx=$oldx" }
  }
  # Mandatory OpenDP legal-row / overlap / core-blockage check, no waiver.
  check_placement -verbose
  if {[llength $failures]} { error "gap adapter post-DPL failures [llength $failures]: [lrange $failures 0 9]" }
  puts "OT_GAP post-DPL PASS [array size ot_gap_moved] repeaters within real gaps and $max_dx um ribbon x"
}
