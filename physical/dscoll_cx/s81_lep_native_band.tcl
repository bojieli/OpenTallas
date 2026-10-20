# S81 standard/MU LEP source-coupled single-band policy. No source, net,
# clock, supply or timing constraint is changed here. All original/new cells
# remain subject to native placement, timing, connectivity and reach checks.
source /src/physical/dscoll_cx/native_cell_fence.tcl
set ot_lep_band {2.16 259.2 473.04 291.6}
set ot_lep_owner ot_s81_lep_std_band
proc ot_lep_nonmacro_names {} {
  set names {}
  foreach i [[ord::get_db_block] getInsts] {
    if {![[$i getMaster] isBlock]} {lappend names [$i getName]}
  }
  return [lsort $names]
}
proc ot_lep_prop {i} { return [odb::dbStringProperty_find $i ot_lep_birth] }
proc ot_lep_manifest {stage} {
  set b [ord::get_db_block]
  set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set path [file join $::env(RESULTS_DIR) ot_lep_${stage}_cells.tsv]
  set f [open $path w]
  puts $f "instance\tmaster\tmaster_type\tbirth_stage\towner\tstatus\tx0_um\ty0_um\tx1_um\ty1_um\tarea_um2"
  set area 0;set cells 0
  foreach n [ot_lep_nonmacro_names] {
    set i [$b findInst $n];set m [$i getMaster];set bb [$i getBBox]
    set prop [ot_lep_prop $i]
    if {$prop eq "NULL"} {error "LEP_MANIFEST missing birth classification $n"}
    set g [$i getGroup]
    if {$g eq "NULL" || [$g getName] ne $::ot_lep_owner} {error "LEP_MANIFEST missing/conflicting owner $n"}
    set a [expr {[$m getWidth]*double([$m getHeight])/($u*$u)}]
    set area [expr {$area+$a}];incr cells
    puts $f [join [list $n [$m getName] [$m getType] [$prop getValue] [$g getName] [$i getPlacementStatus] [expr {[$bb xMin]/double($u)}] [expr {[$bb yMin]/double($u)}] [expr {[$bb xMax]/double($u)}] [expr {[$bb yMax]/double($u)}] $a] "\t"]
  }
  close $f
  # Preserve the exact current native inventory, including retired originals.
  # A resizer may remove buffers; no deletion is hidden by an area estimate.
  set previous [file join $::env(RESULTS_DIR) ot_lep_previous_cells.tsv]
  set retired [open [file join $::env(RESULTS_DIR) ot_lep_${stage}_retired.tsv] w]
  if {[file exists $previous]} {
    set prev [open $previous r];gets $prev header
    while {[gets $prev row] >= 0} {
      set nm [lindex [split $row "\t"] 0]
      if {[$b findInst $nm] eq "NULL"} {puts $retired $row}
    }
    close $prev
  }
  close $retired
  file copy -force $path $previous
  puts "LEP_MANIFEST stage=$stage cells=$cells area_um2=$area path=$path"
}
proc ot_lep_trim_rows {} {
  set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
  lassign $::ot_lep_band x0 y0 x1 y1
  set remove {};set kept 0
  foreach r [$b getRows] {
    set bb [$r getBBox]
    if {[$bb yMin] < round($y0*$u) || [$bb yMax] > round($y1*$u)} {lappend remove $r;continue}
    if {[$bb xMin] > round($x0*$u) || [$bb xMax] < round($x1*$u)} {error "LEP_ROWS not full-width [$r getName]"}
    incr kept
  }
  foreach r $remove {odb::dbRow_destroy $r}
  if {$kept != 120} {error "LEP_ROWS expected120 continuous270nm rows, got$kept"}
  puts "LEP_ROWS kept=$kept removed=[llength $remove] band=$::ot_lep_band"
}
proc ot_lep_initial_owner {} {
  set b [ord::get_db_block];set names [ot_lep_nonmacro_names]
  foreach n $names {
    set i [$b findInst $n]
    if {[ot_lep_prop $i] ne "NULL"} {error "LEP_INITIAL duplicate classification $n"}
    odb::dbStringProperty_create $i ot_lep_birth source_mapped
  }
  ot_native_cell_fence $::ot_lep_owner $::ot_lep_band $names
  ot_lep_manifest source_mapped
}
proc ot_lep_births {stage placed} {
  set b [ord::get_db_block];set born {};set old 0
  foreach n [ot_lep_nonmacro_names] {
    set i [$b findInst $n]
    set p [ot_lep_prop $i]
    if {$p eq "NULL"} {
      # New CTS/repair/physical instances receive explicit stage identity.
      # Do not move or reclassify original cells. Legal rows exist ONLY in band.
      odb::dbStringProperty_create $i ot_lep_birth $stage
      lappend born $n
    } else {incr old}
  }
  ot_native_cell_fence_add $::ot_lep_owner $born
  # Also verify every existing cell's owner; no wildcard ownership exemption.
  ot_lep_manifest $stage
  if {$placed} {
    ot_native_cell_fence_check $::ot_lep_owner $::ot_lep_band $stage
    ot_native_cell_band_check $::ot_lep_band $stage
  }
  puts "LEP_BIRTHS stage=$stage existing=$old new=[llength $born]"
}
